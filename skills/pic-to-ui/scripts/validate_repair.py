#!/usr/bin/env python3
"""Validate pic-to-ui repair audit before edits and at closure.

Audit phase requires an explicit baseline and actionable open mismatches.
Closure phase requires every mismatch to be resolved with code/verification
evidence or honestly flagged. This gate validates declarations; it does not
claim to judge visual similarity itself.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _report import Report, emit  # noqa: E402

CATEGORIES = {"structure", "entry", "icon", "dimension", "style", "state", "bitmap"}
PRIORITIES = {"P0", "P1", "P2"}
BASELINE_STATUSES = {"captured", "provided", "unavailable"}
VERIFICATION_METHODS = {"render_diff", "visual_inspection", "static_inspection"}
VERIFICATION_RESULTS = {"matched"}


def _anchor_ok(value: Any) -> bool:
    return isinstance(value, dict) and bool(value.get("file")) and bool(value.get("widget"))


def _required_text(item: dict[str, Any], *keys: str) -> bool:
    return all(isinstance(item.get(key), str) and bool(item[key].strip()) for key in keys)


def _code_anchor_exists(value: Any, code_root: Path) -> bool:
    if not _anchor_ok(value):
        return False
    root = code_root.resolve()
    candidate = (root / str(value["file"])).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    if not candidate.is_file():
        return False
    try:
        return str(value["widget"]) in candidate.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False


def _blueprint_ids(blueprint: dict[str, Any]) -> set[str]:
    result = {"META"}
    for key in ("entries", "icons", "key_dimensions", "states", "bitmaps"):
        items = blueprint.get(key)
        if isinstance(items, list):
            result.update(str(item["id"]) for item in items if isinstance(item, dict) and item.get("id"))

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            return
        if node.get("node_id"):
            result.add(str(node["node_id"]))
        for child in node.get("children") or []:
            visit(child)

    visit(blueprint.get("structure_skeleton"))
    return result


def validate(
    document: dict[str, Any], phase: str, code_root: Path | None,
    blueprint: dict[str, Any] | None = None,
) -> Report:
    report = Report()
    meta = document.get("meta")
    meta_ok = (
        isinstance(meta, dict)
        and meta.get("mode") == "repair"
        and _required_text(meta, "target_screen", "implementation_root")
        and isinstance(meta.get("reference_screenshots"), list)
        and len(meta["reference_screenshots"]) > 0
    )
    report.add(
        "RPR.meta", "ERROR", meta_ok,
        "meta 须含 mode=repair/target_screen/implementation_root/非空 reference_screenshots"
        if not meta_ok else "repair meta 完整",
    )

    baseline = meta.get("baseline") if isinstance(meta, dict) else None
    baseline_status = baseline.get("status") if isinstance(baseline, dict) else None
    baseline_ok = baseline_status in BASELINE_STATUSES
    if baseline_ok and baseline_status in {"captured", "provided"}:
        baseline_ok = _required_text(baseline, "evidence")
    elif baseline_ok and baseline_status == "unavailable":
        baseline_ok = _required_text(baseline, "reason")
    report.add(
        "RPR.baseline", "ERROR", baseline_ok,
        "baseline 须为 captured/provided+evidence 或 unavailable+reason" if not baseline_ok else f"baseline={baseline_status}",
    )

    mismatches = document.get("mismatches")
    has_items = isinstance(mismatches, list) and len(mismatches) > 0
    report.add("RPR.mismatches", "ERROR", has_items, "mismatches 须为非空数组" if not has_items else f"mismatches={len(mismatches)}")
    if not isinstance(mismatches, list):
        return report

    seen: set[str] = set()
    for index, item in enumerate(mismatches):
        if not isinstance(item, dict):
            report.add("RPR.item", "ERROR", False, f"mismatches[{index}] 须为对象")
            continue
        item_id = str(item.get("id") or "")
        unique_id = bool(item_id) and item_id not in seen
        report.add("RPR.id", "ERROR", unique_id, f"mismatches[{index}] id 缺失或重复: {item_id!r}" if not unique_id else f"{item_id}: id 有效")
        seen.add(item_id)

        fields_ok = (
            item.get("category") in CATEGORIES
            and item.get("priority") in PRIORITIES
            and isinstance(item.get("target_ids"), list)
            and len(item["target_ids"]) > 0
            and all(isinstance(value, str) and value.strip() for value in item["target_ids"])
            and _required_text(item, "screenshot_evidence", "current_evidence", "diagnosis")
        )
        report.add(
            "RPR.fields", "ERROR", fields_ok,
            f"{item_id or index}: category/priority/target_ids/两端证据/diagnosis 不完整" if not fields_ok else f"{item_id}: 审计字段完整",
        )
        if blueprint is not None and isinstance(item.get("target_ids"), list):
            unknown = sorted(set(item["target_ids"]) - _blueprint_ids(blueprint))
            report.add(
                "RPR.target_ids", "ERROR", not unknown,
                f"{item_id}: target_ids 不在 blueprint 中: {unknown}" if unknown else f"{item_id}: target_ids 可追溯",
            )

        current_anchor = item.get("current_code_anchor")
        location_ok = _anchor_ok(current_anchor) or _required_text(item, "anchor_reason")
        report.add(
            "RPR.current_anchor", "ERROR", location_ok,
            f"{item_id or index}: 须含 current_code_anchor(file+widget) 或 anchor_reason" if not location_ok else f"{item_id}: 当前落点已登记",
        )
        if _anchor_ok(current_anchor) and code_root is not None:
            exists = _code_anchor_exists(current_anchor, code_root)
            report.add(
                "RPR.current_anchor.parity", "ERROR", exists,
                f"{item_id}: 当前代码文件/widget 不存在或越出 code-root"
                if not exists else f"{item_id}: 当前代码锚点真实存在",
            )

        status = item.get("status")
        if phase == "audit":
            report.add(
                "RPR.audit.open", "ERROR", status == "open",
                f"{item_id or index}: 审计阶段 status 须为 open，实际 {status!r}" if status != "open" else f"{item_id}: open 待修复",
            )
            continue

        if status == "resolved":
            resolution = item.get("resolution")
            resolution_ok = (
                isinstance(resolution, dict)
                and _required_text(resolution, "summary")
                and _anchor_ok(resolution.get("code_anchor"))
            )
            report.add(
                "RPR.resolution", "ERROR", resolution_ok,
                f"{item_id}: resolved 须含 summary + code_anchor(file+widget)" if not resolution_ok else f"{item_id}: resolution 完整",
            )
            verification = item.get("verification")
            verification_ok = (
                isinstance(verification, dict)
                and verification.get("method") in VERIFICATION_METHODS
                and verification.get("result") in VERIFICATION_RESULTS
                and _required_text(verification, "evidence")
            )
            if (
                verification_ok
                and verification.get("method") == "static_inspection"
                and verification.get("result") == "matched"
                and item.get("category") in {"structure", "icon", "dimension", "style", "bitmap"}
            ):
                verification_ok = False
            report.add(
                "RPR.verification", "ERROR", verification_ok,
                f"{item_id}: resolved 须含真实验证；纯视觉项不能用 static_inspection 声称 matched" if not verification_ok else f"{item_id}: verification 完整",
            )
            if code_root is not None and resolution_ok:
                rel = str(resolution["code_anchor"]["file"])
                exists = _code_anchor_exists(resolution["code_anchor"], code_root)
                report.add(
                    "RPR.parity.file", "ERROR", exists,
                    f"{item_id}: 修改文件/widget 不存在或越出 code-root: {rel}"
                    if not exists else f"{item_id}: 修改代码锚点真实存在 {rel}",
                )
        elif status == "flagged":
            flagged_ok = _required_text(item, "reason", "impact", "next_action")
            report.add(
                "RPR.flagged", "ERROR", flagged_ok,
                f"{item_id}: flagged 须含 reason/impact/next_action" if not flagged_ok else f"{item_id}: flagged（标红）",
            )
        else:
            report.add(
                "RPR.closure", "ERROR", False,
                f"{item_id or index}: 闭环阶段 status 须为 resolved|flagged，实际 {status!r}",
            )

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a pic-to-ui repair audit.")
    parser.add_argument("repair_audit", type=Path, help="Path to repair-audit.json")
    parser.add_argument("--phase", required=True, choices=("audit", "closure"))
    parser.add_argument("--blueprint", required=True, type=Path, help="Target blueprint used to verify mismatch target_ids")
    parser.add_argument("--code-root", type=Path, help="Repository root used to verify resolved code anchors")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()
    try:
        document = json.loads(args.repair_audit.read_text(encoding="utf-8"))
        blueprint = json.loads(args.blueprint.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"无法读取 repair audit：{exc}", file=sys.stderr)
        return 2
    if not isinstance(document, dict):
        print("repair audit 顶层须为对象", file=sys.stderr)
        return 2
    if not isinstance(blueprint, dict):
        print("blueprint 顶层须为对象", file=sys.stderr)
        return 2
    if args.code_root is None:
        print("--code-root 为必填，用于验证 repair 代码锚点", file=sys.stderr)
        return 2
    return emit(validate(document, args.phase, args.code_root, blueprint), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
