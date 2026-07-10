#!/usr/bin/env python3
"""Cross-check overview.json ↔ overview.md for arch-overview.

``overview.json`` is the source of truth; ``overview.md`` is its render. The two
must agree. This gate catches drift between the two artifacts:

  CONTRACT.GRADE  report.overall_grade == json.overall_grade
  CONTRACT.DIM    report.grade_<key> == json.dimensions[key].grade (4 keys)
  CONTRACT.COV    report.covered_files == json.covered_files (as sets)
  CONTRACT.LANG   report.languages == json.languages (as sets)
  CONTRACT.SCOPE  report.scope_level == json.scope_level
  CONTRACT.ID     every highlight/risk id in json is referenced in the report
  CONTRACT.PHANTOM  every HL-/RISK- id in the report exists in json (no phantoms)

Exits non-zero if any check fails. (No WARNING pass-rate gating here: contract
checks are binary — they pass or they don't.)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from render_mermaid import VIEW_ORDER, render_all

DIM_KEYS = ("layering", "cohesion", "extensibility", "readability")
MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)\n```", re.S | re.I)


def load_meta(text: str, path: Path) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        sys.stderr.write(f"{path}: 未找到 YAML front-matter。\n")
        sys.exit(2)
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"{path}: 需要 PyYAML（pip install pyyaml）。{exc}\n")
        sys.exit(2)
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except Exception as exc:
        sys.stderr.write(f"{path}: front-matter YAML 解析失败：{exc}\n")
        sys.exit(2)
    return data if isinstance(data, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-check overview.json ↔ overview.md")
    ap.add_argument("overview", type=Path, help="Path to overview.json")
    ap.add_argument("report", type=Path, help="Path to overview.md")
    args = ap.parse_args()
    for p in (args.overview, args.report):
        if not p.exists():
            sys.stderr.write(f"{p}: 文件不存在\n")
            return 2

    try:
        data = json.loads(args.overview.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.overview}: JSON 解析失败：{exc}\n")
        return 2
    report_text = args.report.read_text(encoding="utf-8")
    meta = load_meta(report_text, args.report)
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", report_text, count=1, flags=re.S)

    errors: list[str] = []
    passed: list[str] = []

    def check(rule: str, cond: bool, ok_msg: str, err_msg: str) -> None:
        if cond:
            passed.append(f"✅ [{rule}] {ok_msg}")
        else:
            errors.append(f"🔴 [{rule}] {err_msg}")

    # ---- CONTRACT.GRADE ----
    j_grade = data.get("overall_grade")
    r_grade = meta.get("overall_grade")
    check("CONTRACT.GRADE", r_grade == j_grade,
          f"overall_grade 一致：{j_grade}",
          f"overall_grade 不一致：report={r_grade!r} vs json={j_grade!r}")

    # ---- CONTRACT.DIM per-dimension grade ----
    dim_map: dict[str, str] = {}
    for d in data.get("dimensions") or []:
        if isinstance(d, dict):
            dim_map[d.get("key")] = d.get("grade")
    for key in DIM_KEYS:
        r_g = meta.get(f"grade_{key}")
        j_g = dim_map.get(key)
        check(f"CONTRACT.DIM.{key}", r_g == j_g,
              f"{key}: report={r_g} = json={j_g}",
              f"{key} 档位不一致：report grade_{key}={r_g!r} vs json={j_g!r}")

    # ---- CONTRACT.COV covered_files as sets ----
    r_cov = meta.get("covered_files")
    j_cov = data.get("covered_files")
    r_set = set(r_cov) if isinstance(r_cov, list) else set()
    j_set = set(j_cov) if isinstance(j_cov, list) else set()
    check("CONTRACT.COV", r_set == j_set,
          f"covered_files 一致（{len(j_set)} 个）",
          f"covered_files 不一致：report-only={sorted(r_set - j_set)} json-only={sorted(j_set - r_set)}")

    # ---- CONTRACT.LANG languages as sets ----
    r_lang = meta.get("languages")
    j_lang = data.get("languages")
    r_langs = set(r_lang) if isinstance(r_lang, list) else set()
    j_langs = set(j_lang) if isinstance(j_lang, list) else set()
    check("CONTRACT.LANG", r_langs == j_langs,
          f"languages 一致：{sorted(j_langs)}",
          f"languages 不一致：report={sorted(r_langs)} vs json={sorted(j_langs)}")

    # ---- CONTRACT.SCOPE ----
    r_scope = meta.get("scope_level")
    j_scope = data.get("scope_level")
    check("CONTRACT.SCOPE", r_scope == j_scope,
          f"scope_level 一致：{j_scope}",
          f"scope_level 不一致：report={r_scope!r} vs json={j_scope!r}")

    # ---- CONTRACT.ID / PHANTOM highlight & risk ids ----
    json_ids: set[str] = set()
    for label in ("highlights", "risks"):
        for it in data.get(label) or []:
            if isinstance(it, dict) and isinstance(it.get("id"), str):
                json_ids.add(it["id"])
    report_ids = set(re.findall(r"\b(?:HL|RISK)-\d+\b", body))
    missing = sorted(json_ids - report_ids)
    check("CONTRACT.ID", not missing,
          f"json {len(json_ids)} 个 id 均在 report 出现",
          f"report 缺失 json 中的 id：{missing}")
    phantom = sorted(report_ids - json_ids)
    check("CONTRACT.PHANTOM", not phantom,
          "report 无悬空 HL-/RISK- id",
          f"report 出现了 json 没有的 id（悬空）：{phantom}")

    # ---- CONTRACT.MERMAID structured diagrams are the only source ----
    try:
        expected_map = render_all(data)
        expected = [(name, expected_map[name].strip()) for name in VIEW_ORDER if name in expected_map]
        actual = [block.strip() for block in MERMAID_BLOCK_RE.findall(body)]
        check("CONTRACT.MERMAID.COUNT", len(actual) == len(expected),
              f"Mermaid 块数与 applicable 视角一致（{len(expected)}）",
              f"Mermaid 块数不一致：report={len(actual)} vs structured={len(expected)}")
        for index, (name, source) in enumerate(expected):
            got = actual[index] if index < len(actual) else None
            check(f"CONTRACT.MERMAID.{name}", got == source,
                  f"{name} Mermaid 与结构化图一致",
                  f"{name} Mermaid 漂移；请用 render_mermaid.py 重新生成")
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"🔴 [CONTRACT.MERMAID] 结构化 Mermaid 生成失败：{exc}")

    print(f"=== validate_contract: {args.overview} ↔ {args.report} ===")
    for line in errors + passed:
        print(line)
    print(f"\nERROR: {len(errors)}  PASSED: {len(passed)}")
    if errors:
        print("\n结果：不一致（json 与 report 契约漂移）")
        return 1
    print("\n结果：一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
