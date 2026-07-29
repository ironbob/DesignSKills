#!/usr/bin/env python3
"""Validate Lite or Full Markdown structure and source backlinks."""
from __future__ import annotations

import argparse
from datetime import date
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
LINK_RE = re.compile(r"`(?P<file>[^`\n]+):(?P<line>\d+)`")
STAGE_RE = re.compile(
    r"^###\s+(?P<id>(?:STAGE-\d{2,}|stage-[a-z0-9]+(?:-[a-z0-9]+)*))\s+·",
    re.M,
)
NUM_RE = re.compile(r"^###\s+(NUM-\d{2,})\s+·", re.M)
BOUNDARY_RE = re.compile(r"^###\s+(BOUNDARY-\d{2,})\s+·", re.M)
CASE_RE = re.compile(r"^###\s+(CASE-\d{2,})\s+·", re.M)
ACCEPT_RE = re.compile(r"^###\s+(ACCEPT-\d{2,})\s+·", re.M)
CONFLICT_RE = re.compile(r"^###\s+(CONFLICT-\d{2,})\s+·", re.M)
OBS_RE = re.compile(r"^###\s+(OBS-\d{2,})\s+·", re.M)
DEBT_RE = re.compile(r"^###\s+(DEBT-(?:ARCH|LOGIC)-\d{2,})\s+·", re.M)
SCOPE_REPORT_RE = re.compile(r"^-\s+\*\*SCOPE-\d{2,}\s+·", re.M)
FLOW_REPORT_RE = re.compile(r"^-\s+\*\*FLOW-\d{2,}\s+·.*$", re.M)
FLOW_EDGE_REPORT_RE = re.compile(r"^-\s+\*\*FLOW-EDGE-\d{2,}\s+·.*$", re.M)
PARTICIPANT_REPORT_RE = re.compile(r"^-\s+\*\*PARTICIPANT-\d{2,}\s+·.*$", re.M)
MESSAGE_REPORT_RE = re.compile(r"^-\s+\*\*MESSAGE-\d{2,}\s+·.*$", re.M)
ROLE_REPORT_RE = re.compile(r"^-\s+\*\*ROLE-\d{2,}\s+·.*$", re.M)
ARCH_EDGE_REPORT_RE = re.compile(r"^-\s+\*\*ARCH-EDGE-\d{2,}\s+·.*$", re.M)
IMAGE_RE = re.compile(
    r"!\[[^\]\n]*\]\((?P<path>[^)\n]+\.(?:svg|png))\)",
    re.I,
)
BANNED_RE = re.compile(r"\b(?:TODO|TBD|lorem ipsum)\b|待定|占位内容|后续再说", re.I)
TARGET_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
WHY_RE = re.compile(r"设计依据（(observed|inferred|unknown)）")
UNKNOWN_WHY_RE = re.compile(
    r"无法(?:证明|确认)|代码(?:无法|未能)|(?:未|没有)记录.*(?:意图|原因)|"
    r"cannot (?:prove|confirm)|not documented|unknown",
    re.I,
)
REQ_SOURCE_RE = re.compile(
    r"需求来源[^\n]*`(user|roadmap|issue|code-evolution|hypothetical)`"
)
REQUIRED_OPERATIONAL_BOUNDARIES = {
    "cancellation", "exception", "concurrency", "backpressure",
}
COVERAGE_KIND_MAP = {
    "cancellation": "cancellation",
    "exception": "exception",
    "concurrency": "concurrency",
    "backpressure": "flow-control",
}


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, str) else value
        except json.JSONDecodeError:
            return value[1:-1]
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1]
    return value


def exact_date(value: Any) -> bool:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def repo_relative_path(value: Any) -> bool:
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\\" in value
        or "`" in value
        or any(ord(char) < 32 for char in value)
    ):
        return False
    path = PurePosixPath(value)
    return (
        value == value.strip()
        and not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in value.split("/"))
    )


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
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                inner = value[1:-1].strip()
                parsed = [strip_quotes(item) for item in inner.split(",")] if inner else []
            result[key] = parsed
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
    match = re.search(rf"(?m)^##\s+{re.escape(title)}\s*$", body)
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


def block_links(block: str, covered: set[str]) -> list[re.Match[str]]:
    return [match for match in LINK_RE.finditer(block) if match.group("file") in covered]


def unique_ids(blocks_found: list[str], regex: re.Pattern[str]) -> bool:
    ids = [
        match.groupdict().get("id") or match.group(1)
        for block in blocks_found
        if (match := regex.search(block))
    ]
    return len(ids) == len(blocks_found) == len(set(ids))


def mermaid_blocks(body: str) -> list[str]:
    return re.findall(r"```mermaid\s*\n(.*?)\n```", body, re.S)


def external_diagram_paths(body: str) -> list[str]:
    return [match.group("path") for match in IMAGE_RE.finditer(body)]


def resolve_mmdc_command() -> tuple[list[str], str] | None:
    direct = shutil.which("mmdc")
    if direct:
        return [direct], "mmdc"
    return None


def validate(path: Path, root: Path) -> tuple[list[str], list[str]]:
    root = root.resolve()
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
    common = (
        "target", "title", "analyzed_at", "covered_files", "chain_segments",
        "business_flow_steps", "sequence_messages", "architecture_roles",
        "boundaries", "behavior_cases", "acceptance_cases",
        "behavior_conflicts", "numerical_examples", "open_questions",
    )
    missing = [key for key in common if meta.get(key) in (None, "", [])]
    if missing:
        errors.append(f"🔴 [FRONT.REQUIRED] 缺字段：{missing}")
    else:
        passed.append("✅ [FRONT.REQUIRED] 通用字段齐全")
    if exact_date(meta.get("analyzed_at")):
        passed.append("✅ [FRONT.DATE] 日期合法")
    else:
        errors.append("🔴 [FRONT.DATE] analyzed_at 必须为 YYYY-MM-DD")
    target = meta.get("target")
    if not isinstance(target, str) or not TARGET_RE.fullmatch(target):
        errors.append("🔴 [FRONT.TARGET] target 必须为 kebab-case")
    if not isinstance(meta.get("title"), str) or len(meta["title"].strip()) < 4:
        errors.append("🔴 [FRONT.TITLE] title 过短")
    if meta.get("status") == "draft":
        errors.append("🔴 [FRONT.STATUS] 已交付报告不得固定标记为 draft")

    covered = meta.get("covered_files")
    covered_set = set(covered) if isinstance(covered, list) else set()
    if not covered_set or len(covered_set) != len(covered or []):
        errors.append("🔴 [FRONT.COVERED] covered_files 必须非空且不重复")
    else:
        covered_error_count = len(errors)
        for value in covered_set:
            if not repo_relative_path(value):
                errors.append(f"🔴 [FRONT.COVERED] 必须为规范化的 repo-root 相对路径：{value!r}")
                continue
            source = (root / value).resolve()
            if not source.is_relative_to(root):
                errors.append(f"🔴 [FRONT.COVERED] 路径解析到 repo root 外：{value}")
                continue
            if not source.is_file():
                errors.append(f"🔴 [FRONT.COVERED] 文件不存在：{source}")
        if len(errors) == covered_error_count:
            passed.append(f"✅ [FRONT.COVERED] {len(covered_set)} 个覆盖文件")

    required_sections = [
        "机制概述", "业务流程图", "时序图", "架构角色图", "全链路",
        "必检边界覆盖", "边界清单", "可验证行为用例", "验收用例",
        "多入口/分支行为矛盾", "数值示例", "已知缺口",
    ]
    if mode == "lite":
        required_sections += ["范围与假设", "设计观察"]
    else:
        required_sections += ["架构设计债", "逻辑设计债", "跨阶段衔接"]
    for name in required_sections:
        if section(body, name):
            passed.append(f"✅ [SECTION] {name}")
        else:
            errors.append(f"🔴 [SECTION] 缺章节：{name}")
    if mode == "full":
        overview = section(body, "机制概述")
        if (
            not re.search(r"(?m)^###\s+范围确认\s*$", overview)
            or not SCOPE_REPORT_RE.search(overview)
        ):
            errors.append("🔴 [SCOPE] Full 报告缺范围确认记录")

    diagram_section_names = ["业务流程图", "时序图", "架构角色图"]
    diagram_sections = {
        name: section(body, name) for name in diagram_section_names
    }
    heading_positions = [
        body.find(f"## {name}") for name in [*diagram_section_names, "全链路"]
    ]
    if not all(position >= 0 for position in heading_positions) or heading_positions != sorted(heading_positions):
        errors.append("🔴 [DIAGRAM.ORDER] 三张图必须按业务流程→时序→架构角色排列，并位于全链路之前")
    else:
        passed.append("✅ [DIAGRAM.ORDER] 三张图位于全链路之前且顺序正确")

    diagram_signatures: list[str] = []
    expected_mermaid = {
        "业务流程图": "flowchart LR",
        "时序图": "sequenceDiagram",
        "架构角色图": "flowchart TB",
    }
    for name in diagram_section_names:
        diagram_section = diagram_sections[name]
        mermaids = mermaid_blocks(diagram_section)
        external_paths = external_diagram_paths(diagram_section)
        if len(mermaids) + len(external_paths) != 1:
            errors.append(f"🔴 [DIAGRAM.ARTIFACT] {name} 必须且只能包含一个 Mermaid 或 SVG/PNG 图")
            continue
        if mermaids:
            first_line = mermaids[0].splitlines()[0].strip() if mermaids[0].splitlines() else ""
            if first_line != expected_mermaid[name]:
                errors.append(
                    f"🔴 [DIAGRAM.TYPE] {name} 必须使用 {expected_mermaid[name]}"
                )
            diagram_signatures.append("mermaid:" + mermaids[0].strip())
        else:
            artifact = external_paths[0]
            if not repo_relative_path(artifact):
                errors.append(f"🔴 [DIAGRAM.PATH] {name} 外部图路径非法：{artifact!r}")
                continue
            artifact_path = (root / artifact).resolve()
            if not artifact_path.is_relative_to(root) or not artifact_path.is_file():
                errors.append(f"🔴 [DIAGRAM.PATH] {name} 外部图不存在或位于 repo root 外：{artifact}")
                continue
            diagram_signatures.append("external:" + artifact)
    if len(diagram_signatures) == 3 and len(set(diagram_signatures)) != 3:
        errors.append("🔴 [DIAGRAM.DISTINCT] 三张必检图不能复用完全相同的图内容或文件")

    flow_items = FLOW_REPORT_RE.findall(diagram_sections["业务流程图"])
    flow_count = integer(meta, "business_flow_steps")
    if flow_count is None or flow_count != len(flow_items) or flow_count < 2:
        errors.append(
            f"🔴 [DIAGRAM.FLOW] frontmatter={flow_count}，业务步骤={len(flow_items)}；至少需要 2"
        )
    elif not all(block_links(item, covered_set) for item in flow_items):
        errors.append("🔴 [DIAGRAM.FLOW] 每个 FLOW 步骤都必须有有效 file:line 证据")
    else:
        passed.append(f"✅ [DIAGRAM.FLOW] {flow_count} 个业务步骤均有证据")
    flow_edges = FLOW_EDGE_REPORT_RE.findall(diagram_sections["业务流程图"])
    if len(flow_edges) < 1 or not all(
        block_links(item, covered_set) for item in flow_edges
    ):
        errors.append("🔴 [DIAGRAM.FLOW_EDGES] 至少一条 FLOW-EDGE，且每条边必须有有效证据")
    else:
        passed.append(f"✅ [DIAGRAM.FLOW_EDGES] {len(flow_edges)} 条业务流转边均有证据")

    participant_items = PARTICIPANT_REPORT_RE.findall(diagram_sections["时序图"])
    if len(participant_items) < 2 or not all(
        block_links(item, covered_set) for item in participant_items
    ):
        errors.append("🔴 [DIAGRAM.PARTICIPANTS] 至少两个 PARTICIPANT，且每个参与者必须有有效证据")
    else:
        passed.append(f"✅ [DIAGRAM.PARTICIPANTS] {len(participant_items)} 个时序参与者均有证据")
    message_items = MESSAGE_REPORT_RE.findall(diagram_sections["时序图"])
    message_count = integer(meta, "sequence_messages")
    if message_count is None or message_count != len(message_items) or message_count < 1:
        errors.append(
            f"🔴 [DIAGRAM.SEQUENCE] frontmatter={message_count}，时序消息={len(message_items)}；至少需要 1"
        )
    elif not all(block_links(item, covered_set) for item in message_items):
        errors.append("🔴 [DIAGRAM.SEQUENCE] 每个 MESSAGE 都必须有有效 file:line 证据")
    else:
        passed.append(f"✅ [DIAGRAM.SEQUENCE] {message_count} 条时序消息均有证据")

    role_items = ROLE_REPORT_RE.findall(diagram_sections["架构角色图"])
    role_count = integer(meta, "architecture_roles")
    if role_count is None or role_count != len(role_items) or role_count < 2:
        errors.append(
            f"🔴 [DIAGRAM.ROLES] frontmatter={role_count}，架构角色={len(role_items)}；至少需要 2"
        )
    elif not all(
        "实体类型" in item
        and "职责" in item
        and block_links(item, covered_set)
        for item in role_items
    ):
        errors.append("🔴 [DIAGRAM.ROLES] 每个 ROLE 都必须含实体类型、具体职责和有效证据")
    else:
        passed.append(f"✅ [DIAGRAM.ROLES] {role_count} 个架构角色职责可追溯")
    architecture_edges = ARCH_EDGE_REPORT_RE.findall(
        diagram_sections["架构角色图"]
    )
    if len(architecture_edges) < 1 or not all(
        block_links(item, covered_set) for item in architecture_edges
    ):
        errors.append("🔴 [DIAGRAM.ROLE_EDGES] 至少一条 ARCH-EDGE，且每条关系必须有有效证据")
    else:
        passed.append(f"✅ [DIAGRAM.ROLE_EDGES] {len(architecture_edges)} 条架构关系均有证据")

    chain_count = integer(meta, "chain_segments")
    chain_blocks = blocks(section(body, "全链路"), STAGE_RE)
    valid_chain_count = (
        chain_count is not None
        and chain_count == len(chain_blocks)
        and (
            3 <= chain_count <= 6
            if mode == "lite"
            else chain_count >= 1
        )
    )
    if not valid_chain_count:
        expected = "Lite 需要 3..6" if mode == "lite" else "Full 至少需要 1"
        errors.append(
            f"🔴 [CHAIN.COUNT] frontmatter={chain_count}，"
            f"实际阶段={len(chain_blocks)}；{expected}"
        )
    else:
        passed.append(f"✅ [CHAIN.COUNT] {chain_count} 个阶段")
    if not unique_ids(chain_blocks, STAGE_RE):
        errors.append("🔴 [CHAIN.IDS] 阶段 id 缺失或重复")
    stage_markers = (
        "做了什么", "怎么实现", "设计依据",
        "交接/最终效果", "交接证据", "证据",
    )
    for index, block in enumerate(chain_blocks):
        missing_markers = [marker for marker in stage_markers if marker not in block]
        if missing_markers:
            errors.append(f"🔴 [CHAIN.BLOCK] 阶段 {index + 1} 缺：{missing_markers}")
        implementation_lines = [
            line for line in block.splitlines()
            if re.search(r"\*\*证据\*\*", line)
        ]
        if not implementation_lines or not any(
            block_links(line, covered_set) for line in implementation_lines
        ):
            errors.append(f"🔴 [CHAIN.EVIDENCE] 阶段 {index + 1} 缺带回链的实现证据")
        handoff_lines = [
            line for line in block.splitlines()
            if "交接证据" in line
        ]
        if not handoff_lines or not any(
            block_links(line, covered_set) for line in handoff_lines
        ):
            errors.append(f"🔴 [CHAIN.HANDOFF] 阶段 {index + 1} 缺带回链的交接证据")
        why_match = WHY_RE.search(block)
        if not why_match:
            errors.append(f"🔴 [CHAIN.WHY] 阶段 {index + 1} 缺合法 why_basis")
            continue
        why_basis = why_match.group(1)
        intent_lines = [
            line for line in block.splitlines()
            if "设计意图证据" in line
        ]
        if why_basis == "observed" and (
            not intent_lines
            or not any(block_links(line, covered_set) for line in intent_lines)
        ):
            errors.append(
                f"🔴 [CHAIN.WHY] 阶段 {index + 1} 的 observed "
                "缺带有效回链的设计意图证据"
            )
        why_lines = [
            line for line in block.splitlines()
            if f"设计依据（{why_basis}）" in line
        ]
        if why_basis == "unknown" and (
            not why_lines
            or not any(UNKNOWN_WHY_RE.search(line) for line in why_lines)
        ):
            errors.append(f"🔴 [CHAIN.WHY] 阶段 {index + 1} 的 unknown 未说明代码无法证明意图")

    boundary_count = integer(meta, "boundaries")
    boundary_blocks = blocks(section(body, "边界清单"), BOUNDARY_RE)
    if (
        boundary_count is None
        or boundary_count != len(boundary_blocks)
        or boundary_count < 1
    ):
        errors.append(
            f"🔴 [BOUNDARY.COUNT] frontmatter={boundary_count}，"
            f"实际={len(boundary_blocks)}；至少需要 1"
        )
    else:
        passed.append(f"✅ [BOUNDARY.COUNT] {boundary_count} 个边界")
    if not unique_ids(boundary_blocks, BOUNDARY_RE):
        errors.append("🔴 [BOUNDARY.IDS] BOUNDARY id 缺失或重复")
    boundary_case_refs: dict[str, set[str]] = {}
    boundary_kinds: set[str] = set()
    boundary_kind_by_id: dict[str, str] = {}
    for index, block in enumerate(boundary_blocks):
        required = (
            "类别", "适用性", "条件", "期望契约", "实际行为",
            "处理能力", "验证状态", "关联行为用例", "源码锚点",
        )
        missing_markers = [marker for marker in required if marker not in block]
        if missing_markers:
            errors.append(
                f"🔴 [BOUNDARY.BLOCK] BOUNDARY 块 {index + 1} 缺：{missing_markers}"
            )
        status_match = re.search(
            r"验证状态[^\n]*`(verified|partially-verified|unverified|not-applicable)`",
            block,
        )
        if not status_match:
            errors.append(f"🔴 [BOUNDARY.STATUS] BOUNDARY 块 {index + 1} 状态非法")
        elif status_match.group(1) != "not-applicable" and not block_links(block, covered_set):
            errors.append(
                f"🔴 [BOUNDARY.ANCHOR] BOUNDARY 块 {index + 1} 缺有效源码锚点"
            )
        applicability_match = re.search(
            r"适用性[^\n]*`(applicable|uncertain|not-applicable)`",
            block,
        )
        if not applicability_match:
            errors.append(
                f"🔴 [BOUNDARY.APPLICABILITY] BOUNDARY 块 {index + 1} 适用性非法"
            )
        elif status_match:
            allowed_pairs = {
                ("applicable", "verified"),
                ("applicable", "partially-verified"),
                ("applicable", "unverified"),
                ("uncertain", "unverified"),
                ("not-applicable", "not-applicable"),
            }
            if (
                applicability_match.group(1),
                status_match.group(1),
            ) not in allowed_pairs:
                errors.append(
                    f"🔴 [BOUNDARY.APPLICABILITY] BOUNDARY 块 {index + 1} "
                    "适用性与验证状态不一致"
                )
        handling_match = re.search(
            r"处理能力[^\n]*`(supported|unsupported|unknown|not-applicable)`",
            block,
        )
        if not handling_match:
            errors.append(
                f"🔴 [BOUNDARY.HANDLING] BOUNDARY 块 {index + 1} 处理能力非法"
            )
        elif applicability_match:
            allowed_handling_pairs = {
                ("applicable", "supported"),
                ("applicable", "unsupported"),
                ("applicable", "unknown"),
                ("uncertain", "unknown"),
                ("not-applicable", "not-applicable"),
            }
            if (
                applicability_match.group(1),
                handling_match.group(1),
            ) not in allowed_handling_pairs:
                errors.append(
                    f"🔴 [BOUNDARY.HANDLING] BOUNDARY 块 {index + 1} "
                    "适用性与处理能力不一致"
                )
        kind_match = re.search(
            r"类别[^\n]*`([a-z]+(?:-[a-z]+)*)`",
            block,
        )
        if kind_match:
            boundary_kinds.add(kind_match.group(1))
        match_id = BOUNDARY_RE.search(block)
        if match_id:
            if kind_match:
                boundary_kind_by_id[match_id.group(1)] = kind_match.group(1)
            boundary_case_refs[match_id.group(1)] = set(
                re.findall(r"`(CASE-\d{2,})`", block)
            )
    missing_operational = sorted(
        kind
        for kind in COVERAGE_KIND_MAP.values()
        if kind not in boundary_kinds
    )
    if missing_operational:
        errors.append(
            f"🔴 [BOUNDARY.OPERATIONAL_COVERAGE] 缺强制边界类别："
            f"{missing_operational}"
        )
    else:
        passed.append("✅ [BOUNDARY.OPERATIONAL_COVERAGE] 取消、异常、并发、背压均有结论")
    coverage = section(body, "必检边界覆盖")
    for kind in sorted(REQUIRED_OPERATIONAL_BOUNDARIES):
        line_match = re.search(
            rf"(?m)^-\s+\*\*{re.escape(kind)}\*\*：(.*)$",
            coverage,
        )
        refs = (
            set(re.findall(r"`(BOUNDARY-\d{2,})`", line_match.group(1)))
            if line_match else set()
        )
        if (
            not refs
            or any(
                boundary_kind_by_id.get(boundary_id)
                != COVERAGE_KIND_MAP[kind]
                for boundary_id in refs
            )
        ):
            errors.append(
                f"🔴 [BOUNDARY.COVERAGE_MAP] {kind} 必须独立引用 "
                f"kind={COVERAGE_KIND_MAP[kind]} 的 BOUNDARY"
            )
        else:
            passed.append(
                f"✅ [BOUNDARY.COVERAGE_MAP] {kind} → {sorted(refs)}"
            )

    case_count = integer(meta, "behavior_cases")
    case_blocks = blocks(section(body, "可验证行为用例"), CASE_RE)
    if case_count is None or case_count != len(case_blocks) or case_count < 1:
        errors.append(
            f"🔴 [CASE.COUNT] frontmatter={case_count}，"
            f"实际={len(case_blocks)}；至少需要 1"
        )
    else:
        passed.append(f"✅ [CASE.COUNT] {case_count} 个行为用例")
    if not unique_ids(case_blocks, CASE_RE):
        errors.append("🔴 [CASE.IDS] CASE id 缺失或重复")
    case_boundary_refs: dict[str, set[str]] = {}
    case_acceptance_refs: dict[str, set[str]] = {}
    case_semantics: dict[str, str] = {}
    for index, block in enumerate(case_blocks):
        required = (
            "关联边界", "入口", "分支路径", "语义条件键",
            "前置条件", "输入", "动作",
            "期望可观察行为", "实际观察行为", "验证", "源码锚点",
            "对应验收用例",
        )
        missing_markers = [marker for marker in required if marker not in block]
        if missing_markers:
            errors.append(f"🔴 [CASE.BLOCK] CASE 块 {index + 1} 缺：{missing_markers}")
        if not re.search(
            r"\*\*验证\*\*[^\n]*`(verified|static-only|not-run)`\s*/\s*"
            r"`(test|command|equivalent-evaluation|inspection|not-run)`",
            block,
        ):
            errors.append(f"🔴 [CASE.VERIFICATION] CASE 块 {index + 1} 验证模式非法")
        if not block_links(block, covered_set):
            errors.append(f"🔴 [CASE.ANCHOR] CASE 块 {index + 1} 缺有效源码锚点")
        match_id = CASE_RE.search(block)
        if match_id:
            case_id = match_id.group(1)
            semantic_match = re.search(
                r"语义条件键[^\n]*`([a-z0-9]+(?:-[a-z0-9]+)*)`",
                block,
            )
            if not semantic_match:
                errors.append(
                    f"🔴 [CASE.SEMANTIC] {case_id} 缺合法 semantic_key"
                )
            else:
                case_semantics[case_id] = semantic_match.group(1)
            case_boundary_refs[case_id] = set(
                re.findall(r"`(BOUNDARY-\d{2,})`", block)
            )
            case_acceptance_refs[case_id] = set(
                re.findall(r"`(ACCEPT-\d{2,})`", block)
            )
            if not case_acceptance_refs[case_id]:
                errors.append(f"🔴 [CASE.ACCEPT] {case_id} 没有对应验收用例")

    acceptance_count = integer(meta, "acceptance_cases")
    acceptance_blocks = blocks(section(body, "验收用例"), ACCEPT_RE)
    if (
        acceptance_count is None
        or acceptance_count != len(acceptance_blocks)
        or acceptance_count < 1
    ):
        errors.append(
            f"🔴 [ACCEPT.COUNT] frontmatter={acceptance_count}，"
            f"实际={len(acceptance_blocks)}；至少需要 1"
        )
    else:
        passed.append(f"✅ [ACCEPT.COUNT] {acceptance_count} 个验收用例")
    if not unique_ids(acceptance_blocks, ACCEPT_RE):
        errors.append("🔴 [ACCEPT.IDS] ACCEPT id 缺失或重复")
    acceptance_case_refs: dict[str, set[str]] = {}
    for index, block in enumerate(acceptance_blocks):
        required = (
            "关联行为用例", "Given", "When", "Then", "验证级别", "源码锚点",
        )
        missing_markers = [marker for marker in required if marker not in block]
        if missing_markers:
            errors.append(
                f"🔴 [ACCEPT.BLOCK] ACCEPT 块 {index + 1} 缺：{missing_markers}"
            )
        if not re.search(r"验证级别[^\n]*`(automated|manual)`", block):
            errors.append(f"🔴 [ACCEPT.LEVEL] ACCEPT 块 {index + 1} 验证级别非法")
        if not block_links(block, covered_set):
            errors.append(f"🔴 [ACCEPT.ANCHOR] ACCEPT 块 {index + 1} 缺有效源码锚点")
        match_id = ACCEPT_RE.search(block)
        if match_id:
            acceptance_case_refs[match_id.group(1)] = set(
                re.findall(r"`(CASE-\d{2,})`", block)
            )

    for boundary_id, refs in boundary_case_refs.items():
        if any(boundary_id not in case_boundary_refs.get(case_id, set()) for case_id in refs):
            errors.append(f"🔴 [TRACE.BOUNDARY] {boundary_id} 与 CASE 引用不一致")
    for case_id, refs in case_boundary_refs.items():
        if any(case_id not in boundary_case_refs.get(boundary_id, set()) for boundary_id in refs):
            errors.append(f"🔴 [TRACE.CASE] {case_id} 与 BOUNDARY 引用不一致")
    for case_id, refs in case_acceptance_refs.items():
        if any(case_id not in acceptance_case_refs.get(accept_id, set()) for accept_id in refs):
            errors.append(f"🔴 [TRACE.CASE] {case_id} 与 ACCEPT 引用不一致")
    for accept_id, refs in acceptance_case_refs.items():
        if not refs or any(
            accept_id not in case_acceptance_refs.get(case_id, set())
            for case_id in refs
        ):
            errors.append(f"🔴 [TRACE.ACCEPT] {accept_id} 与 CASE 引用不一致")

    conflict_count = integer(meta, "behavior_conflicts")
    conflict_blocks = blocks(
        section(body, "多入口/分支行为矛盾"), CONFLICT_RE
    )
    if conflict_count is None or conflict_count != len(conflict_blocks):
        errors.append(
            f"🔴 [CONFLICT.COUNT] frontmatter={conflict_count}，"
            f"实际={len(conflict_blocks)}"
        )
    else:
        passed.append(f"✅ [CONFLICT.COUNT] {conflict_count} 条矛盾记录")
    if not unique_ids(conflict_blocks, CONFLICT_RE):
        errors.append("🔴 [CONFLICT.IDS] CONFLICT id 缺失或重复")
    for index, block in enumerate(conflict_blocks):
        required = (
            "对比行为用例", "比较维度", "矛盾", "影响",
            "意图状态", "收敛方向", "源码锚点",
        )
        missing_markers = [marker for marker in required if marker not in block]
        if missing_markers:
            errors.append(
                f"🔴 [CONFLICT.BLOCK] CONFLICT 块 {index + 1} 缺：{missing_markers}"
            )
        if len(set(re.findall(r"`(CASE-\d{2,})`", block))) < 2:
            errors.append(f"🔴 [CONFLICT.CASES] CONFLICT 块 {index + 1} 少于两个 CASE")
        conflict_case_ids = set(re.findall(r"`(CASE-\d{2,})`", block))
        semantics = {
            case_semantics[case_id]
            for case_id in conflict_case_ids
            if case_id in case_semantics
        }
        if (
            len(conflict_case_ids) >= 2
            and (
                len(semantics) != 1
                or any(case_id not in case_semantics for case_id in conflict_case_ids)
            )
        ):
            errors.append(
                f"🔴 [CONFLICT.SEMANTIC] CONFLICT 块 {index + 1} "
                "引用的 CASE 必须共享同一 semantic_key"
            )
        if not re.search(
            r"意图状态[^\n]*`(intentional|unintentional|unknown)`",
            block,
        ):
            errors.append(f"🔴 [CONFLICT.INTENT] CONFLICT 块 {index + 1} 意图状态非法")
        if not block_links(block, covered_set):
            errors.append(f"🔴 [CONFLICT.ANCHOR] CONFLICT 块 {index + 1} 缺有效源码锚点")
    if conflict_count == 0 and "未识别到多入口/分支行为矛盾" not in section(
        body, "多入口/分支行为矛盾"
    ):
        errors.append("🔴 [CONFLICT.EMPTY] 无矛盾记录时必须明确说明未识别到")

    num_count = integer(meta, "numerical_examples")
    num_blocks = blocks(section(body, "数值示例"), NUM_RE)
    if num_count is None or num_count != len(num_blocks):
        errors.append(f"🔴 [NUM.COUNT] frontmatter={num_count}，实际={len(num_blocks)}")
    else:
        passed.append(f"✅ [NUM.COUNT] {len(num_blocks)} 个数值示例")
    if not unique_ids(num_blocks, NUM_RE):
        errors.append("🔴 [NUM.IDS] NUM id 缺失或重复")
    for index, block in enumerate(num_blocks):
        required = ("示例数据", "计算步骤", "结果", "忠实性", "证据")
        missing_markers = [marker for marker in required if marker not in block]
        if missing_markers or len(re.findall(r"^\s+\d+\.\s+", block, re.M)) < 2:
            errors.append(f"🔴 [NUM.BLOCK] NUM 块 {index + 1} 缺字段或少于两步计算")
        if not block_links(block, covered_set):
            errors.append(f"🔴 [NUM.EVIDENCE] NUM 块 {index + 1} 缺有效 file:line 回链")
    if num_count == 0 and "未识别到需要工作示例的核心数值操作" not in section(body, "数值示例"):
        errors.append("🔴 [NUM.EMPTY] 无数值示例时必须明确说明未识别到核心数值操作")

    if mode == "lite":
        observation_count = integer(meta, "design_observations")
        observation_blocks = blocks(section(body, "设计观察"), OBS_RE)
        if observation_count is None or observation_count != len(observation_blocks) or observation_count > 3:
            errors.append(
                f"🔴 [OBS.COUNT] frontmatter={observation_count}，实际={len(observation_blocks)}，最多 3"
            )
        else:
            passed.append(f"✅ [OBS.COUNT] {len(observation_blocks)} 条设计观察")
        if not unique_ids(observation_blocks, OBS_RE):
            errors.append("🔴 [OBS.IDS] OBS id 缺失或重复")
        required = ("需求来源", "会变难的需求", "为什么难", "演进方向", "代价/影响", "置信度", "证据")
        for index, block in enumerate(observation_blocks):
            missing_markers = [marker for marker in required if marker not in block]
            if missing_markers:
                errors.append(f"🔴 [OBS.BLOCK] OBS 块 {index + 1} 缺：{missing_markers}")
            if not REQ_SOURCE_RE.search(block):
                errors.append(f"🔴 [OBS.SOURCE] OBS 块 {index + 1} 的需求来源非法")
            if not block_links(block, covered_set):
                errors.append(f"🔴 [OBS.EVIDENCE] OBS 块 {index + 1} 缺有效 file:line 回链")
        if observation_count == 0 and "未识别到高相关设计观察" not in section(body, "设计观察"):
            errors.append("🔴 [OBS.EMPTY] 无设计观察时必须明确说明未识别到高相关观察")
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
        if not unique_ids(debt_blocks, DEBT_RE):
            errors.append("🔴 [DEBT.IDS] DEBT id 缺失或重复")
        required = (
            "需求来源", "会变难的需求", "为什么难", "演进方向",
            "代价/影响", "量化范围", "结论置信度", "证据",
        )
        for index, block in enumerate(debt_blocks):
            missing_markers = [marker for marker in required if marker not in block]
            if missing_markers:
                errors.append(f"🔴 [DEBT.BLOCK] DEBT 块 {index + 1} 缺：{missing_markers}")
            if not REQ_SOURCE_RE.search(block):
                errors.append(f"🔴 [DEBT.SOURCE] DEBT 块 {index + 1} 的需求来源非法")
            if not block_links(block, covered_set):
                errors.append(f"🔴 [DEBT.EVIDENCE] DEBT 块 {index + 1} 缺有效 file:line 回链")

    links = block_links(body, covered_set)
    if not links:
        errors.append("🔴 [LINK] 正文没有 file:line 回链")
    for link in links:
        file_value = link.group("file")
        line = int(link.group("line"))
        source = (root / file_value).resolve()
        if not source.is_relative_to(root):
            errors.append(f"🔴 [LINK.SCOPE] {file_value}:{line} 解析到 repo root 外")
            continue
        if not source.is_file():
            continue
        line_count = len(source.read_text(encoding="utf-8", errors="replace").splitlines())
        if not 1 <= line <= line_count:
            errors.append(f"🔴 [LINK.LINE] {file_value}:{line} 超出 1..{line_count}")
    if links and not any(error.startswith("🔴 [LINK") for error in errors):
        passed.append(f"✅ [LINK] {len(links)} 个回链均可达且在范围内")

    diagrams = mermaid_blocks(body)
    mmdc = resolve_mmdc_command()
    mermaid_structure_ok = True
    rendered_count = 0
    render_notes: list[str] = []
    for index, mermaid in enumerate(diagrams, 1):
        first_line = mermaid.splitlines()[0].strip() if mermaid.splitlines() else ""
        if first_line not in {"flowchart LR", "flowchart TB", "sequenceDiagram", "stateDiagram-v2"}:
            errors.append(f"🔴 [MERMAID] 图 {index} 缺受支持的图类型声明")
            mermaid_structure_ok = False
        if "\r" in mermaid or "```" in mermaid or "%%" in mermaid:
            errors.append(f"🔴 [MERMAID] 图 {index} 含不安全控制内容")
            mermaid_structure_ok = False
        if mmdc and mermaid_structure_ok:
            with tempfile.TemporaryDirectory() as temp:
                source = Path(temp) / "diagram.mmd"
                output = Path(temp) / "diagram.svg"
                source.write_text(mermaid, encoding="utf-8")
                try:
                    result = subprocess.run(
                        [*mmdc[0], "-i", str(source), "-o", str(output)],
                        text=True,
                        capture_output=True,
                        timeout=60,
                    )
                except subprocess.TimeoutExpired:
                    render_notes.append(f"图 {index} 实际渲染超时")
                else:
                    if result.returncode != 0 or not output.is_file():
                        detail = (result.stderr or result.stdout).strip()[:300]
                        render_notes.append(
                            f"图 {index} 实际渲染失败：{detail}"
                        )
                    else:
                        rendered_count += 1
    if diagrams:
        if mmdc and mermaid_structure_ok and rendered_count == len(diagrams):
            passed.append(
                f"✅ [MERMAID] {len(diagrams)} 个图通过 {mmdc[1]} 实际渲染"
            )
        elif mmdc and mermaid_structure_ok:
            detail = "；".join(render_notes) or "实际渲染未完成"
            passed.append(
                f"🟡 [MERMAID.RENDER] {detail}；"
                "安全子集结构已通过，不阻塞报告交付"
            )
        elif not mmdc and mermaid_structure_ok:
            passed.append(
                f"🟡 [MERMAID.RENDER] 当前环境无 mmdc；"
                f"{len(diagrams)} 个图仅做安全子集结构检查，不阻塞报告交付"
            )

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
