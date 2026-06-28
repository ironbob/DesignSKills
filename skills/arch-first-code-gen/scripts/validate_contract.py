#!/usr/bin/env python3
"""Validate the design-contract.json manifest for arch-first-code-gen.

``design-contract.json`` is the single source of truth — the machine-readable
design contract. ``<feature>-arch.md`` is its render; ``validate_gate.py``
cross-checks the two and enforces Module E. This gate checks the *internal*
structure & consistency of the manifest:

  C-F    top-level required fields + types
  C-ST   stack ∈ {JVM, C++, FastAPI+Vue}
  C-AL   existing_alignment has recognized_style + new_code_follows
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
    "roles", "design_contract_checks", "business_process",
    "logging_standard", "summary", "gate",
)
STACKS = {"JVM", "C++", "FastAPI+Vue"}
ROLE_KINDS = {"layer", "domain"}
PREFIX_KIND = {"L": "layer", "D": "domain"}
LAYERS = {
    "controller", "service", "repository", "domain", "infrastructure",
    "facade", "router", "view", "store", "util",
}
DOMAIN_ROLES = {
    "aggregate", "entity", "value_object", "domain_service", "domain_event",
}
KEY_NODES = {"入口", "出口", "异常", "外部调用"}
SEVERITIES = {"critical", "major", "minor"}
GATE_NAMES = {"architecture", "logging", "coverage"}

KNOWN_PRINCIPLES = {
    # SOLID
    "SRP", "OCP", "LSP", "ISP", "DIP",
    # DDD
    "aggregate", "entity", "value_object", "domain_service", "domain_event",
    "bounded_context", "context_mapping",
    # 通用
    "high_cohesion_low_coupling", "dependency_direction",
    "separation_of_concerns", "tell_dont_ask",
}

ID_RE = re.compile(r"^ROLE-([LD])\d+$")
DC_RE = re.compile(r"^DC-\d+$")


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
            f"stack 非法：{stack!r}（须 JVM / C++ / FastAPI+Vue）")

    # ---- C-AL existing_alignment ----
    al = data.get("existing_alignment")
    if not isinstance(al, dict):
        r.err("C-AL1", "existing_alignment 须为对象")
    else:
        r.ok_or("C-AL1", _nonempty_str(al.get("recognized_style")),
                "recognized_style 有", "existing_alignment 缺 recognized_style（现有架构风格陈述）")
        r.ok_or("C-AL2", _nonempty_str(al.get("new_code_follows")),
                "new_code_follows 有", "existing_alignment 缺 new_code_follows（新代码如何沿用）")

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

    # ---- design_contract_checks ----
    dcs = data.get("design_contract_checks")
    if dcs is None:
        r.err("C-DC0", "缺 design_contract_checks（简单需求可用空数组 []）")
    elif not isinstance(dcs, list):
        r.err("C-DC0", "design_contract_checks 须为数组")
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

    # ---- summary ----
    summary = data.get("summary")
    if not isinstance(summary, dict):
        r.err("C-SUM0", "summary 须为对象")
    else:
        layer_n = sum(1 for x in roles if isinstance(x, dict) and x.get("role_kind") == "layer")
        domain_n = sum(1 for x in roles if isinstance(x, dict) and x.get("role_kind") == "domain")
        checks = {
            "roles_count": len(roles),
            "process_steps": len(bps),
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
        for k, v in (("architecture", arch), ("logging", logg), ("coverage", cov)):
            r.ok_or("C-GT1", v in ("go", "no-go"),
                    f"gate.{k}={v}", f"gate.{k} 非法 {v!r}（须 go/no-go）")
        verdict = gate.get("verdict")
        expected = "go" if (arch == "go" and logg == "go" and cov == "go") else "no-go"
        r.ok_or("C-GT2", verdict == expected,
                f"verdict={verdict}（三 门 {'全 go' if expected == 'go' else '有 no-go'}）",
                f"verdict={verdict!r} 与三门不符：应为 {expected!r}")
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
