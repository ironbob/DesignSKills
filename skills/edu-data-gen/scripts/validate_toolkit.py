#!/usr/bin/env python3
"""Self-consistency validator for an edu-data-gen toolkit (the 工具包自校验 gate).

Checks that content_list / schema / prompts / scripts / config are mutually
consistent BEFORE user confirmation and sample validation. No LLM calls.

Usage: python validate_toolkit.py <toolkit_dir>
Exit non-zero on any ERROR.
"""

from __future__ import annotations

import argparse
import json
import py_compile
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


VALID_ENTITIES = {"material", "knowledge_point", "explanation", "item"}
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|待定|占位|FIXME|xxx)\b", re.I)
MATERIAL_TARGET_KEYS = ("sentence", "target_sentence", "english_sentence", "term", "concept", "title", "name")

# 年级 → 年级段（对应 config.difficulty_distribution 的键）
GRADE_BAND = {
    "g1": "g1-g2", "g2": "g1-g2",
    "g3": "g3-g4", "g4": "g3-g4",
    "g5": "g5-g6", "g6": "g5-g6",
    "g7": "g7-g9", "g8": "g7-g9", "g9": "g7-g9",
}


def ok(msg):  return ("✓", msg)
def err(msg): return ("✗", msg)
def warn(msg):return ("⚠", msg)


def material_target(seed: dict) -> str:
    if not isinstance(seed, dict):
        return ""
    for key in MATERIAL_TARGET_KEYS:
        val = seed.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def norm_target(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


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
        for key in ["product", "llm", "paths", "file_split", "difficulty_distribution", "gates"]:
            if key not in cfg:
                add(err(f"config missing key: {key}"))
            else:
                add(ok(f"config has {key}"))
        if cfg.get("llm", {}).get("provider") != "claude_code":
            add(err("config.llm.provider must be 'claude_code' (claude_code_direct provider registry name)"))
        else:
            add(ok("config.llm.provider = claude_code"))
        if not cfg.get("llm", {}).get("generate_model"):
            add(err("config.llm.generate_model missing"))
        if cfg.get("paths", {}).get("content_list") is None:
            add(err("config.paths.content_list missing"))

    paths = (cfg or {}).get("paths", {})
    cl_path = root / paths.get("content_list", "content_list")
    outline_dir = root / paths.get("outline_dir", "outline")
    schemas_dir = root / paths.get("schemas_dir", "schema")
    prompts_dir = root / paths.get("prompts_dir", "prompts")

    # --- content_list (per-grade dir or legacy single file) ---
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
            add(ok(f"content_list/: {len(content_list)} content point(s) across {len(cl_files)} grade file(s)"))
        else:
            add(err("content_list/ 无有效内容点（确认有 *.json；*.example.json 会被跳过，需重命名为 *.json）"))
    elif cl_path.is_file():
        try:
            content_list = json.loads(cl_path.read_text(encoding="utf-8"))
            assert isinstance(content_list, list) and content_list
            add(ok(f"content_list.json: {len(content_list)} content point(s) [legacy single-file]"))
        except Exception as e:
            add(err(f"content_list invalid: {e}"))
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
        for f in ("id", "entity", "grade", "bloom"):
            if f not in cp:
                add(err(f"{cid}: missing field '{f}'"))
        # placeholder scan
        blob = json.dumps(cp, ensure_ascii=False)
        if PLACEHOLDER_RE.search(blob):
            add(warn(f"{cid}: contains placeholder (TBD/待定/…)"))
        # referenced prompt template
        tmpl = cp.get("prompt_template", f"{ent}.md")
        if not (prompts_dir / tmpl).exists():
            add(err(f"{cid}: prompt template missing: prompts/{tmpl}"))
        # schema for entity
        if ent and not (schemas_dir / f"{ent}.json").exists():
            add(err(f"{cid}: schema missing: schema/{ent}.json"))

    # --- scripts present + compile ---
    for script in ("generate.py", "validate.py"):
        sp = root / script
        if not sp.exists():
            add(err(f"{script} missing"))
            continue
        try:
            py_compile.compile(str(sp), doraise=True)
            add(ok(f"{script} compiles"))
        except py_compile.PyCompileError as e:
            add(err(f"{script} compile error: {e}"))

    # --- file_split coverage ---
    if cfg:
        fs = cfg.get("file_split", {})
        groups = fs.get("by_field_group", {}) if fs.get("mode", "by_field_group") == "by_field_group" else {}
        for ent in entities_used:
            if fs.get("mode") == "by_field_group" and ent not in groups:
                add(warn(f"entity '{ent}' used but no file_split rule (will single-file)"))
            else:
                add(ok(f"file_split rule for '{ent}'"))

    # --- gates + difficulty ---
    if cfg:
        if not cfg.get("gates"):
            add(warn("config.gates empty (no gates enabled)"))
        dd = cfg.get("difficulty_distribution", {})
        if not dd:
            add(warn("difficulty_distribution empty (G4 will skip)"))
        else:
            add(ok(f"difficulty_distribution covers bands: {sorted(dd)}"))

    # --- outline ↔ content_list 展开自洽 + 计划难度分布 ---
    # group content_list by grade
    cl_ent_by_grade = defaultdict(Counter)       # grade -> Counter(entity -> count)
    item_bloom_by_grade = defaultdict(Counter)   # grade -> Counter(bloom -> count)
    material_by_grade_kp = defaultdict(list)     # (grade, kp_id) -> [content_point, ...]
    for cp in content_list:
        g = cp.get("grade", "?")
        cl_ent_by_grade[g][cp.get("entity", "?")] += 1
        if cp.get("entity") == "item":
            item_bloom_by_grade[g][cp.get("bloom", "?")] += 1
        if cp.get("entity") == "material":
            for kp_id in cp.get("knowledge_point_refs") or []:
                material_by_grade_kp[(g, kp_id)].append(cp)

    outline_by_grade: dict[str, dict] = {}
    if outline_dir.is_dir():
        for f in sorted(outline_dir.glob("*.json")):
            if f.name.endswith(".example.json"):
                continue
            try:
                od = json.loads(f.read_text(encoding="utf-8"))
                g = od.get("grade") or f.stem
                outline_by_grade[g] = od
            except Exception as e:
                add(err(f"outline/{f.name} invalid: {e}"))

    tol = (cfg or {}).get("distribution_tolerance_pp", 15)
    if not outline_by_grade:
        add(warn("无 outline/ 大纲目录——展开自洽检查跳过（旧式骨架工具包可接受；新工具包应有大纲）"))
    for g, od in sorted(outline_by_grade.items()):
        kps = od.get("knowledge_points", []) or []
        exp = Counter()
        for k in kps:
            plan = k.get("generation_plan", {}) or {}
            exp["material"] += int(plan.get("material", 0))
            exp["explanation"] += int(plan.get("explanation", 0))
            for _bloom, n in (plan.get("items_by_bloom") or {}).items():
                exp["item"] += int(n)
        exp["knowledge_point"] = len(kps)
        actual = cl_ent_by_grade.get(g, Counter())
        ents = ("knowledge_point", "material", "explanation", "item")
        mism = [(e, exp[e], actual.get(e, 0)) for e in ents if exp[e] != actual.get(e, 0)]
        if mism:
            detail = ", ".join(f"{e}: 预期{a} 实际{b}" for e, a, b in mism)
            add(err(f"outline/{g}: 展开不自洽（{detail}）—— 重新展开 content_list/{g}.json"))
        else:
            add(ok(f"outline/{g}: 展开自洽（kp={exp['knowledge_point']} material={exp['material']} "
                   f"explanation={exp['explanation']} item={exp['item']}）"))
        # material_seeds: semantic targets for material slots, preventing duplicate free generation.
        subject = od.get("subject") or (cfg or {}).get("product", {}).get("subject")
        for k in kps:
            kid = k.get("id", "<no-kp-id>")
            plan = k.get("generation_plan", {}) or {}
            material_n = int(plan.get("material", 0))
            seeds = plan.get("material_seeds")
            if seeds is None:
                if subject in {"en", "zh"} and material_n >= 5:
                    add(warn(f"outline/{g}/{kid}: material={material_n} 但无 material_seeds；语言类素材建议在大纲阶段列句子/词条数组以降低重复"))
                continue
            if not isinstance(seeds, list):
                add(err(f"outline/{g}/{kid}: material_seeds must be an array"))
                continue
            if len(seeds) != material_n:
                add(err(f"outline/{g}/{kid}: material_seeds 数量 {len(seeds)} != generation_plan.material {material_n}"))
            outline_targets = [material_target(seed) for seed in seeds]
            missing = [i + 1 for i, target in enumerate(outline_targets) if not target]
            if missing:
                add(err(f"outline/{g}/{kid}: material_seeds 第 {missing} 项缺少 target 字段（优先 sentence，其次 term/concept/title/name）"))
            normed = [norm_target(t) for t in outline_targets if t]
            dup = sorted(t for t, c in Counter(normed).items() if c > 1)
            if dup:
                add(err(f"outline/{g}/{kid}: material_seeds 有重复 target: {dup[:5]}"))

            cps = sorted(material_by_grade_kp.get((g, kid), []), key=lambda c: c.get("id", ""))
            cp_targets = [material_target(cp.get("seed") or {}) for cp in cps]
            cp_missing = [cp.get("id", "<no-id>") for cp, target in zip(cps, cp_targets) if not target]
            if cp_missing:
                add(err(f"content_list/{g}: {kid} 展开的 material seed 缺少 target: {cp_missing[:5]}"))
            if outline_targets and cp_targets:
                expected = Counter(norm_target(t) for t in outline_targets if t)
                actual = Counter(norm_target(t) for t in cp_targets if t)
                if expected != actual:
                    add(err(f"content_list/{g}: {kid} material seed 未继承 outline.material_seeds（预期 {sum(expected.values())} 个 target，实际匹配 {sum((expected & actual).values())} 个）"))
                else:
                    add(ok(f"outline/{g}/{kid}: material_seeds 与 content_list 展开一致（{len(seeds)} 个 target）"))
        # 计划难度分布（WARN 预检；硬约束在运行时 G4 门）
        band = GRADE_BAND.get(g)
        target = dd.get(band, {}) if (band and cfg) else {}
        blooms = item_bloom_by_grade.get(g, Counter())
        total = sum(blooms.values())
        if target and total:
            maxdev = max(abs(blooms.get(b, 0) / total * 100 - t * 100) for b, t in target.items())
            if maxdev > tol:
                add(warn(f"outline/{g}: 计划难度分布偏差 {maxdev:.0f}pp > 容差 {tol}pp（段 {band}，运行时 G4 为硬约束）"))
            else:
                add(ok(f"outline/{g}: 计划难度分布达标（最大偏差 {maxdev:.0f}pp）"))

    # --- report ---
    print(f"\n=== 工具包自校验：{root} ===")
    for flag, msg in results:
        print(f"  {flag} {msg}")
    print(f"\n{'PASS' if errors == 0 else 'FAIL'}  ({errors} error(s))")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
