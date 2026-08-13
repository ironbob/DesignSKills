#!/usr/bin/env python3
"""Gate 1 (hard): blueprint completeness — R1.

``blueprint.json`` is the "what should exist" contract parsed from the confirmed input
(5 categories: structure_skeleton / entries / icons / key_dimensions / states).
This gate checks it is complete and has integrity (ids, semantics, input
anchors), no lazy placeholders, and interaction states are source-tagged (R9).

It does NOT judge whether the parse is visually correct — that is advisory
(self-check report + diff). It only enforces "you actually produced a complete,
honest blueprint before generating any code" (R1).

Run:  python3 scripts/validate_blueprint.py <blueprint.json>
      --text-ui-manifest <text-ui-manifest.json> --artifact-root <artifact-root> [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _report import Report, emit  # noqa: E402
from validate_text_ui import validate as validate_text_ui  # noqa: E402

REQUIRED_CATEGORIES = [
    "structure_skeleton",
    "entries",
    "icons",
    "key_dimensions",
    "states",
]
# Lazy markers only — "placeholder"/"占位" are legitimate field values (e.g. bitmap
# handling), so they are NOT matched here. We catch "TODO/待定/lorem" instead.
PLACEHOLDER_RE = re.compile(r"(TODO|TBD|FIXME|XXX|待定|待补|之后再说|lorem)", re.IGNORECASE)
VALID_STATE_SOURCES = {"input", "inferred"}
VALID_MODES = {"create", "repair"}
EMPTY_REASON_CATEGORIES = {"entries", "icons", "key_dimensions", "states"}
VALID_BITMAP_HANDLING = {"placeholder", "crop_inline", "replicate"}


def _ids_are_unique(items: Any, key: str) -> bool:
    if not isinstance(items, list):
        return False
    ids = [str(item.get(key)) for item in items if isinstance(item, dict) and item.get(key)]
    return len(ids) == len(items) and len(ids) == len(set(ids))


def _validate_structure(node: Any, report: Report, seen: set[str], path: str) -> None:
    if not isinstance(node, dict):
        report.add("BP.structure.fields", "ERROR", False, f"{path}: 结构节点须为对象")
        return
    node_id = str(node.get("node_id") or "")
    fields_ok = bool(node_id) and bool(node.get("kind"))
    report.add(
        "BP.structure.fields", "ERROR", fields_ok,
        f"{path}: 须含 node_id/kind" if not fields_ok else f"{node_id}: 结构字段完整",
    )
    unique = bool(node_id) and node_id not in seen
    report.add(
        "BP.structure.unique", "ERROR", unique,
        f"{path}: node_id 缺失或重复 {node_id!r}" if not unique else f"{node_id}: node_id 唯一",
    )
    if node_id:
        seen.add(node_id)
    children = node.get("children", [])
    if not isinstance(children, list):
        report.add("BP.structure.children", "ERROR", False, f"{node_id or path}: children 须为数组")
        return
    for index, child in enumerate(children):
        _validate_structure(child, report, seen, f"{path}.children[{index}]")


def _scan_placeholders(obj: Any, path: str, report: Report) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            _scan_placeholders(v, f"{path}.{k}", report)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _scan_placeholders(v, f"{path}[{i}]", report)
    elif isinstance(obj, str) and PLACEHOLDER_RE.search(obj):
        report.add("BP.placeholder", "ERROR", False, f"{path}: 含偷懒占位符 {obj!r}")


def validate(
    blueprint: dict[str, Any],
    text_ui_manifest: dict[str, Any] | None = None,
    artifact_root: Path | None = None,
    text_ui_manifest_path: Path | None = None,
) -> Report:
    report = Report()

    # 1. task metadata: target context and create/repair mode
    meta = blueprint.get("meta")
    text_guard = meta.get("text_ui_guard") if isinstance(meta, dict) else None
    source_inputs = meta.get("source_inputs") if isinstance(meta, dict) else None
    guard_ok = (
        isinstance(text_guard, dict)
        and bool(text_guard.get("manifest"))
        and text_guard.get("result") == "user_confirmed"
        and isinstance(text_guard.get("confirmed_input_ids"), list)
        and len(text_guard["confirmed_input_ids"]) == len(source_inputs or [])
        and len(text_guard["confirmed_input_ids"]) == len(set(text_guard["confirmed_input_ids"]))
        and bool(text_guard.get("confirmation_evidence"))
    )
    meta_ok = (
        isinstance(meta, dict)
        and meta.get("mode") in VALID_MODES
        and bool(meta.get("platform"))
        and bool(meta.get("framework"))
        and bool(meta.get("screen_job"))
        and meta.get("scope") == "single_screen"
        and isinstance(source_inputs, list)
        and len(source_inputs) > 0
        and all(
            isinstance(item, dict)
            and bool(item.get("id"))
            and item.get("type") in {"screenshot", "verbal"}
            for item in source_inputs
        )
        and guard_ok
    )
    report.add(
        "BP.meta", "ERROR", meta_ok,
        "meta 须含 mode/platform/framework/screen_job/scope=single_screen/非空 source_inputs，"
        "以及 user_confirmed 的 text_ui_guard(manifest/confirmed_input_ids/confirmation_evidence)"
        if not meta_ok else f"meta 完整，mode={meta['mode']}",
    )

    if isinstance(text_ui_manifest, dict) and artifact_root is not None:
        text_report = validate_text_ui(text_ui_manifest, "confirmed", artifact_root)
        report.items.extend(text_report.items)
        inputs = text_ui_manifest.get("inputs")
        manifest_inputs = [
            {"id": item.get("id"), "type": item.get("input_type")}
            for item in inputs if isinstance(item, dict)
        ] if isinstance(inputs, list) else []
        manifest_ids = [item.get("id") for item in inputs if isinstance(item, dict)] if isinstance(inputs, list) else []
        parity = (
            manifest_inputs == source_inputs
            and isinstance(text_guard, dict)
            and manifest_ids == text_guard.get("confirmed_input_ids")
        )
        report.add("BP.text_ui.parity", "ERROR", parity,
                   "blueprint.source_inputs / confirmed_input_ids 必须与已确认 text-ui manifest 顺序一致"
                   if not parity else "blueprint 与已确认文本图一一对账")
        if text_ui_manifest_path is not None and isinstance(text_guard, dict):
            declared = (artifact_root / str(text_guard.get("manifest", ""))).resolve()
            actual = text_ui_manifest_path.resolve()
            try:
                declared.relative_to(artifact_root.resolve())
                inside = True
            except ValueError:
                inside = False
            manifest_ref_ok = inside and declared == actual
            report.add("BP.text_ui.manifest", "ERROR", manifest_ref_ok,
                       "text_ui_guard.manifest 必须在 artifact-root 内并指向传入的真实 manifest"
                       if not manifest_ref_ok else "text-ui manifest 回链真实")

    # 2. five categories present with the expected container type
    for cat in REQUIRED_CATEGORIES:
        value = blueprint.get(cat)
        present = isinstance(value, dict) if cat == "structure_skeleton" else isinstance(value, list)
        report.add(
            f"BP.category.{cat}",
            "ERROR",
            present,
            f"类别 {cat} 缺失或类型错误" if not present else f"类别 {cat} 类型正确",
        )

    # 3. structure_skeleton non-empty root node (R4 source)
    skel = blueprint.get("structure_skeleton")
    has_skel = isinstance(skel, dict) and bool(skel.get("node_id"))
    report.add(
        "BP.structure.nonempty",
        "ERROR",
        has_skel,
        "structure_skeleton 须为非空根节点（含 node_id）" if not has_skel else "结构骨架非空",
    )
    if isinstance(skel, dict):
        _validate_structure(skel, report, set(), "structure_skeleton")

    empty_reasons = blueprint.get("empty_reasons", {})
    empty_reasons_ok = isinstance(empty_reasons, dict)
    report.add(
        "BP.empty_reasons.type", "ERROR", empty_reasons_ok,
        "empty_reasons 须为对象" if not empty_reasons_ok else "empty_reasons 类型正确",
    )
    if not empty_reasons_ok:
        empty_reasons = {}
    unknown_empty_reasons = sorted(set(empty_reasons) - EMPTY_REASON_CATEGORIES)
    report.add(
        "BP.empty_reasons.keys", "ERROR", not unknown_empty_reasons,
        f"empty_reasons 含未知类别: {unknown_empty_reasons}"
        if unknown_empty_reasons else "empty_reasons 类别合法",
    )

    def require_items_or_reason(category: str, items: list[Any]) -> None:
        reason = empty_reasons.get(category)
        ok = bool(items) or (isinstance(reason, str) and bool(reason.strip()))
        report.add(
            f"BP.{category}.count", "ERROR", ok,
            f"{category} 为空时必须提供 empty_reasons.{category}，禁止空数组绿灯"
            if not ok else (
                f"{category}={len(items)}"
                if items else f"{category} 为空，已显式说明: {reason}"
            ),
        )

    # 4. entries — the functional entry points (R2 source).
    entries = blueprint.get("entries")
    if isinstance(entries, list):
        require_items_or_reason("entries", entries)
        for i, e in enumerate(entries):
            ok = (
                isinstance(e, dict)
                and bool(e.get("id"))
                and bool(e.get("kind"))
                and bool(e.get("semantic"))
                and bool(e.get("input_anchor"))
            )
            report.add(
                "BP.entry.fields",
                "ERROR",
                ok,
                f"entries[{i}] {e.get('id', '<无id>') if isinstance(e, dict) else '<非对象>'}: "
                "须含 id / kind / semantic / input_anchor",
            )
        report.add(
            "BP.entry.unique", "ERROR", _ids_are_unique(entries, "id"),
            "entry id 须全部非空且唯一" if not _ids_are_unique(entries, "id") else "entry id 唯一",
        )

    # 5. icons (R3/R11 source).
    icons = blueprint.get("icons")
    if isinstance(icons, list):
        require_items_or_reason("icons", icons)
        for i, ic in enumerate(icons):
            ok = (
                isinstance(ic, dict)
                and bool(ic.get("id"))
                and bool(ic.get("semantic"))
                and bool(ic.get("input_anchor"))
            )
            report.add(
                "BP.icon.fields",
                "ERROR",
                ok,
                f"icons[{i}] {ic.get('id', '<无id>') if isinstance(ic, dict) else '<非对象>'}: "
                "须含 id / semantic / input_anchor",
            )
        report.add(
            "BP.icon.unique", "ERROR", _ids_are_unique(icons, "id"),
            "icon id 须全部非空且唯一" if not _ids_are_unique(icons, "id") else "icon id 唯一",
        )

    # 6. key_dimensions (R5/P1 source).
    kd = blueprint.get("key_dimensions")
    if isinstance(kd, list):
        require_items_or_reason("key_dimensions", kd)
        for i, dim in enumerate(kd):
            ok = (
                isinstance(dim, dict)
                and bool(dim.get("id"))
                and bool(dim.get("what"))
                and bool(dim.get("ratio_note"))
            )
            report.add(
                "BP.dimension.fields", "ERROR", ok,
                f"key_dimensions[{i}]: 须含 id/what/ratio_note" if not ok else f"{dim['id']}: 尺寸字段完整",
            )
        report.add(
            "BP.dimension.unique", "ERROR", _ids_are_unique(kd, "id"),
            "dimension id 须全部非空且唯一" if not _ids_are_unique(kd, "id") else "dimension id 唯一",
        )

    # 7. states source-tagged (R9)
    states = blueprint.get("states")
    if isinstance(states, list):
        require_items_or_reason("states", states)
        for i, s in enumerate(states):
            src = s.get("source") if isinstance(s, dict) else None
            ok = (
                isinstance(s, dict)
                and bool(s.get("id"))
                and bool(s.get("kind"))
                and src in VALID_STATE_SOURCES
                and (src != "input" or bool(s.get("input_anchor")))
            )
            report.add(
                "BP.state.source",
                "ERROR",
                ok,
                f"states[{i}]: 须含 id/kind、合法 source；input 来源还须 anchor"
                if not ok else f"{s['id']}: state 字段与来源完整",
            )
        report.add(
            "BP.state.unique", "ERROR", _ids_are_unique(states, "id"),
            "state id 须全部非空且唯一" if not _ids_are_unique(states, "id") else "state id 唯一",
        )

    # 8. optional bitmaps still need a valid, traceable declaration when present.
    bitmaps = blueprint.get("bitmaps")
    if bitmaps is not None:
        bitmaps_type_ok = isinstance(bitmaps, list)
        report.add(
            "BP.bitmaps.type", "ERROR", bitmaps_type_ok,
            "bitmaps 须为数组" if not bitmaps_type_ok else "bitmaps 类型正确",
        )
        if isinstance(bitmaps, list):
            for i, bitmap in enumerate(bitmaps):
                ok = (
                    isinstance(bitmap, dict)
                    and bool(bitmap.get("id"))
                    and bool(bitmap.get("semantic"))
                    and bitmap.get("handling") in VALID_BITMAP_HANDLING
                )
                report.add(
                    "BP.bitmap.fields", "ERROR", ok,
                    f"bitmaps[{i}] 须含 id/semantic 及合法 handling"
                    if not ok else f"{bitmap['id']}: 位图字段完整",
                )
            report.add(
                "BP.bitmap.unique", "ERROR", _ids_are_unique(bitmaps, "id"),
                "bitmap id 须全部非空且唯一"
                if not _ids_are_unique(bitmaps, "id") else "bitmap id 唯一",
            )

    # 9. placeholder scan across the whole document
    _scan_placeholders(blueprint, "blueprint", report)

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate 1: blueprint completeness (R1).")
    ap.add_argument("blueprint", type=Path, help="Path to blueprint.json")
    ap.add_argument("--text-ui-manifest", required=True, type=Path,
                    help="Path to the user-confirmed text-ui-manifest.json")
    ap.add_argument("--artifact-root", required=True, type=Path,
                    help="Root containing text UI files")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = ap.parse_args()
    try:
        blueprint = json.loads(args.blueprint.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取 blueprint：{exc}", file=sys.stderr)
        return 2
    if not isinstance(blueprint, dict):
        print("blueprint 顶层须为对象", file=sys.stderr)
        return 2
    try:
        text_ui_manifest = json.loads(args.text_ui_manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取 text-ui manifest：{exc}", file=sys.stderr)
        return 2
    if not isinstance(text_ui_manifest, dict):
        print("text-ui manifest 顶层须为对象", file=sys.stderr)
        return 2
    return emit(validate(
        blueprint, text_ui_manifest, args.artifact_root, args.text_ui_manifest
    ), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
