#!/usr/bin/env python3
"""Require Full analysis.md to equal the deterministic JSON render."""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

from render_report import render_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    if not args.analysis.is_file() or not args.report.is_file():
        sys.stderr.write("analysis.json 或 analysis.md 不存在\n")
        return 2
    try:
        data = json.loads(args.analysis.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"JSON 解析失败：{exc}\n")
        return 2
    expected = render_report(data)
    actual = args.report.read_text(encoding="utf-8")
    print(f"=== validate_contract: {args.analysis} ↔ {args.report} ===")
    if actual == expected:
        print("✅ [CONTRACT.EXACT] Markdown 与 JSON 的确定性渲染完全一致")
        print("\n结果：一致")
        return 0
    print("🔴 [CONTRACT.EXACT] Markdown 不是当前 JSON 的确定性渲染")
    diff = difflib.unified_diff(
        expected.splitlines(), actual.splitlines(),
        fromfile="expected-from-json", tofile="actual-report", lineterm="",
    )
    for line in list(diff)[:80]:
        print(line)
    print("\n结果：不一致；请重新运行 render_report.py")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
