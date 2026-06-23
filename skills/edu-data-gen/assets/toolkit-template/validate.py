#!/usr/bin/env python3
"""Quality-gate runner for an edu-data-gen toolkit.

Implements gates G1-G9 (see references/quality-gates.md). Operates on output/
by merging each content point's multiple files back into the flat entity, then
checking. Writes validation_report.json; exits non-zero if any ERROR gate fails.

Usage:
  python validate.py                  # validate all output
  python validate.py --report custom.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


GRADE_BANDS = {"g1": "g1-g2", "g2": "g1-g2", "g3": "g3-g4", "g4": "g3-g4",
               "g5": "g5-g6", "g6": "g5-g6", "g7": "g7-g9",
               "g8": "g7-g9", "g9": "g7-g9"}


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Load + reconstruct entities from multi-file output
# ---------------------------------------------------------------------------

def load_entities(output_dir: Path, content_list: list) -> dict[str, dict]:
    """Return {content_point_id: merged_flat_entity} merging each cp's group files."""
    entities: dict[str, dict] = {}
    for cp in content_list:
        cid = cp["id"]
        cp_dir = output_dir / cid
        merged: dict = {}
        if cp_dir.exists():
            for f in sorted(cp_dir.glob("*.json")):
                if f.name == "_meta.json":
                    continue
                try:
                    piece = load_json(f)
                except Exception:
                    continue
                if isinstance(piece, dict):
                    merged.update(piece)
        entities[cid] = merged
    return entities


def load_meta(output_dir: Path, cid: str) -> dict:
    p = output_dir / cid / "_meta.json"
    return load_json(p) if p.exists() else {}


# ---------------------------------------------------------------------------
# Lightweight JSON-Schema-ish validator (no external deps)
# ---------------------------------------------------------------------------

_PY_TYPES = {"string": str, "integer": int, "number": (int, float),
             "boolean": bool, "array": list, "object": dict}


def check_schema(entity: dict, schema: dict) -> list[str]:
    """Return list of violation strings (empty = ok). Minimal schema check."""
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
            # bool is subclass of int — guard
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
# Gates
# ---------------------------------------------------------------------------

def g1_schema(entities, schemas, enabled) -> dict:
    failures = {}
    if not enabled:
        return _gate(True, [])
    for cid, ent in entities.items():
        entity_type = ent.get("type", "")
        sch = schemas.get(entity_type, {})
        errs = check_schema(ent, sch) if sch else []
        if errs:
            failures[cid] = errs
    return _gate(not failures, failures)


def g2_coverage(output_dir, content_list, threshold, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    missing = []
    for cp in content_list:
        cid = cp["id"]
        cp_dir = output_dir / cid
        files = [f for f in cp_dir.glob("*.json") if f.name != "_meta.json"] if cp_dir.exists() else []
        if not files:
            missing.append(cid)
    total = len(content_list)
    covered = total - len(missing)
    ratio = covered / total if total else 1.0
    return _gate(ratio + 1e-9 >= threshold and not missing,
                 {"missing": missing, "coverage": round(ratio, 4)})


def g3_question(entities, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    failures = {}
    for cid, ent in entities.items():
        if ent.get("type") != "item" or ent.get("question_type") != "choice":
            continue
        errs = []
        options = ent.get("options") or []
        answer = ent.get("answer")
        distractors = ent.get("distractors") or []
        stem = (ent.get("stem") or "").strip()
        if not stem:
            errs.append("empty stem")
        if len(options) < 4:
            errs.append(f"options<4 ({len(options)})")
        if answer not in options:
            errs.append("answer not in options")
        if len(distractors) < 3:
            errs.append(f"distractors<3 ({len(distractors)})")
        if any(d == answer for d in distractors):
            errs.append("a distractor equals the answer")
        if len(set(map(str, options))) != len(options):
            errs.append("duplicate options")
        if errs:
            failures[cid] = errs
    return _gate(not failures, failures)


def _band_targets(grade, config):
    band = GRADE_BANDS.get(grade, "g7-g9")
    return config.get("difficulty_distribution", {}).get(band, {})


def g4_distribution(entities, config, enabled) -> dict:
    if not enabled:
        return _gate(True, {"skipped": True})
    # count items by (grade_band, bloom)
    counts = defaultdict(Counter)
    for ent in entities.values():
        if ent.get("type") != "item":
            continue
        coord = ent.get("difficulty_coordinate") or {}
        grade = coord.get("grade") or ent.get("grade")
        bloom = coord.get("bloom") or ent.get("bloom")
        if grade and bloom:
            counts[GRADE_BANDS.get(grade, "g7-g9")][bloom] += 1
    tol = config.get("distribution_tolerance_pp", 15) / 100.0
    errors, warns, detail = [], [], {}
    for band, c in counts.items():
        total = sum(c.values()) or 1
        target = config.get("difficulty_distribution", {}).get(band, {})
        actual = {b: round(n / total, 4) for b, n in c.items()}
        detail[band] = {"actual": actual, "target": target}
        for b, tgt in target.items():
            act = actual.get(b, 0.0)
            if tgt > 0 and act == 0:
                errors.append(f"{band}/{b}: target {tgt:.0%} but 0 generated")
            elif abs(act - tgt) > tol:
                warns.append(f"{band}/{b}: |{act:.0%}-{tgt:.0%}|>{tol:.0%}")
    ok = not errors
    return {"severity": "ERROR", "pass": ok, "errors": errors, "warnings": warns, "detail": detail}


def _norm_answer(v):
    return re.sub(r"\s+", "", str(v)).strip().lower()


def g5_accuracy(entities, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    failures = {}
    for cid, ent in entities.items():
        errs = []
        ph = ent.get("phonetic")
        if ph is not None and ph != "":
            if not re.fullmatch(r"/[^/]+/", str(ph).strip()):
                errs.append(f"bad phonetic {ph!r}")
        if ent.get("type") == "item" and ent.get("question_type") == "choice":
            if ent.get("answer") not in (ent.get("options") or []):
                errs.append("answer∉options (accuracy)")
            # explanation final value vs answer
            steps = ent.get("solution_steps") or []
            if steps and ent.get("answer") is not None:
                last = _norm_answer(steps[-1].split("=")[-1].split("→")[-1])
                if last and last != _norm_answer(ent["answer"]) and _norm_answer(ent["answer"]) not in last:
                    errs.append("solution final != answer")
        if errs:
            failures[cid] = errs
    return _gate(not failures, failures)


def g6_age(entities, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    # heuristic: stem length by grade band
    limits = {"g3-g4": 40, "g5-g6": 70, "g7-g9": 140}
    flagged = {}
    for cid, ent in entities.items():
        grade = (ent.get("difficulty_coordinate") or {}).get("grade") or ent.get("grade")
        band = GRADE_BANDS.get(grade, "g7-g9")
        stem = str(ent.get("stem") or ent.get("context_sentence") or "")
        if stem and len(stem) > limits.get(band, 140):
            flagged[cid] = f"length {len(stem)} > band {band} limit"
    return _gate(True, flagged, severity="WARN")


def _shingles(s: str) -> set:
    s = re.sub(r"[^\w\s]", " ", s.lower())
    toks = s.split()
    return set(toks) | {" ".join(toks[i:i+2]) for i in range(len(toks))}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def g7_diversity(entities, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    texts = []
    for cid, ent in entities.items():
        t = ent.get("stem") or ent.get("term") or ent.get("context_sentence")
        if t:
            texts.append((cid, str(t)))
    dups = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            if _jaccard(_shingles(texts[i][1]), _shingles(texts[j][1])) >= 0.85:
                dups.append([texts[i][0], texts[j][0]])
    return _gate(True, {"duplicates": dups}, severity="WARN")


def g8_traceability(output_dir, content_list, enabled) -> dict:
    if not enabled:
        return _gate(True, [])
    failures = []
    for cp in content_list:
        meta = load_meta(output_dir, cp["id"])
        if not meta.get("model_version") or not meta.get("prompt_version"):
            failures.append(cp["id"])
    return _gate(not failures, failures)


def _load_curriculum_kps(ref_path: Path) -> dict:
    """Load curriculum refs from full JSON or compatibility Markdown.

    Returns {kp_id: {"grade": "g5", "domain": "...", "title": "..."}}.
    """
    kps = {}
    if not ref_path.exists():
        return kps
    if ref_path.suffix.lower() == ".json":
        data = load_json(ref_path)
        for grade_data in (data.get("grades") or {}).values():
            for kp in grade_data.get("knowledge_points", []) or []:
                kp_id = kp.get("id")
                if kp_id:
                    kps[kp_id] = {
                        "grade": kp.get("grade"),
                        "domain": kp.get("domain"),
                        "title": kp.get("title"),
                    }
        return kps
    for m in re.finditer(r"`(kp-[a-z]+-(g\d)-[a-z0-9-]+)`", ref_path.read_text(encoding="utf-8")):
        kps[m.group(1)] = {"grade": m.group(2), "domain": None, "title": None}
    return kps


def g9_curriculum(entities, config, tk_root, enabled) -> dict:
    cfg = config.get("curriculum_alignment", {})
    if not enabled or not cfg.get("enabled"):
        return _gate(True, {"enabled": False})
    ref = cfg.get("ref_path", "")
    ref_path = Path(ref) if Path(ref).is_absolute() else tk_root / ref
    kps = _load_curriculum_kps(ref_path)
    off = []
    for cid, ent in entities.items():
        for ref_id in ent.get("knowledge_point_refs", []) or []:
            if ref_id not in kps:
                off.append(f"{cid}: {ref_id} not in curriculum")
            elif ent.get("grade") and kps[ref_id].get("grade") != ent.get("grade"):
                off.append(f"{cid}: {ref_id} grade {kps[ref_id].get('grade')} != {ent.get('grade')}")
    domains = sorted({v.get("domain") for v in kps.values() if v.get("domain")})
    return _gate(True, {"enabled": True, "off_curriculum": off, "kp_count": len(kps), "domain_count": len(domains)}, severity="WARN")


# ---------------------------------------------------------------------------
def _gate(passed: bool, detail, severity="ERROR") -> dict:
    return {"severity": severity, "pass": bool(passed), "detail": detail}


def main() -> int:
    ap = argparse.ArgumentParser(description="edu-data-gen toolkit validator")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--root", default=None)
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    tk_root = Path(args.root).resolve() if args.root else Path.cwd().resolve()
    config = load_json(tk_root / args.config)
    content_list = load_json(tk_root / config["paths"]["content_list"])
    output_dir = tk_root / config["paths"]["output_dir"]
    schemas_dir = tk_root / config["paths"]["schemas_dir"]
    schemas = {}
    if schemas_dir.exists():
        for f in schemas_dir.glob("*.json"):
            schemas[f.stem] = load_json(f)

    entities = load_entities(output_dir, content_list)
    gates_cfg = config.get("gates", {})

    report = {"gates": {
        "G1_schema": g1_schema(entities, schemas, gates_cfg.get("G1_schema", True)),
        "G2_coverage": g2_coverage(output_dir, content_list, config.get("coverage_threshold", 1.0), gates_cfg.get("G2_coverage", True)),
        "G3_question": g3_question(entities, gates_cfg.get("G3_question", True)),
        "G4_distribution": g4_distribution(entities, config, gates_cfg.get("G4_distribution", True)),
        "G5_accuracy": g5_accuracy(entities, gates_cfg.get("G5_accuracy", True)),
        "G6_age": g6_age(entities, gates_cfg.get("G6_age", True)),
        "G7_diversity": g7_diversity(entities, gates_cfg.get("G7_diversity", True)),
        "G8_traceability": g8_traceability(output_dir, content_list, gates_cfg.get("G8_traceability", True)),
        "G9_curriculum": g9_curriculum(entities, config, tk_root, gates_cfg.get("G9_curriculum", False)),
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
