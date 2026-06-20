#!/usr/bin/env python3
"""Cross-check findings.json ↔ report.md for arch-quality-eval.

``findings.json`` is the source of truth; ``report.md`` is its render. The two
must agree. This gate is the *external* contract gate (alongside
``validate_findings.py`` which checks json internally and ``validate_report.py``
which checks md internally). It catches drift between the two artifacts:

  CONTRACT.ID    every finding id in json is referenced in the report
  CONTRACT.PHANTOM  every FINDING block in the report exists in json (no phantoms)
  CONTRACT.COUNT report frontmatter critical/major/minor == json summary tallies
  CONTRACT.VERDICT   report.verdict == json.summary.verdict
  CONTRACT.CONV  report.conventions_fed == json.conventions_fed
  CONTRACT.LANG  report.language == json.language
  CONTRACT.COV   report.covered_files == json.covered_files (as sets)
  CONTRACT.THRESH report.no_go_threshold == json.no_go_threshold

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
    ap = argparse.ArgumentParser(description="Cross-check findings.json ↔ report.md")
    ap.add_argument("findings", type=Path, help="Path to findings.json")
    ap.add_argument("report", type=Path, help="Path to report.md")
    args = ap.parse_args()
    for p in (args.findings, args.report):
        if not p.exists():
            sys.stderr.write(f"{p}: 文件不存在\n")
            return 2

    try:
        data = json.loads(args.findings.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.findings}: JSON 解析失败：{exc}\n")
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

    findings = data.get("findings") if isinstance(data, dict) else []
    json_ids = {str(f.get("id")) for f in findings
                if isinstance(f, dict) and isinstance(f.get("id"), str)}

    # report FINDING ids referenced (headers + any FINDING- mention)
    report_ids = set(re.findall(r"FINDING-[A-Z]\d+", body))

    # ---- CONTRACT.ID every json id in report ----
    missing = sorted(json_ids - report_ids)
    check("CONTRACT.ID", not missing,
          f"json {len(json_ids)} 个 id 均在 report 出现",
          f"report 缺失 json 中的 finding id：{missing}")

    # ---- CONTRACT.PHANTOM no report id absent from json ----
    phantom = sorted(report_ids - json_ids)
    check("CONTRACT.PHANTOM", not phantom,
          "report 无悬空 finding id",
          f"report 出现了 json 没有的 finding id（悬空）：{phantom}")

    # ---- CONTRACT.COUNT severity counts ----
    summary = data.get("summary") if isinstance(data, dict) else {}
    for sev in ("critical", "major", "minor"):
        front_key = f"{sev}_count"
        front_val = meta.get(front_key)
        json_val = summary.get(sev) if isinstance(summary, dict) else None
        try:
            front_n = int(front_val)
        except (TypeError, ValueError):
            front_n = "??"
        check(
            f"CONTRACT.COUNT.{sev}",
            front_n == json_val,
            f"{sev}: report={front_n} = json={json_val}",
            f"{sev} 计数不一致：report {front_key}={front_val} vs json summary.{sev}={json_val}",
        )

    # ---- CONTRACT.VERDICT ----
    r_verdict = str(meta.get("verdict", "")).strip().lower()
    j_verdict = str(summary.get("verdict", "")).strip().lower() if isinstance(summary, dict) else ""
    check("CONTRACT.VERDICT", r_verdict == j_verdict and r_verdict != "",
          f"verdict 一致：{r_verdict}",
          f"verdict 不一致：report={r_verdict!r} vs json={j_verdict!r}")

    # ---- CONTRACT.CONV ----
    r_conv = meta.get("conventions_fed")
    j_conv = data.get("conventions_fed") if isinstance(data, dict) else None
    check("CONTRACT.CONV", (bool(r_conv) == bool(j_conv)) or r_conv == j_conv,
          f"conventions_fed 一致：{r_conv}",
          f"conventions_fed 不一致：report={r_conv!r} vs json={j_conv!r}")

    # ---- CONTRACT.LANG ----
    r_lang = meta.get("language")
    j_lang = data.get("language") if isinstance(data, dict) else None
    check("CONTRACT.LANG", r_lang == j_lang,
          f"language 一致：{r_lang}",
          f"language 不一致：report={r_lang!r} vs json={j_lang!r}")

    # ---- CONTRACT.THRESH ----
    r_thr = meta.get("no_go_threshold")
    j_thr = data.get("no_go_threshold") if isinstance(data, dict) else None
    check("CONTRACT.THRESH", str(r_thr) == str(j_thr),
          f"no_go_threshold 一致：{j_thr}",
          f"no_go_threshold 不一致：report={r_thr!r} vs json={j_thr!r}")

    # ---- CONTRACT.COV covered_files as sets ----
    r_cov = meta.get("covered_files")
    j_cov = data.get("covered_files") if isinstance(data, dict) else None
    r_set = set(r_cov) if isinstance(r_cov, list) else set()
    j_set = set(j_cov) if isinstance(j_cov, list) else set()
    check("CONTRACT.COV", r_set == j_set,
          f"covered_files 一致（{len(j_set)} 个）",
          f"covered_files 不一致：report-only={sorted(r_set - j_set)} json-only={sorted(j_set - r_set)}")

    print(f"=== validate_contract: {args.findings} ↔ {args.report} ===")
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
