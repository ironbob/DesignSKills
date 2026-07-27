#!/usr/bin/env python3
"""Validate the Full analysis.json contract."""
from __future__ import annotations

import argparse
from datetime import date
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

REQUIRED_TOP = (
    "mode", "target", "analyzed_at", "scope_confirmations",
    "languages", "language_analysis",
    "covered_files", "responsibility", "mechanism_type",
    "secondary_mechanism_types", "mechanism_type_basis", "chain_template",
    "chain_stages", "boundary_inventory", "behavior_cases",
    "acceptance_cases", "behavior_conflicts", "numerical_examples",
    "defects", "gaps",
)
MECH_TYPES = {"data-flow", "lifecycle", "call-chain", "state-machine", "other"}
CONFIDENCES = {"high", "medium", "low"}
WHY_BASES = {"observed", "inferred", "unknown"}
REQ_SOURCES = {"user", "roadmap", "issue", "code-evolution", "hypothetical"}
AXES = {"architecture", "logic"}
DIAG_TYPES = {"sequence", "flowchart", "state"}
SCOPE_TRIGGERS = {"initial", "material-expansion"}
WHY_SOURCE_TYPES = {"adr", "documentation", "issue", "explicit-comment"}
CHANGE_SCALES = {"small", "medium", "large"}
BOUNDARY_KINDS = {
    "empty-input", "lower-bound", "upper-bound", "invalid-input",
    "invalid-state", "terminal-sentinel", "cancellation", "exception",
    "timeout", "concurrency", "dynamic-resolution", "resource-limit", "custom",
}
BOUNDARY_STATUSES = {
    "verified", "partially-verified", "unverified", "not-applicable",
}
CASE_STATUSES = {"verified", "static-only", "not-run"}
CASE_METHODS = {
    "test", "command", "equivalent-evaluation", "inspection", "not-run",
}
RUNTIME_METHODS = {"test", "command", "equivalent-evaluation"}
VERIFICATION_LEVELS = {"automated", "manual"}
INTENT_STATUSES = {"intentional", "unintentional", "unknown"}
FORBIDDEN_KEYS = {"severity", "bug", "repro", "mermaid"}
TARGET_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SCOPE_RE = re.compile(r"^SCOPE-\d{2,}$")
STAGE_ID_RE = re.compile(r"^stage-[a-z0-9]+(?:-[a-z0-9]+)*$")
NUM_RE = re.compile(r"^NUM-\d{2,}$")
BOUNDARY_RE = re.compile(r"^BOUNDARY-\d{2,}$")
CASE_RE = re.compile(r"^CASE-\d{2,}$")
ACCEPT_RE = re.compile(r"^ACCEPT-\d{2,}$")
CONFLICT_RE = re.compile(r"^CONFLICT-\d{2,}$")
DEBT_RE = re.compile(r"^DEBT-(ARCH|LOGIC)-\d{2,}$")
DIAGRAM_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
UNKNOWN_WHY_RE = re.compile(
    r"无法(?:证明|确认)|代码(?:无法|未能)|(?:未|没有)记录.*(?:意图|原因)|"
    r"cannot (?:prove|confirm)|not documented|unknown",
    re.I,
)

TOP_KEYS = set(REQUIRED_TOP) | {"diagrams"}
SCOPE_KEYS = {
    "id", "confirmed_at", "trigger", "target", "mechanism_type",
    "responsibility", "candidate_files", "confirmation_basis",
}
LANGUAGE_KEYS = {"language", "confidence", "basis", "tools"}
STAGE_KEYS = {
    "id", "segment", "name", "what", "how", "why", "why_basis",
    "why_evidence", "key_structures", "numerical", "handoff",
    "handoff_evidence", "evidence",
}
BOUNDARY_KEYS = {
    "id", "kind", "condition", "expected_contract", "observed_behavior",
    "status", "behavior_case_ids", "source_anchors",
}
CASE_KEYS = {
    "id", "title", "boundary_ids", "entry_point", "branch_path",
    "preconditions", "input", "action", "expected_observable",
    "observed_observable", "verification", "source_anchors",
    "acceptance_case_ids",
}
VERIFICATION_KEYS = {"status", "method", "procedure", "observed_result"}
ACCEPTANCE_KEYS = {
    "id", "title", "behavior_case_ids", "given", "when", "then",
    "verification_level", "source_anchors",
}
CONFLICT_KEYS = {
    "id", "title", "case_ids", "comparison_dimension", "contradiction",
    "impact", "intent_status", "resolution", "source_anchors",
}
NUMERICAL_KEYS = {
    "id", "stage_id", "operation", "sample_data", "computation_steps",
    "result", "code_translation", "faithfulness_note", "evidence",
}
DEFECT_KEYS = {
    "id", "axis", "stage_id", "cross_stage", "title",
    "requirement_source", "hard_requirement", "why_hard",
    "evolution_direction", "cost_impact", "cost_quantification",
    "confidence", "confidence_basis", "evidence",
}
COST_KEYS = {
    "affected_stages", "affected_files", "affected_modules",
    "change_scale", "basis",
}
EVIDENCE_KEYS = {"file", "line", "note"}
WHY_EVIDENCE_KEYS = EVIDENCE_KEYS | {"source_type"}
DIAGRAM_KEYS = {"applicable", "type", "nodes", "edges", "reason"}
NODE_KEYS = {"id", "label", "evidence"}
EDGE_KEYS = {"from", "to", "label", "evidence"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.passed: list[str] = []

    def check(self, rule: str, condition: bool, ok: str, error: str) -> None:
        (self.passed if condition else self.errors).append(
            f"{'✅' if condition else '🔴'} [{rule}] {ok if condition else error}"
        )


def nonempty(value: Any, minimum: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def string_list(value: Any, *, required: bool = False, unique: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not required or bool(value))
        and all(nonempty(item) for item in value)
        and (not unique or len(value) == len(set(value)))
    )


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
    raw_parts = value.split("/")
    return (
        value == value.strip()
        and not path.is_absolute()
        and all(part not in {"", ".", ".."} for part in raw_parts)
    )


def exact_keys(value: Any, allowed: set[str]) -> bool:
    return isinstance(value, dict) and not (set(value) - allowed)


def single_line(value: Any, minimum: int = 1) -> bool:
    return nonempty(value, minimum) and "\n" not in value and "\r" not in value


def evidence_ok(
    value: Any,
    covered: set[str],
    *,
    required: bool = True,
    why: bool = False,
) -> bool:
    allowed = WHY_EVIDENCE_KEYS if why else EVIDENCE_KEYS
    return (
        isinstance(value, list)
        and (bool(value) or not required)
        and all(
            isinstance(item, dict)
            and exact_keys(item, allowed)
            and nonempty(item.get("file"))
            and repo_relative_path(item.get("file"))
            and item.get("file") in covered
            and type(item.get("line")) is int
            and item["line"] > 0
            and nonempty(item.get("note"), 4)
            and (not why or item.get("source_type") in WHY_SOURCE_TYPES)
            for item in value
        )
    )


def find_forbidden(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_KEYS:
                found.append(f"{path}.{key}")
            found.extend(find_forbidden(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(find_forbidden(child, f"{path}[{index}]"))
    return found


def validate(data: Any) -> Report:
    r = Report()
    if not isinstance(data, dict):
        r.check("TOP", False, "", "顶层必须是 JSON object")
        return r

    missing = [key for key in REQUIRED_TOP if key not in data]
    r.check("TOP.REQUIRED", not missing, "顶层字段齐全", f"缺顶层字段：{missing}")
    unknown_top = sorted(set(data) - TOP_KEYS)
    r.check("TOP.KEYS", not unknown_top, "顶层无未知字段", f"顶层出现未知字段：{unknown_top}")
    r.check("TOP.MODE", data.get("mode") == "full", "mode=full", "Full JSON 的 mode 必须为 full")
    r.check(
        "TOP.TARGET",
        isinstance(data.get("target"), str) and bool(TARGET_RE.fullmatch(data["target"])),
        f"target={data.get('target')}",
        "target 必须为 kebab-case",
    )
    date_ok = exact_date(data.get("analyzed_at"))
    r.check("TOP.DATE", date_ok, "日期合法", "analyzed_at 必须为 YYYY-MM-DD")
    r.check("TOP.RESP", nonempty(data.get("responsibility"), 8), "职责已填写", "responsibility 过短或为空")

    scope_confirmations = data.get("scope_confirmations")
    scopes_ok = isinstance(scope_confirmations, list) and bool(scope_confirmations)
    r.check(
        "SCOPE.LIST",
        scopes_ok,
        "scope_confirmations 非空",
        "Full 必须记录至少一次范围确认",
    )
    scope_confirmations = scope_confirmations if scopes_ok else []
    scope_ids: list[str] = []
    for index, scope in enumerate(scope_confirmations):
        prefix = f"SCOPE[{index}]"
        if not isinstance(scope, dict):
            r.check(prefix, False, "", "范围确认必须为 object")
            continue
        unknown = sorted(set(scope) - SCOPE_KEYS)
        r.check(f"{prefix}.KEYS", not unknown, "字段闭合", f"未知字段：{unknown}")
        scope_id = scope.get("id")
        scope_id_ok = isinstance(scope_id, str) and bool(SCOPE_RE.fullmatch(scope_id))
        r.check(f"{prefix}.ID", scope_id_ok, f"id={scope_id}", "id 必须匹配 SCOPE-NN")
        if scope_id_ok:
            scope_ids.append(scope_id)
        r.check(
            f"{prefix}.DATE",
            exact_date(scope.get("confirmed_at")),
            "确认日期合法",
            "confirmed_at 必须为 YYYY-MM-DD",
        )
        r.check(
            f"{prefix}.TRIGGER",
            scope.get("trigger") in SCOPE_TRIGGERS,
            f"trigger={scope.get('trigger')}",
            "trigger 必须为 initial/material-expansion",
        )
        r.check(
            f"{prefix}.TARGET",
            isinstance(scope.get("target"), str)
            and bool(TARGET_RE.fullmatch(scope["target"])),
            "target 合法",
            "target 必须为 kebab-case",
        )
        r.check(
            f"{prefix}.TYPE",
            scope.get("mechanism_type") in MECH_TYPES,
            "机制类型合法",
            "mechanism_type 非法",
        )
        r.check(
            f"{prefix}.RESP",
            nonempty(scope.get("responsibility"), 8),
            "候选职责已记录",
            "responsibility 过短或为空",
        )
        candidate_files = scope.get("candidate_files")
        candidates_ok = (
            string_list(candidate_files, required=True, unique=True)
            and all(repo_relative_path(item) for item in candidate_files)
        )
        r.check(
            f"{prefix}.FILES",
            candidates_ok,
            "候选文件合法",
            "candidate_files 必须为非空、唯一的 repo-root 相对路径",
        )
        r.check(
            f"{prefix}.BASIS",
            nonempty(scope.get("confirmation_basis"), 8),
            "确认依据已记录",
            "confirmation_basis 过短或为空",
        )
    r.check(
        "SCOPE.IDS",
        len(scope_ids) == len(scope_confirmations) == len(set(scope_ids)),
        "范围确认 id 完整且唯一",
        "范围确认 id 缺失、非法或重复",
    )
    if scope_confirmations:
        triggers = [
            scope.get("trigger") if isinstance(scope, dict) else None
            for scope in scope_confirmations
        ]
        r.check(
            "SCOPE.ORDER",
            triggers[0] == "initial"
            and all(trigger == "material-expansion" for trigger in triggers[1:]),
            "范围确认顺序合法",
            "第一条必须为 initial，后续记录必须为 material-expansion",
        )
    if scope_confirmations and isinstance(scope_confirmations[-1], dict):
        latest = scope_confirmations[-1]
        latest_matches = (
            latest.get("target") == data.get("target")
            and latest.get("mechanism_type") == data.get("mechanism_type")
            and latest.get("responsibility") == data.get("responsibility")
        )
        r.check(
            "SCOPE.LATEST",
            latest_matches,
            "最后一次确认与当前范围一致",
            "最后一次范围确认的 target/type/responsibility 与顶层不一致",
        )

    languages = data.get("languages")
    lang_ok = string_list(languages, required=True, unique=True)
    r.check("LANG.LIST", lang_ok, "languages 非空且唯一", "languages 必须是非空、不重复字符串数组")
    analyses = data.get("language_analysis")
    analysis_ok = isinstance(analyses, list) and bool(analyses) and all(
        isinstance(item, dict)
        and exact_keys(item, LANGUAGE_KEYS)
        and nonempty(item.get("language"))
        and item.get("confidence") in CONFIDENCES
        and nonempty(item.get("basis"), 8)
        and string_list(item.get("tools"), required=True, unique=True)
        for item in analyses
    )
    r.check("LANG.ANALYSIS", analysis_ok, "language_analysis 结构合法", "language_analysis 字段不完整")
    if lang_ok and analysis_ok:
        analyzed_languages = [item["language"] for item in analyses]
        r.check(
            "LANG.MATCH",
            len(analyzed_languages) == len(set(analyzed_languages))
            and set(analyzed_languages) == set(languages),
            "language_analysis 与 languages 一一对应",
            "language_analysis 与 languages 不一致或重复",
        )

    covered_files = data.get("covered_files")
    covered_ok = (
        string_list(covered_files, required=True, unique=True)
        and all(repo_relative_path(item) for item in covered_files)
    )
    r.check("COVERED", covered_ok, "covered_files 非空且唯一", "covered_files 必须是非空、不重复字符串数组")
    covered = set(covered_files) if covered_ok else set()

    mechanism_type = data.get("mechanism_type")
    r.check("TYPE.PRIMARY", mechanism_type in MECH_TYPES, f"主类型={mechanism_type}", "mechanism_type 非法")
    secondary = data.get("secondary_mechanism_types")
    secondary_ok = string_list(secondary, unique=True) and all(item in MECH_TYPES for item in secondary or [])
    r.check("TYPE.SECONDARY", secondary_ok, "次类型合法", "secondary_mechanism_types 非法或重复")
    if secondary_ok:
        r.check("TYPE.DISTINCT", mechanism_type not in secondary, "主次类型不重复", "次类型不得重复主类型")
    r.check("TYPE.BASIS", nonempty(data.get("mechanism_type_basis"), 12), "类型依据已填写", "mechanism_type_basis 过短或为空")

    template = data.get("chain_template")
    template_ok = string_list(template, required=True, unique=True)
    r.check("CHAIN.TEMPLATE", template_ok, "chain_template 非空且唯一", "chain_template 必须非空且阶段名不重复")
    stages = data.get("chain_stages")
    stages_ok = isinstance(stages, list) and bool(stages)
    r.check("CHAIN.STAGES", stages_ok, "chain_stages 非空", "chain_stages 必须为非空数组")
    stages = stages if stages_ok else []
    stage_ids: list[str] = []
    segments: list[str] = []
    numerical_stages: set[str] = set()
    for index, stage in enumerate(stages):
        prefix = f"CHAIN[{index}]"
        if not isinstance(stage, dict):
            r.check(prefix, False, "", "阶段必须为 object")
            continue
        unknown = sorted(set(stage) - STAGE_KEYS)
        r.check(f"{prefix}.KEYS", not unknown, "字段闭合", f"未知字段：{unknown}")
        stage_id = stage.get("id")
        id_ok = isinstance(stage_id, str) and bool(STAGE_ID_RE.fullmatch(stage_id))
        r.check(f"{prefix}.ID", id_ok, f"id={stage_id}", "阶段 id 非法")
        if id_ok:
            stage_ids.append(stage_id)
        segment = stage.get("segment")
        segments.append(segment)
        r.check(
            f"{prefix}.SEGMENT",
            nonempty(segment),
            f"segment={segment}",
            "segment 不能为空",
        )
        for field in ("name", "what", "how", "why", "handoff"):
            r.check(
                f"{prefix}.{field.upper()}",
                nonempty(stage.get(field), 4),
                f"{field} 已填写",
                f"{field} 过短或为空",
            )
        r.check(
            f"{prefix}.WHY_BASIS",
            stage.get("why_basis") in WHY_BASES,
            f"why_basis={stage.get('why_basis')}",
            "why_basis 必须为 observed/inferred/unknown",
        )
        why_basis = stage.get("why_basis")
        why_evidence = stage.get("why_evidence")
        if why_basis == "observed":
            why_ok = evidence_ok(why_evidence, covered, why=True)
            why_message = "observed 必须提供带 source_type 的直接设计意图证据"
        else:
            why_ok = evidence_ok(why_evidence, covered, required=False, why=True) and not why_evidence
            why_message = "inferred/unknown 的 why_evidence 必须为空"
        r.check(
            f"{prefix}.WHY_EVIDENCE",
            why_ok,
            "why_evidence 与依据类型一致",
            why_message,
        )
        if why_basis == "unknown":
            r.check(
                f"{prefix}.WHY_UNKNOWN",
                isinstance(stage.get("why"), str)
                and bool(UNKNOWN_WHY_RE.search(stage["why"])),
                "unknown 明确说明无法证明设计意图",
                "why_basis=unknown 时 why 必须明确说明代码无法证明设计意图",
            )
        r.check(
            f"{prefix}.STRUCTURES",
            string_list(stage.get("key_structures"), required=True, unique=True),
            "key_structures 合法",
            "key_structures 必须非空且不重复",
        )
        numerical = stage.get("numerical")
        r.check(f"{prefix}.NUMERICAL", isinstance(numerical, bool), f"numerical={numerical}", "numerical 必须为 bool")
        r.check(
            f"{prefix}.EVIDENCE",
            evidence_ok(stage.get("evidence"), covered),
            "evidence 合法",
            "evidence 必须含 covered_files 内的 file、正整数 line 和具体 note",
        )
        r.check(
            f"{prefix}.HANDOFF_EVIDENCE",
            evidence_ok(stage.get("handoff_evidence"), covered),
            "handoff_evidence 合法",
            "handoff_evidence 必须为交接或最终效果提供独立证据",
        )
        if numerical is True and id_ok:
            numerical_stages.add(stage_id)

    r.check("CHAIN.IDS", len(stage_ids) == len(set(stage_ids)), "阶段 id 唯一", "阶段 id 重复")
    if template_ok and stages_ok:
        r.check(
            "CHAIN.EXACT",
            segments == template,
            "chain_template 与 stages 按顺序一一对应",
            f"链路不一致：template={template} stages={segments}",
        )
    valid_stage_ids = set(stage_ids)

    boundaries = data.get("boundary_inventory")
    boundaries_ok = isinstance(boundaries, list) and bool(boundaries)
    r.check(
        "BOUNDARY.LIST",
        boundaries_ok,
        "boundary_inventory 非空",
        "boundary_inventory 必须为非空数组",
    )
    boundaries = boundaries if boundaries_ok else []
    boundary_ids: list[str] = []
    boundary_case_refs: dict[str, set[str]] = {}
    for index, boundary in enumerate(boundaries):
        prefix = f"BOUNDARY[{index}]"
        if not isinstance(boundary, dict):
            r.check(prefix, False, "", "边界项必须为 object")
            continue
        unknown = sorted(set(boundary) - BOUNDARY_KEYS)
        r.check(f"{prefix}.KEYS", not unknown, "字段闭合", f"未知字段：{unknown}")
        boundary_id = boundary.get("id")
        id_ok = isinstance(boundary_id, str) and bool(BOUNDARY_RE.fullmatch(boundary_id))
        r.check(f"{prefix}.ID", id_ok, f"id={boundary_id}", "id 必须匹配 BOUNDARY-NN")
        if id_ok:
            boundary_ids.append(boundary_id)
        r.check(
            f"{prefix}.KIND",
            boundary.get("kind") in BOUNDARY_KINDS,
            f"kind={boundary.get('kind')}",
            "kind 非法",
        )
        for field in ("condition", "expected_contract", "observed_behavior"):
            r.check(
                f"{prefix}.{field.upper()}",
                nonempty(boundary.get(field), 6),
                f"{field} 已填写",
                f"{field} 过短或为空",
            )
        status = boundary.get("status")
        r.check(
            f"{prefix}.STATUS",
            status in BOUNDARY_STATUSES,
            f"status={status}",
            "status 必须为 verified/partially-verified/unverified/not-applicable",
        )
        case_refs = boundary.get("behavior_case_ids")
        case_refs_ok = string_list(case_refs, unique=True)
        r.check(
            f"{prefix}.CASE_REFS",
            case_refs_ok
            and (
                status not in {"verified", "partially-verified"}
                or bool(case_refs)
            )
            and (status != "not-applicable" or not case_refs),
            "行为用例引用与状态一致",
            "behavior_case_ids 非法；已验证边界必须关联用例，不适用边界不得关联用例",
        )
        if id_ok and case_refs_ok:
            boundary_case_refs[boundary_id] = set(case_refs)
        anchors = boundary.get("source_anchors")
        anchors_ok = evidence_ok(
            anchors,
            covered,
            required=status != "not-applicable",
        )
        r.check(
            f"{prefix}.ANCHORS",
            anchors_ok and (status != "not-applicable" or not anchors),
            "源码锚点与状态一致",
            "source_anchors 非法；除 not-applicable 外必须非空，不适用边界必须为空",
        )
    r.check(
        "BOUNDARY.IDS",
        len(boundary_ids) == len(boundaries) == len(set(boundary_ids)),
        "BOUNDARY id 完整且唯一",
        "BOUNDARY id 缺失、非法或重复",
    )
    valid_boundary_ids = set(boundary_ids)

    behavior_cases = data.get("behavior_cases")
    cases_ok = isinstance(behavior_cases, list) and bool(behavior_cases)
    r.check(
        "CASE.LIST",
        cases_ok,
        "behavior_cases 非空",
        "behavior_cases 必须为非空数组",
    )
    behavior_cases = behavior_cases if cases_ok else []
    case_ids: list[str] = []
    case_boundary_refs: dict[str, set[str]] = {}
    case_acceptance_refs: dict[str, set[str]] = {}
    case_routes: dict[str, tuple[str, str]] = {}
    for index, case in enumerate(behavior_cases):
        prefix = f"CASE[{index}]"
        if not isinstance(case, dict):
            r.check(prefix, False, "", "行为用例必须为 object")
            continue
        unknown = sorted(set(case) - CASE_KEYS)
        r.check(f"{prefix}.KEYS", not unknown, "字段闭合", f"未知字段：{unknown}")
        case_id = case.get("id")
        id_ok = isinstance(case_id, str) and bool(CASE_RE.fullmatch(case_id))
        r.check(f"{prefix}.ID", id_ok, f"id={case_id}", "id 必须匹配 CASE-NN")
        if id_ok:
            case_ids.append(case_id)
        for field in (
            "title", "entry_point", "branch_path", "input", "action",
            "expected_observable", "observed_observable",
        ):
            r.check(
                f"{prefix}.{field.upper()}",
                nonempty(case.get(field), 4),
                f"{field} 已填写",
                f"{field} 过短或为空",
            )
        r.check(
            f"{prefix}.PRECONDITIONS",
            string_list(case.get("preconditions"), required=True, unique=True),
            "preconditions 非空且唯一",
            "preconditions 必须为非空、不重复字符串数组",
        )
        boundary_refs = case.get("boundary_ids")
        boundary_refs_ok = (
            string_list(boundary_refs, unique=True)
            and set(boundary_refs) <= valid_boundary_ids
        )
        r.check(
            f"{prefix}.BOUNDARIES",
            boundary_refs_ok,
            "边界引用合法",
            "boundary_ids 必须唯一并引用真实 BOUNDARY",
        )
        if id_ok and boundary_refs_ok:
            case_boundary_refs[case_id] = set(boundary_refs)
        acceptance_refs = case.get("acceptance_case_ids")
        acceptance_refs_ok = string_list(
            acceptance_refs, required=True, unique=True
        )
        r.check(
            f"{prefix}.ACCEPTANCE_REFS",
            acceptance_refs_ok,
            "验收用例引用非空且唯一",
            "acceptance_case_ids 必须为非空、不重复字符串数组",
        )
        if id_ok and acceptance_refs_ok:
            case_acceptance_refs[case_id] = set(acceptance_refs)
        verification = case.get("verification")
        verification_ok = (
            isinstance(verification, dict)
            and exact_keys(verification, VERIFICATION_KEYS)
        )
        r.check(
            f"{prefix}.VERIFICATION_KEYS",
            verification_ok,
            "verification 字段闭合",
            "verification 缺失、类型非法或含未知字段",
        )
        verification = verification if isinstance(verification, dict) else {}
        status = verification.get("status")
        method = verification.get("method")
        status_method_ok = (
            status in CASE_STATUSES
            and method in CASE_METHODS
            and (
                (status == "verified" and method in RUNTIME_METHODS)
                or (status == "static-only" and method == "inspection")
                or (status == "not-run" and method == "not-run")
            )
        )
        r.check(
            f"{prefix}.VERIFICATION_MODE",
            status_method_ok,
            f"status={status}, method={method}",
            "verification.status 与 method 不匹配",
        )
        r.check(
            f"{prefix}.VERIFICATION_DETAIL",
            nonempty(verification.get("procedure"), 8)
            and nonempty(verification.get("observed_result"), 6),
            "验证步骤和结果已填写",
            "verification.procedure/observed_result 过短或为空",
        )
        r.check(
            f"{prefix}.ANCHORS",
            evidence_ok(case.get("source_anchors"), covered),
            "源码锚点合法",
            "source_anchors 必须含 covered_files 内的 file、line、note",
        )
        if id_ok and nonempty(case.get("entry_point")) and nonempty(case.get("branch_path")):
            case_routes[case_id] = (case["entry_point"], case["branch_path"])
    r.check(
        "CASE.IDS",
        len(case_ids) == len(behavior_cases) == len(set(case_ids)),
        "CASE id 完整且唯一",
        "CASE id 缺失、非法或重复",
    )
    valid_case_ids = set(case_ids)

    acceptance_cases = data.get("acceptance_cases")
    acceptance_ok = isinstance(acceptance_cases, list) and bool(acceptance_cases)
    r.check(
        "ACCEPT.LIST",
        acceptance_ok,
        "acceptance_cases 非空",
        "acceptance_cases 必须为非空数组",
    )
    acceptance_cases = acceptance_cases if acceptance_ok else []
    acceptance_ids: list[str] = []
    acceptance_case_refs: dict[str, set[str]] = {}
    for index, acceptance in enumerate(acceptance_cases):
        prefix = f"ACCEPT[{index}]"
        if not isinstance(acceptance, dict):
            r.check(prefix, False, "", "验收用例必须为 object")
            continue
        unknown = sorted(set(acceptance) - ACCEPTANCE_KEYS)
        r.check(f"{prefix}.KEYS", not unknown, "字段闭合", f"未知字段：{unknown}")
        acceptance_id = acceptance.get("id")
        id_ok = (
            isinstance(acceptance_id, str)
            and bool(ACCEPT_RE.fullmatch(acceptance_id))
        )
        r.check(f"{prefix}.ID", id_ok, f"id={acceptance_id}", "id 必须匹配 ACCEPT-NN")
        if id_ok:
            acceptance_ids.append(acceptance_id)
        case_refs = acceptance.get("behavior_case_ids")
        refs_ok = (
            string_list(case_refs, required=True, unique=True)
            and set(case_refs) <= valid_case_ids
        )
        r.check(
            f"{prefix}.CASE_REFS",
            refs_ok,
            "行为用例引用合法",
            "behavior_case_ids 必须非空、唯一并引用真实 CASE",
        )
        if id_ok and refs_ok:
            acceptance_case_refs[acceptance_id] = set(case_refs)
        for field in ("title", "given", "when", "then"):
            r.check(
                f"{prefix}.{field.upper()}",
                nonempty(acceptance.get(field), 6),
                f"{field} 已填写",
                f"{field} 过短或为空",
            )
        r.check(
            f"{prefix}.LEVEL",
            acceptance.get("verification_level") in VERIFICATION_LEVELS,
            f"verification_level={acceptance.get('verification_level')}",
            "verification_level 必须为 automated/manual",
        )
        r.check(
            f"{prefix}.ANCHORS",
            evidence_ok(acceptance.get("source_anchors"), covered),
            "源码锚点合法",
            "source_anchors 必须含 covered_files 内的 file、line、note",
        )
    r.check(
        "ACCEPT.IDS",
        len(acceptance_ids) == len(acceptance_cases) == len(set(acceptance_ids)),
        "ACCEPT id 完整且唯一",
        "ACCEPT id 缺失、非法或重复",
    )
    valid_acceptance_ids = set(acceptance_ids)

    for boundary_id, refs in boundary_case_refs.items():
        valid_refs = refs <= valid_case_ids
        reciprocal = valid_refs and all(
            boundary_id in case_boundary_refs.get(case_id, set())
            for case_id in refs
        )
        r.check(
            f"TRACE.{boundary_id}",
            reciprocal,
            "边界与行为用例双向一致",
            "边界引用未知 CASE，或 CASE.boundary_ids 未回指",
        )
    for case_id, refs in case_boundary_refs.items():
        reciprocal = all(
            case_id in boundary_case_refs.get(boundary_id, set())
            for boundary_id in refs
        )
        r.check(
            f"TRACE.{case_id}.BOUNDARY",
            reciprocal,
            "行为用例与边界双向一致",
            "CASE.boundary_ids 与 BOUNDARY.behavior_case_ids 不一致",
        )
    for case_id, refs in case_acceptance_refs.items():
        valid_refs = refs <= valid_acceptance_ids
        reciprocal = valid_refs and all(
            case_id in acceptance_case_refs.get(acceptance_id, set())
            for acceptance_id in refs
        )
        r.check(
            f"TRACE.{case_id}.ACCEPT",
            reciprocal,
            "行为用例与验收用例双向一致",
            "CASE 引用未知 ACCEPT，或 ACCEPT.behavior_case_ids 未回指",
        )
    for acceptance_id, refs in acceptance_case_refs.items():
        reciprocal = all(
            acceptance_id in case_acceptance_refs.get(case_id, set())
            for case_id in refs
        )
        r.check(
            f"TRACE.{acceptance_id}",
            reciprocal,
            "验收用例与行为用例双向一致",
            "ACCEPT.behavior_case_ids 与 CASE.acceptance_case_ids 不一致",
        )

    conflicts = data.get("behavior_conflicts")
    conflicts_ok = isinstance(conflicts, list)
    r.check(
        "CONFLICT.LIST",
        conflicts_ok,
        "behavior_conflicts 是数组",
        "behavior_conflicts 必须为数组",
    )
    conflicts = conflicts if conflicts_ok else []
    conflict_ids: list[str] = []
    for index, conflict in enumerate(conflicts):
        prefix = f"CONFLICT[{index}]"
        if not isinstance(conflict, dict):
            r.check(prefix, False, "", "矛盾记录必须为 object")
            continue
        unknown = sorted(set(conflict) - CONFLICT_KEYS)
        r.check(f"{prefix}.KEYS", not unknown, "字段闭合", f"未知字段：{unknown}")
        conflict_id = conflict.get("id")
        id_ok = isinstance(conflict_id, str) and bool(CONFLICT_RE.fullmatch(conflict_id))
        r.check(f"{prefix}.ID", id_ok, f"id={conflict_id}", "id 必须匹配 CONFLICT-NN")
        if id_ok:
            conflict_ids.append(conflict_id)
        refs = conflict.get("case_ids")
        refs_ok = (
            string_list(refs, required=True, unique=True)
            and len(refs) >= 2
            and set(refs) <= valid_case_ids
        )
        r.check(
            f"{prefix}.CASE_REFS",
            refs_ok,
            "至少引用两个真实行为用例",
            "case_ids 必须至少含两个不同且真实的 CASE",
        )
        ref_items = refs if isinstance(refs, list) else []
        routes = {case_routes[item] for item in ref_items if item in case_routes}
        r.check(
            f"{prefix}.ROUTES",
            refs_ok and len(routes) >= 2,
            "引用用例来自不同入口或分支",
            "矛盾必须比较至少两个不同 (entry_point, branch_path)",
        )
        for field in (
            "title", "comparison_dimension", "contradiction", "impact", "resolution",
        ):
            r.check(
                f"{prefix}.{field.upper()}",
                nonempty(conflict.get(field), 6),
                f"{field} 已填写",
                f"{field} 过短或为空",
            )
        r.check(
            f"{prefix}.INTENT",
            conflict.get("intent_status") in INTENT_STATUSES,
            f"intent_status={conflict.get('intent_status')}",
            "intent_status 必须为 intentional/unintentional/unknown",
        )
        r.check(
            f"{prefix}.ANCHORS",
            evidence_ok(conflict.get("source_anchors"), covered),
            "源码锚点合法",
            "source_anchors 必须支持矛盾两侧行为",
        )
    r.check(
        "CONFLICT.IDS",
        len(conflict_ids) == len(conflicts) == len(set(conflict_ids)),
        "CONFLICT id 完整且唯一",
        "CONFLICT id 缺失、非法或重复",
    )

    examples = data.get("numerical_examples")
    examples_ok = isinstance(examples, list)
    r.check("NUM.LIST", examples_ok, "numerical_examples 是数组", "numerical_examples 必须为数组")
    examples = examples if examples_ok else []
    numerical_ids: list[str] = []
    covered_numerical_stages: set[str] = set()
    for index, example in enumerate(examples):
        prefix = f"NUM[{index}]"
        if not isinstance(example, dict):
            r.check(prefix, False, "", "数值示例必须为 object")
            continue
        unknown = sorted(set(example) - NUMERICAL_KEYS)
        r.check(f"{prefix}.KEYS", not unknown, "字段闭合", f"未知字段：{unknown}")
        example_id = example.get("id")
        id_ok = isinstance(example_id, str) and bool(NUM_RE.fullmatch(example_id))
        r.check(f"{prefix}.ID", id_ok, f"id={example_id}", "数值示例 id 必须完整匹配 NUM-NN")
        if id_ok:
            numerical_ids.append(example_id)
        stage_id = example.get("stage_id")
        r.check(f"{prefix}.STAGE", stage_id in numerical_stages, f"stage_id={stage_id}", "stage_id 必须引用 numerical=true 阶段")
        if stage_id in numerical_stages:
            covered_numerical_stages.add(stage_id)
        for field in ("operation", "sample_data", "result", "faithfulness_note"):
            r.check(f"{prefix}.{field.upper()}", nonempty(example.get(field), 6), f"{field} 已填写", f"{field} 过短或为空")
        steps = example.get("computation_steps")
        r.check(
            f"{prefix}.STEPS",
            string_list(steps, required=True) and len(steps) >= 2,
            "计算步骤不少于两步",
            "computation_steps 至少需要两个非空步骤",
        )
        r.check(
            f"{prefix}.EVIDENCE",
            evidence_ok(example.get("evidence"), covered),
            "evidence 合法",
            "数值示例 evidence 非法",
        )
    r.check("NUM.IDS", len(numerical_ids) == len(set(numerical_ids)), "NUM id 唯一", "NUM id 重复")
    r.check(
        "NUM.COVERAGE",
        covered_numerical_stages == numerical_stages,
        "所有数值阶段均有示例",
        f"数值阶段覆盖不完整：缺 {sorted(numerical_stages - covered_numerical_stages)}",
    )

    defects = data.get("defects")
    defects_ok = isinstance(defects, list)
    r.check("DEBT.LIST", defects_ok, "defects 是数组", "defects 必须为数组")
    defects = defects if defects_ok else []
    debt_ids: list[str] = []
    for index, defect in enumerate(defects):
        prefix = f"DEBT[{index}]"
        if not isinstance(defect, dict):
            r.check(prefix, False, "", "设计债必须为 object")
            continue
        unknown = sorted(set(defect) - DEFECT_KEYS)
        r.check(f"{prefix}.KEYS", not unknown, "字段闭合", f"未知字段：{unknown}")
        defect_id = defect.get("id")
        match = DEBT_RE.fullmatch(defect_id) if isinstance(defect_id, str) else None
        r.check(f"{prefix}.ID", bool(match), f"id={defect_id}", "设计债 id 必须完整匹配 DEBT-ARCH/LOGIC-NN")
        if match:
            debt_ids.append(defect_id)
            expected_axis = "architecture" if match.group(1) == "ARCH" else "logic"
            r.check(f"{prefix}.AXIS_ID", defect.get("axis") == expected_axis, "axis 与 id 一致", "axis 与 id 前缀不一致")
        r.check(f"{prefix}.AXIS", defect.get("axis") in AXES, f"axis={defect.get('axis')}", "axis 非法")
        r.check(f"{prefix}.STAGE", defect.get("stage_id") in valid_stage_ids, "stage_id 有效", "stage_id 未引用真实阶段")
        r.check(f"{prefix}.CROSS", isinstance(defect.get("cross_stage"), bool), "cross_stage 合法", "cross_stage 必须为 bool")
        r.check(
            f"{prefix}.SOURCE",
            defect.get("requirement_source") in REQ_SOURCES,
            f"source={defect.get('requirement_source')}",
            "requirement_source 非法",
        )
        for field in (
            "title", "hard_requirement", "why_hard", "evolution_direction",
            "cost_impact", "confidence_basis",
        ):
            r.check(f"{prefix}.{field.upper()}", nonempty(defect.get(field), 6), f"{field} 已填写", f"{field} 过短或为空")
        r.check(
            f"{prefix}.CONFIDENCE",
            defect.get("confidence") in CONFIDENCES,
            f"confidence={defect.get('confidence')}",
            "confidence 必须为 high/medium/low",
        )
        cost = defect.get("cost_quantification")
        cost_keys_ok = isinstance(cost, dict) and exact_keys(cost, COST_KEYS)
        r.check(
            f"{prefix}.COST_KEYS",
            cost_keys_ok,
            "cost_quantification 字段闭合",
            "cost_quantification 缺失、类型非法或含未知字段",
        )
        cost = cost if isinstance(cost, dict) else {}
        affected_stages = cost.get("affected_stages")
        affected_files = cost.get("affected_files")
        affected_modules = cost.get("affected_modules")
        r.check(
            f"{prefix}.COST_STAGES",
            string_list(affected_stages, required=True, unique=True)
            and set(affected_stages) <= valid_stage_ids
            and defect.get("stage_id") in affected_stages
            and (
                not defect.get("cross_stage")
                or len(affected_stages) >= 2
            ),
            "受影响阶段合法",
            "affected_stages 必须包含所属阶段；cross_stage=true 时至少包含两个真实阶段",
        )
        r.check(
            f"{prefix}.COST_FILES",
            string_list(affected_files, required=True, unique=True)
            and set(affected_files) <= covered,
            "受影响文件合法",
            "affected_files 必须非空、唯一并属于 covered_files",
        )
        r.check(
            f"{prefix}.COST_MODULES",
            string_list(affected_modules, unique=True),
            "受影响模块合法",
            "affected_modules 必须为不重复字符串数组",
        )
        r.check(
            f"{prefix}.COST_SCALE",
            cost.get("change_scale") in CHANGE_SCALES,
            f"change_scale={cost.get('change_scale')}",
            "change_scale 必须为 small/medium/large",
        )
        r.check(
            f"{prefix}.COST_BASIS",
            nonempty(cost.get("basis"), 8),
            "量化依据已填写",
            "cost_quantification.basis 过短或为空",
        )
        r.check(
            f"{prefix}.EVIDENCE",
            evidence_ok(defect.get("evidence"), covered),
            "evidence 合法",
            "设计债 evidence 非法",
        )
    r.check("DEBT.IDS", len(debt_ids) == len(set(debt_ids)), "DEBT id 唯一", "DEBT id 重复")

    gaps = data.get("gaps")
    r.check("GAPS", string_list(gaps, unique=True), "gaps 合法且唯一", "gaps 必须为不重复字符串数组")

    diagram = data.get("diagrams")
    if diagram is not None:
        diagram_ok = (
            isinstance(diagram, dict)
            and exact_keys(diagram, DIAGRAM_KEYS)
            and isinstance(diagram.get("applicable"), bool)
        )
        r.check("DIAGRAM", diagram_ok, "diagrams 基础结构合法", "diagrams 必须含 bool applicable")
        if diagram_ok and diagram["applicable"]:
            nodes = diagram.get("nodes")
            edges = diagram.get("edges")
            node_ok = isinstance(nodes, list) and bool(nodes)
            edge_ok = isinstance(edges, list)
            r.check("DIAGRAM.TYPE", diagram.get("type") in DIAG_TYPES, "图类型合法", "图类型非法")
            r.check("DIAGRAM.NODES", node_ok, "nodes 非空", "nodes 必须非空")
            r.check("DIAGRAM.EDGES", edge_ok, "edges 是数组", "edges 必须为数组")
            node_ids = [
                node.get("id") for node in nodes or []
                if isinstance(node, dict)
                and isinstance(node.get("id"), str)
                and DIAGRAM_ID_RE.fullmatch(node["id"])
            ]
            r.check("DIAGRAM.NODE_IDS", len(node_ids) == len(nodes or []) == len(set(node_ids)), "node id 完整且唯一", "node id 缺失或重复")
            node_set = set(node_ids)
            for index, node in enumerate(nodes or []):
                r.check(
                    f"DIAGRAM.NODE[{index}]",
                    isinstance(node, dict)
                    and exact_keys(node, NODE_KEYS)
                    and single_line(node.get("label"), 2)
                    and evidence_ok(node.get("evidence"), covered),
                    "node 合法",
                    "node id/label/evidence 非法或含未知字段",
                )
            for index, edge in enumerate(edges or []):
                r.check(
                    f"DIAGRAM.EDGE[{index}]",
                    isinstance(edge, dict)
                    and exact_keys(edge, EDGE_KEYS)
                    and edge.get("from") in node_set
                    and edge.get("to") in node_set
                    and (
                        "label" not in edge
                        or single_line(edge.get("label"))
                    )
                    and evidence_ok(edge.get("evidence"), covered),
                    "edge 合法",
                    "edge 端点、label、evidence 非法或含未知字段",
                )
        elif diagram_ok:
            r.check("DIAGRAM.REASON", nonempty(diagram.get("reason"), 6), "不适用原因已填写", "applicable=false 时必须说明 reason")

    forbidden = find_forbidden(data)
    r.check("FORBIDDEN", not forbidden, "无禁止键", f"出现禁止键：{forbidden}")
    return r


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("doc", type=Path)
    args = parser.parse_args()
    if not args.doc.is_file():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    try:
        data = json.loads(args.doc.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.doc}: JSON 解析失败：{exc}\n")
        return 2
    report = validate(data)
    print(f"=== validate_analysis: {args.doc} ===")
    for line in report.errors + report.passed:
        print(line)
    print(f"\nERROR: {len(report.errors)}  PASSED: {len(report.passed)}")
    print("\n结果：" + ("不合格" if report.errors else "合格"))
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
