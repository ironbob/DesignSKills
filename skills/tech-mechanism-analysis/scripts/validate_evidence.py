#!/usr/bin/env python3
"""Validate Full JSON coverage and evidence locations."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterator

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
STOP = {
    "and", "the", "for", "with", "from", "this", "that", "into",
    "class", "public", "private", "return", "value", "line",
}


def resolve(root: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def iter_evidence(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        evidence = value.get("evidence")
        if isinstance(evidence, list):
            for item in evidence:
                if isinstance(item, dict):
                    yield item
        for key, child in value.items():
            if key != "evidence":
                yield from iter_evidence(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_evidence(child)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("doc", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if not args.doc.is_file():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    try:
        data = json.loads(args.doc.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"JSON 解析失败：{exc}\n")
        return 2

    root = args.root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    passed: list[str] = []
    covered_values = data.get("covered_files")
    if not isinstance(covered_values, list):
        covered_values = []
        errors.append("🔴 [COVERED] covered_files 必须为数组")
    covered_paths: dict[Path, str] = {}
    for value in covered_values:
        if not isinstance(value, str):
            errors.append(f"🔴 [COVERED] 非字符串路径：{value!r}")
            continue
        path = resolve(root, value)
        if path in covered_paths:
            errors.append(f"🔴 [COVERED] 重复文件：{value}")
        covered_paths[path] = value
        if not path.is_file():
            errors.append(f"🔴 [COVERED] 覆盖文件不存在或不是文件：{path}")
        else:
            passed.append(f"✅ [COVERED] {value}")

    referenced: set[Path] = set()
    for index, item in enumerate(iter_evidence(data)):
        file_value = item.get("file")
        line = item.get("line")
        note = item.get("note")
        prefix = f"evidence#{index}"
        if not isinstance(file_value, str):
            errors.append(f"🔴 [EVIDENCE.FILE] {prefix}: 缺 file")
            continue
        path = resolve(root, file_value)
        if path not in covered_paths:
            errors.append(f"🔴 [EVIDENCE.SCOPE] {prefix}: {file_value} 不在 covered_files")
            continue
        referenced.add(path)
        if not path.is_file():
            errors.append(f"🔴 [EVIDENCE.FILE] {prefix}: 文件不存在 {path}")
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if not isinstance(line, int) or not 1 <= line <= len(lines):
            errors.append(f"🔴 [EVIDENCE.LINE] {prefix}: line={line!r} 不在 1..{len(lines)}")
            continue
        if not isinstance(note, str) or len(note.strip()) < 4:
            errors.append(f"🔴 [EVIDENCE.NOTE] {prefix}: note 为空或过短")
            continue
        nearby = "\n".join(lines[max(0, line - 4): min(len(lines), line + 3)])
        tokens = [token for token in TOKEN_RE.findall(note) if token.lower() not in STOP][:8]
        if tokens and not any(token in nearby for token in tokens):
            warnings.append(
                f"🟡 [EVIDENCE.NOTE] {prefix}: note 标识符未在附近命中 {tokens[:4]}；请人工确认语义"
            )
        passed.append(f"✅ [EVIDENCE] {file_value}:{line}")

    unreferenced = sorted(
        covered_paths[path] for path in set(covered_paths) - referenced
    )
    if unreferenced:
        errors.append(f"🔴 [COVERED.UNUSED] covered_files 中没有证据引用：{unreferenced}")
    else:
        passed.append("✅ [COVERED.UNUSED] 每个覆盖文件至少有一条证据")

    print(f"=== validate_evidence: {args.doc} (root={root}) ===")
    for line in errors + warnings + passed:
        print(line)
    print(f"\nERROR: {len(errors)}  WARNING: {len(warnings)}  PASSED: {len(passed)}")
    print("\n结果：" + ("不合格" if errors else "合格"))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
