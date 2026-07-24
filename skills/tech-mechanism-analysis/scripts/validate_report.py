#!/usr/bin/env python3
"""Validate Lite or Full Markdown structure and source backlinks."""
from __future__ import annotations

import argparse
from datetime import date
import re
import sys
from pathlib import Path
from typing import Any

FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
LINK_RE = re.compile(r"`(?P<file>[^`\n]+?\.[A-Za-z0-9_+-]+):(?P<line>\d+)`")
STAGE_RE = re.compile(r"^###\s+(?P<id>(?:STAGE-\d+|[A-Za-z][A-Za-z0-9_-]*))\s+·", re.M)
NUM_RE = re.compile(r"^###\s+(NUM-\d+)\s+·", re.M)
OBS_RE = re.compile(r"^###\s+(OBS-\d+)\s+·", re.M)
DEBT_RE = re.compile(r"^###\s+(DEBT-(?:ARCH|LOGIC)-\d+)\s+·", re.M)
BANNED_RE = re.compile(r"\b(?:TODO|TBD|lorem ipsum)\b|待定|占位内容|后续再说", re.I)


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_frontmatter(block: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    pending: str | None = None
    for raw in block.splitlines():
        if not raw.strip():
            continue
        item = re.match(r"^\s+-\s+(.*)$", raw)
        if item and pending:
            result.setdefault(pending, []).append(strip_quotes(item.group(1)))
            continue
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw.rstrip())
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if not value:
            result[key] = []
            pending = key
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            result[key] = [strip_quotes(item) for item in inner.split(",")] if inner else []
            pending = None
        else:
            result[key] = strip_quotes(value)
            pending = None
    return result


def integer(meta: dict[str, Any], key: str) -> int | None:
    try:
        return int(meta.get(key))
    except (TypeError, ValueError):
        return None


def section(body: str, title: str) -> str:
    match = re.search(rf"(?m)^##\s+.*{re.escape(title)}.*$", body)
    if not match:
        return ""
    next_h2 = re.search(r"(?m)^##\s+", body[match.end():])
    end = match.end() + next_h2.start() if next_h2 else len(body)
    return body[match.start():end]


def blocks(body: str, header_re: re.Pattern[str]) -> list[str]:
    matches = list(header_re.finditer(body))
    out: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        next_h2 = re.search(r"(?m)^##\s+", body[match.end():end])
        if next_h2:
            end = match.end() + next_h2.start()
        out.append(body[match.start():end])
    return out


def validate(path: Path, root: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    match = FRONT_RE.match(text)
    if not match:
        return ["🔴 [FRONT] 缺 YAML frontmatter"], []
    meta = parse_frontmatter(match.group(1))
    body = text[match.end():]
    errors: list[str] = []
    passed: list[str] = []

    mode = meta.get("mode")
    if mode not in {"lite", "full"}:
        errors.append("🔴 [FRONT.MODE] mode 必须为 lite 或 full")
    else:
        passed.append(f"✅ [FRONT.MODE] mode={mode}")
    common = ("target", "title", "analyzed_at", "covered_files", "chain_segments", "numerical_examples", "open_questions")
    missing = [key for key in common if meta.get(key) in (None, "", [])]
    if missing:
        errors.append(f"🔴 [FRONT.REQUIRED] 缺字段：{missing}")
    else:
        passed.append("✅ [FRONT.REQUIRED] 通用字段齐全")
    try:
        date.fromisoformat(str(meta.get("analyzed_at")))
        passed.append("✅ [FRONT.DATE] 日期合法")
    except ValueError:
        errors.append("🔴 [FRONT.DATE] analyzed_at 必须为 YYYY-MM-DD")
    if not isinstance(meta.get("title"), str) or len(meta["title"].strip()) < 4:
        errors.append("🔴 [FRONT.TITLE] title 过短")

    covered = meta.get("covered_files")
    covered_set = set(covered) if isinstance(covered, list) else set()
    if not covered_set or len(covered_set) != len(covered or []):
        errors.append("🔴 [FRONT.COVERED] covered_files 必须非空且不重复")
    else:
        for value in covered_set:
            source = Path(value)
            source = source if source.is_absolute() else root / source
            if not source.is_file():
                errors.append(f"🔴 [FRONT.COVERED] 文件不存在：{source}")
        passed.append(f"✅ [FRONT.COVERED] {len(covered_set)} 个覆盖文件")

    required_sections = ["机制概述", "全链路", "数值示例", "已知缺口"]
    if mode == "lite":
        required_sections += ["范围与假设", "设计观察"]
    else:
        required_sections += ["架构设计债", "逻辑设计债", "跨阶段衔接"]
    for name in required_sections:
        if section(body, name):
            passed.append(f"✅ [SECTION] {name}")
        else:
            errors.append(f"🔴 [SECTION] 缺章节：{name}")

    chain_count = integer(meta, "chain_segments")
    chain_blocks = blocks(section(body, "全链路"), STAGE_RE)
    if chain_count is None or chain_count != len(chain_blocks) or chain_count < 2:
        errors.append(f"🔴 [CHAIN.COUNT] frontmatter={chain_count}，实际阶段={len(chain_blocks)}，至少需要 2")
    else:
        passed.append(f"✅ [CHAIN.COUNT] {chain_count} 个阶段")
    stage_markers = ("做了什么", "怎么实现", "设计依据", "交接/最终效果", "证据")
    for index, block in enumerate(chain_blocks):
        missing_markers = [marker for marker in stage_markers if marker not in block]
        if missing_markers:
            errors.append(f"🔴 [CHAIN.BLOCK] 阶段 {index + 1} 缺：{missing_markers}")

    num_count = integer(meta, "numerical_examples")
    num_blocks = blocks(section(body, "数值示例"), NUM_RE)
    if num_count is None or num_count != len(num_blocks):
        errors.append(f"🔴 [NUM.COUNT] frontmatter={num_count}，实际={len(num_blocks)}")
    else:
        passed.append(f"✅ [NUM.COUNT] {len(num_blocks)} 个数值示例")
    for index, block in enumerate(num_blocks):
        required = ("示例数据", "计算步骤", "结果", "忠实性", "证据")
        missing_markers = [marker for marker in required if marker not in block]
        if missing_markers or len(re.findall(r"^\s+\d+\.\s+", block, re.M)) < 2:
            errors.append(f"🔴 [NUM.BLOCK] NUM 块 {index + 1} 缺字段或少于两步计算")

    if mode == "lite":
        observation_count = integer(meta, "design_observations")
        observation_blocks = blocks(section(body, "设计观察"), OBS_RE)
        if observation_count is None or observation_count != len(observation_blocks) or observation_count > 3:
            errors.append(
                f"🔴 [OBS.COUNT] frontmatter={observation_count}，实际={len(observation_blocks)}，最多 3"
            )
        else:
            passed.append(f"✅ [OBS.COUNT] {len(observation_blocks)} 条设计观察")
        required = ("需求来源", "会变难的需求", "为什么难", "演进方向", "代价/影响", "置信度", "证据")
        for index, block in enumerate(observation_blocks):
            missing_markers = [marker for marker in required if marker not in block]
            if missing_markers:
                errors.append(f"🔴 [OBS.BLOCK] OBS 块 {index + 1} 缺：{missing_markers}")
    else:
        expected_arch = integer(meta, "defects_arch")
        expected_logic = integer(meta, "defects_logic")
        debt_blocks = blocks(body, DEBT_RE)
        arch = sum("DEBT-ARCH-" in block.splitlines()[0] for block in debt_blocks)
        logic = sum("DEBT-LOGIC-" in block.splitlines()[0] for block in debt_blocks)
        if expected_arch != arch or expected_logic != logic:
            errors.append(
                f"🔴 [DEBT.COUNT] frontmatter arch/logic={expected_arch}/{expected_logic}，实际={arch}/{logic}"
            )
        else:
            passed.append(f"✅ [DEBT.COUNT] arch/logic={arch}/{logic}")
        required = ("需求来源", "会变难的需求", "为什么难", "演进方向", "代价/影响", "结论置信度", "证据")
        for index, block in enumerate(debt_blocks):
            missing_markers = [marker for marker in required if marker not in block]
            if missing_markers:
                errors.append(f"🔴 [DEBT.BLOCK] DEBT 块 {index + 1} 缺：{missing_markers}")

    links = list(LINK_RE.finditer(body))
    if not links:
        errors.append("🔴 [LINK] 正文没有 file:line 回链")
    for link in links:
        file_value = link.group("file")
        line = int(link.group("line"))
        if file_value not in covered_set:
            errors.append(f"🔴 [LINK.SCOPE] {file_value}:{line} 不在 covered_files")
            continue
        source = Path(file_value)
        source = source if source.is_absolute() else root / source
        if not source.is_file():
            continue
        line_count = len(source.read_text(encoding="utf-8", errors="replace").splitlines())
        if not 1 <= line <= line_count:
            errors.append(f"🔴 [LINK.LINE] {file_value}:{line} 超出 1..{line_count}")
    if links and not any(error.startswith("🔴 [LINK") for error in errors):
        passed.append(f"✅ [LINK] {len(links)} 个回链均可达且在范围内")

    if BANNED_RE.search(body):
        errors.append("🔴 [CONTENT] 正文含占位或待办措辞")
    else:
        passed.append("✅ [CONTENT] 未发现占位措辞")
    open_questions = integer(meta, "open_questions")
    unresolved = len(re.findall(r"⚠\s*未确认", body))
    if open_questions != unresolved:
        errors.append(f"🔴 [GAPS] open_questions={open_questions}，正文未确认={unresolved}")
    else:
        passed.append(f"✅ [GAPS] {unresolved} 个未确认项")
    return errors, passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("doc", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    if not args.doc.is_file():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    errors, passed = validate(args.doc, args.root.resolve())
    print(f"=== validate_report: {args.doc} ===")
    for line in errors + passed:
        print(line)
    print(f"\nERROR: {len(errors)}  PASSED: {len(passed)}")
    print("\n结果：" + ("不合格" if errors else "合格"))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
