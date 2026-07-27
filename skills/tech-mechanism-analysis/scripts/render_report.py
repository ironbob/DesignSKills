#!/usr/bin/env python3
"""Deterministically render a Full analysis.json to analysis.md."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def evidence_lines(items: list[dict[str, Any]]) -> str:
    return "、".join(
        f"`{item['file']}:{item['line']}`（{item['note']}）" for item in items
    )


def yaml_scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def yaml_list(items: list[str], indent: int = 2) -> list[str]:
    return [f"{' ' * indent}- {yaml_scalar(item)}" for item in items]


def mermaid_text(value: Any) -> str:
    return str(value).translate(
        {
            ord("\r"): " ",
            ord("\n"): " ",
            ord("&"): "&amp;",
            ord('"'): "&quot;",
            ord(";"): "&#59;",
            ord("%"): "&#37;",
            ord("`"): "&#96;",
        }
    )


def render_report(data: dict[str, Any]) -> str:
    defects = data.get("defects", [])
    architecture = [item for item in defects if item.get("axis") == "architecture"]
    logic = [item for item in defects if item.get("axis") == "logic"]
    lines = [
        "---",
        "mode: full",
        f"target: {yaml_scalar(data['target'])}",
        f"title: {yaml_scalar(data['target'] + ' 技术机制深度分析')}",
        f"mechanism_type: {yaml_scalar(data['mechanism_type'])}",
        "languages: " + yaml_scalar(data["languages"]),
        f"analyzed_at: {yaml_scalar(data['analyzed_at'])}",
        "covered_files:",
        *yaml_list(data["covered_files"]),
        f"chain_segments: {len(data['chain_stages'])}",
        f"boundaries: {len(data['boundary_inventory'])}",
        f"behavior_cases: {len(data['behavior_cases'])}",
        f"acceptance_cases: {len(data['acceptance_cases'])}",
        f"behavior_conflicts: {len(data['behavior_conflicts'])}",
        f"numerical_examples: {len(data['numerical_examples'])}",
        f"defects_arch: {len(architecture)}",
        f"defects_logic: {len(logic)}",
        f"open_questions: {len(data['gaps'])}",
        "---",
        "",
        f"# {data['target']} 技术机制深度分析",
        "",
        "## 机制概述",
        "",
        f"- **模式**：full。",
        f"- **一句话职责**：{data['responsibility']}。",
        f"- **主机制类型**：`{data['mechanism_type']}`。",
        "- **次机制类型**：" + (
            "、".join(f"`{item}`" for item in data["secondary_mechanism_types"])
            if data["secondary_mechanism_types"] else "无"
        ) + "。",
        f"- **类型依据**：{data['mechanism_type_basis']}。",
        "- **链路模板**：" + " → ".join(f"`{item}`" for item in data["chain_template"]) + "。",
        "",
        "### 范围确认",
        "",
    ]
    for item in data["scope_confirmations"]:
        lines.append(
            f"- **{item['id']} · {item['trigger']} · {item['confirmed_at']}**："
            f"{item['confirmation_basis']}；候选文件："
            f"{'、'.join(f'`{path}`' for path in item['candidate_files'])}。"
        )
    lines.extend(["", "### 工具与证据置信度", ""])
    for item in data["language_analysis"]:
        lines.append(
            f"- **{item['language']} · {item['confidence']}**：{item['basis']}；"
            f"工具：{'、'.join(item['tools'])}。"
        )
    lines.extend(["", "## 全链路", ""])
    for stage in data["chain_stages"]:
        lines.extend([
            f"### {stage['id']} · {stage['name']}",
            "",
            f"- **阶段标识**：`{stage['segment']}`。",
            f"- **做了什么**：{stage['what']}。",
            f"- **怎么实现**：{stage['how']}。",
            f"- **设计依据（{stage['why_basis']}）**：{stage['why']}。",
            *(
                [f"- **设计意图证据**：{evidence_lines(stage['why_evidence'])}。"]
                if stage["why_basis"] == "observed"
                else []
            ),
            f"- **关键结构**：{'、'.join(f'`{item}`' for item in stage['key_structures'])}。",
            f"- **交接/最终效果**：{stage['handoff']}。",
            f"- **交接证据**：{evidence_lines(stage['handoff_evidence'])}。",
            f"- **证据**：{evidence_lines(stage['evidence'])}。",
            "",
        ])

    diagram = data.get("diagrams")
    if isinstance(diagram, dict) and diagram.get("applicable"):
        lines.extend(["### 链路图", "", "```mermaid"])
        if diagram["type"] == "sequence":
            lines.append("sequenceDiagram")
            for node in diagram["nodes"]:
                lines.append(f"  participant {node['id']} as {mermaid_text(node['label'])}")
            for edge in diagram["edges"]:
                lines.append(
                    f"  {edge['from']}->>{edge['to']}: "
                    f"{mermaid_text(edge.get('label', ''))}"
                )
        elif diagram["type"] == "state":
            lines.append("stateDiagram-v2")
            for node in diagram["nodes"]:
                lines.append(
                    f'  state "{mermaid_text(node["label"])}" as {node["id"]}'
                )
            for edge in diagram["edges"]:
                lines.append(
                    f"  {edge['from']} --> {edge['to']}: "
                    f"{mermaid_text(edge.get('label', ''))}"
                )
        else:
            lines.append("flowchart LR")
            for node in diagram["nodes"]:
                label = mermaid_text(node["label"])
                lines.append(f'  {node["id"]}["{label}"]')
            for edge in diagram["edges"]:
                label = mermaid_text(edge.get("label", ""))
                lines.append(f'  {edge["from"]} -->|"{label}"| {edge["to"]}')
        lines.extend(["```", ""])

    lines.extend(["## 边界清单", ""])
    for boundary in data["boundary_inventory"]:
        lines.extend([
            f"### {boundary['id']} · {boundary['condition']}",
            "",
            f"- **类别**：`{boundary['kind']}`。",
            f"- **适用性**：`{boundary['applicability']}`。",
            f"- **条件**：{boundary['condition']}。",
            f"- **期望契约**：{boundary['expected_contract']}。",
            f"- **实际行为**：{boundary['observed_behavior']}。",
            f"- **验证状态**：`{boundary['status']}`。",
            "- **关联行为用例**：" + (
                "、".join(f"`{item}`" for item in boundary["behavior_case_ids"])
                if boundary["behavior_case_ids"] else "无"
            ) + "。",
            "- **源码锚点**：" + (
                evidence_lines(boundary["source_anchors"])
                if boundary["source_anchors"] else "不适用"
            ) + "。",
            "",
        ])

    lines.extend(["## 可验证行为用例", ""])
    for case in data["behavior_cases"]:
        verification = case["verification"]
        lines.extend([
            f"### {case['id']} · {case['title']}",
            "",
            "- **关联边界**：" + (
                "、".join(f"`{item}`" for item in case["boundary_ids"])
                if case["boundary_ids"] else "无"
            ) + "。",
            f"- **入口**：`{case['entry_point']}`。",
            f"- **分支路径**：`{case['branch_path']}`。",
            f"- **语义条件键**：`{case['semantic_key']}`。",
            f"- **前置条件**：{'；'.join(case['preconditions'])}。",
            f"- **输入**：{case['input']}。",
            f"- **动作**：{case['action']}。",
            f"- **期望可观察行为**：{case['expected_observable']}。",
            f"- **实际观察行为**：{case['observed_observable']}。",
            f"- **验证**：`{verification['status']}` / `{verification['method']}`；"
            f"{verification['procedure']}；结果：{verification['observed_result']}。",
            f"- **源码锚点**：{evidence_lines(case['source_anchors'])}。",
            "- **对应验收用例**："
            + "、".join(f"`{item}`" for item in case["acceptance_case_ids"])
            + "。",
            "",
        ])

    lines.extend(["## 验收用例", ""])
    for acceptance in data["acceptance_cases"]:
        lines.extend([
            f"### {acceptance['id']} · {acceptance['title']}",
            "",
            "- **关联行为用例**："
            + "、".join(f"`{item}`" for item in acceptance["behavior_case_ids"])
            + "。",
            f"- **Given**：{acceptance['given']}。",
            f"- **When**：{acceptance['when']}。",
            f"- **Then**：{acceptance['then']}。",
            f"- **验证级别**：`{acceptance['verification_level']}`。",
            f"- **源码锚点**：{evidence_lines(acceptance['source_anchors'])}。",
            "",
        ])

    lines.extend(["## 多入口/分支行为矛盾", ""])
    if not data["behavior_conflicts"]:
        lines.extend(["在已覆盖入口和分支内，未识别到多入口/分支行为矛盾。", ""])
    for conflict in data["behavior_conflicts"]:
        lines.extend([
            f"### {conflict['id']} · {conflict['title']}",
            "",
            "- **对比行为用例**："
            + "、".join(f"`{item}`" for item in conflict["case_ids"])
            + "。",
            f"- **比较维度**：{conflict['comparison_dimension']}。",
            f"- **矛盾**：{conflict['contradiction']}。",
            f"- **影响**：{conflict['impact']}。",
            f"- **意图状态**：`{conflict['intent_status']}`。",
            f"- **收敛方向**：{conflict['resolution']}。",
            f"- **源码锚点**：{evidence_lines(conflict['source_anchors'])}。",
            "",
        ])

    lines.extend(["## 数值示例", ""])
    if not data["numerical_examples"]:
        lines.extend(["本机制未识别到需要工作示例的核心数值操作。", ""])
    for example in data["numerical_examples"]:
        lines.extend([
            f"### {example['id']} · {example['operation']}",
            "",
            f"- **所属阶段**：`{example['stage_id']}`。",
            f"- **示例数据**：{example['sample_data']}。",
            "- **计算步骤**：",
        ])
        lines.extend(f"  {index}. {step}" for index, step in enumerate(example["computation_steps"], 1))
        lines.extend([
            f"- **结果**：{example['result']}。",
            f"- **代码翻译**：{example.get('code_translation', '未使用代码翻译')}。",
            f"- **忠实性**：{example['faithfulness_note']}。",
            f"- **证据**：{evidence_lines(example['evidence'])}。",
            "",
        ])

    def render_debts(title: str, items: list[dict[str, Any]]) -> None:
        lines.extend([f"## {title}", ""])
        if not items:
            lines.extend([f"本机制未识别到{title}。", ""])
            return
        for item in items:
            cross = "；跨阶段" if item["cross_stage"] else ""
            lines.extend([
                f"### {item['id']} · {item['title']}",
                "",
                f"- **所属阶段**：`{item['stage_id']}`{cross}。",
                f"- **需求来源**：`{item['requirement_source']}`。",
                f"- **会变难的需求**：{item['hard_requirement']}。",
                f"- **为什么难**：{item['why_hard']}。",
                f"- **演进方向**：{item['evolution_direction']}。",
                f"- **代价/影响**：{item['cost_impact']}。",
                "- **量化范围**："
                f"阶段 {len(item['cost_quantification']['affected_stages'])} 个"
                f"（{'、'.join(f'`{value}`' for value in item['cost_quantification']['affected_stages'])}）；"
                f"文件 {len(item['cost_quantification']['affected_files'])} 个"
                f"（{'、'.join(f'`{value}`' for value in item['cost_quantification']['affected_files'])}）；"
                f"模块 {len(item['cost_quantification']['affected_modules'])} 个"
                + (
                    f"（{'、'.join(f'`{value}`' for value in item['cost_quantification']['affected_modules'])}）"
                    if item["cost_quantification"]["affected_modules"]
                    else ""
                )
                + f"；量级 `{item['cost_quantification']['change_scale']}`；"
                f"{item['cost_quantification']['basis']}。",
                f"- **结论置信度**：`{item['confidence']}`；{item['confidence_basis']}。",
                f"- **证据**：{evidence_lines(item['evidence'])}。",
                "",
            ])

    render_debts("架构设计债", architecture)
    render_debts("逻辑设计债", logic)
    cross_stage = [item for item in defects if item.get("cross_stage")]
    lines.extend(["## 跨阶段衔接", ""])
    if cross_stage:
        lines.append("、".join(f"`{item['id']}`" for item in cross_stage) + " 涉及跨阶段约定。")
    else:
        lines.append("本机制未识别到独立的跨阶段衔接设计债。")
    lines.extend(["", "## 已知缺口", ""])
    if data["gaps"]:
        lines.extend(f"- ⚠ 未确认：{item}" for item in data["gaps"])
    else:
        lines.append("- 无。")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    data = json.loads(args.analysis.read_text(encoding="utf-8"))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(data), encoding="utf-8")
    print(f"已生成 {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
