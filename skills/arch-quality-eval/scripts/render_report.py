#!/usr/bin/env python3
"""Render report.md deterministically from the findings.json source of truth."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

CORE_SMELLS = (
    ("circular-dependency", "循环依赖 circular-dependency", {"circular-dependency"}),
    ("god-class-or-package", "God Class / God Package", {"god-class", "god-package"}),
    ("cross-layer", "跨层调用 cross-layer", {"cross-layer"}),
    ("shotgun-surgery", "霰弹式修改 shotgun-surgery", {"shotgun-surgery"}),
    ("inappropriate-exposure", "不恰当暴露 inappropriate-exposure", {"inappropriate-exposure"}),
)
SEVERITY_ICON = {"critical": "🔴", "major": "🟠", "minor": "🟡"}


def scalar(value: Any) -> str:
    text = str(value)
    if any(ch in text for ch in ":#{}[],'\"\n") or text.strip() != text:
        return json.dumps(text, ensure_ascii=False)
    return text


def evidence_anchor(item: dict) -> str:
    path = str(item.get("file", ""))
    line = item.get("line")
    return f"{path}:{line}" if isinstance(line, int) else path


def evidence_text(items: list[dict]) -> str:
    rendered = []
    for item in items:
        anchor = evidence_anchor(item)
        note = str(item.get("note", "")).strip()
        rendered.append(f"`{anchor}`（{note}）" if note else f"`{anchor}`")
    return "；".join(rendered)


def finding_map(data: dict) -> dict[str, list[dict]]:
    by_category: dict[str, list[dict]] = defaultdict(list)
    for finding in data.get("findings", []):
        if isinstance(finding, dict):
            by_category[str(finding.get("category", ""))].append(finding)
    return by_category


def render(data: dict) -> str:
    module = str(data["module"])
    summary = data["summary"]
    findings = [item for item in data.get("findings", []) if isinstance(item, dict)]
    scope = data.get("scope") or {}
    analysis = data.get("analysis") or {}
    readability = data.get("readability") or {}
    coverage = data.get("core_smell_coverage") or {}
    known_gaps = [str(item) for item in data.get("known_gaps", [])]
    unconfirmed_count = sum(bool(item.get("unconfirmed")) for item in findings)
    by_category = finding_map(data)
    critical = [item for item in findings if item.get("severity") == "critical"]

    lines = [
        "---",
        f"module: {scalar(module)}",
        f"title: {scalar(data.get('title') or f'{module} 架构质量诊断（重构前）')}",
        f"language: {scalar(data['language'])}",
        f"analyzed_at: {scalar(data['analyzed_at'])}",
        "covered_files:",
    ]
    lines.extend(f"  - {scalar(path)}" for path in data["covered_files"])
    lines.extend([
        f"conventions_fed: {'true' if data['conventions_fed'] else 'false'}",
        f"no_go_threshold: {data['no_go_threshold']}",
        f"verdict: {summary['verdict']}",
        f"critical_count: {summary['critical']}",
        f"major_count: {summary['major']}",
        f"minor_count: {summary['minor']}",
        f"cpp_limitation_noted: {'true' if data.get('cpp_limitation_noted', False) else 'false'}",
        f"open_questions: {unconfirmed_count}",
        "status: draft",
        "---",
        "",
        f"# {module} 架构质量诊断报告",
        "",
        "> 重构前诊断：只回答模块是否值得重构、阻塞点和优先顺序；不输出完整重构方案，不做 lint 或 CI 卡关。",
        "",
        "## 一、评估范围",
        "",
        f"- **路径**：{'、'.join(f'`{path}`' for path in scope.get('root_paths', []))}。",
        f"- **覆盖文件**：{len(data['covered_files'])} 个源文件，详见 frontmatter。",
        f"- **语言与结构**：{data['language']}；{scope.get('structure_summary', '')}",
        f"- **模块职责基线**：{scope.get('responsibility', '')}",
        f"- **项目规约**：{'已手工喂入并参与检查' if data['conventions_fed'] else '未喂入，只检查通用架构准则'}。",
        "",
        "## 二、go/no-go 门禁结论",
        "",
        f"**{'⛔ no-go' if summary['verdict'] == 'no-go' else '✅ go'}** —— critical {summary['critical']}，阈值 {data['no_go_threshold']}。",
        "",
    ])
    if critical:
        lines.append("critical 项：")
        lines.append("")
        lines.extend(f"- `{item['id']}` {item['title']}：{item['severity_basis']}" for item in critical)
    else:
        lines.append("未发现达到 critical 的阻塞问题，可以按优先级增量治理。")

    lines.extend(["", "## 三、架构坏味道清单", "", "| 核心坏味道 | 判定 | 证据锚点 |", "|---|---|---|"])
    for key, label, categories in CORE_SMELLS:
        matches = [item for category in categories for item in by_category.get(category, [])]
        status = coverage.get(key)
        if status == "detected":
            ids = " / ".join(str(item["id"]) for item in matches)
            anchors = " / ".join(
                evidence_anchor(evidence)
                for item in matches
                for evidence in item.get("evidence", [])[:1]
            ) or "—"
            lines.append(f"| {label} | ✅ 已检出 → {ids} | {anchors} |")
        else:
            lines.append(f"| {label} | ⬜ 未检出 | — |")

    for finding in findings:
        if finding.get("axis") != "smell":
            continue
        severity = str(finding["severity"])
        lines.extend([
            "",
            f"#### {finding['id']} · {finding['title']} · {SEVERITY_ICON[severity]} {severity}{' · ⚠ 未确认' if finding.get('unconfirmed') else ''}",
            "",
            f"- 证据：{evidence_text(finding['evidence'])}",
            f"- 违反原理：{finding['principle_violated']}",
            f"- 影响：{finding['impact']}",
            f"- 分级依据：{finding['severity_basis']}",
            f"- 改进方向：{finding['improvement']}",
            f"- 修复成本：{finding['fix_cost']}　优先级：{finding['priority']}（{finding['priority_basis']}）",
        ])

    if data["conventions_fed"]:
        lines.extend(["", "## 四、项目规约违规", ""])
        for rule in data.get("convention_rules", []):
            related = [item for item in findings if item.get("convention_violated") == rule.get("id")]
            status = "✅ 检出违规" if related else "⬜ 未检出违规"
            ids = " → " + ", ".join(str(item["id"]) for item in related) if related else ""
            lines.append(f"- `{rule['id']}` {rule['rule']}：{status}{ids}")
        for finding in findings:
            if finding.get("axis") != "convention":
                continue
            severity = str(finding["severity"])
            lines.extend([
                "",
                f"#### {finding['id']} · {finding['title']} · {SEVERITY_ICON[severity]} {severity}{' · ⚠ 未确认' if finding.get('unconfirmed') else ''}",
                "",
                f"- 证据：{evidence_text(finding['evidence'])}",
                f"- 违反规约：{finding['convention_violated']}",
                f"- 影响：{finding['impact']}",
                f"- 分级依据：{finding['severity_basis']}",
                f"- 改进方向：{finding['improvement']}",
                f"- 修复成本：{finding['fix_cost']}　优先级：{finding['priority']}（{finding['priority_basis']}）",
            ])

    read_section = "五" if data["conventions_fed"] else "四"
    priority_section = "六" if data["conventions_fed"] else "五"
    method_section = "七" if data["conventions_fed"] else "六"
    lines.extend([
        "",
        f"## {read_section}、架构可读性",
        "",
        "| 轴 | 结论 |",
        "|---|---|",
        f"| 职责清晰度 | {readability['responsibility_clarity']} |",
        f"| 依赖可理解性 | {readability['dependency_understandability']} |",
        f"| 命名表意度 | {readability['naming_expressiveness']} |",
        f"| 分层清晰度 | {readability['layering_clarity']} |",
        "",
        f"总体可读性：**{readability['overall']}**",
    ])
    for finding in findings:
        if finding.get("axis") != "readability":
            continue
        severity = str(finding["severity"])
        lines.extend([
            "",
            f"#### {finding['id']} · {finding['title']} · {SEVERITY_ICON[severity]} {severity}{' · ⚠ 未确认' if finding.get('unconfirmed') else ''}",
            "",
            f"- 证据：{evidence_text(finding['evidence'])}",
            f"- 违反原理：{finding['principle_violated']}",
            f"- 影响：{finding['impact']}",
            f"- 分级依据：{finding['severity_basis']}",
            f"- 改进方向：{finding['improvement']}",
            f"- 修复成本：{finding['fix_cost']}　优先级：{finding['priority']}（{finding['priority_basis']}）",
        ])
    lines.extend([
        "",
        f"## {priority_section}、重构优先级总览",
        "",
        "| 优先级 | finding | 排序依据 |",
        "|---|---|---|",
    ])
    for priority in ("P1", "P2", "P3"):
        group = [item for item in findings if item.get("priority") == priority]
        if group:
            ids = "、".join(str(item["id"]) for item in group)
            basis = "；".join(f"{item['id']}：{item['priority_basis']}" for item in group)
            lines.append(f"| {priority} | {ids} | {basis} |")
    if not findings:
        lines.append("| — | 无 | 未发现达到 finding 级别的问题 |")

    symbol_mode = analysis.get("symbol_mode", "text-search")
    mode_text = "LSP 精确符号查询" if symbol_mode == "LSP" else "文本搜索降级"
    lines.extend([
        "",
        f"## {method_section}、评估方法与已知缺口",
        "",
        f"- **取证方式**：{mode_text}。",
        f"- **聚焦策略**：{analysis.get('focus_strategy', '')}",
        f"- **Git 历史**：{'已采样用于协同变更线索' if analysis.get('git_history_used') else '未使用，历史型坏味道结论保持保守'}。",
    ])
    for omission in analysis.get("omissions", []):
        lines.append(f"- **未覆盖**：{omission}")
    if known_gaps:
        lines.append("- **已知缺口**：")
        lines.extend(f"  - {gap}" for gap in known_gaps)
    else:
        lines.append("- **已知缺口**：无未确认项。")
    lines.append("- **边界**：仅做重构前诊断；完整重构设计、代码风格和 CI 门禁不在本报告范围。")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render arch-quality-eval report.md from findings.json")
    parser.add_argument("findings", type=Path)
    parser.add_argument("--output", type=Path, help="Output report path; default next to findings")
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
