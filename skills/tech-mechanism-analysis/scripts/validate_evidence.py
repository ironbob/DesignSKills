#!/usr/bin/env python3
"""Lightly validate evidence locations in tech-mechanism-analysis analysis.json.

Walks EVERY ``evidence[]`` in the contract (chain_stages / numerical_examples /
defects / diagrams) and checks the part format validators cannot see:

  E-FILE  every evidence.file exists under --root (or as an absolute path)
  E-LINE  evidence.line, when present, is inside the file
  E-NOTE  code-like tokens from evidence.note are found near evidence.line

The note check is intentionally lightweight — it catches obvious drift or
made-up locations without trying to parse any language.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
STOP_TOKENS = {
    "and", "the", "for", "with", "from", "this", "that",
    "import", "public", "private", "protected", "void", "class",
    "java", "kt", "cpp", "hpp", "src", "main", "ts", "tsx", "py",
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


def iter_evidence(obj: Any):
    """Yield every evidence item (dict) anywhere under a nested evidence[] list."""
    if isinstance(obj, dict):
        ev = obj.get("evidence")
        if isinstance(ev, list):
            for item in ev:
                if isinstance(item, dict):
                    yield item
        for v in obj.values():
            yield from iter_evidence(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_evidence(v)


def validate(data: Any, root: Path) -> Report:
    r = Report()
    if not isinstance(data, dict):
        r.err("E-F1", "顶层不是 JSON 对象")
        return r

    items = list(iter_evidence(data))
    if not items:
        r.warn("E-F1", "未发现任何 evidence（至少链路段须有证据）")
        return r

    checked = 0
    for idx, item in enumerate(items):
        ctx = f"evidence#{idx}"
        file_value = item.get("file")
        if not isinstance(file_value, str) or not file_value.strip():
            r.err("E-FILE", f"{ctx}: 缺 evidence.file")
            continue
        path = evidence_path(root, file_value)
        if not path.exists() or not path.is_file():
            r.err("E-FILE", f"{ctx}: 文件不存在：{path}")
            continue
        r.ok("E-FILE", f"{ctx}: 文件存在 {file_value}")

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:
            r.err("E-FILE", f"{ctx}: 无法读取 {path}: {exc}")
            continue

        raw_line = item.get("line")
        line_no: int | None
        if raw_line in (None, ""):
            line_no = None
            r.ok("E-LINE", f"{ctx}: 类/模块级证据，无行号")
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
        if hits:
            r.ok("E-NOTE", f"{ctx}: note 关键字命中 {hits[:3]}")
        else:
            r.warn("E-NOTE", f"{ctx}: note 关键字未在证据行附近命中：{tokens[:5]}")
        checked += 1

    if checked:
        r.ok("E-F1", f"已校验 {checked} 条 evidence")
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate evidence file/line locations in analysis.json")
    ap.add_argument("doc", type=Path, help="Path to analysis.json")
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
