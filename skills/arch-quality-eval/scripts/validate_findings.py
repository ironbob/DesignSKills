#!/usr/bin/env python3
"""Validate the findings.json contract for arch-quality-eval.

``findings.json`` is the single source of truth — the machine-readable finding
contract. ``report.md`` is its render; ``validate_contract.py`` cross-checks the
two. This gate checks the *internal* structure & consistency of findings.json:

  S-F    top-level required fields + types
  S-L    language ∈ {JVM, C++}; C++ ⇒ cpp_limitation_noted == true
  S-META scope, analysis method, gaps, module id, and date
  S-COV  covered_files non-empty; conventions_fed == true ⇒ convention_rules non-empty
  S-CORE five core smell coverage statuses agree with findings
  S-ID   findings is a list; ids unique; match FINDING-[SRC]<n>; prefix ⇒ axis
  S-FD   per-finding required fields + enums (axis / severity / fix_cost / priority)
  S-EV   each finding has ≥1 evidence item carrying a `file`
  S-P    smell & readability ⇒ principle_violated; convention ⇒ convention_violated
         that points to a declared convention_rules[].id
  S-SUM  summary counts == actual severity tallies;
         verdict ⇔ critical ≥ no_go_threshold
  S-RD   readability four axes + overall present and evidence-linked

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
    "module", "analyzed_at", "language", "scope", "covered_files",
    "conventions_fed", "analysis", "core_smell_coverage", "known_gaps",
    "no_go_threshold", "summary", "readability", "findings",
)
LANGUAGES = {"JVM", "C++"}
AXES = {"smell", "readability", "convention"}
SEVERITIES = {"critical", "major", "minor"}
FIX_COSTS = {"low", "medium", "high"}
PRIORITIES = {"P1", "P2", "P3"}
READABILITY_AXES = (
    "responsibility_clarity", "dependency_understandability",
    "naming_expressiveness", "layering_clarity", "overall",
)
CORE_SMELL_CATEGORIES = {
    "circular-dependency": {"circular-dependency"},
    "god-class-or-package": {"god-class", "god-package"},
    "cross-layer": {"cross-layer"},
    "shotgun-surgery": {"shotgun-surgery"},
    "inappropriate-exposure": {"inappropriate-exposure"},
}
CORE_STATUSES = {"detected", "not-detected"}
SMELL_CATEGORIES = {
    "circular-dependency", "god-class", "god-package", "cross-layer",
    "shotgun-surgery", "inappropriate-exposure", "facade-controller-abuse",
    "parallel-inheritance", "middle-man", "divergent-change", "feature-envy-arch",
    "dependency-toward-instability",
}
READABILITY_CATEGORIES = {
    "responsibility-mixed", "dependency-opaque", "naming-unexpressive", "layering-unclear",
}
ID_RE = re.compile(r"^FINDING-([SRC])\d+$")
MODULE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ANCHOR_RE = re.compile(r"([\w.-]+\.(?:java|kt|h|hpp|hh|cc|cpp|cxx)):\d+", re.I)
PREFIX_AXIS = {"S": "smell", "R": "readability", "C": "convention"}


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

    # ---- S-F top-level required fields ----
    if not isinstance(data, dict):
        r.err("S-F1", "顶层不是 JSON 对象")
        return r
    miss = [k for k in REQUIRED_TOP if data.get(k) in (None, "")]
    if miss:
        r.err("S-F1", f"缺必填顶层字段：{miss}")
    else:
        r.ok("S-F1")

    # ---- S-META stable identity / date / scope / analysis ----
    module = data.get("module")
    r.ok_or("S-META1", isinstance(module, str) and bool(MODULE_RE.fullmatch(module)),
            f"module={module}", f"module 须为 kebab-case，实际 {module!r}")
    analyzed_at = data.get("analyzed_at")
    r.ok_or("S-META2", isinstance(analyzed_at, str) and bool(DATE_RE.fullmatch(analyzed_at)),
            f"analyzed_at={analyzed_at}", f"analyzed_at 须为 YYYY-MM-DD，实际 {analyzed_at!r}")
    scope = data.get("scope")
    scope_ok = isinstance(scope, dict) and (
        isinstance(scope.get("root_paths"), list) and len(scope["root_paths"]) > 0
        and all(_nonempty_str(item) for item in scope["root_paths"])
        and _nonempty_str(scope.get("responsibility"))
        and _nonempty_str(scope.get("structure_summary"))
    )
    r.ok_or("S-META3", scope_ok, "scope 路径/职责/结构齐全",
            "scope 须含非空 root_paths、responsibility、structure_summary")
    analysis = data.get("analysis")
    analysis_ok = isinstance(analysis, dict) and analysis.get("symbol_mode") in {"LSP", "clang-ast", "text-search"} \
        and _nonempty_str(analysis.get("focus_strategy")) \
        and isinstance(analysis.get("git_history_used"), bool) \
        and isinstance(analysis.get("omissions"), list) \
        and all(_nonempty_str(item) for item in analysis.get("omissions", []))
    r.ok_or("S-META4", analysis_ok, "analysis 取证模式/聚焦/缺口齐全",
            "analysis 须含 symbol_mode(LSP/clang-ast/text-search)、focus_strategy、git_history_used、omissions[]")
    gaps = data.get("known_gaps")
    r.ok_or("S-META5", isinstance(gaps, list) and all(_nonempty_str(item) for item in gaps),
            f"known_gaps {len(gaps) if isinstance(gaps, list) else 0} 条",
            "known_gaps 须为字符串数组")

    # ---- S-L language ----
    lang = data.get("language")
    r.ok_or("S-L1", lang in LANGUAGES, f"language={lang}",
            f"language 非法：{lang!r}（须 JVM 或 C++）")
    if lang == "C++":
        r.ok_or("S-L2", data.get("cpp_limitation_noted") is True,
                "C++ 已标注能力受限", "C++ 须 cpp_limitation_noted=true（已标注结构/依赖分析受限）")
    else:
        r.ok("S-L2", "非 C++，跳过受限标注检查")
    if isinstance(analysis, dict) and analysis.get("symbol_mode") == "clang-ast":
        r.ok_or("S-L3", lang == "C++", "clang-ast 仅用于 C++（一致）",
                "symbol_mode=clang-ast 只能用于 language=C++")
    else:
        r.ok("S-L3", "未使用 clang-ast，跳过语言绑定检查")

    # ---- S-COV covered_files / convention_rules ----
    cov = data.get("covered_files")
    r.ok_or("S-COV1", isinstance(cov, list) and len(cov) > 0 and all(_nonempty_str(item) for item in cov),
            f"covered_files {len(cov) if isinstance(cov, list) else 0} 个",
            "covered_files 须为非空字符串数组（模块 A 边界，显式声明优于推断）")
    conventions_fed = data.get("conventions_fed")
    cr = data.get("convention_rules")
    if not isinstance(conventions_fed, bool):
        r.err("S-COV2", "conventions_fed 须为 bool")
    elif not isinstance(cr, list):
        r.err("S-COV2", "convention_rules 须为数组")
    else:
        valid_rules = all(
            isinstance(item, dict) and _nonempty_str(item.get("id")) and _nonempty_str(item.get("rule"))
            for item in cr
        )
        rule_id_list = [item.get("id") for item in cr if isinstance(item, dict)]
        unique_rules = len(rule_id_list) == len(set(rule_id_list))
        consistent = (conventions_fed and len(cr) > 0) or (not conventions_fed and len(cr) == 0)
        r.ok_or("S-COV2", valid_rules and unique_rules and consistent,
                f"规约状态一致，共 {len(cr)} 条",
                "规约须为唯一 {id,rule} 数组；fed=true 时非空，false 时必须为空")

    # ---- S-CORE explicit five-core-smell coverage ----
    core = data.get("core_smell_coverage")
    if not isinstance(core, dict):
        r.err("S-CORE1", "core_smell_coverage 须为对象")
    else:
        missing = sorted(set(CORE_SMELL_CATEGORIES) - set(core))
        extra = sorted(set(core) - set(CORE_SMELL_CATEGORIES))
        invalid = {key: value for key, value in core.items() if value not in CORE_STATUSES}
        if missing or extra or invalid:
            r.err("S-CORE1", f"核心覆盖非法：missing={missing}, extra={extra}, invalid={invalid}")
        else:
            r.ok("S-CORE1", "5 个核心坏味道覆盖状态齐全")

    # ---- S-ID / S-FD / S-EV / S-P per finding ----
    findings = data.get("findings")
    if not isinstance(findings, list):
        r.err("S-ID1", "findings 须为数组；无达到 finding 级别的问题时可用空数组 []")
        findings = []
    elif not findings:
        r.ok("S-ID1", "findings 为空：按健康 go 报告处理")
    else:
        r.ok("S-ID1", f"findings {len(findings)} 条")

    ids: list[str] = []
    rule_ids: set[str] = set()
    cr = data.get("convention_rules") or []
    if isinstance(cr, list):
        rule_ids = {str(item.get("id")) for item in cr
                    if isinstance(item, dict) and _nonempty_str(item.get("id"))}

    for i, f in enumerate(findings):
        if not isinstance(f, dict):
            r.err("S-FD1", f"findings[{i}] 不是对象")
            continue
        ctx = f"findings[{i}] ({f.get('id', '?')})"

        fid = f.get("id")
        mid = ID_RE.match(fid) if isinstance(fid, str) else None
        r.ok_or("S-ID2", bool(mid), f"{fid}: id 合法",
                f"{ctx}: id 非法 {fid!r}（须 FINDING-[SRC]<n>，如 FINDING-S01）")
        if mid:
            prefix_axis = PREFIX_AXIS[mid.group(1)]
            r.ok_or("S-ID3", f.get("axis") == prefix_axis,
                    f"{fid}: 前缀 {mid.group(1)}⇒axis {prefix_axis} 一致",
                    f"{ctx}: id 前缀 {mid.group(1)}⇒{prefix_axis} 与 axis={f.get('axis')!r} 不一致")
        if isinstance(fid, str):
            if fid in ids:
                r.err("S-ID4", f"{ctx}: id 重复（{fid}）")
            ids.append(fid)

        # required scalar fields
        r.ok_or("S-FD2", _nonempty_str(f.get("category")),
                f"{fid}: category 有", f"{ctx}: 缺 category")
        r.ok_or("S-FD3", _nonempty_str(f.get("title")),
                f"{fid}: title 有", f"{ctx}: 缺 title")
        r.ok_or("S-FD4", _nonempty_str(f.get("impact")),
                f"{fid}: impact 有", f"{ctx}: 缺 impact")
        r.ok_or("S-FD5", _nonempty_str(f.get("improvement")),
                f"{fid}: improvement 有", f"{ctx}: 缺 improvement")
        r.ok_or("S-FD5A", _nonempty_str(f.get("severity_basis")),
                f"{fid}: severity_basis 有", f"{ctx}: 缺 severity_basis")
        r.ok_or("S-FD5B", _nonempty_str(f.get("priority_basis")),
                f"{fid}: priority_basis 有", f"{ctx}: 缺 priority_basis")
        # enums
        r.ok_or("S-FD6", f.get("axis") in AXES, f"{fid}: axis={f.get('axis')}",
                f"{ctx}: axis 非法 {f.get('axis')!r}（须 smell/readability/convention）")
        r.ok_or("S-FD7", f.get("severity") in SEVERITIES,
                f"{fid}: severity={f.get('severity')}",
                f"{ctx}: severity 非法 {f.get('severity')!r}")
        r.ok_or("S-FD8", f.get("fix_cost") in FIX_COSTS,
                f"{fid}: fix_cost={f.get('fix_cost')}",
                f"{ctx}: fix_cost 非法 {f.get('fix_cost')!r}")
        r.ok_or("S-FD9", f.get("priority") in PRIORITIES,
                f"{fid}: priority={f.get('priority')}",
                f"{ctx}: priority 非法 {f.get('priority')!r}")
        r.ok_or("S-FD10", isinstance(f.get("unconfirmed"), bool),
                f"{fid}: unconfirmed={f.get('unconfirmed')}",
                f"{ctx}: unconfirmed 须为 bool")

        # evidence
        ev = f.get("evidence")
        if isinstance(ev, list) and ev and all(
                isinstance(e, dict)
                and _nonempty_str(e.get("file"))
                and _nonempty_str(e.get("note"))
                and (e.get("line") is None or isinstance(e.get("line"), int))
                for e in ev):
            r.ok("S-EV1", f"{fid}: {len(ev)} 条证据")
        else:
            r.err("S-EV1", f"{ctx}: evidence 须为非空数组，每项含 file/note，line 为整数或省略")

        # principle / convention by axis
        axis = f.get("axis")
        if axis in ("smell", "readability"):
            r.ok_or("S-P1", _nonempty_str(f.get("principle_violated")),
                    f"{fid}: principle_violated={f.get('principle_violated')}",
                    f"{ctx}: axis={axis} 须点名 principle_violated（通用设计原理，禁空泛）")
        elif axis == "convention":
            cv = f.get("convention_violated")
            r.ok_or("S-P2", _nonempty_str(cv),
                    f"{fid}: convention_violated={cv}",
                    f"{ctx}: axis=convention 须点名 convention_violated（用户规约 id）")
            if _nonempty_str(cv) and cv not in rule_ids:
                r.err("S-P3", f"{ctx}: convention_violated={cv} 不在 convention_rules id 集合 {sorted(rule_ids) or '{}'}")
        else:
            r.warn("S-P1", f"{ctx}: axis 非法，跳过原理/规约检查")

        category = f.get("category")
        allowed_categories = (
            SMELL_CATEGORIES if axis == "smell"
            else READABILITY_CATEGORIES if axis == "readability"
            else {"convention-violation"} if axis == "convention"
            else set()
        )
        r.ok_or("S-CAT1", category in allowed_categories,
                f"{fid}: category={category}",
                f"{ctx}: category={category!r} 不属于 axis={axis!r} 的允许集合")

    # coverage status must agree with actual core finding categories
    if isinstance(core, dict):
        categories = {str(f.get("category")) for f in findings if isinstance(f, dict)}
        for key, mapped in CORE_SMELL_CATEGORIES.items():
            expected = "detected" if categories & mapped else "not-detected"
            r.ok_or("S-CORE2", core.get(key) == expected,
                    f"{key}={expected} 与 findings 一致",
                    f"{key}={core.get(key)!r}，但 findings 推导应为 {expected!r}")

    # ---- S-SUM summary counts + verdict ----
    summary = data.get("summary")
    if not isinstance(summary, dict):
        r.err("S-SUM1", "summary 须为对象")
    else:
        tally = {"critical": 0, "major": 0, "minor": 0}
        for f in findings:
            sev = f.get("severity") if isinstance(f, dict) else None
            if sev in tally:
                tally[sev] += 1
        for sev in tally:
            r.ok_or(
                "S-SUM2", summary.get(sev) == tally[sev],
                f"summary.{sev}={tally[sev]} 一致",
                f"summary.{sev}={summary.get(sev)} 与实际 {tally[sev]} 不一致",
            )
        crit = tally["critical"]
        threshold = data.get("no_go_threshold")
        if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1:
            r.err("S-SUM3", f"no_go_threshold 须为正整数，实际 {threshold!r}")
            threshold = 1
        expected = "no-go" if crit >= threshold else "go"
        verdict = summary.get("verdict")
        relation = ">=" if crit >= threshold else "<"
        r.ok_or(
            "S-SUM3", verdict == expected,
            f"verdict={verdict}（critical {crit} {relation} {threshold}）",
            f"verdict={verdict!r} 与规则不符：critical {crit} {relation} 阈值 {threshold} ⇒ 应为 {expected!r}",
        )

    # ---- S-RD readability four axes ----
    rd = data.get("readability")
    if not isinstance(rd, dict):
        r.err("S-RD1", "readability 须为对象")
    else:
        miss_axis = [a for a in READABILITY_AXES if not _nonempty_str(rd.get(a))]
        if miss_axis:
            r.err("S-RD1", f"readability 缺轴或为空：{miss_axis}（四轴：职责/依赖可理解/命名表意/分层清晰）")
        else:
            r.ok("S-RD1", "可读性四轴齐全")
            covered_basenames = {Path(item).name for item in cov} if isinstance(cov, list) else set()
            missing_rd_anchor = []
            for axis_name in READABILITY_AXES[:-1]:
                anchors = ANCHOR_RE.findall(rd[axis_name])
                if not anchors or not any(Path(anchor).name in covered_basenames for anchor in anchors):
                    missing_rd_anchor.append(axis_name)
            r.ok_or("S-RD2", not missing_rd_anchor,
                    "可读性四轴均回链 covered_files",
                    f"可读性轴缺 covered_files 证据锚点：{missing_rd_anchor}")

    unconfirmed = [f for f in findings if isinstance(f, dict) and f.get("unconfirmed") is True]
    missing_gap_ids = [
        str(f.get("id")) for f in unconfirmed
        if not isinstance(gaps, list) or not any(str(f.get("id")) in gap for gap in gaps)
    ]
    if missing_gap_ids:
        r.err("S-GAP1", f"unconfirmed finding 未在 known_gaps 按 id 登记：{missing_gap_ids}")
    else:
        r.ok("S-GAP1", "未确认项与 known_gaps 数量可对账")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate an arch-quality-eval findings.json")
    ap.add_argument("doc", type=Path, help="Path to findings.json")
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

    print(f"=== validate_findings: {args.doc} ===")
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
