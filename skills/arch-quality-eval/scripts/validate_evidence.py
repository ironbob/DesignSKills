#!/usr/bin/env python3
"""Lightly validate evidence locations in arch-quality-eval findings.json.

This gate checks the part the format validators cannot see:

  E-FILE  every evidence.file exists under --root (or as an absolute path)
  E-LINE  evidence.line, when present, is inside the file
  E-NOTE  code-like tokens from evidence.note are found near evidence.line

The note check is intentionally lightweight. It catches obvious drift or made-up
locations without trying to parse Java/Kotlin/C++.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
STOP_TOKENS = {
    "and", "the", "for", "with", "from", "this", "that",
    "import", "public", "private", "protected", "void", "class",
    "java", "kt", "cpp", "hpp", "src", "main",
}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warns: list[str] = []
        self.passed: list[str] = []

    def err(self, rule: str, msg: str) -> None:
        self.errors.append(f"🔴 [{rule}] {msg}")

    def warn(self, rule: str, msg: str) -> None:
        self.warns.append(f"🟡 [{rule}] {msg}")

    def ok(self, rule: str, msg: str = "") -> None:
        self.passed.append(f"✅ [{rule}]" + (f" {msg}" if msg else ""))


def evidence_path(root: Path, file_value: str) -> Path:
    p = Path(file_value)
    return p if p.is_absolute() else root / p


def note_tokens(note: Any) -> list[str]:
    if not isinstance(note, str):
        return []
    out: list[str] = []
    for token in TOKEN_RE.findall(note):
        low = token.lower()
        if low in STOP_TOKENS:
            continue
        if token not in out:
            out.append(token)
    return out[:8]


def nearby_text(lines: list[str], line_no: int | None) -> str:
    if line_no is None:
        return "\n".join(lines[:80])
    start = max(0, line_no - 4)
    end = min(len(lines), line_no + 3)
    return "\n".join(lines[start:end])


def validate(data: Any, root: Path) -> Report:
    r = Report()
    if not isinstance(data, dict):
        r.err("E-F1", "顶层不是 JSON 对象")
        return r
    findings = data.get("findings")
    if not isinstance(findings, list):
        r.err("E-F1", "findings 须为数组")
        return r
    coverage = data.get("coverage")
    covered_files = coverage.get("scope_files") if isinstance(coverage, dict) else None
    if not isinstance(covered_files, list) or not covered_files:
        r.err("E-COV", "coverage.scope_files 须为非空数组")
        covered_set: set[str] = set()
    else:
        covered_set = {str(item) for item in covered_files}
        for item in sorted(covered_set):
            path = evidence_path(root, item)
            if path.exists() and path.is_file():
                r.ok("E-COV", f"covered file 存在：{item}")
            else:
                r.err("E-COV", f"covered file 不存在：{path}")
    if not findings:
        r.ok("E-F1", "findings 为空，无 finding evidence 需要校验")

    checked = 0
    for f_idx, finding in enumerate(findings):
        if not isinstance(finding, dict):
            r.err("E-F1", f"findings[{f_idx}] 不是对象")
            continue
        fid = finding.get("id", f"findings[{f_idx}]")
        evidence = finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            r.err("E-F1", f"{fid}: evidence 须为非空数组")
            continue

        for e_idx, item in enumerate(evidence):
            ctx = f"{fid}.evidence[{e_idx}]"
            if not isinstance(item, dict):
                r.err("E-F1", f"{ctx}: 不是对象")
                continue
            file_value = item.get("file")
            if not isinstance(file_value, str) or not file_value.strip():
                r.err("E-FILE", f"{ctx}: 缺 evidence.file")
                continue
            if file_value not in covered_set and not Path(file_value).is_absolute():
                r.err("E-SCOPE", f"{ctx}: evidence.file 不在 coverage.scope_files：{file_value}")
                continue
            path = evidence_path(root, file_value)
            if not path.exists() or not path.is_file():
                r.err("E-FILE", f"{ctx}: 文件不存在：{path}")
                continue
            r.ok("E-FILE", f"{ctx}: 文件存在")

            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError as exc:
                r.err("E-FILE", f"{ctx}: 无法读取 {path}: {exc}")
                continue

            raw_line = item.get("line")
            line_no: int | None
            if raw_line in (None, ""):
                line_no = None
                r.ok("E-LINE", f"{ctx}: 类/包级证据，无行号")
            elif isinstance(raw_line, int):
                line_no = raw_line
                if 1 <= line_no <= len(lines):
                    r.ok("E-LINE", f"{ctx}: line {line_no} 在范围内")
                else:
                    r.err("E-LINE", f"{ctx}: line {line_no} 超出文件范围 1..{len(lines)}")
                    continue
            else:
                r.err("E-LINE", f"{ctx}: line 须为整数或省略，实际 {raw_line!r}")
                continue

            tokens = note_tokens(item.get("note"))
            if not tokens:
                r.warn("E-NOTE", f"{ctx}: note 没有可校验的代码关键字")
                continue
            haystack = nearby_text(lines, line_no)
            hits = [token for token in tokens if token in haystack]
            required_hits = 1 if len(tokens) == 1 else min(2, math.ceil(len(tokens) / 2))
            if len(hits) >= required_hits:
                r.ok("E-NOTE", f"{ctx}: note 关键字命中 {hits[:3]}（要求 {required_hits}）")
            elif hits:
                r.warn("E-NOTE", f"{ctx}: note 仅命中 {hits[:3]}，低于要求 {required_hits}；请核对语义")
            else:
                r.err("E-NOTE", f"{ctx}: note 关键字未在证据行附近命中：{tokens[:5]}")
            checked += 1

    principles = data.get("design_principle_coverage")
    if isinstance(principles, dict):
        for principle, item in principles.items():
            evidence = item.get("evidence") if isinstance(item, dict) else None
            if not isinstance(evidence, list):
                r.err("E-P1", f"{principle}: evidence 须为数组")
                continue
            for index, anchor in enumerate(evidence):
                ctx = f"design_principle_coverage.{principle}.evidence[{index}]"
                if not isinstance(anchor, dict) or not isinstance(anchor.get("file"), str):
                    r.err("E-PFILE", f"{ctx}: 缺 file")
                    continue
                file_value = anchor["file"]
                if file_value not in covered_set and not Path(file_value).is_absolute():
                    r.err("E-PSCOPE", f"{ctx}: file 不在 coverage.scope_files：{file_value}")
                    continue
                path = evidence_path(root, file_value)
                if not path.exists() or not path.is_file():
                    r.err("E-PFILE", f"{ctx}: 文件不存在：{path}")
                    continue
                r.ok("E-PFILE", f"{ctx}: 文件存在")
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                line_no = anchor.get("line")
                if line_no is None:
                    r.ok("E-PLINE", f"{ctx}: 文件级证据")
                elif isinstance(line_no, int) and 1 <= line_no <= len(lines):
                    r.ok("E-PLINE", f"{ctx}: line {line_no} 在范围内")
                else:
                    r.err("E-PLINE", f"{ctx}: line {line_no!r} 超出文件范围")
                    continue
                checked += 1

    if checked:
        r.ok("E-F1", f"已校验 {checked} 条 evidence")
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate evidence file/line locations in findings.json")
    ap.add_argument("doc", type=Path, help="Path to findings.json")
    ap.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root for relative evidence.file paths")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    try:
        data = json.loads(args.doc.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.doc}: JSON 解析失败：{exc}\n")
        return 2

    root = args.root.resolve()
    r = validate(data, root)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_evidence: {args.doc} (root={root}) ===")
    for line in r.errors + r.warns + r.passed:
        print(line)
    print(f"\nERROR: {len(r.errors)}  WARNING: {len(r.warns)}  PASSED: {len(r.passed)}")
    print(f"WARNING 通过率: {wp * 100:.0f}%  质量分: {quality * 100:.0f}%")

    if r.errors or wp < 0.80:
        print("\n结果：不合格（有 ERROR 或 WARNING 通过率 <80%）")
        return 1
    print("\n结果：合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
