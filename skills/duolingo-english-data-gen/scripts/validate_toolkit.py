#!/usr/bin/env python3
"""Self-consistency validator for a duolingo-english-data-gen toolkit (工具包自校验).

Checks content_list / schema / prompts / scripts / config are mutually consistent
BEFORE user confirmation and sample validation. No LLM calls. Duolingo-specific:
  - outline (sections/units/lessons + duoradio_episodes) ↔ content_list expansion
  - curve_plan validity (counts sum, ends on end_on_easy, allowed_types ⊂ 13 enum)
  - cast refs (character_dialogue_hook + duoradio speakers ∈ cast.json, no trademark)
Usage: python validate_toolkit.py <toolkit_dir>   Exit non-zero on any ERROR.
"""

from __future__ import annotations

import argparse
import json
import py_compile
import re
import sys
from pathlib import Path


VALID_ENTITIES = {"lesson", "duoradio_episode"}
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|待定|占位|FIXME|xxx)\b", re.I)
TRADEMARKED_NAMES = {"duo", "lily", "eddy", "junior", "oscar", "bea", "lin",
                     "vikram", "zari", "lucy", "fofo", "bear", "falstaff", "nera"}
EXERCISE_TYPES = {
    "tap_pairs", "picture_flashcard", "mark_meaning", "select_missing_word",
    "read_and_respond", "arrange_words", "sentence_shuffle", "complete_translation",
    "translate", "type_what_you_hear", "what_do_you_hear", "speak_this_sentence",
    "character_dialogue",
}
VALID_STAGES = {"recognition", "understanding", "constrained_production", "free_production", "end_on_easy"}


def ok(msg):   return ("✓", msg)
def err(msg):  return ("✗", msg)
def warn(msg): return ("⚠", msg)


def _norm(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip().lower()


def _collect_outline_lessons(od: dict):
    """Yield (lesson_node) from outline; also return duoradio count."""
    lessons = []
    for sec in od.get("sections") or []:
        for unit in sec.get("units") or []:
            for les in unit.get("lessons") or []:
                lessons.append(les)
    radios = od.get("duoradio_episodes") or []
    return lessons, radios


def _validate_curve_plan(plan, label, add):
    if not isinstance(plan, dict) or not plan.get("stages"):
        add(err(f"{label}: curve_plan missing stages"))
        return
    stages = plan["stages"]
    total = int(plan.get("total", 0))
    counts_sum = sum(int(s.get("count", 0)) for s in stages)
    if counts_sum != total:
        add(err(f"{label}: stage counts {counts_sum} != total {total}"))
    if not stages or stages[-1].get("stage") != "end_on_easy":
        add(err(f"{label}: last stage must be end_on_easy"))
    for s in stages:
        stg = s.get("stage")
        if stg not in VALID_STAGES:
            add(err(f"{label}: unknown stage {stg!r}"))
        for t in s.get("allowed_types") or []:
            if t not in EXERCISE_TYPES:
                add(err(f"{label}/{stg}: allowed_type {t!r} not a valid exercise type"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="toolkit dir")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    results: list[tuple[str, str]] = []
    errors = 0

    def add(r):
        nonlocal errors
        results.append(r)
        if r[0] == "✗":
            errors += 1

    if not root.is_dir():
        print(f"[validate_toolkit] not a dir: {root}", file=sys.stderr)
        return 2

    # --- config ---
    cfg_path = root / "config.json"
    cfg = None
    if not cfg_path.exists():
        add(err("config.json missing"))
    else:
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            add(ok("config.json parses"))
        except Exception as e:
            add(err(f"config.json invalid JSON: {e}"))
            cfg = None

    if cfg:
        for key in ["product", "llm", "paths", "file_split", "curve_defaults", "gates"]:
            if key not in cfg:
                add(err(f"config missing key: {key}"))
            else:
                add(ok(f"config has {key}"))
        if cfg.get("llm", {}).get("provider") != "claude_code":
            add(err("config.llm.provider must be 'claude_code'"))
        else:
            add(ok("config.llm.provider = claude_code"))
        if not cfg.get("llm", {}).get("generate_model"):
            add(err("config.llm.generate_model missing"))
        if cfg.get("file_split", {}).get("mode") != "single_file":
            add(err("config.file_split.mode must be 'single_file' (one lesson = one file)"))
        else:
            add(ok("config.file_split.mode = single_file"))

    paths = (cfg or {}).get("paths", {})
    cl_path = root / paths.get("content_list", "content_list")
    outline_dir = root / paths.get("outline_dir", "outline")
    schemas_dir = root / paths.get("schemas_dir", "schema")
    prompts_dir = root / paths.get("prompts_dir", "prompts")
    cast_path = root / paths.get("cast_file", "cast.json")

    # --- content_list ---
    content_list = []
    if cl_path.is_dir():
        cl_files = sorted(f for f in cl_path.glob("*.json") if not f.name.endswith(".example.json"))
        for f in cl_files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    content_list.extend(data)
                else:
                    add(err(f"content_list/{f.name}: not a JSON array"))
            except Exception as e:
                add(err(f"content_list/{f.name} invalid: {e}"))
        if content_list:
            add(ok(f"content_list/: {len(content_list)} content point(s) across {len(cl_files)} CEFR file(s)"))
        else:
            add(err("content_list/ 无有效内容点（*.example.json 会被跳过，需重命名为 *.json）"))
    else:
        add(err(f"content_list not found: {cl_path}"))

    entities_used = set()
    for cp in content_list:
        cid = cp.get("id", "<no-id>")
        ent = cp.get("entity")
        if ent not in VALID_ENTITIES:
            add(err(f"{cid}: entity '{ent}' not in {sorted(VALID_ENTITIES)}"))
        else:
            entities_used.add(ent)
        for f in ("id", "entity", "cefr"):
            if f not in cp:
                add(err(f"{cid}: missing field '{f}'"))
        blob = json.dumps(cp, ensure_ascii=False)
        if PLACEHOLDER_RE.search(blob):
            add(warn(f"{cid}: contains placeholder (TBD/待定/…)"))
        tmpl = cp.get("prompt_template", f"{ent}.md")
        if ent and not (prompts_dir / tmpl).exists():
            add(err(f"{cid}: prompt template missing: prompts/{tmpl}"))
        if ent and not (schemas_dir / f"{ent}.json").exists():
            add(err(f"{cid}: schema missing: schema/{ent}.json"))

    # --- scripts compile ---
    for script in ("generate.py", "validate.py", "generate_audio.py", "build_android_assets.py"):
        sp = root / script
        if not sp.exists():
            add(warn(f"{script} missing (optional)" if script in ("generate_audio.py", "build_android_assets.py") else f"{script} missing"))
            continue
        try:
            py_compile.compile(str(sp), doraise=True)
            add(ok(f"{script} compiles"))
        except py_compile.PyCompileError as e:
            add(err(f"{script} compile error: {e}"))

    # --- cast registry ---
    cast_ids = set()
    cast_names = set()
    if cast_path.exists():
        try:
            cdata = json.loads(cast_path.read_text(encoding="utf-8"))
            for c in cdata.get("characters") or []:
                if c.get("id"):
                    cast_ids.add(c["id"])
                if c.get("name"):
                    cast_names.add(_norm(c["name"]))
            add(ok(f"cast.json: {len(cast_ids)} character(s)"))
        except Exception as e:
            add(err(f"cast.json invalid: {e}"))
    else:
        add(warn("cast.json missing (DL-Cast will fail at validate; create it from assets/cast.example.json)"))

    # --- outline ↔ content_list expansion + curve_plan + cast refs ---
    outline_lessons_total = 0
    outline_radios_total = 0
    outline_by_cefr: dict[str, dict] = {}
    if outline_dir.is_dir():
        for f in sorted(outline_dir.glob("*.json")):
            if f.name.endswith(".example.json"):
                continue
            try:
                od = json.loads(f.read_text(encoding="utf-8"))
                cefr = (od.get("cefr") or f.stem).upper()
                outline_by_cefr[cefr] = od
                lessons, radios = _collect_outline_lessons(od)
                outline_lessons_total += len(lessons)
                outline_radios_total += len(radios)
            except Exception as e:
                add(err(f"outline/{f.name} invalid: {e}"))
    else:
        add(warn("无 outline/ 目录——展开自洽检查跳过"))

    cl_lessons = [c for c in content_list if c.get("entity") == "lesson"]
    cl_radios = [c for c in content_list if c.get("entity") == "duoradio_episode"]
    if outline_by_cefr:
        if len(cl_lessons) != outline_lessons_total:
            add(err(f"展开不自洽：outline lessons={outline_lessons_total} 但 content_list lessons={len(cl_lessons)}"))
        else:
            add(ok(f"lesson 展开自洽（{len(cl_lessons)} 节）"))
        if len(cl_radios) != outline_radios_total:
            add(warn(f"duoradio 展开：outline={outline_radios_total} content_list={len(cl_radios)}"))
        else:
            add(ok(f"duoradio 展开自洽（{len(cl_radios)} 集）"))

    # curve_plan per lesson content point (explicit or inheritable from curve_defaults)
    curve_defaults = {str(k).upper(): v for k, v in (cfg or {}).get("curve_defaults", {}).items()} if cfg else {}
    for cp in cl_lessons:
        cefr = (cp.get("cefr") or "").upper()
        plan = cp.get("curve_plan") or (cp.get("seed") or {}).get("curve_plan")
        if not (isinstance(plan, dict) and plan.get("stages")):
            plan = curve_defaults.get(cefr)
            if not (isinstance(plan, dict) and plan.get("stages")):
                add(err(f"{cp['id']}: no curve_plan and no curve_defaults[{cefr}] to inherit"))
                continue
            add(ok(f"{cp['id']}: curve_plan inherited from curve_defaults[{cefr}]"))
        _validate_curve_plan(plan, cp["id"], add)

    # cast refs: character_dialogue_hook.characters + duoradio speakers
    for cp in content_list:
        seed = cp.get("seed") or {}
        refs = list((seed.get("character_dialogue_hook") or {}).get("characters") or [])
        refs += list(seed.get("speakers") or [])
        for r in refs:
            if _norm(r) in TRADEMARKED_NAMES or _norm(r).split("-")[-1] in TRADEMARKED_NAMES:
                add(err(f"{cp['id']}: trademarked character {r!r} (use original cast)"))
            elif cast_ids and r not in cast_ids:
                add(err(f"{cp['id']}: character {r!r} not in cast.json"))

    # --- gates + curve_defaults coverage ---
    if cfg:
        if not cfg.get("gates"):
            add(warn("config.gates empty"))
        cd = cfg.get("curve_defaults", {})
        missing_levels = [lv for lv in ("A1", "A2", "B1", "B2") if lv not in cd]
        if missing_levels:
            add(warn(f"curve_defaults 缺等级: {missing_levels}（DL-Curve 会因无法继承而失败）"))
        else:
            add(ok("curve_defaults 覆盖 A1/A2/B1/B2"))
        # validate each curve_default
        for lv, plan in cd.items():
            _validate_curve_plan(plan, f"curve_defaults[{lv}]", add)

    # --- report ---
    print(f"\n=== 工具包自校验：{root} ===")
    for flag, msg in results:
        print(f"  {flag} {msg}")
    print(f"\n{'PASS' if errors == 0 else 'FAIL'}  ({errors} error(s))")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
