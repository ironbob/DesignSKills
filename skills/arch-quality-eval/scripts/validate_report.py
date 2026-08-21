#!/usr/bin/env python3
"""Validate the deterministic human report for findings v2."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_META = (
    "schema_version", "module", "title", "language", "analyzed_at", "scope_files",
    "indexed_file_count", "inspected_file_count", "semantic_resolved_file_count",
    "coverage_sufficient", "conventions_fed", "no_go_threshold", "verdict",
    "critical_count", "major_count", "minor_count", "confirmed_critical_count",
    "cpp_limitation_noted", "open_questions", "status",
)
PRINCIPLE_LABELS = ["复杂度管理", "职责与内聚", "耦合与依赖方向", "信息隐藏与接口边界", "抽象层级一致性", "变化隔离与可演进性"]
FINDING_RE = re.compile(r"^####\s+(FINDING-[DC]\d+)\b(.*)$", re.M)
SEVERITY_RE = re.compile(r"\b(critical|major|minor)\b")
FILE_RE = re.compile(r"[\w/.-]+\.(?:java|kt|h|hpp|hh|cc|cpp|cxx)(?::\d+)?", re.I)
BANNED_RE = re.compile("|".join(map(re.escape, ["TBD", "TODO", "语法错误", "代码风格问题"])))


def load_meta(text: str, path: Path) -> dict:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        raise ValueError(f"{path}: 缺 frontmatter")
    import yaml  # type: ignore
    data = yaml.safe_load(match.group(1)) or {}
    return data if isinstance(data, dict) else {}


def blocks(body: str) -> list[tuple[str, str, str]]:
    matches = list(FINDING_RE.finditer(body))
    result = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        result.append((match.group(1), match.group(2), body[match.start():end]))
    return result


def validate(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    meta = load_meta(text, path)
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)
    errors: list[str] = []
    passed: list[str] = []

    def check(rule: str, condition: bool, ok: str, error: str) -> None:
        (passed if condition else errors).append(f"{'✅' if condition else '🔴'} [{rule}] {ok if condition else error}")

    missing = [key for key in REQUIRED_META if key not in meta or meta.get(key) in (None, "")]
    check("R-F1", not missing, "frontmatter 齐全", f"frontmatter 缺字段：{missing}")
    check("R-G1", meta.get("verdict") in {"go", "no-go", "inconclusive"},
          f"verdict={meta.get('verdict')}", "verdict 须 go/no-go/inconclusive")
    check("R-C1", "设计原则矩阵" in body and all(label in body for label in PRINCIPLE_LABELS),
          "六个设计轴齐全", "设计原则矩阵缺六轴")
    check("R-C2", "架构可理解性" in body, "架构可理解性摘要存在", "缺架构可理解性摘要")
    report_blocks = blocks(body)
    counts = {key: 0 for key in ("critical", "major", "minor")}
    bad_blocks = []
    for fid, tail, block in report_blocks:
        severity = SEVERITY_RE.search(tail)
        if severity:
            counts[severity.group(1)] += 1
        required = (
            severity is not None,
            "confidence=" in tail,
            bool(FILE_RE.search(next((line for line in block.splitlines() if "证据" in line), ""))),
            "违反原则" in block,
            "关联规约" in block,
            "改进方向" in block,
            "优先级" in block,
        )
        if not all(required):
            bad_blocks.append(fid)
    check("R-BLOCK1", not bad_blocks, f"{len(report_blocks)} 个 finding 块契约完整", f"finding 块不完整：{bad_blocks}")
    for severity, count in counts.items():
        try:
            declared = int(meta.get(f"{severity}_count"))
        except (TypeError, ValueError):
            declared = -1
        check("R-COUNT", declared == count, f"{severity}={count}", f"{severity} 正文={count} frontmatter={declared}")
    conventions_fed = meta.get("conventions_fed")
    check("R-CONV1", (conventions_fed is True and "项目规约" in body) or (conventions_fed is False and "项目规约" not in body),
          "规约章节与标志一致", "规约章节与 conventions_fed 不一致")
    check("R-B1", not BANNED_RE.search(body), "未混入语法/lint/TODO 结论", "正文含越界或占位词")
    return errors, passed


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate arch-quality-eval v2 report")
    parser.add_argument("doc", type=Path)
    args = parser.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    try:
        errors, passed = validate(args.doc)
    except Exception as exc:
        sys.stderr.write(f"{args.doc}: {exc}\n")
        return 2
    print(f"=== validate_report: {args.doc} ===")
    for line in errors + passed:
        print(line)
    print(f"\nERROR: {len(errors)}  PASSED: {len(passed)}")
    print("\n结果：合格" if not errors else "\n结果：不合格")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
