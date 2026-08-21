#!/usr/bin/env python3
"""Render an architecture Markdown document from design-contract.json.

The contract remains the only hand-maintained source. This renderer is
deterministic so contract/doc drift can be fixed by regeneration, not manual
copy editing.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _text(value: Any, empty: str = "—") -> str:
    if value is None:
        return empty
    if isinstance(value, list):
        return "、".join(_text(item, "") for item in value) or empty
    value = str(value).strip()
    return value or empty


def _cell(value: Any) -> str:
    return _text(value).replace("|", "\\|").replace("\n", " ")


def _node_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _mermaid(value: Any) -> str:
    return _text(value).replace('"', "'").replace("\n", " ")


def _bullet(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "无"
    return "；".join(_text(value) for value in values)


def render(contract: dict[str, Any]) -> str:
    roles = [r for r in contract.get("roles", []) if isinstance(r, dict)]
    role_by_id = {r.get("id"): r for r in roles}
    processes = [p for p in contract.get("business_process", []) if isinstance(p, dict)]
    interfaces = [i for i in contract.get("interfaces", []) if isinstance(i, dict)]
    verification = contract.get("verification") or {}
    questions = [q for q in contract.get("open_questions", []) if isinstance(q, dict)]
    unverified = [u for u in verification.get("unverified", []) if isinstance(u, dict)]
    gap_count = len(questions) + len(unverified)
    decision = contract.get("design_decision") or {}
    confirmation = contract.get("interaction_confirmation") or {}
    profile_confirmation = confirmation.get("profile_selection") or {}
    design_confirmation = confirmation.get("design_confirmation") or {}
    gate = contract.get("gate") or {}
    guidance = contract.get("guidance") or {}

    lines: list[str] = [
        "---",
        f"feature: {_text(contract.get('feature'))}",
        f"title: {_text(contract.get('title'))} — 架构文档",
        f"stack: {_text(contract.get('stack'))}",
        f"design_profile: {_text(decision.get('profile'))}",
        f"analyzed_at: {_text(contract.get('analyzed_at'))}",
        f"roles_count: {len(roles)}",
        f"process_steps: {len(processes)}",
        f"verdict: {_text(gate.get('verdict'))}",
        f"open_questions: {gap_count}",
        "---",
        "",
        f"# {_text(contract.get('title'))} 架构文档",
        "",
        "## 零、用户确认记录",
        "",
        f"- 等级：用户选择 `{_text(profile_confirmation.get('selected_profile'))}`；证据：{_text(profile_confirmation.get('evidence'))}。",
        f"- 方案版本：`{_text(confirmation.get('proposal_revision'))}`。",
        f"- 确认：用户在方案展示后的后续消息中确认 `{_text(design_confirmation.get('confirmed_candidate'))}`；证据：{_text(design_confirmation.get('evidence'))}。",
        f"- 主指导：{_text(guidance.get('primary_source'), 'legacy contract')}；执行优先级：{_cell(guidance.get('priority_order'))}。",
        "",
        "## 一、模块结构图",
        "",
        "```mermaid",
        "flowchart TD",
    ]
    if roles:
        for role in roles:
            rid = _node_id(_text(role.get("id"), "role"))
            lines.append(f'  {rid}["{_mermaid(role.get("name"))}<br/>{_mermaid(role.get("layer"))}"]')
        for role in roles:
            source = _node_id(_text(role.get("id"), "role"))
            for dep in role.get("depends_on") or []:
                if dep in role_by_id:
                    lines.append(f"  {source} --> {_node_id(str(dep))}")
    else:
        lines.append('  EMPTY["契约尚无角色"]')
    lines.extend(["```", "", "## 二、业务流程图", "", "```mermaid", "flowchart TD"])
    if processes:
        for process in processes:
            step = process.get("step")
            lines.append(f'  P{step}["步骤{step}：{_mermaid(process.get("name"))}"]')
        for left, right in zip(processes, processes[1:]):
            lines.append(f"  P{left.get('step')} --> P{right.get('step')}")
    else:
        lines.append('  START["开始"] --> DONE["无跨角色业务流程"]')
    lines.extend(["```", ""])
    for process in processes:
        lines.append(
            f"- {_text(process.get('doc_ref'))}：{_text(process.get('name'))}；"
            f"异常分支：{_text(process.get('exception'), '无')}。"
        )

    lines.extend([
        "",
        "## 三、角色职责清单",
        "",
        "| 角色 | 类型 | 层 | 职责 | 隐藏秘密 | 数据所有权 | 依赖 | 设计原则 |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for role in roles:
        dependencies = [role_by_id.get(dep, {}).get("name", dep) for dep in role.get("depends_on") or []]
        lines.append(
            "| " + " | ".join([
                _cell(role.get("name")), _cell(role.get("role_kind")), _cell(role.get("layer")),
                _cell(role.get("responsibility")), _cell(role.get("hidden_secret")),
                _cell(role.get("data_owned")), _cell(dependencies),
                _cell(role.get("design_principles")),
            ]) + " |"
        )

    lines.extend(["", "## 四、质量属性与方案取舍", ""])
    for qa in decision.get("quality_attributes") or []:
        lines.append(
            f"- **{_text(qa.get('name'))} ({_text(qa.get('priority'))})**："
            f"场景：{_text(qa.get('scenario'))}；验收：{_text(qa.get('acceptance'))}。"
        )
    lines.append("")
    for candidate in decision.get("candidates") or []:
        lines.append(
            f"- 候选 `{_text(candidate.get('id'))}`：{_text(candidate.get('summary'))}。"
            f"优点：{_bullet(candidate.get('strengths'))}；代价：{_bullet(candidate.get('weaknesses'))}；"
            f"风险：{_bullet(candidate.get('risks'))}。"
        )
    lines.extend([
        "",
        f"- 选择 `{_text(decision.get('selected_id'))}`：{_text(decision.get('selection_reason'))}。",
        f"- 自顶向下检查：{_text(decision.get('top_down_check'))}。",
        f"- 自底向上检查：{_text(decision.get('bottom_up_check'))}。",
    ])
    for spike in decision.get("risk_spikes") or []:
        lines.append(
            f"- Spike：{_text(spike.get('question'))}；方法：{_text(spike.get('method'))}；"
            f"结果：{_text(spike.get('result'))}；状态：`{_text(spike.get('status'))}`。"
        )

    lines.extend(["", "## 五、设计依据", ""])
    for role in roles:
        lines.extend([
            f"### {_text(role.get('name'))}",
            "",
            f"- 划分理由：{_text(role.get('responsibility'))}；隐藏 {_text(role.get('hidden_secret'))}。",
            f"- 依据原则：{_cell(role.get('design_principles'))}。",
            f"- 业界来源：{_text(role.get('industry_basis'))}。",
            f"- 变化触发器：{_bullet(role.get('change_triggers'))}。",
            "",
        ])
    ui = contract.get("ui_architecture")
    if isinstance(ui, dict):
        lines.extend([
            "### UI 架构决策",
            "",
            f"- 框架：{_text(ui.get('framework'))}；当前模式：{_cell(ui.get('current_patterns'))}；目标模式：{_cell(ui.get('target_patterns'))}。",
            f"- 状态管理：{_text(ui.get('state_management'))}。",
            f"- MVVM 适用性：{_text(ui.get('mvvm_suitability'))}；迁移影响：{_text(ui.get('migration_impact'))}；确认：{_text(ui.get('migration_confirmation'))}。",
            f"- 决策理由：{_text(ui.get('decision_reason'))}。",
            "",
        ])

    lines.extend(["## 六、关键接口契约", ""])
    if not interfaces:
        lines.append("无跨角色接口。")
    for interface in interfaces:
        lines.extend([
            f"### {_text(interface.get('name'))}",
            "",
            f"- Provider：`{_text(interface.get('provider'))}`；Consumers：{_cell(interface.get('consumers'))}。",
            f"- 输入：{_text(interface.get('input'))}。",
            f"- 输出：{_text(interface.get('output'))}。",
            f"- 前置条件：{_bullet(interface.get('preconditions'))}。",
            f"- 后置条件：{_bullet(interface.get('postconditions'))}。",
            f"- 不变量：{_bullet(interface.get('invariants'))}。",
            f"- 错误：{_bullet(interface.get('errors'))}。",
            f"- 数据所有权：{_text(interface.get('data_ownership'))}。",
            f"- 事务：{_text(interface.get('transaction'))}；并发/取消：{_text(interface.get('concurrency'))}。",
            "",
        ])

    lines.extend(["## 七、验证证据", ""])
    for command in verification.get("commands") or []:
        if isinstance(command.get("argv"), list):
            execution = command.get("execution") or {}
            lines.append(
                f"- 命令 `{_text(command.get('id'))}` / `{_text(' '.join(command.get('argv')))}`："
                f"`{_text(command.get('status'))}`；exit={_text(execution.get('exit_code'))}；"
                f"耗时={_text(execution.get('duration_ms'))}ms；执行时间={_text(execution.get('executed_at'))}。"
                f"输入={_cell(command.get('inputs'))}；inputs_sha256={_text(execution.get('inputs_sha256'))}。"
            )
        else:
            lines.append(
                f"- 命令 `{_text(command.get('command'))}`：`{_text(command.get('status'))}`；"
                f"结果：{_text(command.get('result'))}；证据：{_text(command.get('evidence'))}。"
            )
    for check in verification.get("checks") or []:
        test_ref = f"；测试引用：{_text(check.get('test_ref'))}" if check.get("test_ref") else ""
        lines.append(
            f"- 检查 {_text(check.get('target'))}：`{_text(check.get('status'))}`；"
            f"方法：{_text(check.get('method'))}；证据：{_text(check.get('evidence'))}{test_ref}。"
        )

    traceability = contract.get("traceability") or []
    if traceability:
        lines.extend(["", "### 验收追踪", ""])
        for trace in traceability:
            lines.append(
                f"- `{_text(trace.get('id'))}`：{_text(trace.get('acceptance'))}；"
                f"角色={_cell(trace.get('role_ids'))}；接口={_cell(trace.get('interface_ids'))}；"
                f"测试={_text(trace.get('test_ref'))}；命令={_cell(trace.get('command_ids'))}。"
            )

    lines.extend(["", "## 八、原则复核", "", f"- {_text(gate.get('notes'))}"])
    review = contract.get("construction_review") or {}
    for item in review.get("items") or []:
        lines.append(
            f"- `{_text(item.get('principle'))}`：`{_text(item.get('status'))}`；"
            f"证据/理由：{_text(item.get('evidence'))}。"
        )
    if gap_count:
        lines.extend(["", "### 已知缺口 / 未决", ""])
        for item in questions:
            lines.append(
                f"- 问题：{_text(item.get('question', item.get('item')))}；"
                f"影响：{_text(item.get('impact'))}；后续阶段：{_text(item.get('follow_up'))}。"
            )
        for item in unverified:
            lines.append(
                f"- 未验证：{_text(item.get('item'))}；影响：{_text(item.get('impact'))}；"
                f"后续阶段：{_text(item.get('follow_up'))}。"
            )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render arch.md from design-contract.json")
    parser.add_argument("contract", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing output file")
    args = parser.parse_args()
    if not args.contract.exists():
        parser.error(f"contract does not exist: {args.contract}")
    if args.output.exists() and not args.force:
        parser.error(f"output exists: {args.output}; pass --force to overwrite")
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        parser.error(f"invalid JSON: {exc}")
    if not isinstance(contract, dict):
        parser.error("contract top level must be an object")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(contract), encoding="utf-8")
    print(f"rendered {args.output} from {args.contract}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
