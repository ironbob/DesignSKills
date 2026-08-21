#!/usr/bin/env python3
"""Cross-check findings.json v2 and its deterministic report."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from render_report import render


def load_meta(text: str) -> dict:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        return {}
    import yaml  # type: ignore
    value = yaml.safe_load(match.group(1)) or {}
    return value if isinstance(value, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate findings/report v2 contract")
    parser.add_argument("findings", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    if not args.findings.exists() or not args.report.exists():
        sys.stderr.write("findings 或 report 不存在\n")
        return 2
    try:
        data = json.loads(args.findings.read_text(encoding="utf-8"))
        report_text = args.report.read_text(encoding="utf-8")
        meta = load_meta(report_text)
        expected = render(data)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        sys.stderr.write(f"契约读取失败：{exc}\n")
        return 2
    errors: list[str] = []
    passed: list[str] = []

    def check(rule: str, condition: bool, ok: str, error: str) -> None:
        (passed if condition else errors).append(f"{'✅' if condition else '🔴'} [{rule}] {ok if condition else error}")

    check("CONTRACT.RENDER", report_text == expected, "report 是确定性渲染", "report 与 renderer 输出不一致")
    json_ids = {str(item["id"]) for item in data.get("findings", []) if isinstance(item, dict) and item.get("id")}
    body_ids = set(re.findall(r"^####\s+(FINDING-[DC]\d+)\b", report_text, re.M))
    check("CONTRACT.ID", json_ids == body_ids, f"finding id 一致（{len(json_ids)}）",
          f"finding id 漂移：report-only={sorted(body_ids-json_ids)} json-only={sorted(json_ids-body_ids)}")
    summary = data.get("summary", {})
    for severity in ("critical", "major", "minor"):
        check(f"CONTRACT.COUNT.{severity}", meta.get(f"{severity}_count") == summary.get(severity),
              f"{severity} 计数一致", f"{severity} 计数不一致")
    checks = {
        "schema_version": data.get("schema_version"),
        "module": data.get("module"),
        "language": data.get("language"),
        "analyzed_at": data.get("analyzed_at"),
        "conventions_fed": data.get("conventions_fed"),
        "no_go_threshold": data.get("no_go_threshold"),
        "verdict": summary.get("verdict"),
        "confirmed_critical_count": summary.get("confirmed_critical"),
        "coverage_sufficient": (data.get("coverage") or {}).get("sufficient_for_verdict"),
        "cpp_limitation_noted": data.get("cpp_limitation_noted", False),
    }
    for key, value in checks.items():
        report_value = meta.get(key)
        equal = str(report_value) == str(value) if key == "analyzed_at" else report_value == value
        check(f"CONTRACT.META.{key}", equal, f"{key} 一致", f"{key}: report={report_value!r} json={value!r}")
    scope_files = set((data.get("coverage") or {}).get("scope_files", []))
    report_scope = set(meta.get("scope_files", [])) if isinstance(meta.get("scope_files"), list) else set()
    check("CONTRACT.COV", scope_files == report_scope, f"scope_files 一致（{len(scope_files)}）", "scope_files 漂移")
    for key in ("indexed_files", "inspected_files", "semantic_resolved_files"):
        expected_count = len((data.get("coverage") or {}).get(key, []))
        report_key = key[:-1] + "_count"
        check(f"CONTRACT.COV.{key}", meta.get(report_key) == expected_count,
              f"{key} 数量一致", f"{key} 数量漂移")
    convention_ids = {str(item.get("id")) for item in data.get("convention_rules", []) if isinstance(item, dict)}
    check("CONTRACT.CONV", all(rule_id in report_text for rule_id in convention_ids),
          "规约 id 均已渲染", "report 缺规约 id")
    print(f"=== validate_contract: {args.findings} ↔ {args.report} ===")
    for line in errors + passed:
        print(line)
    print(f"\nERROR: {len(errors)}  PASSED: {len(passed)}")
    print("\n结果：一致" if not errors else "\n结果：不一致")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
