#!/usr/bin/env python3
"""Cross-check analysis.json ↔ analysis.md for tech-mechanism-analysis.

``analysis.json`` is the source of truth; ``analysis.md`` is its render. The two
must agree. This is the *external* contract gate (alongside ``validate_analysis``
for json-internal and ``validate_report`` for md-internal). It catches drift:

  CONTRACT.ID       every DEBT-*/NUM-* id in json is referenced in the report
  CONTRACT.PHANTOM  every DEBT/NUM id in the report exists in json (no phantoms)
  CONTRACT.COUNT    report frontmatter counts == json tallies
                    (chain_segments / numerical_examples / defects_arch / defects_logic)
  CONTRACT.TYPE     report.mechanism_type == json.mechanism_type
  CONTRACT.LANG     report.languages == json.languages (as sets)
  CONTRACT.COV      report.covered_files == json.covered_files (as sets)
  CONTRACT.TARGET   report.target == json.target

Exits non-zero if any check fails (binary: pass or fail).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


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


def _debt_num_ids(obj: Any) -> tuple[set[str], set[str]]:
    debt: set[str] = set()
    num: set[str] = set()
    if isinstance(obj, dict):
        defects = obj.get("defects")
        if isinstance(defects, list):
            for d in defects:
                if isinstance(d, dict) and isinstance(d.get("id"), str):
                    debt.add(d["id"])
        nums = obj.get("numerical_examples")
        if isinstance(nums, list):
            for n in nums:
                if isinstance(n, dict) and isinstance(n.get("id"), str):
                    num.add(n["id"])
    return debt, num


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-check analysis.json ↔ analysis.md")
    ap.add_argument("analysis", type=Path, help="Path to analysis.json")
    ap.add_argument("report", type=Path, help="Path to analysis.md")
    args = ap.parse_args()
    for p in (args.analysis, args.report):
        if not p.exists():
            sys.stderr.write(f"{p}: 文件不存在\n")
            return 2

    try:
        data = json.loads(args.analysis.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.analysis}: JSON 解析失败：{exc}\n")
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

    json_debt, json_num = _debt_num_ids(data)
    report_ids = set(re.findall(r"DEBT-(?:ARCH|LOGIC)-\d+|NUM-\d+", body))
    report_debt = {i for i in report_ids if i.startswith("DEBT-")}
    report_num = {i for i in report_ids if i.startswith("NUM-")}

    # ---- CONTRACT.ID ----
    missing = sorted((json_debt | json_num) - report_ids)
    check("CONTRACT.ID", not missing,
          f"json {len(json_debt) + len(json_num)} 个 id 均在 report 出现",
          f"report 缺失 json 中的 id：{missing}")

    # ---- CONTRACT.PHANTOM ----
    phantom = sorted(report_ids - (json_debt | json_num))
    check("CONTRACT.PHANTOM", not phantom,
          "report 无悬空 id",
          f"report 出现了 json 没有的 id（悬空）：{phantom}")

    # ---- CONTRACT.COUNT ----
    def count_defects(axis: str) -> int:
        ds = data.get("defects")
        if not isinstance(ds, list):
            return 0
        return sum(1 for d in ds if isinstance(d, dict) and d.get("axis") == axis)

    chain_n = len(data.get("chain_stages") or []) if isinstance(data.get("chain_stages"), list) else 0
    num_n = len(data.get("numerical_examples") or []) if isinstance(data.get("numerical_examples"), list) else 0

    def front_int(key: str) -> Any:
        try:
            return int(meta.get(key))
        except (TypeError, ValueError):
            return "??"

    for front_key, json_val in (
        ("chain_segments", chain_n),
        ("numerical_examples", num_n),
        ("defects_arch", count_defects("architecture")),
        ("defects_logic", count_defects("logic")),
    ):
        fv = front_int(front_key)
        check(f"CONTRACT.COUNT.{front_key}", fv == json_val,
              f"{front_key}: report={fv} = json={json_val}",
              f"{front_key} 不一致：report={fv} vs json={json_val}")

    # ---- CONTRACT.TYPE ----
    r_type = meta.get("mechanism_type")
    j_type = data.get("mechanism_type")
    check("CONTRACT.TYPE", r_type == j_type,
          f"mechanism_type 一致：{j_type}",
          f"mechanism_type 不一致：report={r_type!r} vs json={j_type!r}")

    # ---- CONTRACT.LANG ----
    r_lang = meta.get("languages")
    j_lang = data.get("languages")
    r_set = set(r_lang) if isinstance(r_lang, list) else set()
    j_set = set(j_lang) if isinstance(j_lang, list) else set()
    check("CONTRACT.LANG", r_set == j_set,
          f"languages 一致：{sorted(j_set)}",
          f"languages 不一致：report={sorted(r_set)} vs json={sorted(j_set)}")

    # ---- CONTRACT.COV ----
    r_cov = meta.get("covered_files")
    j_cov = data.get("covered_files")
    rc = set(r_cov) if isinstance(r_cov, list) else set()
    jc = set(j_cov) if isinstance(j_cov, list) else set()
    check("CONTRACT.COV", rc == jc,
          f"covered_files 一致（{len(jc)} 个）",
          f"covered_files 不一致：report-only={sorted(rc - jc)} json-only={sorted(jc - rc)}")

    # ---- CONTRACT.TARGET ----
    r_tgt = meta.get("target")
    j_tgt = data.get("target")
    check("CONTRACT.TARGET", r_tgt == j_tgt,
          f"target 一致：{j_tgt}",
          f"target 不一致：report={r_tgt!r} vs json={j_tgt!r}")

    print(f"=== validate_contract: {args.analysis} ↔ {args.report} ===")
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
