#!/usr/bin/env python3
"""Validate the v2 architecture-quality findings contract."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

PRINCIPLES = (
    "complexity-management",
    "responsibility-cohesion",
    "coupling-dependency-direction",
    "information-hiding",
    "abstraction-consistency",
    "change-isolation",
)
PRINCIPLE_STATUSES = {"concern", "no-material-concern", "inconclusive"}
CONFIDENCES = {"confirmed", "probable", "hypothesis"}
SEVERITIES = {"critical", "major", "minor"}
FIX_COSTS = {"low", "medium", "high"}
PRIORITIES = {"P1", "P2", "P3"}
VERDICTS = {"go", "no-go", "inconclusive"}
AXES = {"design", "convention"}
ID_RE = re.compile(r"^FINDING-([DC])\d+$")
MODULE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PREFIX_AXIS = {"D": "design", "C": "convention"}
REQUIRED_TOP = (
    "schema_version", "module", "analyzed_at", "language", "scope", "coverage",
    "conventions_fed", "convention_rules", "analysis", "design_principle_coverage",
    "known_gaps", "no_go_threshold", "summary", "architecture_readability", "findings",
)


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

    def check(self, rule: str, condition: bool, ok: str, error: str) -> None:
        self.ok(rule, ok) if condition else self.err(rule, error)


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_evidence(items: Any) -> bool:
    return isinstance(items, list) and all(
        isinstance(item, dict)
        and nonempty(item.get("file"))
        and nonempty(item.get("note"))
        and (item.get("line") is None or isinstance(item.get("line"), int))
        for item in items
    )


def validate(data: Any, _path: Path) -> Report:
    r = Report()
    if not isinstance(data, dict):
        r.err("S-F1", "顶层不是 JSON 对象")
        return r
    missing = [key for key in REQUIRED_TOP if key not in data]
    r.check("S-F1", not missing, "v2 顶层字段齐全", f"缺必填顶层字段：{missing}")
    r.check("S-V1", data.get("schema_version") == 2, "schema_version=2", "schema_version 必须为 2")
    r.check("S-META1", bool(MODULE_RE.fullmatch(str(data.get("module", "")))),
            f"module={data.get('module')}", "module 须为 kebab-case")
    r.check("S-META2", bool(DATE_RE.fullmatch(str(data.get("analyzed_at", "")))),
            f"analyzed_at={data.get('analyzed_at')}", "analyzed_at 须为 YYYY-MM-DD")

    language = data.get("language")
    r.check("S-L1", language in {"JVM", "C++"}, f"language={language}", "language 须为 JVM 或 C++")
    if language == "C++":
        r.check("S-L2", data.get("cpp_limitation_noted") is True,
                "C++ 已声明实际取证限制", "C++ 须 cpp_limitation_noted=true")

    scope = data.get("scope")
    scope_ok = isinstance(scope, dict) and isinstance(scope.get("root_paths"), list) \
        and bool(scope.get("root_paths")) and all(nonempty(x) for x in scope["root_paths"]) \
        and nonempty(scope.get("responsibility")) and nonempty(scope.get("structure_summary"))
    r.check("S-SCOPE1", scope_ok, "scope 路径/职责/结构齐全",
            "scope 须含非空 root_paths、responsibility、structure_summary")

    coverage = data.get("coverage")
    coverage_ok = isinstance(coverage, dict)
    required_arrays = ("scope_files", "indexed_files", "inspected_files", "semantic_resolved_files", "gaps")
    if not coverage_ok:
        r.err("S-COV1", "coverage 须为对象")
        scope_files: set[str] = set()
    else:
        arrays_ok = all(isinstance(coverage.get(key), list) for key in required_arrays)
        scope_list = coverage.get("scope_files", [])
        scope_files = {str(item) for item in scope_list} if isinstance(scope_list, list) else set()
        strings_ok = arrays_ok and bool(scope_files) and all(
            nonempty(item) for key in required_arrays for item in coverage.get(key, [])
        )
        subsets_ok = arrays_ok and all(
            set(map(str, coverage.get(key, []))) <= scope_files
            for key in ("indexed_files", "inspected_files", "semantic_resolved_files")
        )
        flags_ok = isinstance(coverage.get("history_available"), bool) \
            and isinstance(coverage.get("sufficient_for_verdict"), bool)
        r.check("S-COV1", strings_ok and subsets_ok and flags_ok,
                f"coverage 声明范围 {len(scope_files)} 个文件",
                "coverage 文件数组须非空/为 scope_files 子集，并含两个 bool 标志")

    analysis = data.get("analysis")
    analysis_ok = isinstance(analysis, dict) and analysis.get("symbol_mode") in {"LSP", "clang-ast", "text-search"} \
        and nonempty(analysis.get("focus_strategy")) and isinstance(analysis.get("git_history_used"), bool) \
        and isinstance(analysis.get("omissions"), list) and all(nonempty(x) for x in analysis.get("omissions", []))
    r.check("S-META3", analysis_ok, "analysis 取证声明齐全", "analysis backend/策略/Git/omissions 非法")
    if isinstance(analysis, dict) and analysis.get("symbol_mode") == "clang-ast":
        r.check("S-L3", language == "C++", "clang-ast 与 C++ 一致", "clang-ast 只能用于 C++")

    conventions_fed = data.get("conventions_fed")
    rules = data.get("convention_rules")
    rule_ids: set[str] = set()
    rules_ok = isinstance(conventions_fed, bool) and isinstance(rules, list)
    if isinstance(rules, list):
        rule_ids = {str(item.get("id")) for item in rules if isinstance(item, dict) and nonempty(item.get("id"))}
        rules_ok = rules_ok and len(rule_ids) == len(rules) and all(
            isinstance(item, dict) and nonempty(item.get("id")) and nonempty(item.get("rule")) for item in rules
        ) and ((conventions_fed and bool(rules)) or (not conventions_fed and not rules))
    r.check("S-CONV1", bool(rules_ok), f"规约状态一致，共 {len(rule_ids)} 条",
            "规约须为唯一 {id,rule} 数组；fed=true 时非空，false 时为空")

    principle_coverage = data.get("design_principle_coverage")
    if not isinstance(principle_coverage, dict) or set(principle_coverage) != set(PRINCIPLES):
        r.err("S-PR1", f"design_principle_coverage 必须且只能包含六轴：{list(PRINCIPLES)}")
        principle_coverage = {}
    else:
        invalid_axes = []
        for key, item in principle_coverage.items():
            if not isinstance(item, dict) or item.get("status") not in PRINCIPLE_STATUSES \
                    or not nonempty(item.get("conclusion")) or not valid_evidence(item.get("evidence")):
                invalid_axes.append(key)
            elif item["status"] == "concern" and not item["evidence"]:
                invalid_axes.append(key)
        r.check("S-PR1", not invalid_axes, "六个设计轴状态与结论齐全",
                f"设计轴结构非法：{invalid_axes}")

    findings = data.get("findings")
    if not isinstance(findings, list):
        r.err("S-FD1", "findings 须为数组")
        findings = []
    else:
        r.ok("S-FD1", f"findings {len(findings)} 条")

    ids: set[str] = set()
    evidence_signatures: dict[tuple[tuple[str, Any], ...], tuple[str, str]] = {}
    linked_principles: set[str] = set()
    for index, finding in enumerate(findings):
        ctx = f"findings[{index}]"
        if not isinstance(finding, dict):
            r.err("S-FD2", f"{ctx} 不是对象")
            continue
        fid = finding.get("id")
        match = ID_RE.fullmatch(str(fid))
        r.check("S-ID1", bool(match) and fid not in ids, f"{fid}: id 唯一合法", f"{ctx}: id 非法或重复 {fid!r}")
        if isinstance(fid, str):
            ids.add(fid)
        axis = finding.get("axis")
        r.check("S-ID2", bool(match) and axis == PREFIX_AXIS.get(match.group(1)) if match else False,
                f"{fid}: axis={axis}", f"{ctx}: id 前缀与 axis 不一致")
        r.check("S-FD3", axis in AXES, f"{fid}: axis={axis}", f"{ctx}: axis 须 design/convention")
        for key in ("category", "title", "impact", "severity_basis", "improvement", "priority_basis"):
            r.check("S-FD4", nonempty(finding.get(key)), f"{fid}: {key} 有", f"{ctx}: 缺 {key}")
        r.check("S-FD5", finding.get("severity") in SEVERITIES, f"{fid}: severity 合法", f"{ctx}: severity 非法")
        r.check("S-FD6", finding.get("confidence") in CONFIDENCES, f"{fid}: confidence 合法", f"{ctx}: confidence 非法")
        r.check("S-FD7", finding.get("fix_cost") in FIX_COSTS, f"{fid}: fix_cost 合法", f"{ctx}: fix_cost 非法")
        r.check("S-FD8", finding.get("priority") in PRIORITIES, f"{fid}: priority 合法", f"{ctx}: priority 非法")
        evidence = finding.get("evidence")
        r.check("S-EV1", valid_evidence(evidence) and bool(evidence), f"{fid}: evidence 合法", f"{ctx}: evidence 须非空")
        principles = finding.get("principles_violated")
        principle_ok = isinstance(principles, list) and len(principles) == len(set(principles)) \
            and all(item in PRINCIPLES for item in principles)
        if axis == "design":
            principle_ok = principle_ok and bool(principles)
        r.check("S-P1", principle_ok, f"{fid}: 原理关联合法", f"{ctx}: principles_violated 非法")
        if isinstance(principles, list):
            linked_principles.update(item for item in principles if item in PRINCIPLES)
        convention_ids = finding.get("convention_rule_ids")
        convention_ok = isinstance(convention_ids, list) and len(convention_ids) == len(set(convention_ids)) \
            and set(convention_ids) <= rule_ids
        if axis == "convention":
            convention_ok = convention_ok and bool(convention_ids)
        r.check("S-P2", convention_ok, f"{fid}: 规约关联合法", f"{ctx}: convention_rule_ids 非法")
        if finding.get("confidence") != "confirmed":
            gaps = data.get("known_gaps", [])
            r.check("S-GAP1", isinstance(gaps, list) and any(str(fid) in str(gap) for gap in gaps),
                    f"{fid}: 非确认项已登记缺口", f"{fid}: probable/hypothesis 必须在 known_gaps 按 id 登记")
        if valid_evidence(evidence) and evidence:
            signature = tuple(sorted((str(item["file"]), item.get("line")) for item in evidence))
            prior = evidence_signatures.get(signature)
            duplicate_cross_axis = prior is not None and prior[1] != axis
            r.check("S-DEDUP1", not duplicate_cross_axis, f"{fid}: 无跨轴重复 finding",
                    f"{fid} 与 {prior[0] if prior else '?'} 使用相同证据重复计数；请合并原则与规约 id")
            evidence_signatures[signature] = (str(fid), str(axis))

    for principle in PRINCIPLES:
        status = (principle_coverage.get(principle) or {}).get("status") if isinstance(principle_coverage, dict) else None
        expected_concern = principle in linked_principles
        r.check("S-PR2", (status == "concern") == expected_concern,
                f"{principle}: coverage 与 findings 一致",
                f"{principle}: status={status!r} 与 findings 原理关联不一致")

    inconclusive_axes = [
        key for key, item in principle_coverage.items()
        if isinstance(item, dict) and item.get("status") == "inconclusive"
    ] if isinstance(principle_coverage, dict) else []
    sufficient = coverage.get("sufficient_for_verdict") if isinstance(coverage, dict) else None
    r.check("S-COV2", not inconclusive_axes or sufficient is False,
            "inconclusive 轴与覆盖充分性一致",
            f"存在 inconclusive 设计轴 {inconclusive_axes} 时 sufficient_for_verdict 必须为 false")

    summary = data.get("summary")
    if not isinstance(summary, dict):
        r.err("S-SUM1", "summary 须为对象")
    else:
        tally = Counter(
            finding.get("severity") for finding in findings
            if isinstance(finding, dict) and finding.get("severity") in SEVERITIES
        )
        for severity in SEVERITIES:
            r.check("S-SUM2", summary.get(severity) == tally[severity],
                    f"summary.{severity}={tally[severity]}", f"summary.{severity} 与 findings 不一致")
        confirmed_critical = sum(
            1 for finding in findings if isinstance(finding, dict)
            and finding.get("severity") == "critical" and finding.get("confidence") == "confirmed"
        )
        r.check("S-SUM3", summary.get("confirmed_critical") == confirmed_critical,
                f"confirmed_critical={confirmed_critical}", "summary.confirmed_critical 不一致")
        threshold = data.get("no_go_threshold")
        threshold_ok = isinstance(threshold, int) and not isinstance(threshold, bool) and threshold > 0
        r.check("S-SUM4", threshold_ok, f"no_go_threshold={threshold}", "no_go_threshold 须为正整数")
        threshold = threshold if threshold_ok else 1
        expected_verdict = "no-go" if confirmed_critical >= threshold else "go" if sufficient is True else "inconclusive"
        verdict = summary.get("verdict")
        r.check("S-SUM5", verdict in VERDICTS and verdict == expected_verdict,
                f"verdict={verdict}",
                f"verdict 应为 {expected_verdict}；覆盖不足且无 confirmed critical 时必须 inconclusive")

    readability = data.get("architecture_readability")
    readability_ok = isinstance(readability, dict) and readability.get("overall") in {"clear", "mixed", "opaque", "inconclusive"} \
        and nonempty(readability.get("rationale"))
    r.check("S-RD1", readability_ok, "架构可理解性摘要齐全", "architecture_readability 须含 overall/rationale")
    gaps = data.get("known_gaps")
    r.check("S-GAP2", isinstance(gaps, list) and all(nonempty(item) for item in gaps),
            f"known_gaps {len(gaps) if isinstance(gaps, list) else 0} 条", "known_gaps 须为字符串数组")
    return r


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate arch-quality-eval findings v2")
    parser.add_argument("doc", type=Path)
    args = parser.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    try:
        data = json.loads(args.doc.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.doc}: JSON 解析失败：{exc}\n")
        return 2
    report = validate(data, args.doc)
    print(f"=== validate_findings: {args.doc} ===")
    for line in report.errors + report.warns + report.passed:
        print(line)
    print(f"\nERROR: {len(report.errors)}  WARNING: {len(report.warns)}  PASSED: {len(report.passed)}")
    if report.errors:
        print("\n结果：不合格")
        return 1
    print("\n结果：合格")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
