#!/usr/bin/env python3
"""Quality-gate runner for a duolingo-english-data-gen toolkit.

Reuses G1/G2/G5-G8 (schema/coverage/accuracy/age/diversity/traceability) and adds
the Duolingo-specific DL-* gates (see references/quality-gates.md). Reads single-file
atomic lessons under output/<cefr>/<id>/lesson.json, iterates exercises[]. Writes
validation_report.json; exits non-zero if any ERROR gate fails.

Usage: python validate.py [--root <toolkit>] [--report <path>]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


CEFR_BANDS = {"A1": "A1-A2", "A2": "A1-A2", "B1": "B1-B2", "B2": "B1-B2"}

# Duolingo trademarked character names — DL-Cast hard-blocks these (legal risk).
TRADEMARKED_NAMES = {
    "duo", "lily", "eddy", "junior", "oscar", "bea", "lin", "vikram",
    "zari", "lucy", "fofo", "bear", "falstaff", "nera",
}

EXERCISE_TYPES = {
    "tap_pairs", "picture_flashcard", "mark_meaning", "select_missing_word",
    "read_and_respond", "arrange_words", "sentence_shuffle", "complete_translation",
    "translate", "type_what_you_hear", "what_do_you_hear", "speak_this_sentence",
    "character_dialogue",
}

# authoritative target field per exercise type (for DL-Lock)
TARGET_FIELD = {
    "translate": "target_sentence", "complete_translation": "target_sentence",
    "arrange_words": "target_sentence", "sentence_shuffle": "target_sentence",
    "type_what_you_hear": "target_sentence", "what_do_you_hear": "target_sentence",
    "speak_this_sentence": "target_sentence",
    "mark_meaning": "source_text", "select_missing_word": "source_text",
    "read_and_respond": "source_text",
}

# per-type required fields (DL-Type branches on exercise_type)
PER_TYPE_REQUIRED = {
    "picture_flashcard": ["options", "answer", "distractors", "image_desc"],
    "mark_meaning": ["options", "answer", "distractors", "source_text"],
    "tap_pairs": ["tokens", "answer", "distractors"],
    "select_missing_word": ["source_text", "options", "answer", "distractors"],
    "read_and_respond": ["source_text", "question", "options", "answer"],
    "arrange_words": ["tokens", "answer", "target_sentence"],
    "sentence_shuffle": ["tokens", "answer", "target_sentence"],
    "complete_translation": ["source_text", "target_sentence", "answer"],
    "translate": ["source_text", "target_sentence", "accepted_variants"],
    "type_what_you_hear": ["audio_ref", "target_sentence", "accepted_variants"],
    "what_do_you_hear": ["audio_ref", "options", "answer"],
    "speak_this_sentence": ["target_sentence", "audio_ref", "scoring_rubric"],
    "character_dialogue": ["turns", "question", "options", "answer"],
}

CHOICE_TYPES = {"picture_flashcard", "mark_meaning", "select_missing_word",
                "read_and_respond", "what_do_you_hear"}
# min distractors per choice type: 4-option types need 3; 3-option types (read_and_respond /
# what_do_you_hear) need 2.
DISTRACTORS_MIN = {"picture_flashcard": 3, "mark_meaning": 3, "select_missing_word": 3,
                   "read_and_respond": 2, "what_do_you_hear": 2}


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _gate(passed, detail, severity="ERROR"):
    return {"severity": severity, "pass": bool(passed), "detail": detail}


# ---------------------------------------------------------------------------
# Load entities (single-file-per-lesson): output/<cefr>/<id>/<entity>.json
# ---------------------------------------------------------------------------

def cp_output_dir(output_dir: Path, cp: dict) -> Path:
    cefr = (cp.get("cefr") or "").upper() or "A1"
    return output_dir / cefr / cp["id"]


def load_entities(output_dir: Path, content_list: list) -> dict[str, dict]:
    """Return {content_point_id: entity_obj} reading the single atomic file per cp."""
    entities: dict[str, dict] = {}
    for cp in content_list:
        cid = cp["id"]
        d = cp_output_dir(output_dir, cp)
        ent: dict = {}
        if d.exists():
            for f in sorted(d.glob("*.json")):
                if f.name == "_meta.json":
                    continue
                try:
                    piece = load_json(f)
                except Exception:
                    continue
                if isinstance(piece, dict):
                    ent.update(piece)
        entities[cid] = ent
    return entities


def load_meta(output_dir: Path, cp: dict) -> dict:
    p = cp_output_dir(output_dir, cp) / "_meta.json"
    return load_json(p) if p.exists() else {}


def load_all_content_list(tk_root: Path, config: dict) -> list:
    cl = tk_root / config["paths"]["content_list"]
    items: list = []
    if cl.is_dir():
        for f in sorted(cl.glob("*.json")):
            if f.name.endswith(".example.json"):
                continue
            data = load_json(f)
            if isinstance(data, list):
                items.extend(data)
    elif cl.is_file():
        items = load_json(cl)
    return items


# ---------------------------------------------------------------------------
# Lightweight schema validator
# ---------------------------------------------------------------------------

_PY_TYPES = {"string": str, "integer": int, "number": (int, float),
             "boolean": bool, "array": list, "object": dict}


def check_schema(entity: dict, schema: dict) -> list[str]:
    errs = []
    if not schema:
        return errs
    for field in schema.get("required", []):
        if field not in entity or entity[field] in (None, "", [], {}):
            errs.append(f"missing required '{field}'")
    for field, spec in schema.get("properties", {}).items():
        if field not in entity:
            continue
        val = entity[field]
        t = spec.get("type")
        if t and t in _PY_TYPES and val is not None:
            if t == "integer" and isinstance(val, bool):
                errs.append(f"'{field}' expected integer, got bool")
            elif t == "number" and isinstance(val, bool):
                errs.append(f"'{field}' expected number, got bool")
            elif not isinstance(val, _PY_TYPES[t]):
                errs.append(f"'{field}' expected {t}, got {type(val).__name__}")
        if spec.get("enum") and val not in spec["enum"]:
            errs.append(f"'{field}'={val!r} not in enum {spec['enum']}")
    return errs


# ---------------------------------------------------------------------------
# Reused gates: G1 schema / G2 coverage / G5 accuracy / G6 age / G7 diversity / G8 traceability
# ---------------------------------------------------------------------------

def g1_schema(entities, schemas, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    failures = {}
    for cid, ent in entities.items():
        etype = ent.get("type", "")
        sch = schemas.get(etype, {})
        errs = check_schema(ent, sch) if sch else []
        if errs:
            failures[cid] = errs
    return _gate(not failures, failures)


def g2_coverage(output_dir, content_list, threshold, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    missing = []
    for cp in content_list:
        d = cp_output_dir(output_dir, cp)
        files = [f for f in d.glob("*.json") if f.name != "_meta.json"] if d.exists() else []
        if not files:
            missing.append(cp["id"])
    total = len(content_list)
    covered = total - len(missing)
    ratio = covered / total if total else 1.0
    return _gate(ratio + 1e-9 >= threshold and not missing,
                 {"missing": missing, "coverage": round(ratio, 4)})


def g5_accuracy(entities, enabled) -> dict:
    """Cheap structural accuracy: choice-type answer ∈ options."""
    if not enabled:
        return _gate(True, [])
    failures = {}
    for cid, ent in entities.items():
        errs = []
        for ex in ent.get("exercises") or []:
            if not isinstance(ex, dict):
                continue
            if ex.get("exercise_type") in CHOICE_TYPES:
                if ex.get("answer") not in (ex.get("options") or []):
                    errs.append(f"{ex.get('id')}: answer∉options")
        if errs:
            failures[cid] = errs
    return _gate(not failures, failures)


def g6_age(entities, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    limits = {"A1": 90, "A2": 110, "B1": 150, "B2": 200}
    flagged = {}
    for cid, ent in entities.items():
        cefr = (ent.get("cefr") or "A1").upper()
        lim = limits.get(cefr, 150)
        bad = []
        for ex in ent.get("exercises") or []:
            ts = str(ex.get("target_sentence") or ex.get("source_text") or "")
            if ts and len(ts) > lim:
                bad.append(f"{ex.get('id')}: len {len(ts)} > {cefr} limit {lim}")
        if bad:
            flagged[cid] = bad
    return _gate(True, flagged, severity="WARN")


def _shingles(s: str) -> set:
    s = re.sub(r"[^\w\s]", " ", s.lower())
    toks = s.split()
    return set(toks) | {" ".join(toks[i:i + 2]) for i in range(len(toks))}


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def g7_diversity(entities, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    texts = []
    for cid, ent in entities.items():
        unit = ent.get("unit_id", "")
        for ex in ent.get("exercises") or []:
            ts = str(ex.get("target_sentence") or "").strip()
            if ts:
                texts.append((cid, unit, ts))
    near = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if texts[i][1] == texts[j][1] and _jaccard(_shingles(texts[i][2]), _shingles(texts[j][2])) >= 0.85:
                near.append([texts[i][0], texts[j][0]])
    return _gate(True, {"near_duplicates_within_unit": near}, severity="WARN")


def g8_traceability(output_dir, content_list, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    failures = []
    for cp in content_list:
        meta = load_meta(output_dir, cp)
        if not meta.get("model_version") or not meta.get("prompt_version"):
            failures.append(cp["id"])
    return _gate(not failures, failures)


# ---------------------------------------------------------------------------
# DL-* gates (Duolingo-specific)
# ---------------------------------------------------------------------------

def _norm(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip().lower()


def resolve_curve_plan(cp: dict, config: dict) -> dict:
    plan = cp.get("curve_plan") or (cp.get("seed") or {}).get("curve_plan")
    if isinstance(plan, dict) and plan.get("stages"):
        return plan
    cefr = (cp.get("cefr") or "").upper()
    defaults = {str(k).upper(): v for k, v in config.get("curve_defaults", {}).items()}
    inh = defaults.get(cefr)
    return inh if isinstance(inh, dict) and inh.get("stages") else {}


def dl_type(entities, enabled) -> dict:
    """Every exercise: valid type ∈ 13 + per-type required fields non-empty + no gamification fields."""
    if not enabled:
        return _gate(True, [])
    failures = {}
    GAMIF = {"xp", "hearts", "streak", "league", "coins", "gems"}
    for cid, ent in entities.items():
        errs = []
        for ex in ent.get("exercises") or []:
            if not isinstance(ex, dict):
                errs.append("non-dict exercise")
                continue
            et = ex.get("exercise_type")
            exid = ex.get("id", "?")
            if et not in EXERCISE_TYPES:
                errs.append(f"{exid}: unknown exercise_type {et!r}")
                continue
            for f in PER_TYPE_REQUIRED.get(et, []):
                v = ex.get(f)
                if v in (None, "", [], {}):
                    errs.append(f"{exid}({et}): missing required '{f}'")
            if et in CHOICE_TYPES:
                opts = ex.get("options") or []
                if ex.get("answer") not in opts:
                    errs.append(f"{exid}({et}): answer∉options")
            unknown_gamif = GAMIF & set(ex.keys())
            if unknown_gamif:
                errs.append(f"{exid}({et}): forbidden runtime field(s) {sorted(unknown_gamif)}")
        if errs:
            failures[cid] = errs
    return _gate(not failures, failures)


def dl_curve(entities, content_list, config, enabled) -> dict:
    """Per lesson: len==total; stages contiguous+ordered; type∈allowed; bloom==stage.bloom; last==end_on_easy."""
    if not enabled:
        return _gate(True, [])
    cp_map = {cp["id"]: cp for cp in content_list}
    failures = {}
    for cid, ent in entities.items():
        if ent.get("type") != "lesson":
            continue
        plan = resolve_curve_plan(cp_map.get(cid, {}), config)
        errs = []
        exs = ent.get("exercises") or []
        if not plan or not plan.get("stages"):
            errs.append("no curve_plan resolvable (check config.curve_defaults or content_list)")
            if errs:
                failures[cid] = errs
            continue
        total = int(plan.get("total", 0))
        stages = plan["stages"]
        if len(exs) != total:
            errs.append(f"exercise count {len(exs)} != curve_plan.total {total}")
        # expected stage sequence (expanded by count)
        expected = []
        for st in stages:
            expected.extend([st] * int(st.get("count", 0)))
        # last stage must be end_on_easy
        if stages and stages[-1].get("stage") != "end_on_easy":
            errs.append("last stage is not end_on_easy")
        # counts sum check
        if sum(int(s.get("count", 0)) for s in stages) != total:
            errs.append("stage counts do not sum to total")
        # per-position checks
        allowed_by_stage = {s.get("stage"): set(s.get("allowed_types") or []) for s in stages}
        bloom_by_stage = {s.get("stage"): s.get("bloom") for s in stages}
        stage_order = [s.get("stage") for s in stages]
        prev_idx = -1
        for i, ex in enumerate(exs):
            if not isinstance(ex, dict):
                continue
            stg = ex.get("stage")
            et = ex.get("exercise_type")
            if stg not in stage_order:
                errs.append(f"ex{i+1}: unknown stage {stg!r}")
                continue
            if stg not in allowed_by_stage.get(stg, set()) and et not in allowed_by_stage.get(stg, set()):
                errs.append(f"ex{i+1}: type {et} not allowed in stage {stg}")
            if bloom_by_stage.get(stg) and ex.get("bloom") != bloom_by_stage.get(stg):
                errs.append(f"ex{i+1}: bloom {ex.get('bloom')} != stage bloom {bloom_by_stage.get(stg)}")
            # ordering: stage index non-decreasing
            idx = stage_order.index(stg)
            if idx < prev_idx:
                errs.append(f"ex{i+1}: stage {stg} out of order (prev {stage_order[prev_idx]})")
            prev_idx = max(prev_idx, idx)
        # last exercise must be end_on_easy
        if exs and isinstance(exs[-1], dict) and exs[-1].get("stage") != "end_on_easy":
            errs.append("last exercise is not end_on_easy")
        if errs:
            failures[cid] = errs
    return _gate(not failures, failures)


def dl_distractors(entities, enabled) -> dict:
    """Choice-type: ≥3 distractors (explicit `distractors` OR implicit wrong `options`),
    ≠answer, distinct. Structural=ERROR. For mark_meaning/read_and_respond/what_do_you_hear
    the wrong options are valid distractors even if not in a separate field."""
    if not enabled:
        return _gate(True, [])
    failures = {}
    warns = {}
    for cid, ent in entities.items():
        e_errs = []
        for ex in ent.get("exercises") or []:
            if not isinstance(ex, dict):
                continue
            et = ex.get("exercise_type")
            if et not in CHOICE_TYPES:
                continue
            exid = ex.get("id", "?")
            ans = ex.get("answer")
            dist = ex.get("distractors") or []
            opts = ex.get("options") or []
            implicit = [o for o in opts if _norm(o) != _norm(ans)]  # wrong options are distractors
            effective = dist if len(dist) >= len(implicit) else implicit
            need = DISTRACTORS_MIN.get(et, 3)
            local = []
            if len(effective) < need:
                local.append(f"{exid}: effective distractors<{need} (explicit {len(dist)} / implicit {len(implicit)})")
            if any(_norm(d) == _norm(ans) for d in effective):
                local.append(f"{exid}: a distractor equals the answer")
            ne = [_norm(d) for d in effective]
            if len(set(ne)) != len(ne):
                local.append(f"{exid}: duplicate distractors")
            if local:
                e_errs.extend(local)
        if e_errs:
            failures[cid] = e_errs
    return _gate(not failures, {"structural_failures": failures, "warnings": warns})


def dl_translation(entities, enabled) -> dict:
    """A1/A2 must have non-null Chinese; B1/B2 English-only (meaning_zh null, hint_zh optional)."""
    if not enabled:
        return _gate(True, [])
    failures = {}
    for cid, ent in entities.items():
        cefr = (ent.get("cefr") or "A1").upper()
        if cefr not in ("A1", "A2", "B1", "B2"):
            continue
        errs = []
        for ex in ent.get("exercises") or []:
            if not isinstance(ex, dict):
                continue
            exid = ex.get("id", "?")
            has_zh = bool((ex.get("hint_zh") or "").strip() or (ex.get("meaning_zh") or "").strip()
                          or any(_norm(t) and _is_chinese(t) for t in (ex.get("accepted_variants") or [])))
            if cefr in ("A1", "A2"):
                if not has_zh:
                    errs.append(f"{exid}: A1/A2 exercise has no Chinese (hint_zh/meaning_zh)")
            else:  # B1/B2
                if (ex.get("meaning_zh") or "").strip():
                    errs.append(f"{exid}: B-level must not have full meaning_zh (immersive)")
        if errs:
            failures[cid] = errs
    return _gate(not failures, failures)


def _is_chinese(s: str) -> bool:
    return bool(re.search(r"[一-鿿]", str(s)))


def dl_lock(entities, content_list, enabled) -> dict:
    """Every locked target sentence appears in some authoritative field (normalized; variants allowed)."""
    if not enabled:
        return _gate(True, [])
    cp_map = {cp["id"]: cp for cp in content_list}
    failures = {}
    for cid, ent in entities.items():
        cp = cp_map.get(cid, {})
        locked = (cp.get("seed") or {}).get("locked_targets") or cp.get("locked_targets") or []
        sentences = [_norm(t.get("text")) for t in locked
                     if isinstance(t, dict) and t.get("kind") == "sentence" and t.get("text")]
        if not sentences:
            continue
        present = set()
        for ex in ent.get("exercises") or []:
            if not isinstance(ex, dict):
                continue
            for f in ("target_sentence", "answer", "source_text"):
                if ex.get(f):
                    present.add(_norm(ex[f]))
            for v in ex.get("accepted_variants") or []:
                present.add(_norm(v))
        vocab = [_norm(t.get("text")) for t in locked if isinstance(t, dict) and t.get("kind") == "vocab"]
        tv = {_norm(v) for v in (ent.get("target_vocab") or [])}
        missing = [s for s in sentences if s and s not in present]
        missing_vocab = [v for v in vocab if v and v not in tv and v not in present]
        if missing or missing_vocab:
            failures[cid] = {"missing_sentences": missing, "missing_vocab": missing_vocab}
    return _gate(not failures, failures)


def dl_cast(entities, cast_registry, enabled) -> dict:
    """Every character_id referenced ∈ cast registry; trademarked names hard-blocked."""
    if not enabled:
        return _gate(True, [])
    known_ids = {c.get("id") for c in cast_registry}
    known_names = {_norm(c.get("name")) for c in cast_registry}
    failures = {}
    for cid, ent in entities.items():
        errs = []
        refs = []
        for ex in ent.get("exercises") or []:
            if isinstance(ex, dict):
                for t in ex.get("turns") or []:
                    if isinstance(t, dict) and t.get("character_id"):
                        refs.append((ex.get("id", "?"), t["character_id"]))
        for t in ent.get("turns") or []:   # duoradio top-level turns
            if isinstance(t, dict) and t.get("character_id"):
                refs.append((cid, t["character_id"]))
        for sp in ent.get("speakers") or []:
            refs.append((cid, sp))
        for exid, char in refs:
            if _norm(char) in TRADEMARKED_NAMES or _norm(char).split("-")[-1] in TRADEMARKED_NAMES:
                errs.append(f"{exid}: trademarked character {char!r} (use original cast)")
            elif char not in known_ids:
                errs.append(f"{exid}: character_id {char!r} not in cast registry")
        if errs:
            failures[cid] = errs
    return _gate(not failures, failures)


def dl_audio(output_dir, content_list, strict, enabled) -> dict:
    """Every spoken string has audio_ref + mp3 exists. WARN default, ERROR if strict or listening-type null."""
    if not enabled:
        return _gate(True, [])
    missing_ref = []     # listening type with null audio_ref → ERROR
    missing_file = []    # audio_ref set but mp3 missing → WARN/ERROR
    for cp in content_list:
        cid = cp["id"]
        d = cp_output_dir(output_dir, cp)
        ent = {}
        if d.exists():
            for f in sorted(d.glob("*.json")):
                if f.name == "_meta.json":
                    continue
                try:
                    p = load_json(f)
                    if isinstance(p, dict):
                        ent.update(p)
                except Exception:
                    pass
        for ex in ent.get("exercises") or []:
            if not isinstance(ex, dict):
                continue
            et = ex.get("exercise_type")
            exid = ex.get("id", "?")
            if et in ("type_what_you_hear", "what_do_you_hear", "speak_this_sentence"):
                if not (ex.get("audio_ref") or "").strip():
                    missing_ref.append(f"{cid}/{exid}: listening/speaking type has no audio_ref")
            for f in ("audio_ref",):
                ref = ex.get(f)
                if ref:
                    mp3 = d / ref
                    if not mp3.exists() or mp3.stat().st_size == 0:
                        missing_file.append(f"{cid}/{exid}: {ref} missing/empty")
            for t in ex.get("turns") or []:
                if isinstance(t, dict) and t.get("audio_ref"):
                    mp3 = d / t["audio_ref"]
                    if not mp3.exists() or mp3.stat().st_size == 0:
                        missing_file.append(f"{cid}/{exid} turn: {t['audio_ref']} missing/empty")
    errors = missing_ref  # null audio_ref on listening is always ERROR
    if strict:
        errors = errors + missing_file
        return _gate(not errors, {"missing_ref": missing_ref, "missing_file": missing_file})
    return _gate(not errors, {"missing_ref (ERROR)": missing_ref, "missing_file (WARN)": missing_file},
                 severity="WARN" if not errors else "ERROR")


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="duolingo-english-data-gen toolkit validator")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--root", default=None)
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    tk_root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    config = load_json(tk_root / args.config)
    content_list = load_all_content_list(tk_root, config)
    output_dir = tk_root / config["paths"]["output_dir"]
    schemas_dir = tk_root / config["paths"]["schemas_dir"]
    schemas = {}
    if schemas_dir.exists():
        for f in schemas_dir.glob("*.json"):
            schemas[f.stem] = load_json(f)

    # cast registry (human-authored, at tk_root or config.paths.cast_file)
    cast_file = tk_root / config.get("paths", {}).get("cast_file", "cast.json")
    cast_registry = []
    if cast_file.exists():
        data = load_json(cast_file)
        cast_registry = data.get("characters", []) if isinstance(data, dict) else []

    entities = load_entities(output_dir, content_list)
    gates_cfg = config.get("gates", {})

    report = {"gates": {
        "G1_schema": g1_schema(entities, schemas, gates_cfg.get("G1_schema", True)),
        "G2_coverage": g2_coverage(output_dir, content_list, config.get("coverage_threshold", 1.0), gates_cfg.get("G2_coverage", True)),
        "G5_accuracy": g5_accuracy(entities, gates_cfg.get("G5_accuracy", True)),
        "G6_age": g6_age(entities, gates_cfg.get("G6_age", True)),
        "G7_diversity": g7_diversity(entities, gates_cfg.get("G7_diversity", True)),
        "G8_traceability": g8_traceability(output_dir, content_list, gates_cfg.get("G8_traceability", True)),
        "DL_Type": dl_type(entities, gates_cfg.get("DL_Type", True)),
        "DL_Curve": dl_curve(entities, content_list, config, gates_cfg.get("DL_Curve", True)),
        "DL_Distractors": dl_distractors(entities, gates_cfg.get("DL_Distractors", True)),
        "DL_Translation": dl_translation(entities, gates_cfg.get("DL_Translation", True)),
        "DL_Lock": dl_lock(entities, content_list, gates_cfg.get("DL_Lock", True)),
        "DL_Cast": dl_cast(entities, cast_registry, gates_cfg.get("DL_Cast", True)),
        "DL_Audio": dl_audio(output_dir, content_list, config.get("dl_audio_strict", False), gates_cfg.get("DL_Audio", True)),
    }}

    errors = sum(1 for g in report["gates"].values() if g["severity"] == "ERROR" and not g["pass"])
    warns = sum(1 for g in report["gates"].values() if g["severity"] == "WARN")
    report["summary"] = {"pass": errors == 0, "errors": errors, "warnings": warns}

    out_report = Path(args.report) if args.report else tk_root / "validation_report.json"
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    for name, g in report["gates"].items():
        flag = "✓" if g["pass"] else ("✗" if g["severity"] == "ERROR" else "⚠")
        print(f"  {flag} {name} [{g['severity']}]")
    print(f"[validate] report → {out_report}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
