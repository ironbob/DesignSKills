#!/usr/bin/env python3
"""Gate 3: validate structured visual acceptance and the human report."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _report import Report, emit  # noqa: E402

MODES = {"create", "repair"}
SELF_CHECK_DIMENSIONS = {"structure", "entries", "dimensions", "style", "icons", "states", "a11y"}
CHECK_STATUSES = {"passed", "improved", "flagged"}
FLAG_PRIORITIES = {"P0", "P1", "P2"}
PROPORTION_STATUSES = {"passed", "flagged", "unverified"}


def _required_text(item: dict[str, Any], *keys: str) -> bool:
    return all(isinstance(item.get(key), str) and bool(item[key].strip()) for key in keys)


def _artifact_file(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    root = root.resolve()
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _delivery_status_ids(delivery: dict[str, Any], status: str) -> set[str]:
    result: set[str] = set()
    for category in ("entries", "icons", "structure_nodes", "dimensions", "states"):
        items = delivery.get(category)
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict) or item.get("status") != status:
                continue
            for key in ("entry_id", "icon_id", "node_id", "dimension_id", "state_id"):
                if item.get(key):
                    result.add(str(item[key]))
                    break
    return result


def _positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _ratio(measurement: Any) -> float | None:
    if not isinstance(measurement, dict):
        return None
    numerator = measurement.get("numerator_px")
    denominator = measurement.get("denominator_px")
    if not _positive_number(numerator) or not _positive_number(denominator):
        return None
    return float(numerator) / float(denominator)


def validate(
    document: dict[str, Any], artifact_root: Path,
    delivery: dict[str, Any], repair_audit: dict[str, Any] | None = None,
) -> Report:
    report = Report()
    root_ok = artifact_root.is_dir()
    report.add("ACC.root", "ERROR", root_ok, f"artifact-root 不存在: {artifact_root}" if not root_ok else "artifact-root 存在")

    meta = document.get("meta")
    mode = meta.get("mode") if isinstance(meta, dict) else None
    meta_ok = isinstance(meta, dict) and mode in MODES and _required_text(meta, "report")
    report.add("ACC.meta", "ERROR", meta_ok, "meta 须含 mode(create|repair) 与 report" if not meta_ok else f"acceptance mode={mode}")
    report_path = _artifact_file(artifact_root, meta.get("report") if isinstance(meta, dict) else None)
    report_ok = report_path is not None and report_path.stat().st_size > 0
    report.add("ACC.report", "ERROR", report_ok, "report.md 不存在、越界或为空" if not report_ok else "人读报告存在且非空")

    gates = document.get("gates")
    gates_type_ok = isinstance(gates, list)
    report.add("ACC.gates", "ERROR", gates_type_ok, "gates 须为数组" if not gates_type_ok else "gates 类型正确")
    gate_index: dict[str, dict[str, Any]] = {}
    if isinstance(gates, list):
        for item in gates:
            if isinstance(item, dict) and item.get("name"):
                gate_index[str(item["name"])] = item
    gates_unique = isinstance(gates, list) and len(gate_index) == len(gates)
    report.add("ACC.gates.unique", "ERROR", gates_unique, "gates name 须非空且唯一" if not gates_unique else "gates name 唯一")
    required_gates = {"text-ui-confirmation", "blueprint", "coding-path", "delivery"}
    if mode == "repair":
        required_gates.update({"repair-audit", "repair-closure"})
        report.add(
            "ACC.repair_audit", "ERROR", isinstance(repair_audit, dict),
            "repair mode 必须传 --repair-audit 用于 flagged 对账"
            if not isinstance(repair_audit, dict) else "repair-audit 已提供",
        )
    for name in sorted(required_gates):
        item = gate_index.get(name)
        ok = isinstance(item, dict) and item.get("status") == "passed" and _required_text(item, "evidence")
        report.add("ACC.gate.result", "ERROR", ok, f"gate {name} 缺失、未 passed 或无 evidence" if not ok else f"gate {name}=passed")

    render = document.get("render_diff")
    render_status = render.get("status") if isinstance(render, dict) else None
    if render_status == "executed":
        fields_ok = (
            render.get("result") in {"matched", "improved", "flagged"}
            and all(_artifact_file(artifact_root, render.get(key)) is not None for key in ("reference", "after", "comparison"))
        )
        report.add("ACC.diff", "ERROR", fields_ok, "已执行 diff 时 reference/after/comparison 必须是真实文件，result 必须合法" if not fields_ok else f"diff={render.get('result')}")
    elif render_status == "unavailable":
        fields_ok = _required_text(render, "reason") and render.get("result") == "unverified"
        report.add("ACC.diff", "ERROR", fields_ok, "diff 不可用时须写 reason 且 result=unverified" if not fields_ok else "diff 不可用且未冒充视觉匹配")
    else:
        report.add("ACC.diff", "ERROR", False, "render_diff.status 须为 executed|unavailable")

    checks = document.get("self_check")
    check_index: dict[str, dict[str, Any]] = {}
    if isinstance(checks, list):
        for item in checks:
            if isinstance(item, dict) and item.get("dimension"):
                check_index[str(item["dimension"])] = item
    report.add("ACC.self_check.unique", "ERROR", isinstance(checks, list) and len(check_index) == len(checks), "self_check 须为数组且 dimension 唯一" if not isinstance(checks, list) or len(check_index) != len(checks) else "self_check dimension 唯一")
    exact_dimensions = set(check_index) == SELF_CHECK_DIMENSIONS
    report.add(
        "ACC.self_check.dimensions", "ERROR", exact_dimensions,
        f"self_check dimensions 必须恰为 {sorted(SELF_CHECK_DIMENSIONS)}，实际 {sorted(check_index)}"
        if not exact_dimensions else "self_check dimensions 集合正确",
    )
    for dimension in sorted(SELF_CHECK_DIMENSIONS):
        item = check_index.get(dimension)
        ok = isinstance(item, dict) and item.get("status") in CHECK_STATUSES and _required_text(item, "evidence")
        report.add("ACC.self_check.coverage", "ERROR", ok, f"self_check 缺少 {dimension} 或判定/evidence 不完整" if not ok else f"self_check.{dimension}={item['status']}")

    proportion = document.get("proportion_check")
    dimension_ids = {
        str(item["dimension_id"])
        for item in delivery.get("dimensions", [])
        if isinstance(item, dict) and item.get("dimension_id")
    }
    viewport_ok = (
        isinstance(proportion, dict)
        and all(
            isinstance(proportion.get(viewport), dict)
            and _positive_number(proportion[viewport].get("width_px"))
            and _positive_number(proportion[viewport].get("height_px"))
            for viewport in ("reference_viewport", "rendered_viewport")
        )
    )
    report.add("ACC.proportion.viewport", "ERROR", viewport_ok, "proportion_check 须记录参考图与实际渲染的正数 viewport 尺寸" if not viewport_ok else "比例验收 viewport 完整")
    proportion_items = proportion.get("items") if isinstance(proportion, dict) else None
    proportion_index = {
        str(item["dimension_id"]): item
        for item in proportion_items or []
        if isinstance(item, dict) and item.get("dimension_id")
    }
    coverage_ok = isinstance(proportion_items, list) and len(proportion_index) == len(proportion_items) and set(proportion_index) == dimension_ids
    report.add("ACC.proportion.coverage", "ERROR", coverage_ok, f"比例验收必须恰覆盖 delivery.dimensions: 期望 {sorted(dimension_ids)}，实际 {sorted(proportion_index)}" if not coverage_ok else "每个关键尺寸都有比例验收")
    proportion_flag_ids: set[str] = set()
    for dimension_id, item in proportion_index.items():
        reference_ratio = _ratio(item.get("reference"))
        rendered_ratio = _ratio(item.get("rendered"))
        tolerance = item.get("tolerance_pct")
        status = item.get("status")
        fields_ok = (
            status in PROPORTION_STATUSES
            and reference_ratio is not None
            and rendered_ratio is not None
            and _positive_number(tolerance)
            and float(tolerance) <= 8
            and _required_text(item, "evidence")
        )
        report.add("ACC.proportion.fields", "ERROR", fields_ok, f"{dimension_id}: reference/rendered 比例、0<tolerance_pct≤8、status、evidence 不完整" if not fields_ok else f"{dimension_id}: 比例字段完整")
        if not fields_ok:
            continue
        deviation = abs(rendered_ratio - reference_ratio) / reference_ratio * 100
        claimed = item.get("deviation_pct")
        deviation_ok = (
            isinstance(claimed, (int, float))
            and not isinstance(claimed, bool)
            and math.isfinite(claimed)
            and claimed >= 0
        )
        deviation_ok = deviation_ok and abs(float(claimed) - deviation) <= 0.11
        report.add("ACC.proportion.math", "ERROR", deviation_ok, f"{dimension_id}: deviation_pct 与测量值不一致" if not deviation_ok else f"{dimension_id}: 比例偏差 {deviation:.2f}%")
        if status == "passed":
            within_tolerance = deviation <= float(tolerance) + 1e-9
            report.add("ACC.proportion.tolerance", "ERROR", within_tolerance, f"{dimension_id}: 比例偏差 {deviation:.2f}% 超出 {tolerance}% 容差" if not within_tolerance else f"{dimension_id}: 比例在容差内")
        else:
            values = item.get("flag_ids")
            links_ok = isinstance(values, list) and bool(values) and all(isinstance(value, str) and value for value in values)
            report.add("ACC.proportion.flags", "ERROR", links_ok, f"{dimension_id}: flagged/unverified 必须关联非空 flag_ids" if not links_ok else f"{dimension_id}: 残差已标红")
            if links_ok:
                proportion_flag_ids.update(values)

    tests = document.get("tests")
    tests_ok = isinstance(tests, list) and len(tests) > 0
    report.add("ACC.tests", "ERROR", tests_ok, "tests 须为非空数组" if not tests_ok else f"tests={len(tests)}")
    if isinstance(tests, list):
        for index, item in enumerate(tests):
            item_ok = isinstance(item, dict) and _required_text(item, "command", "evidence") and item.get("result") in {"passed", "failed", "not_run"}
            report.add("ACC.test.fields", "ERROR", item_ok, f"tests[{index}] command/result/evidence 不完整" if not item_ok else f"test[{index}]={item['result']}")
            if item_ok:
                report.add("ACC.test.result", "ERROR", item["result"] != "failed", f"测试失败: {item['command']}" if item["result"] == "failed" else f"测试未失败: {item['command']}")

    flags = document.get("flags")
    flags_ok = isinstance(flags, list)
    report.add("ACC.flags", "ERROR", flags_ok, "flags 须为数组" if not flags_ok else f"flags={len(flags)}")
    if isinstance(flags, list):
        seen: set[str] = set()
        for index, item in enumerate(flags):
            item_id = str(item.get("id") or "") if isinstance(item, dict) else ""
            item_ok = (
                isinstance(item, dict)
                and bool(item_id)
                and item_id not in seen
                and item.get("priority") in FLAG_PRIORITIES
                and _required_text(item, "reason", "next_action")
            )
            report.add("ACC.flag.fields", "ERROR", item_ok, f"flags[{index}] id/priority/reason/next_action 缺失或重复" if not item_ok else f"flag {item_id} 完整")
            seen.add(item_id)
            if item_ok:
                report.add("ACC.flag.p0", "ERROR", item["priority"] != "P0", f"未关闭 P0 flag 阻断交付: {item_id}" if item["priority"] == "P0" else f"flag {item_id} 非 P0")

    flag_ids = {
        str(item["id"])
        for item in flags or []
        if isinstance(item, dict) and item.get("id")
    } if isinstance(flags, list) else set()
    expected_flags = _delivery_status_ids(delivery, "flagged")
    if isinstance(repair_audit, dict):
        expected_flags.update(
            str(item["id"])
            for item in repair_audit.get("mismatches", [])
            if isinstance(item, dict) and item.get("status") == "flagged" and item.get("id")
        )
    missing_flags = sorted(expected_flags - flag_ids)
    report.add("ACC.flags.parity", "ERROR", not missing_flags, f"delivery/repair flagged 未汇总到 acceptance: {missing_flags}" if missing_flags else "delivery/repair flagged 已汇总")

    linked_flag_ids: set[str] = set()
    if isinstance(render, dict) and (
        render.get("status") == "unavailable" or render.get("result") in {"improved", "flagged"}
    ):
        values = render.get("flag_ids")
        ok = isinstance(values, list) and bool(values) and all(isinstance(value, str) and value for value in values)
        report.add("ACC.diff.flags", "ERROR", ok, "diff unavailable/improved/flagged 时必须关联非空 flag_ids" if not ok else "diff 残差已关联 flags")
        if ok:
            linked_flag_ids.update(values)
    for dimension, item in check_index.items():
        if item.get("status") not in {"improved", "flagged"}:
            continue
        values = item.get("flag_ids")
        ok = isinstance(values, list) and bool(values) and all(isinstance(value, str) and value for value in values)
        report.add("ACC.self_check.flags", "ERROR", ok, f"self_check.{dimension} 非 passed 时必须关联 flag_ids" if not ok else f"self_check.{dimension} 已关联 flags")
        if ok:
            linked_flag_ids.update(values)
    linked_flag_ids.update(proportion_flag_ids)
    unknown_links = sorted(linked_flag_ids - flag_ids)
    report.add("ACC.flag.links", "ERROR", not unknown_links, f"diff/self_check 引用了不存在的 flags: {unknown_links}" if unknown_links else "diff/self_check flag 引用有效")

    waivers = document.get("waivers")
    waivers_ok = isinstance(waivers, list)
    report.add("ACC.waivers", "ERROR", waivers_ok, "waivers 须为数组（无豁免时用 []）" if not waivers_ok else f"waivers={len(waivers)}")
    waiver_ids: set[str] = set()
    if isinstance(waivers, list):
        for index, item in enumerate(waivers):
            item_id = str(item.get("id") or "") if isinstance(item, dict) else ""
            ok = isinstance(item, dict) and bool(item_id) and item_id not in waiver_ids and _required_text(item, "reason", "evidence")
            report.add("ACC.waiver.fields", "ERROR", ok, f"waivers[{index}] id/reason/evidence 缺失或重复" if not ok else f"waiver {item_id} 完整")
            waiver_ids.add(item_id)
    expected_waivers = _delivery_status_ids(delivery, "waived")
    missing_waivers = sorted(expected_waivers - waiver_ids)
    report.add("ACC.waivers.parity", "ERROR", not missing_waivers, f"delivery waived 未汇总到 acceptance: {missing_waivers}" if missing_waivers else "delivery waivers 已汇总")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate 3: structured acceptance validation.")
    parser.add_argument("acceptance", type=Path)
    parser.add_argument("delivery", type=Path)
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("--repair-audit", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        document = json.loads(args.acceptance.read_text(encoding="utf-8"))
        delivery = json.loads(args.delivery.read_text(encoding="utf-8"))
        repair_audit = (
            json.loads(args.repair_audit.read_text(encoding="utf-8"))
            if args.repair_audit is not None else None
        )
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取 acceptance：{exc}", file=sys.stderr)
        return 2
    if not isinstance(document, dict):
        print("acceptance 顶层须为对象", file=sys.stderr)
        return 2
    if not isinstance(delivery, dict):
        print("delivery 顶层须为对象", file=sys.stderr)
        return 2
    if args.repair_audit is not None and not isinstance(repair_audit, dict):
        print("repair-audit 顶层须为对象", file=sys.stderr)
        return 2
    return emit(validate(document, args.artifact_root, delivery, repair_audit), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
