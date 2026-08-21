#!/usr/bin/env python3
"""Render a deterministic report from findings.json v2."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PRINCIPLE_LABELS = {
    "complexity-management": "复杂度管理",
    "responsibility-cohesion": "职责与内聚",
    "coupling-dependency-direction": "耦合与依赖方向",
    "information-hiding": "信息隐藏与接口边界",
    "abstraction-consistency": "抽象层级一致性",
    "change-isolation": "变化隔离与可演进性",
}
STATUS_LABELS = {
    "concern": "⚠ concern",
    "no-material-concern": "✅ no material concern",
    "inconclusive": "❓ inconclusive",
}
SEVERITY_ICON = {"critical": "🔴", "major": "🟠", "minor": "🟡"}
VERDICT_LABEL = {"go": "✅ go", "no-go": "⛔ no-go", "inconclusive": "❓ inconclusive"}


def scalar(value: Any) -> str:
    text = str(value)
    if any(ch in text for ch in ":#{}[],'\"\n") or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    return text


def anchor(item: dict) -> str:
    value = str(item.get("file", ""))
    return f"{value}:{item['line']}" if isinstance(item.get("line"), int) else value


def evidence_text(items: list[dict]) -> str:
    return "；".join(f"`{anchor(item)}`（{item.get('note', '')}）" for item in items) or "—"


def render(data: dict) -> str:
    summary = data["summary"]
    coverage = data["coverage"]
    scope = data["scope"]
    analysis = data["analysis"]
    principles = data["design_principle_coverage"]
    findings = [item for item in data.get("findings", []) if isinstance(item, dict)]
    known_gaps = [str(item) for item in data.get("known_gaps", [])]
    open_questions = sum(item.get("confidence") != "confirmed" for item in findings)
    lines = [
        "---",
        f"schema_version: {data['schema_version']}",
        f"module: {scalar(data['module'])}",
        f"title: {scalar(data.get('title') or str(data['module']) + ' 架构设计质量诊断')}",
        f"language: {scalar(data['language'])}",
        f"analyzed_at: {scalar(data['analyzed_at'])}",
        "scope_files:",
    ]
    lines.extend(f"  - {scalar(path)}" for path in coverage["scope_files"])
    lines.extend([
        f"indexed_file_count: {len(coverage['indexed_files'])}",
        f"inspected_file_count: {len(coverage['inspected_files'])}",
        f"semantic_resolved_file_count: {len(coverage['semantic_resolved_files'])}",
        f"coverage_sufficient: {'true' if coverage['sufficient_for_verdict'] else 'false'}",
        f"conventions_fed: {'true' if data['conventions_fed'] else 'false'}",
        f"no_go_threshold: {data['no_go_threshold']}",
        f"verdict: {summary['verdict']}",
        f"critical_count: {summary['critical']}",
        f"major_count: {summary['major']}",
        f"minor_count: {summary['minor']}",
        f"confirmed_critical_count: {summary['confirmed_critical']}",
        f"cpp_limitation_noted: {'true' if data.get('cpp_limitation_noted', False) else 'false'}",
        f"open_questions: {open_questions}",
        "status: draft",
        "---",
        "",
        f"# {data['module']} 架构设计质量诊断",
        "",
        "> 以复杂度管理、职责边界、依赖、信息隐藏、抽象一致性和变化隔离为主轴；不检查语法、语言技巧、lint 或 CI。",
        "",
        "## 一、范围与覆盖",
        "",
        f"- **路径**：{'、'.join(f'`{path}`' for path in scope['root_paths'])}。",
        f"- **职责基线**：{scope['responsibility']}",
        f"- **结构**：{scope['structure_summary']}",
        f"- **覆盖**：范围 {len(coverage['scope_files'])}，索引 {len(coverage['indexed_files'])}，精读 {len(coverage['inspected_files'])}，语义解析 {len(coverage['semantic_resolved_files'])} 个文件。",
        f"- **结论覆盖充分性**：{'充分' if coverage['sufficient_for_verdict'] else '不足'}。",
        "",
        "## 二、诊断结论",
        "",
        f"**{VERDICT_LABEL[summary['verdict']]}** —— confirmed critical {summary['confirmed_critical']}，阈值 {data['no_go_threshold']}。",
        "",
    ])
    critical = [item for item in findings if item.get("severity") == "critical"]
    if critical:
        lines.append("critical 候选：")
        lines.append("")
        lines.extend(
            f"- `{item['id']}` {item['title']}（confidence={item['confidence']}）：{item['severity_basis']}"
            for item in critical
        )
    elif summary["verdict"] == "inconclusive":
        lines.append("未确认 critical，但覆盖不足，不能把当前结果解释为架构健康。")
    else:
        lines.append("在声明覆盖内未发现 confirmed critical，可按优先级增量治理。")

    lines.extend([
        "",
        "## 三、设计原则矩阵",
        "",
        "| 设计轴 | 状态 | 结论 | 代表证据 |",
        "|---|---|---|---|",
    ])
    for key, label in PRINCIPLE_LABELS.items():
        item = principles[key]
        evidence = " / ".join(anchor(entry) for entry in item.get("evidence", [])[:2]) or "—"
        lines.append(f"| {label} (`{key}`) | {STATUS_LABELS[item['status']]} | {item['conclusion']} | {evidence} |")

    if data["conventions_fed"]:
        lines.extend(["", "## 四、项目规约", "", "| 规约 | 结果 |", "|---|---|"])
        for rule in data.get("convention_rules", []):
            related = [item["id"] for item in findings if rule["id"] in item.get("convention_rule_ids", [])]
            result = "违规 → " + "、".join(related) if related else "未检出违规"
            lines.append(f"| `{rule['id']}` {rule['rule']} | {result} |")

    finding_section = "五" if data["conventions_fed"] else "四"
    lines.extend(["", f"## {finding_section}、结构问题", ""])
    if not findings:
        lines.append("没有达到 finding 级别的结构问题。")
    for finding in findings:
        severity = finding["severity"]
        lines.extend([
            f"#### {finding['id']} · {finding['title']} · {SEVERITY_ICON[severity]} {severity} · confidence={finding['confidence']}",
            "",
            f"- 证据：{evidence_text(finding['evidence'])}",
            f"- 违反原则：{'、'.join(finding.get('principles_violated', [])) or '—'}",
            f"- 关联规约：{'、'.join(finding.get('convention_rule_ids', [])) or '—'}",
            f"- 影响：{finding['impact']}",
            f"- 分级依据：{finding['severity_basis']}",
            f"- 改进方向：{finding['improvement']}",
            f"- 修复成本：{finding['fix_cost']}　优先级：{finding['priority']}（{finding['priority_basis']}）",
            "",
        ])

    read_number = "六" if data["conventions_fed"] else "五"
    priority_number = "七" if data["conventions_fed"] else "六"
    method_number = "八" if data["conventions_fed"] else "七"
    readability = data["architecture_readability"]
    lines.extend([
        f"## {read_number}、架构可理解性",
        "",
        f"**{readability['overall']}** —— {readability['rationale']}",
        "",
        f"## {priority_number}、优先级",
        "",
        "| 优先级 | finding | 排序依据 |",
        "|---|---|---|",
    ])
    for priority in ("P1", "P2", "P3"):
        group = [item for item in findings if item.get("priority") == priority]
        if group:
            lines.append(f"| {priority} | {'、'.join(item['id'] for item in group)} | {'；'.join(item['priority_basis'] for item in group)} |")
    if not findings:
        lines.append("| — | 无 | 无需排序 |")

    mode_text = {"LSP": "LSP", "clang-ast": "compile_commands + clang AST", "text-search": "文本索引/搜索"}.get(
        analysis["symbol_mode"], analysis["symbol_mode"]
    )
    lines.extend([
        "",
        f"## {method_number}、方法与缺口",
        "",
        f"- **取证方式**：{mode_text}；语言工具只提供架构证据。",
        f"- **聚焦策略**：{analysis['focus_strategy']}",
        f"- **Git 历史**：{'可用' if coverage['history_available'] else '不可用或未采样'}。",
    ])
    for omission in analysis.get("omissions", []):
        lines.append(f"- **未覆盖**：{omission}")
    for gap in coverage.get("gaps", []):
        lines.append(f"- **覆盖缺口**：{gap}")
    for gap in known_gaps:
        lines.append(f"- **已知缺口**：{gap}")
    if not coverage.get("gaps") and not known_gaps:
        lines.append("- **已知缺口**：无影响 verdict 的缺口。")
    lines.append("- **边界**：仅做重构前架构诊断；完整重构方案、语法检查和语言技巧不在范围内。")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render arch-quality-eval v2 report")
    parser.add_argument("findings", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not args.findings.exists():
        sys.stderr.write(f"{args.findings}: 文件不存在\n")
        return 2
    try:
        data = json.loads(args.findings.read_text(encoding="utf-8"))
        output = args.output or args.findings.with_name(args.findings.name.replace("-findings.json", "-report.md"))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render(data), encoding="utf-8")
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"render_report: findings 契约不完整：{exc}\n")
        return 2
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
