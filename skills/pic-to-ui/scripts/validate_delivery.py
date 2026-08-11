#!/usr/bin/env python3
"""Gate 2: reconcile blueprint, delivery, real code anchors, and assets.

P0 entries/icons/structure must be delivered. A flagged P0 item blocks delivery;
only an explicit user-approved ``waived`` record can pass as an exception.
P1 dimensions/states may be flagged with a reason. Every delivered code anchor is
verified against a required code root, and every icon/bitmap is reconciled with
assets-manifest.json.

Run:
  python3 validate_delivery.py blueprint.json delivery.json \
    assets-manifest.json change-assessment.json code-root [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _report import Report, emit  # noqa: E402
from validate_change_assessment import validate as validate_change_assessment  # noqa: E402

VALID_ICON_ASSET_TYPES = {"downloaded", "self_drawn"}
APPROVED_ICON_SITES = {"Iconfont", "Lucide", "Material Symbols"}
DELIVERY_ID_KEYS = ("entry_id", "icon_id", "node_id", "dimension_id", "state_id")
DELIVERY_CATEGORIES = ("entries", "icons", "structure_nodes", "dimensions", "states")


def _required_text(item: dict[str, Any], *keys: str) -> bool:
    return all(isinstance(item.get(key), str) and bool(item[key].strip()) for key in keys)


def _icon_search_trace_ok(asset: dict[str, Any]) -> tuple[bool, str]:
    """Validate the mandatory designated-site search trail for one icon."""
    trace = asset.get("search_trace")
    if not isinstance(trace, list) or not trace:
        return False, "缺少非空 search_trace"
    results: dict[str, str] = {}
    for item in trace:
        if (
            not isinstance(item, dict)
            or item.get("site") not in APPROVED_ICON_SITES
            or item.get("result") not in {"found", "not_found"}
            or not _required_text(item, "query", "search_url")
        ):
            return False, "search_trace 条目须含指定 site、query、search_url 与 found|not_found"
        results[str(item["site"])] = str(item["result"])

    asset_type = asset.get("type")
    source_site = asset.get("source_site")
    if asset_type == "downloaded":
        if source_site not in APPROVED_ICON_SITES:
            return False, "downloaded 图标的 source_site 必须是指定网站"
        if results.get(str(source_site)) != "found":
            return False, "downloaded 图标须记录来源网站的 found 检索结果"
        return True, "指定网站检索与下载来源完整"
    if asset_type == "self_drawn":
        if source_site != "generated":
            return False, "self_drawn 图标的 source_site 必须为 generated"
        if not isinstance(asset.get("file"), str) or not asset["file"].lower().endswith(".svg"):
            return False, "self_drawn 图标只能以 SVG 文件交付"
        missing = sorted(site for site in APPROVED_ICON_SITES if results.get(site) != "not_found")
        if missing:
            return False, f"自绘前必须记录所有指定网站无语义匹配: {missing}"
        return True, "指定网站均无匹配，允许自绘 SVG"
    return False, "图标类型不合法"


def _flatten_nodes(node: Any, acc: list[str]) -> None:
    if isinstance(node, dict):
        if node.get("node_id"):
            acc.append(str(node["node_id"]))
        for child in node.get("children") or []:
            _flatten_nodes(child, acc)


def _index(items: Any, keys: tuple[str, ...] = DELIVERY_ID_KEYS) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in keys:
            if item.get(key):
                out[str(item[key])] = item
                break
    return out


def _duplicate_ids(items: Any, keys: tuple[str, ...] = DELIVERY_ID_KEYS) -> list[str]:
    if not isinstance(items, list):
        return []
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        for key in keys:
            if item.get(key):
                item_id = str(item[key])
                if item_id in seen:
                    duplicates.add(item_id)
                seen.add(item_id)
                break
    return sorted(duplicates)


def _safe_file(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        return None
    root = root.resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _check_anchor(
    report: Report,
    code_root: Path,
    code: str,
    severity: str,
    item_id: str,
    anchor: Any,
    cache: dict[Path, str | None],
) -> str | None:
    shape_ok = isinstance(anchor, dict) and _required_text(anchor, "file", "widget")
    report.add(
        f"{code}.anchor", severity, shape_ok,
        f"{item_id}: delivered 须含 code_anchor(file+widget)"
        if not shape_ok else f"{item_id}: code_anchor 字段完整",
    )
    if not shape_ok:
        return None

    path = _safe_file(code_root, anchor["file"])
    path_ok = path is not None and path.is_file()
    report.add(
        f"{code}.file", severity, path_ok,
        f"{item_id}: 代码文件不存在或越出 code-root: {anchor['file']}"
        if not path_ok else f"{item_id}: 代码文件存在 {anchor['file']}",
    )
    if not path_ok or path is None:
        return None

    if path not in cache:
        try:
            cache[path] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            cache[path] = None
    contents = cache[path]
    widget_ok = isinstance(contents, str) and anchor["widget"] in contents
    report.add(
        f"{code}.widget", severity, widget_ok,
        f"{item_id}: 文件中找不到声明的 widget/symbol {anchor['widget']!r}"
        if not widget_ok else f"{item_id}: widget/symbol 可在代码中定位",
    )
    return contents


def _waiver_ok(item: dict[str, Any]) -> bool:
    waiver = item.get("waiver")
    return (
        _required_text(item, "reason")
        and isinstance(waiver, dict)
        and waiver.get("approved_by") == "user"
        and _required_text(waiver, "evidence")
    )


def _check_status(
    report: Report,
    code_root: Path,
    code: str,
    severity: str,
    item_id: str,
    item: dict[str, Any] | None,
    kind: str,
    p0: bool,
    cache: dict[Path, str | None],
) -> str | None:
    if item is None:
        report.add(code, severity, False, f"{kind} {item_id}: 静默省略")
        return None
    status = item.get("status")
    if status == "delivered":
        return _check_anchor(report, code_root, code, severity, item_id, item.get("code_anchor"), cache)
    if status == "flagged":
        reason_ok = _required_text(item, "reason")
        passed = reason_ok and not p0
        detail = (
            f"{kind} {item_id}: P0 flagged 阻断最终交付"
            if p0 and reason_ok else
            f"{kind} {item_id}: flagged 须带 reason"
            if not reason_ok else f"{kind} {item_id}: flagged（P1 标红）"
        )
        report.add(code, severity, passed, detail)
        return None
    if status == "waived":
        passed = p0 and _waiver_ok(item)
        report.add(
            code, severity, passed,
            f"{kind} {item_id}: waived 必须含 reason 及 user-approved waiver.evidence"
            if not passed else f"{kind} {item_id}: 用户已显式豁免",
        )
        return None
    report.add(code, severity, False, f"{kind} {item_id}: status 须为 delivered|flagged|waived")
    return None


def _coding_guard_ok(guard: Any, assessment: dict[str, Any]) -> bool:
    decision = assessment.get("decision")
    meta = assessment.get("meta")
    if not isinstance(guard, dict) or not isinstance(decision, dict) or not isinstance(meta, dict):
        return False
    common = (
        guard.get("mode") == decision.get("path")
        and guard.get("assessment") == "change-assessment.json"
        and guard.get("assessment_revision") == meta.get("revision")
        and guard.get("result") == "passed"
        and _required_text(guard, "validation_evidence")
    )
    if not common:
        return False
    if guard.get("mode") == "direct_ui":
        return guard.get("implementation_owner") == "pic-to-ui"
    if guard.get("mode") == "arch_first":
        return (
            guard.get("skill") == "arch-first-code-gen"
            and guard.get("invocation") in {"same_agent", "subagent"}
            and guard.get("confirmation_mode") in {"user_confirmed", "automatic_confirmed"}
            and _required_text(guard, "design_contract", "architecture_doc")
            and (guard.get("invocation") != "subagent" or guard.get("delegation_authorized") is True)
        )
    return False


def validate(
    blueprint: dict[str, Any],
    delivery: dict[str, Any],
    manifest: dict[str, Any],
    assessment: dict[str, Any],
    code_root: Path,
) -> Report:
    report = Report()
    cache: dict[Path, str | None] = {}

    root_ok = code_root.is_dir()
    report.add("DLV.code_root", "ERROR", root_ok, f"code-root 不存在: {code_root}" if not root_ok else "code-root 存在")

    report.add("DLV.present", "ERROR", isinstance(delivery, dict), "delivery 顶层须为对象" if not isinstance(delivery, dict) else "delivery 存在")
    if not isinstance(delivery, dict):
        return report
    report.add("AST.present", "ERROR", isinstance(manifest, dict), "assets-manifest 顶层须为对象" if not isinstance(manifest, dict) else "assets-manifest 存在")
    if not isinstance(manifest, dict):
        return report

    assessment_report = validate_change_assessment(assessment)
    report.items.extend(assessment_report.items)
    assessment_mode_ok = assessment.get("meta", {}).get("mode") == blueprint.get("meta", {}).get("mode")
    report.add("DLV.assessment.mode", "ERROR", assessment_mode_ok, "change assessment mode 必须与 blueprint 一致" if not assessment_mode_ok else "change assessment mode 与 blueprint 一致")

    for category in DELIVERY_CATEGORIES:
        ok = isinstance(delivery.get(category), list)
        report.add("DLV.category", "ERROR", ok, f"delivery.{category} 须为数组" if not ok else f"delivery.{category} 类型正确")

    coding_guard = delivery.get("meta", {}).get("architecture_guard") if isinstance(delivery.get("meta"), dict) else None
    coding_guard_valid = _coding_guard_ok(coding_guard, assessment)
    report.add("DLV.coding_path", "ERROR", coding_guard_valid, "编码路径声明与 change assessment 不一致或证据不完整" if not coding_guard_valid else f"编码路径声明完整：{coding_guard['mode']}")
    if coding_guard_valid and coding_guard.get("mode") == "arch_first":
        for label in ("design_contract", "architecture_doc"):
            path = _safe_file(code_root, coding_guard[label])
            exists = path is not None and path.is_file()
            report.add("DLV.architecture.file", "ERROR", exists, f"架构产物不存在或越界: {coding_guard[label]}" if not exists else f"架构产物存在: {coding_guard[label]}")

    change_scope = delivery.get("meta", {}).get("change_scope") if isinstance(delivery.get("meta"), dict) else None
    scope_files = change_scope.get("production_files") if isinstance(change_scope, dict) else None
    scope_ok = (
        isinstance(change_scope, dict)
        and isinstance(scope_files, list)
        and bool(scope_files)
        and all(isinstance(value, str) and value.strip() for value in scope_files)
        and len(scope_files) == len(set(scope_files))
        and change_scope.get("assessment_revision") == assessment.get("meta", {}).get("revision")
        and len(scope_files) == assessment.get("estimate", {}).get("production_files")
    )
    report.add("DLV.change_scope", "ERROR", scope_ok, "delivery.meta.change_scope 须列出唯一真实生产文件，数量和 revision 必须与 assessment 一致" if not scope_ok else f"实际生产文件={len(scope_files)}")
    if isinstance(scope_files, list):
        for value in scope_files:
            path = _safe_file(code_root, value)
            exists = path is not None and path.is_file()
            report.add("DLV.change_scope.file", "ERROR", exists, f"实际改动文件不存在或越界: {value}" if not exists else f"实际改动文件存在: {value}")

    indexes = {
        "entries": _index(delivery.get("entries")),
        "icons": _index(delivery.get("icons")),
        "structure_nodes": _index(delivery.get("structure_nodes")),
        "dimensions": _index(delivery.get("dimensions")),
        "states": _index(delivery.get("states")),
    }
    delivered_anchor_files = {
        str(item["code_anchor"]["file"])
        for category in DELIVERY_CATEGORIES
        for item in (delivery.get(category) or [])
        if isinstance(item, dict)
        and item.get("status") == "delivered"
        and isinstance(item.get("code_anchor"), dict)
        and item["code_anchor"].get("file")
    }
    scope_file_set = {value for value in scope_files or [] if isinstance(value, str)} if isinstance(scope_files, list) else set()
    scope_parity = isinstance(scope_files, list) and delivered_anchor_files.issubset(scope_file_set)
    report.add("DLV.change_scope.parity", "ERROR", scope_parity, f"code anchors 含未列入 change_scope 的文件: {sorted(delivered_anchor_files - scope_file_set)}" if not scope_parity else "code anchors 均在实际改动范围内")
    for category in DELIVERY_CATEGORIES:
        duplicates = _duplicate_ids(delivery.get(category))
        report.add("DLV.unique", "ERROR", not duplicates, f"delivery.{category} 含重复 id: {duplicates}" if duplicates else f"delivery.{category} id 唯一")

    bp_entries = {str(x["id"]): x for x in blueprint.get("entries", []) if isinstance(x, dict) and x.get("id")}
    bp_icons = {str(x["id"]): x for x in blueprint.get("icons", []) if isinstance(x, dict) and x.get("id")}
    bp_dimensions = {str(x["id"]): x for x in blueprint.get("key_dimensions", []) if isinstance(x, dict) and x.get("id")}
    bp_states = {str(x["id"]): x for x in blueprint.get("states", []) if isinstance(x, dict) and x.get("id")}
    node_ids: list[str] = []
    _flatten_nodes(blueprint.get("structure_skeleton"), node_ids)
    bp_nodes = set(node_ids)

    for item_id in sorted(bp_entries):
        _check_status(report, code_root, "DLV.entry", "ERROR", item_id, indexes["entries"].get(item_id), "entry", True, cache)
    for item_id in sorted(bp_nodes):
        _check_status(report, code_root, "DLV.structure", "ERROR", item_id, indexes["structure_nodes"].get(item_id), "node", True, cache)
    for item_id in sorted(bp_dimensions):
        _check_status(report, code_root, "DLV.dimension", "ERROR", item_id, indexes["dimensions"].get(item_id), "dimension", False, cache)
    for item_id in sorted(bp_states):
        _check_status(report, code_root, "DLV.state", "ERROR", item_id, indexes["states"].get(item_id), "state", False, cache)

    manifest_icons = _index(manifest.get("icons"), ("icon_id",))
    manifest_bitmaps = _index(manifest.get("bitmaps"), ("bitmap_id",))
    for category, items, keys in (
        ("icons", manifest.get("icons"), ("icon_id",)),
        ("bitmaps", manifest.get("bitmaps"), ("bitmap_id",)),
    ):
        ok = isinstance(items, list)
        report.add("AST.category", "ERROR", ok, f"assets-manifest.{category} 须为数组" if not ok else f"assets-manifest.{category} 类型正确")
        duplicates = _duplicate_ids(items, keys)
        report.add("AST.unique", "ERROR", not duplicates, f"assets-manifest.{category} 含重复 id: {duplicates}" if duplicates else f"assets-manifest.{category} id 唯一")

    for icon_id, bp_icon in sorted(bp_icons.items()):
        delivery_icon = indexes["icons"].get(icon_id)
        contents = _check_status(report, code_root, "DLV.icon", "ERROR", icon_id, delivery_icon, "icon", True, cache)
        manifest_icon = manifest_icons.get(icon_id)
        present = isinstance(manifest_icon, dict)
        report.add("AST.icon", "ERROR", present, f"icon {icon_id}: 素材清单缺失" if not present else f"icon {icon_id}: 素材已登记")
        if not present or delivery_icon is None:
            continue
        status = delivery_icon.get("status")
        if status == "waived":
            waiver_match = manifest_icon.get("status") == "waived" and _required_text(manifest_icon, "reason")
            report.add("AST.icon.waiver", "ERROR", waiver_match, f"icon {icon_id}: manifest 须同步 waived+reason" if not waiver_match else f"icon {icon_id}: waiver 已同步")
            continue
        if status != "delivered":
            continue
        asset = delivery_icon.get("asset")
        manifest_asset = manifest_icon.get("asset")
        asset_ok = (
            isinstance(asset, dict)
            and asset.get("type") in VALID_ICON_ASSET_TYPES
            and _required_text(asset, "source", "source_site", "name", "code_reference")
        )
        report.add("DLV.icon.asset", "ERROR", asset_ok, f"icon {icon_id}: asset 须含合法 type/source/name/code_reference" if not asset_ok else f"icon {icon_id}: delivery asset 完整")
        manifest_ok = (
            manifest_icon.get("status") == "delivered"
            and manifest_icon.get("semantic") == bp_icon.get("semantic")
            and isinstance(manifest_asset, dict)
            and manifest_asset.get("type") in VALID_ICON_ASSET_TYPES
            and _required_text(manifest_asset, "source", "source_site", "name", "license", "code_reference")
        )
        report.add("AST.icon.fields", "ERROR", manifest_ok, f"icon {icon_id}: manifest 语义/status/asset/license 不完整" if not manifest_ok else f"icon {icon_id}: manifest 字段完整")
        if not asset_ok or not manifest_ok:
            continue
        parity_keys = ("type", "source", "source_site", "name", "code_reference", "file", "search_trace")
        parity = all(asset.get(key) == manifest_asset.get(key) for key in parity_keys)
        report.add("AST.icon.parity", "ERROR", parity, f"icon {icon_id}: delivery 与 manifest asset 不一致" if not parity else f"icon {icon_id}: asset 对账一致")
        code_reference_ok = isinstance(contents, str) and asset["code_reference"] in contents
        report.add("DLV.icon.code_reference", "ERROR", code_reference_ok, f"icon {icon_id}: 代码中找不到资源引用 {asset['code_reference']!r}" if not code_reference_ok else f"icon {icon_id}: 资源引用存在于代码")
        trace_ok, trace_detail = _icon_search_trace_ok(asset)
        report.add("AST.icon.source_policy", "ERROR", trace_ok, f"icon {icon_id}: {trace_detail}" if not trace_ok else f"icon {icon_id}: {trace_detail}")
        if asset["type"] in {"downloaded", "self_drawn"}:
            asset_path = _safe_file(code_root, asset.get("file"))
            asset_file_ok = asset_path is not None and asset_path.is_file()
            report.add("AST.icon.file", "ERROR", asset_file_ok, f"icon {icon_id}: downloaded/self_drawn 必须提供 code-root 内真实 file" if not asset_file_ok else f"icon {icon_id}: 素材文件存在")

    bp_bitmaps = {str(x["id"]): x for x in blueprint.get("bitmaps", []) if isinstance(x, dict) and x.get("id")}
    for bitmap_id, bitmap in sorted(bp_bitmaps.items()):
        item = manifest_bitmaps.get(bitmap_id)
        ok = (
            isinstance(item, dict)
            and item.get("semantic") == bitmap.get("semantic")
            and item.get("handling") == bitmap.get("handling")
            and _required_text(item, "license")
            and bool(item.get("source") or item.get("suggested_source"))
        )
        report.add("AST.bitmap", "ERROR", ok, f"bitmap {bitmap_id}: semantic/handling/source/license 不完整或不一致" if not ok else f"bitmap {bitmap_id}: 素材登记完整")

    valid_sets = {
        "entries": set(bp_entries),
        "icons": set(bp_icons),
        "structure_nodes": bp_nodes,
        "dimensions": set(bp_dimensions),
        "states": set(bp_states),
    }
    for category, index in indexes.items():
        dangling = sorted(set(index) - valid_sets[category])
        report.add("DLV.dangling", "ERROR", not dangling, f"delivery.{category} 引用了 blueprint 外 id: {dangling}" if dangling else f"delivery.{category} 无悬空 id")
    dangling_icons = sorted(set(manifest_icons) - set(bp_icons))
    dangling_bitmaps = sorted(set(manifest_bitmaps) - set(bp_bitmaps))
    report.add("AST.dangling", "ERROR", not dangling_icons and not dangling_bitmaps, f"assets-manifest 含悬空 id: icons={dangling_icons}, bitmaps={dangling_bitmaps}" if dangling_icons or dangling_bitmaps else "assets-manifest 无悬空 id")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate 2: delivery/code/assets reconciliation.")
    parser.add_argument("blueprint", type=Path)
    parser.add_argument("delivery", type=Path)
    parser.add_argument("assets_manifest", type=Path)
    parser.add_argument("change_assessment", type=Path)
    parser.add_argument("code_root", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        blueprint = json.loads(args.blueprint.read_text(encoding="utf-8"))
        delivery = json.loads(args.delivery.read_text(encoding="utf-8"))
        manifest = json.loads(args.assets_manifest.read_text(encoding="utf-8"))
        assessment = json.loads(args.change_assessment.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取输入：{exc}", file=sys.stderr)
        return 2
    if not isinstance(blueprint, dict):
        print("blueprint 顶层须为对象", file=sys.stderr)
        return 2
    if not isinstance(assessment, dict):
        print("change assessment 顶层须为对象", file=sys.stderr)
        return 2
    return emit(validate(blueprint, delivery, manifest, assessment, args.code_root), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
