#!/usr/bin/env python3
"""Validate the design-contract.json manifest for arch-first-code-gen.

``design-contract.json`` is the single source of truth — the machine-readable
design contract. ``<feature>-arch.md`` is its render; ``validate_gate.py``
cross-checks the two and enforces Module E. This gate checks the *internal*
structure & consistency of the manifest:

  C-F    top-level required fields + types
  C-ST   stack ∈ {JVM, C++, FastAPI+Vue, Swift/iOS}
  C-AL   existing_alignment has recognized_style + new_code_follows
  C-CF   user selected the profile and confirmed the presented proposal revision
         in a later user message; selection/candidate/revision must not drift
  C-UI   every UI feature records current/target architecture, MVVM suitability,
         migration impact and confirmation; MVVM must match a view_model role;
         high-impact MVVM adoption requires explicit user confirmation
  C-ID   roles is a list; ids unique; match ROLE-[LD]<n>; prefix ⇒ role_kind
  C-RD   per-role required fields + enums (role_kind/layer/domain_role);
         domain role ⇒ domain_role set; layered role ⇒ domain_role null/ok
  C-DEP  each depends_on resolves to a declared role id
  C-BAS  industry_basis + design_principles non-empty (PRD 强制);
         design_principles known-set WARN on unknown (advisory)
  C-CU   each role has ≥1 code_units entry
  C-DC   design_contract_checks ids DC-<n>; principle non-empty
  C-BP   business_process steps unique ints; roles valid; code_refs/doc_ref
         non-empty; exception key present
  C-LS   logging_standard: library + key_nodes subset of {入口,出口,异常,外部调用}
  C-SUM  summary counts == actual tallies
  C-GT   gate: architecture/logging/coverage ∈ {go,no-go};
         verdict == all-go; no-go ⇒ ≥1 critical issue; go ⇒ only minor;
         issue.gate/severity/role_or_step/problem/evidence non-empty

Exits non-zero when any ERROR fails or the WARNING pass rate < 80%.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REQUIRED_TOP = (
    "feature", "title", "stack", "analyzed_at", "existing_alignment",
    "interaction_confirmation", "design_decision", "roles", "interfaces", "design_contract_checks",
    "business_process", "logging_standard", "verification", "summary", "gate",
)
STACKS = {"JVM", "C++", "FastAPI+Vue", "Swift/iOS"}
ROLE_KINDS = {"layer", "domain"}
PREFIX_KIND = {"L": "layer", "D": "domain"}
LAYERS = {
    "controller", "service", "repository", "domain", "infrastructure",
    "facade", "router", "view", "view_model", "application", "coordinator",
    "composition", "mapper", "store", "util",
}
DOMAIN_ROLES = {
    "aggregate", "entity", "value_object", "domain_service", "domain_event",
}
KEY_NODES = {"入口", "出口", "异常", "外部调用"}
SEVERITIES = {"critical", "major", "minor"}
GATE_NAMES = {"architecture", "logging", "coverage", "verification"}
DESIGN_PROFILES = {"light", "standard", "high_risk"}
PRIORITIES = {"high", "medium", "low"}
REVIEW_MODES = {"self", "user", "peer", "independent"}
SPIKE_STATUSES = {"passed", "failed", "inconclusive"}
VERIFY_METHODS = {"existing_test", "new_test", "static_check", "manual_review"}
VERIFY_STATUSES = {"passed", "failed", "skipped"}
UI_ROLE_LAYERS = {"view", "view_model", "store", "coordinator"}
UI_PATTERNS = {
    "MVVM", "MVC", "MVP", "Coordinator", "Clean/VIP", "TCA",
    "Redux/Store", "Direct View", "Other",
}
VIEW_MODEL_POLICIES = {"required", "optional", "not_used"}
MVVM_SUITABILITY = {"suitable", "not_suitable", "already_used"}
MIGRATION_IMPACTS = {"none", "low", "medium", "high"}
MIGRATION_CONFIRMATIONS = {"not_required", "user_confirmed", "pending"}

KNOWN_PRINCIPLES = {
    # SOLID
    "SRP", "OCP", "LSP", "ISP", "DIP",
    # DDD
    "aggregate", "entity", "value_object", "domain_service", "domain_event",
    "bounded_context", "context_mapping",
    # 通用
    "high_cohesion_low_coupling", "dependency_direction",
    "separation_of_concerns", "tell_dont_ask", "information_hiding",
    "minimize_complexity", "defensive_design",
}

ID_RE = re.compile(r"^ROLE-([LD])\d+$")
DC_RE = re.compile(r"^DC-\d+$")
ALT_RE = re.compile(r"^ALT-\d+$")
IFC_RE = re.compile(r"^IFC-\d+$")


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

    def ok_or(self, rule: str, cond: bool, msg_ok: str, msg_err: str,
              warn: bool = False) -> None:
        if cond:
            self.ok(rule, msg_ok)
        elif warn:
            self.warn(rule, msg_err)
        else:
            self.err(rule, msg_err)


def _nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def validate(data: Any, path: Path) -> Report:
    r = Report()

    if not isinstance(data, dict):
        r.err("C-F1", "顶层不是 JSON 对象")
        return r

    miss = [k for k in REQUIRED_TOP if data.get(k) in (None, "")]
    r.ok_or("C-F1", not miss, "顶层字段齐全", f"缺必填顶层字段：{miss}")

    # ---- C-ST stack ----
    stack = data.get("stack")
    r.ok_or("C-ST1", stack in STACKS, f"stack={stack}",
            f"stack 非法：{stack!r}（须 JVM / C++ / FastAPI+Vue / Swift/iOS）")

    # ---- C-AL existing_alignment ----
    al = data.get("existing_alignment")
    if not isinstance(al, dict):
        r.err("C-AL1", "existing_alignment 须为对象")
    else:
        r.ok_or("C-AL1", _nonempty_str(al.get("recognized_style")),
                "recognized_style 有", "existing_alignment 缺 recognized_style（现有架构风格陈述）")
        r.ok_or("C-AL2", _nonempty_str(al.get("new_code_follows")),
                "new_code_follows 有", "existing_alignment 缺 new_code_follows（新代码如何沿用）")

    # ---- design decision ----
    dd = data.get("design_decision")
    if not isinstance(dd, dict):
        r.err("C-DD0", "design_decision 须为对象")
        dd = {}
    profile = dd.get("profile")
    r.ok_or("C-DD1", profile in DESIGN_PROFILES, f"profile={profile}",
            f"design_decision.profile 非法（须 {sorted(DESIGN_PROFILES)}）")
    qas = dd.get("quality_attributes")
    if not isinstance(qas, list) or not qas:
        r.err("C-DD2", "quality_attributes 须为非空数组")
        qas = []
    else:
        r.ok("C-DD2", f"quality_attributes {len(qas)} 项")
    for i, qa in enumerate(qas):
        ctx = f"quality_attributes[{i}]"
        if not isinstance(qa, dict):
            r.err("C-DD3", f"{ctx} 不是对象")
            continue
        for fld in ("name", "scenario", "acceptance"):
            r.ok_or("C-DD3", _nonempty_str(qa.get(fld)), f"{ctx}.{fld} 有", f"{ctx} 缺 {fld}")
        r.ok_or("C-DD3", qa.get("priority") in PRIORITIES,
                f"{ctx}.priority={qa.get('priority')}", f"{ctx}.priority 非法")
    candidates = dd.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        r.err("C-DD4", "candidates 须为非空数组")
        candidates = []
    elif profile in {"standard", "high_risk"} and len(candidates) < 2:
        r.err("C-DD4", f"profile={profile} 须比较至少 2 个候选方案")
    else:
        r.ok("C-DD4", f"candidates {len(candidates)} 个")
    alt_ids: set[str] = set()
    for i, alt in enumerate(candidates):
        ctx = f"candidates[{i}]"
        if not isinstance(alt, dict):
            r.err("C-DD5", f"{ctx} 不是对象")
            continue
        aid = alt.get("id")
        ok_id = isinstance(aid, str) and bool(ALT_RE.match(aid)) and aid not in alt_ids
        r.ok_or("C-DD5", ok_id, f"{aid}: 候选 id 合法唯一", f"{ctx}.id 非法或重复")
        if isinstance(aid, str):
            alt_ids.add(aid)
        r.ok_or("C-DD5", _nonempty_str(alt.get("summary")), f"{aid}: summary 有", f"{ctx} 缺 summary")
        for fld in ("strengths", "weaknesses", "risks"):
            value = alt.get(fld)
            r.ok_or("C-DD5", isinstance(value, list) and bool(value) and all(_nonempty_str(x) for x in value),
                    f"{aid}: {fld} 有", f"{ctx}.{fld} 须为非空字符串数组")
    r.ok_or("C-DD6", dd.get("selected_id") in alt_ids,
            f"selected_id={dd.get('selected_id')} 可解析", "selected_id 必须解析到候选方案")
    for fld in ("selection_reason", "top_down_check", "bottom_up_check"):
        r.ok_or("C-DD7", _nonempty_str(dd.get(fld)), f"{fld} 有", f"design_decision 缺 {fld}")
    spikes = dd.get("risk_spikes")
    if not isinstance(spikes, list):
        r.err("C-DD8", "risk_spikes 须为数组")
        spikes = []
    elif profile == "high_risk" and not spikes:
        r.err("C-DD8", "high_risk 至少需要 1 个风险 spike")
    else:
        r.ok("C-DD8", f"risk_spikes {len(spikes)} 个")
    for i, spike in enumerate(spikes):
        ctx = f"risk_spikes[{i}]"
        if not isinstance(spike, dict):
            r.err("C-DD9", f"{ctx} 不是对象")
            continue
        for fld in ("question", "method", "result"):
            r.ok_or("C-DD9", _nonempty_str(spike.get(fld)), f"{ctx}.{fld} 有", f"{ctx} 缺 {fld}")
        r.ok_or("C-DD9", spike.get("status") in SPIKE_STATUSES,
                f"{ctx}.status={spike.get('status')}", f"{ctx}.status 非法")
    review = dd.get("review")
    if not isinstance(review, dict):
        r.err("C-DD10", "design_decision.review 须为对象")
    else:
        mode = review.get("mode")
        r.ok_or("C-DD10", mode in REVIEW_MODES, f"review.mode={mode}", "review.mode 非法")
        if profile == "standard":
            r.ok_or("C-DD10", mode in {"user", "peer", "independent"},
                    "standard 已独立复核", "standard 不允许仅 self review")
        if profile == "high_risk":
            r.ok_or("C-DD10", mode in {"user", "peer"},
                    "high_risk 已由用户/同行评审", "high_risk 必须由 user/peer 评审")
        for fld in ("reviewer", "findings", "disposition"):
            r.ok_or("C-DD10", _nonempty_str(review.get(fld)), f"review.{fld} 有", f"review 缺 {fld}")

    # ---- C-CF mandatory user interaction confirmations ----
    interaction = data.get("interaction_confirmation")
    if not isinstance(interaction, dict):
        r.err("C-CF0", "interaction_confirmation 须为对象；编码前必须记录等级选择与方案确认")
        interaction = {}

    revision = interaction.get("proposal_revision")
    r.ok_or(
        "C-CF1", isinstance(revision, int) and not isinstance(revision, bool) and revision > 0,
        f"proposal_revision={revision}",
        "interaction_confirmation.proposal_revision 须为正整数",
    )

    profile_selection = interaction.get("profile_selection")
    if not isinstance(profile_selection, dict):
        r.err("C-CF2", "profile_selection 须为对象；模型推荐或默认等级不能替代用户选择")
        profile_selection = {}
    r.ok_or(
        "C-CF3", profile_selection.get("status") == "user_selected",
        "profile_selection.status=user_selected",
        "profile_selection.status 必须为 user_selected",
    )
    r.ok_or(
        "C-CF4", profile_selection.get("selected_profile") == profile,
        f"用户选择等级与 design_decision.profile={profile} 一致",
        "profile_selection.selected_profile 必须等于 design_decision.profile",
    )
    r.ok_or(
        "C-CF5", profile_selection.get("source") == "user_message",
        "等级选择来源为 user_message",
        "profile_selection.source 必须为 user_message；不得用模型推断或自动确认",
    )
    r.ok_or(
        "C-CF6", _nonempty_str(profile_selection.get("evidence")),
        "等级选择 evidence 有",
        "profile_selection.evidence 须引用或概述用户选择等级的消息",
    )

    design_confirmation = interaction.get("design_confirmation")
    if not isinstance(design_confirmation, dict):
        r.err("C-CF7", "design_confirmation 须为对象；方案展示后必须等待用户明确确认")
        design_confirmation = {}
    confirmed = (
        design_confirmation.get("status") == "user_confirmed"
        and design_confirmation.get("confirmed_candidate") == dd.get("selected_id")
        and design_confirmation.get("confirmed_revision") == revision
        and design_confirmation.get("source") == "later_user_message"
    )
    r.ok_or(
        "C-CF8", confirmed,
        "方案确认状态、候选、版本与消息时序一致",
        "design_confirmation 必须为 user_confirmed，匹配 selected_id/proposal_revision，且 source=later_user_message",
    )
    r.ok_or(
        "C-CF9", _nonempty_str(design_confirmation.get("evidence")),
        "方案确认 evidence 有",
        "design_confirmation.evidence 须引用或概述方案展示后的用户确认消息",
    )

    # ---- C-UI parsed here; validated after roles reveal whether this is UI ----
    ui = data.get("ui_architecture")

    # ---- roles ----
    roles = data.get("roles")
    if not isinstance(roles, list) or not roles:
        r.err("C-ID1", "roles 须为非空数组（分层角色 + 领域角色至少一类）")
        roles = []
    else:
        r.ok("C-ID1", f"roles {len(roles)} 个")

    ids: list[str] = []
    name_set: set[str] = set()
    for i, role in enumerate(roles):
        if not isinstance(role, dict):
            r.err("C-RD0", f"roles[{i}] 不是对象")
            continue
        rid = role.get("id")
        ctx = f"roles[{i}] ({rid or '?'})"
        mid = ID_RE.match(rid) if isinstance(rid, str) else None
        r.ok_or("C-ID2", bool(mid), f"{rid}: id 合法",
                f"{ctx}: id 非法 {rid!r}（须 ROLE-L<n> 分层 / ROLE-D<n> 领域）")
        if mid:
            want_kind = PREFIX_KIND[mid.group(1)]
            r.ok_or("C-ID3", role.get("role_kind") == want_kind,
                    f"{rid}: 前缀 {mid.group(1)}⇒role_kind {want_kind} 一致",
                    f"{ctx}: 前缀 {mid.group(1)}⇒{want_kind} 与 role_kind={role.get('role_kind')!r} 不一致")
        if isinstance(rid, str):
            if rid in ids:
                r.err("C-ID4", f"{ctx}: id 重复（{rid}）")
            ids.append(rid)
        # required scalars
        r.ok_or("C-RD1", _nonempty_str(role.get("name")),
                f"{rid}: name 有", f"{ctx}: 缺 name")
        r.ok_or("C-RD2", role.get("role_kind") in ROLE_KINDS,
                f"{rid}: role_kind={role.get('role_kind')}",
                f"{ctx}: role_kind 非法（须 layer/domain）")
        r.ok_or("C-RD3", role.get("layer") in LAYERS,
                f"{rid}: layer={role.get('layer')}",
                f"{ctx}: layer 非法 {role.get('layer')!r}（须 {sorted(LAYERS)}）")
        dr = role.get("domain_role")
        r.ok_or("C-RD4", dr is None or dr in DOMAIN_ROLES,
                f"{rid}: domain_role={dr}",
                f"{ctx}: domain_role 非法 {dr!r}（须 {sorted(DOMAIN_ROLES)} 或 null）")
        # domain role ⇒ domain_role set; layered ⇒ null tolerated
        if role.get("role_kind") == "domain":
            r.ok_or("C-RD5", dr in DOMAIN_ROLES,
                    f"{rid}: 领域角色 domain_role={dr}",
                    f"{ctx}: role_kind=domain 须设 domain_role（aggregate/entity/…）")
        r.ok_or("C-RD6", _nonempty_str(role.get("responsibility")),
                f"{rid}: responsibility 有", f"{ctx}: 缺 responsibility（动词开头、单一职责）")
        r.ok_or("C-RD7", _nonempty_str(role.get("hidden_secret")),
                f"{rid}: hidden_secret 有", f"{ctx}: 缺 hidden_secret（信息隐藏边界）")
        triggers = role.get("change_triggers")
        r.ok_or("C-RD8", isinstance(triggers, list) and bool(triggers) and all(_nonempty_str(x) for x in triggers),
                f"{rid}: change_triggers 有", f"{ctx}: change_triggers 须为非空字符串数组")
        r.ok_or("C-RD9", _nonempty_str(role.get("data_owned")),
                f"{rid}: data_owned 有", f"{ctx}: 缺 data_owned（无状态也要明确）")
        # depends_on
        deps = role.get("depends_on")
        if isinstance(deps, list):
            r.ok("C-DEP0", f"{rid}: depends_on {len(deps)} 项")
        else:
            r.err("C-DEP0", f"{ctx}: depends_on 须为数组（无依赖用 []）")
            deps = []
        # basis + principles (PRD 强制)
        r.ok_or("C-BAS1", _nonempty_str(role.get("industry_basis")),
                f"{rid}: industry_basis 有",
                f"{ctx}: 缺 industry_basis（业界做法依据，PRD 强制）")
        pr = role.get("design_principles")
        if isinstance(pr, list) and pr:
            r.ok("C-BAS2", f"{rid}: design_principles {len(pr)} 项")
            unknown = [p for p in pr if not _nonempty_str(p) or p not in KNOWN_PRINCIPLES]
            known_unknown = [p for p in pr if _nonempty_str(p) and p not in KNOWN_PRINCIPLES]
            if known_unknown:
                r.warn("C-BAS3", f"{ctx}: design_principles 含非规范集值 {known_unknown}（规范集见 schema §九；团队引用其他原则请确认拼写）")
        else:
            r.err("C-BAS2", f"{ctx}: design_principles 须为非空数组（所依据的设计原则，PRD 强制）")
        # code_units
        cu = role.get("code_units")
        r.ok_or("C-CU1", isinstance(cu, list) and len(cu) > 0 and all(_nonempty_str(c) for c in cu),
                f"{rid}: code_units {len(cu) if isinstance(cu, list) else 0} 个",
                f"{ctx}: code_units 须为非空字符串数组（角色对应代码文件；架构门校验存在）")
        if isinstance(role.get("name"), str):
            name_set.add(role["name"])

    is_ui_feature = any(
        isinstance(role, dict) and role.get("layer") in UI_ROLE_LAYERS
        for role in roles
    ) or isinstance(ui, dict)
    if is_ui_feature and not isinstance(ui, dict):
        r.err("C-UI0", "UI feature 须声明 ui_architecture（现有/目标模式、状态、MVVM 适用性、迁移影响与确认）")
    elif isinstance(ui, dict):
        r.ok_or("C-UI1", _nonempty_str(ui.get("framework")),
                f"framework={ui.get('framework')}",
                "ui_architecture.framework 须为非空字符串（真实 UI 框架）")

        def validate_patterns(field: str, rule: str) -> list[str]:
            value = ui.get(field)
            ok = (
                isinstance(value, list) and bool(value)
                and all(p in UI_PATTERNS for p in value)
                and len(value) == len(set(value))
            )
            r.ok_or(rule, ok, f"{field}={value}",
                    f"ui_architecture.{field} 须为非空、唯一且取自 {sorted(UI_PATTERNS)}")
            return value if isinstance(value, list) else []

        current_patterns = validate_patterns("current_patterns", "C-UI2")
        target_patterns = validate_patterns("target_patterns", "C-UI3")
        r.ok_or("C-UI4", _nonempty_str(ui.get("state_management")),
                "state_management 有", "ui_architecture 缺 state_management（状态事实源与所有者）")
        r.ok_or("C-UI5", ui.get("view_model_policy") in VIEW_MODEL_POLICIES,
                f"view_model_policy={ui.get('view_model_policy')}",
                f"view_model_policy 非法（须 {sorted(VIEW_MODEL_POLICIES)}）")
        r.ok_or("C-UI6", ui.get("mvvm_suitability") in MVVM_SUITABILITY,
                f"mvvm_suitability={ui.get('mvvm_suitability')}",
                f"mvvm_suitability 非法（须 {sorted(MVVM_SUITABILITY)}）")
        r.ok_or("C-UI7", ui.get("migration_impact") in MIGRATION_IMPACTS,
                f"migration_impact={ui.get('migration_impact')}",
                f"migration_impact 非法（须 {sorted(MIGRATION_IMPACTS)}）")
        impact_scope = ui.get("impact_scope")
        impact_scope_ok = isinstance(impact_scope, list) and all(
            _nonempty_str(item) for item in impact_scope
        )
        r.ok_or("C-UI8", impact_scope_ok,
                f"impact_scope={impact_scope}",
                "impact_scope 须为字符串数组（无影响可用 []）")
        if ui.get("migration_impact") == "high":
            r.ok_or("C-UI9", bool(impact_scope),
                    "high impact 已列 impact_scope",
                    "migration_impact=high 时 impact_scope 不得为空")
        r.ok_or("C-UI10", ui.get("migration_confirmation") in MIGRATION_CONFIRMATIONS,
                f"migration_confirmation={ui.get('migration_confirmation')}",
                f"migration_confirmation 非法（须 {sorted(MIGRATION_CONFIRMATIONS)}）")
        r.ok_or("C-UI11", _nonempty_str(ui.get("decision_reason")),
                "decision_reason 有", "ui_architecture 缺 decision_reason（采用/不采用 MVVM 的理由）")

        policy = ui.get("view_model_policy")
        view_model_count = sum(
            1 for role in roles
            if isinstance(role, dict) and role.get("layer") == "view_model"
        )
        mvvm_declared = "MVVM" in target_patterns
        r.ok_or(
            "C-UI12",
            (mvvm_declared and policy == "required" and view_model_count > 0)
            or (not mvvm_declared and policy in {"optional", "not_used"} and view_model_count == 0),
            f"MVVM 声明与 ViewModel 角色一致（count={view_model_count}）",
            "MVVM/policy/ViewModel 角色不一致：声明 MVVM 须 policy=required 且有 view_model 角色；未声明 MVVM 不得创建 ViewModel 角色",
        )
        suitability = ui.get("mvvm_suitability")
        if suitability in {"suitable", "already_used"} and not mvvm_declared:
            r.warn("C-UI13", "MVVM 被判定为适合/已使用但目标模式未采用；请确认 decision_reason 已说明具体取舍")
        elif suitability in {"suitable", "already_used"}:
            r.ok("C-UI13", "MVVM 适用性判断与目标模式一致")

        introducing_mvvm = mvvm_declared and "MVVM" not in current_patterns
        high_impact_adoption = introducing_mvvm and ui.get("migration_impact") == "high"
        if high_impact_adoption:
            r.ok_or(
                "C-UI15", profile == "high_risk",
                "高影响 MVVM 迁移使用 high_risk 设计强度",
                "新引入 MVVM 且 migration_impact=high：design_decision.profile 必须为 high_risk",
            )
            r.ok_or(
                "C-UI14",
                ui.get("migration_confirmation") == "user_confirmed",
                "高影响 MVVM 迁移已有用户明确确认",
                "新引入 MVVM 且 migration_impact=high：须 migration_confirmation=user_confirmed；通用方案确认不能代替",
            )
        else:
            r.ok_or(
                "C-UI14",
                ui.get("migration_confirmation") != "pending",
                "无需等待高影响 MVVM 迁移确认",
                "migration_confirmation=pending：确认完成前不得交付",
            )

    id_set = set(ids)
    # depends_on resolve (after collecting ids)
    for role in roles:
        if not isinstance(role, dict):
            continue
        rid = role.get("id")
        deps = role.get("depends_on") or []
        if not isinstance(deps, list):
            continue
        bad = [d for d in deps if d not in id_set]
        if bad:
            r.err("C-DEP1", f"{rid}: depends_on 指向未定义角色 {bad}（须为已声明 role id）")

    # ---- interfaces ----
    interfaces = data.get("interfaces")
    if not isinstance(interfaces, list):
        r.err("C-IF0", "interfaces 须为数组")
        interfaces = []
    elif not interfaces and not (profile == "light" and len(roles) == 1):
        r.err("C-IF0", "存在多角色或非 light 设计时 interfaces 不得为空")
    else:
        r.ok("C-IF0", f"interfaces {len(interfaces)} 个")
    interface_ids: set[str] = set()
    for i, interface in enumerate(interfaces):
        ctx = f"interfaces[{i}]"
        if not isinstance(interface, dict):
            r.err("C-IF1", f"{ctx} 不是对象")
            continue
        iid = interface.get("id")
        ok_id = isinstance(iid, str) and bool(IFC_RE.match(iid)) and iid not in interface_ids
        r.ok_or("C-IF1", ok_id, f"{iid}: id 合法唯一", f"{ctx}.id 非法或重复")
        if isinstance(iid, str):
            interface_ids.add(iid)
        for fld in ("name", "input", "output", "data_ownership", "transaction", "concurrency"):
            r.ok_or("C-IF2", _nonempty_str(interface.get(fld)), f"{iid}: {fld} 有", f"{ctx} 缺 {fld}")
        r.ok_or("C-IF3", interface.get("provider") in id_set,
                f"{iid}: provider 有效", f"{ctx}.provider 未解析")
        consumers = interface.get("consumers")
        r.ok_or("C-IF4", isinstance(consumers, list) and bool(consumers) and all(x in id_set for x in consumers),
                f"{iid}: consumers 有效", f"{ctx}.consumers 须为非空有效 role id 数组")
        for fld in ("preconditions", "postconditions", "invariants", "errors"):
            value = interface.get(fld)
            r.ok_or("C-IF5", isinstance(value, list) and bool(value) and all(_nonempty_str(x) for x in value),
                    f"{iid}: {fld} 有", f"{ctx}.{fld} 须为非空字符串数组")

    # ---- design_contract_checks ----
    dcs = data.get("design_contract_checks")
    if dcs is None:
        r.err("C-DC0", "缺 design_contract_checks（简单需求可用空数组 []）")
    elif not isinstance(dcs, list):
        r.err("C-DC0", "design_contract_checks 须为数组")
    elif not dcs:
        r.err("C-DC0", "design_contract_checks 至少包含 1 条可对照约束")
    else:
        r.ok("C-DC0", f"design_contract_checks {len(dcs)} 条")
        for i, dc in enumerate(dcs):
            if not isinstance(dc, dict):
                r.err("C-DC1", f"design_contract_checks[{i}] 不是对象")
                continue
            ctx = f"design_contract_checks[{i}] ({dc.get('id', '?')})"
            r.ok_or("C-DC1", bool(DC_RE.match(dc.get("id", "") if isinstance(dc.get("id"), str) else "")),
                    f"{dc.get('id')}: id 合法", f"{ctx}: id 非法（须 DC-<n>）")
            r.ok_or("C-DC2", _nonempty_str(dc.get("item")),
                    f"{dc.get('id')}: item 有", f"{ctx}: 缺 item（对照条目）")
            r.ok_or("C-DC3", _nonempty_str(dc.get("principle")),
                    f"{dc.get('id')}: principle 有", f"{ctx}: 缺 principle")
            if _nonempty_str(dc.get("principle")) and dc["principle"] not in KNOWN_PRINCIPLES:
                r.warn("C-DC4", f"{ctx}: principle {dc['principle']!r} 非规范集值（确认拼写）")

    # ---- business_process ----
    bps = data.get("business_process")
    if not isinstance(bps, list):
        r.err("C-BP0", "business_process 须为数组（纯 CRUD 无流程可用 []，但需文档说明）")
        bps = []
    else:
        r.ok("C-BP0", f"business_process {len(bps)} 步")
    seen_steps: set[int] = set()
    for i, bp in enumerate(bps):
        if not isinstance(bp, dict):
            r.err("C-BP1", f"business_process[{i}] 不是对象")
            continue
        ctx = f"business_process[{i}] (step:{bp.get('step', '?')})"
        step = bp.get("step")
        r.ok_or("C-BP1", isinstance(step, int) and step > 0,
                f"step={step}", f"{ctx}: step 须为正整数")
        if isinstance(step, int):
            if step in seen_steps:
                r.err("C-BP2", f"{ctx}: step 重复（{step}）")
            seen_steps.add(step)
        # roles valid
        proles = bp.get("roles")
        if isinstance(proles, list) and proles:
            bad = [p for p in proles if p not in id_set]
            r.ok_or("C-BP3", not bad,
                    f"step:{step} roles 有效", f"{ctx}: roles 指向未定义角色 {bad}")
        else:
            r.err("C-BP3", f"{ctx}: roles 须为非空数组（参与本步的 role id）")
        # code_refs
        cr = bp.get("code_refs")
        r.ok_or("C-BP4", isinstance(cr, list) and cr and all(_nonempty_str(c) for c in cr),
                f"step:{step} code_refs {len(cr) if isinstance(cr, list) else 0} 个",
                f"{ctx}: code_refs 须为非空字符串数组（覆盖门校验存在）")
        r.ok_or("C-BP5", _nonempty_str(bp.get("doc_ref")),
                f"step:{step} doc_ref 有", f"{ctx}: 缺 doc_ref（覆盖门交叉对账）")
        # exception key present (None ok)
        r.ok_or("C-BP6", "exception" in bp,
                f"step:{step} exception 字段在", f"{ctx}: 缺 exception 字段（无异常用 null）")

    # ---- logging_standard ----
    ls = data.get("logging_standard")
    if not isinstance(ls, dict):
        r.err("C-LS0", "logging_standard 须为对象")
    else:
        r.ok_or("C-LS1", _nonempty_str(ls.get("library")),
                f"library={ls.get('library')}", "logging_standard 缺 library（按栈日志库）")
        kn = ls.get("key_nodes_instrumented")
        if isinstance(kn, list) and kn:
            bad = [k for k in kn if k not in KEY_NODES]
            r.ok_or("C-LS2", not bad,
                    f"key_nodes {len(kn)} 个", f"key_nodes_instrumented 含非法值 {bad}（须 {sorted(KEY_NODES)}）")
        else:
            r.err("C-LS2", "key_nodes_instrumented 须为非空数组（已打点关键节点）")

    # ---- verification ----
    verification = data.get("verification")
    command_statuses: list[str] = []
    check_statuses: list[str] = []
    unverified: list[Any] = []
    if not isinstance(verification, dict):
        r.err("C-VR0", "verification 须为对象")
        verification = {}
    commands = verification.get("commands")
    if not isinstance(commands, list) or not commands:
        r.err("C-VR1", "verification.commands 须为非空数组（实际执行记录）")
        commands = []
    else:
        r.ok("C-VR1", f"verification.commands {len(commands)} 条")
    for i, command in enumerate(commands):
        ctx = f"verification.commands[{i}]"
        if not isinstance(command, dict):
            r.err("C-VR2", f"{ctx} 不是对象")
            continue
        for fld in ("command", "result", "evidence"):
            r.ok_or("C-VR2", _nonempty_str(command.get(fld)), f"{ctx}.{fld} 有", f"{ctx} 缺 {fld}")
        status = command.get("status")
        command_statuses.append(status)
        r.ok_or("C-VR2", status in VERIFY_STATUSES, f"{ctx}.status={status}", f"{ctx}.status 非法")
    verification_checks = verification.get("checks")
    if not isinstance(verification_checks, list) or not verification_checks:
        r.err("C-VR3", "verification.checks 须为非空数组")
        verification_checks = []
    else:
        r.ok("C-VR3", f"verification.checks {len(verification_checks)} 条")
    for i, check in enumerate(verification_checks):
        ctx = f"verification.checks[{i}]"
        if not isinstance(check, dict):
            r.err("C-VR4", f"{ctx} 不是对象")
            continue
        for fld in ("target", "evidence"):
            r.ok_or("C-VR4", _nonempty_str(check.get(fld)), f"{ctx}.{fld} 有", f"{ctx} 缺 {fld}")
        r.ok_or("C-VR4", check.get("method") in VERIFY_METHODS,
                f"{ctx}.method={check.get('method')}", f"{ctx}.method 非法")
        status = check.get("status")
        check_statuses.append(status)
        r.ok_or("C-VR4", status in VERIFY_STATUSES, f"{ctx}.status={status}", f"{ctx}.status 非法")
    unverified = verification.get("unverified")
    if not isinstance(unverified, list):
        r.err("C-VR5", "verification.unverified 须为数组")
        unverified = []
    else:
        r.ok("C-VR5", f"unverified {len(unverified)} 项")
    for i, item in enumerate(unverified):
        ctx = f"verification.unverified[{i}]"
        if not isinstance(item, dict):
            r.err("C-VR5", f"{ctx} 不是对象")
            continue
        for fld in ("item", "impact", "follow_up"):
            r.ok_or("C-VR5", _nonempty_str(item.get(fld)), f"{ctx}.{fld} 有", f"{ctx} 缺 {fld}")

    # ---- summary ----
    summary = data.get("summary")
    if not isinstance(summary, dict):
        r.err("C-SUM0", "summary 须为对象")
    else:
        layer_n = sum(1 for x in roles if isinstance(x, dict) and x.get("role_kind") == "layer")
        domain_n = sum(1 for x in roles if isinstance(x, dict) and x.get("role_kind") == "domain")
        checks = {
            "roles_count": len(roles),
            "interfaces_count": len(interfaces),
            "process_steps": len(bps),
            "verification_checks": len(verification_checks),
            "layer_roles": layer_n,
            "domain_roles": domain_n,
        }
        for k, v in checks.items():
            r.ok_or("C-SUM1", summary.get(k) == v,
                    f"summary.{k}={v} 一致",
                    f"summary.{k}={summary.get(k)} 与实际 {v} 不一致")

    # ---- gate ----
    gate = data.get("gate")
    if not isinstance(gate, dict):
        r.err("C-GT0", "gate 须为对象")
    else:
        arch = gate.get("architecture")
        logg = gate.get("logging")
        cov = gate.get("coverage")
        ver = gate.get("verification")
        for k, v in (("architecture", arch), ("logging", logg), ("coverage", cov), ("verification", ver)):
            r.ok_or("C-GT1", v in ("go", "no-go"),
                    f"gate.{k}={v}", f"gate.{k} 非法 {v!r}（须 go/no-go）")
        verdict = gate.get("verdict")
        expected = "go" if (arch == "go" and logg == "go" and cov == "go" and ver == "go") else "no-go"
        r.ok_or("C-GT2", verdict == expected,
                f"verdict={verdict}（四门 {'全 go' if expected == 'go' else '有 no-go'}）",
                f"verdict={verdict!r} 与四门不符：应为 {expected!r}")
        has_failed_verification = "failed" in command_statuses or "failed" in check_statuses
        r.ok_or("C-GT9", not (ver == "go" and has_failed_verification),
                "verification gate 与执行结果一致", "gate.verification=go 但存在 failed 验证")
        r.ok_or("C-GT3", _nonempty_str(gate.get("notes")),
                "gate.notes 有", "gate 缺 notes（门禁诚实说明）")
        # issues
        issues = gate.get("issues")
        if not isinstance(issues, list):
            r.err("C-GT4", "gate.issues 须为数组（全 go 可空 []）")
            issues = []
        sev_set: set[str] = set()
        for j, iss in enumerate(issues):
            if not isinstance(iss, dict):
                r.err("C-GT4", f"gate.issues[{j}] 不是对象")
                continue
            ctx = f"gate.issues[{j}]"
            for fld in ("gate", "severity", "role_or_step", "problem", "evidence"):
                r.ok_or("C-GT5", _nonempty_str(iss.get(fld)),
                        f"issue[{j}].{fld} 有", f"{ctx}: 缺 {fld}")
            if iss.get("gate") not in GATE_NAMES and _nonempty_str(iss.get("gate")):
                r.err("C-GT6", f"{ctx}: gate={iss.get('gate')!r} 非法（须 {sorted(GATE_NAMES)}）")
            if iss.get("severity") in SEVERITIES:
                sev_set.add(iss["severity"])
            elif _nonempty_str(iss.get("severity")):
                r.err("C-GT7", f"{ctx}: severity={iss.get('severity')!r} 非法")
        if verdict == "no-go":
            r.ok_or("C-GT8", "critical" in sev_set,
                    "no-go 且含 critical issue",
                    "verdict=no-go 须至少一个 critical issue（说明阻塞项）")
        else:
            bad = sev_set - {"minor"}
            r.ok_or("C-GT8", not bad,
                    "go 仅含 minor issue",
                    f"verdict=go 但 issues 含 {sorted(bad)}（go 时 issues 仅可含 minor）")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate an arch-first-code-gen design-contract.json")
    ap.add_argument("doc", type=Path, help="Path to design-contract.json")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    try:
        data = json.loads(args.doc.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.doc}: JSON 解析失败：{exc}\n")
        return 2

    r = validate(data, args.doc)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_contract: {args.doc} ===")
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
