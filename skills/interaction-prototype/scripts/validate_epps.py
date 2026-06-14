#!/usr/bin/env python3
"""Validate an interaction-prototype EPPS spec.

Accepts JSON, YAML when PyYAML is installed, or prototype.md containing a fenced
```json epps / ```yaml epps block. Exits non-zero when any ERROR fails or the
WARNING pass rate is below 80%.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ZONE_KINDS = {
    "hero_card",
    "quick_entries",
    "badge_strip",
    "word_card",
    "option_list",
    "input_block",
    "row_list",
    "chapter_tree",
    "mastery_bar",
    "score_ring",
    "stat_grid",
    "progress_strip",
    "hint_block",
    "text_block",
}

PAGE_TYPES = {
    "home",
    "course_detail",
    "learning",
    "quiz",
    "result",
    "profile",
    "list",
    "modal",
    "misc",
}

PROGRESS_ELEMENTS = {"overall", "chapter_locator", "streak", "today_minutes"}
PLACEMENTS = {"action_bar", "content", "inline"}
FEEDBACK_TYPES = {"immediate", "async", "none"}
LEVELS = {1, 2, 3, "1", "2", "3", "modal"}
LEGAL_BEHAVIOR_TARGETS = {
    "next_question",
    "previous_question",
    "submit_answer",
    "retry_quiz",
    "play_audio",
    "toggle_bookmark",
    "share",
    "close_modal",
}


def load_doc(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return json.loads(text)
    if suffix in {".yaml", ".yml"}:
        return load_yaml(text, path)
    if suffix == ".md":
        fenced = extract_fenced_spec(text)
        return load_structured_text(fenced, path)
    return load_structured_text(text, path)


def extract_fenced_spec(text: str) -> str:
    pattern = re.compile(r"```(?:json|yaml|yml)(?:\s+epps)?\s*\n(.*?)```", re.S)
    for match in pattern.finditer(text):
        block = match.group(1).strip()
        if "prototype:" in block or '"prototype"' in block:
            return block
    raise SystemExit("No fenced EPPS JSON/YAML block found in prototype.md")


def load_structured_text(text: str, path: Path) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("{"):
        return json.loads(stripped)
    return load_yaml(stripped, path)


def load_yaml(text: str, path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on host packages
        raise SystemExit(
            f"{path} looks like YAML, but PyYAML is not installed. "
            "Use JSON or install PyYAML."
        ) from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise SystemExit(f"{path} did not parse to an object")
    return data


def normalize(raw: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if "prototype" in raw:
        proto = raw.get("prototype") or {}
        pages = raw.get("pages") or proto.get("pages") or []
    else:
        proto = raw
        pages = raw.get("pages") or []
    if not isinstance(proto, dict):
        raise SystemExit("prototype must be an object")
    if not isinstance(pages, list):
        raise SystemExit("pages must be an array")
    return proto, [p for p in pages if isinstance(p, dict)]


class Report:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, rule: str, severity: str, ok: bool, message: str) -> None:
        self.items.append(
            {
                "rule": rule,
                "severity": severity,
                "status": "PASS" if ok else "FAIL",
                "message": message,
            }
        )

    def print(self) -> None:
        for item in self.items:
            icon = "OK" if item["status"] == "PASS" else "FAIL"
            print(f"{icon} {item['severity']} {item['rule']}: {item['message']}")
        errors = [i for i in self.items if i["severity"] == "ERROR"]
        warnings = [i for i in self.items if i["severity"] == "WARNING"]
        failed_errors = [i for i in errors if i["status"] == "FAIL"]
        passed_warnings = [i for i in warnings if i["status"] == "PASS"]
        warning_rate = 1.0 if not warnings else len(passed_warnings) / len(warnings)
        passed = len([i for i in self.items if i["status"] == "PASS"])
        total = len(self.items)
        print()
        print(f"Quality score: {passed}/{total} = {passed / total * 100:.1f}%")
        print(f"Warning pass rate: {warning_rate * 100:.1f}%")
        if failed_errors:
            print(f"Blocking ERROR failures: {len(failed_errors)}")

    def ok(self) -> bool:
        failed_errors = [i for i in self.items if i["severity"] == "ERROR" and i["status"] == "FAIL"]
        warnings = [i for i in self.items if i["severity"] == "WARNING"]
        passed_warnings = [i for i in warnings if i["status"] == "PASS"]
        warning_rate = 1.0 if not warnings else len(passed_warnings) / len(warnings)
        return not failed_errors and warning_rate >= 0.8


def as_level(value: Any) -> Any:
    if value in {"1", "2", "3"}:
        return int(value)
    return value


def target_ok(target: Any, page_ids: set[str], anchor_ids: set[str], allow_null: bool = False) -> bool:
    if target is None:
        return allow_null
    return isinstance(target, str) and (
        target in page_ids or target in anchor_ids or target in LEGAL_BEHAVIOR_TARGETS
    )


def target_label(target: Any) -> str:
    return "null" if target is None else str(target)


def page_name(page: dict[str, Any]) -> str:
    return str(page.get("id", "<missing-id>"))


def outgoing_targets(page: dict[str, Any]) -> list[Any]:
    targets: list[Any] = []
    primary = page.get("primary_action") or {}
    if isinstance(primary, dict) and primary.get("target") is not None:
        targets.append(primary.get("target"))
    for jump in page.get("jumps") or []:
        if isinstance(jump, dict):
            targets.append(jump.get("target"))
    return targets


def validate(proto: dict[str, Any], pages: list[dict[str, Any]]) -> Report:
    report = Report()
    scope = proto.get("scope", "whole_app")
    tab_bar_mode = proto.get("tab_bar_mode") or ("inherit" if scope == "whole_app" else "hidden")
    host_anchors = proto.get("host_anchors") or []
    anchor_ids = {a.get("id") for a in host_anchors if isinstance(a, dict) and a.get("id")}
    page_ids = {p.get("id") for p in pages if isinstance(p.get("id"), str)}
    scope_decision = proto.get("scope_decision")
    levels = {as_level(p.get("level")) for p in pages}

    report.add(
        "SCHEMA.scope",
        "ERROR",
        scope in {"whole_app", "feature_flow"},
        f"prototype.scope is {scope!r}",
    )
    report.add(
        "SCHEMA.scope_decision",
        "ERROR",
        isinstance(scope_decision, dict)
        and scope_decision.get("inferred_from") in {"user_text", "requirement_doc", "user_confirmation"}
        and scope_decision.get("confidence") in {"high", "medium", "low"}
        and bool(scope_decision.get("reason")),
        "prototype.scope_decision records inferred_from, confidence, and reason",
    )
    report.add(
        "SCHEMA.tab_bar_mode",
        "ERROR",
        tab_bar_mode in {"inherit", "hidden"},
        f"prototype.tab_bar_mode is {tab_bar_mode!r}",
    )
    if scope == "feature_flow":
        report.add(
            "SCHEMA.scope_feature_flow_anchors",
            "ERROR",
            bool(anchor_ids),
            "feature_flow declares at least one host_anchor",
        )
        report.add(
            "SCHEMA.scope_feature_flow_no_level1",
            "ERROR",
            1 not in levels,
            "feature_flow does not include level1 shell pages",
        )
    if scope == "whole_app":
        report.add(
            "SCHEMA.scope_whole_app_level1",
            "ERROR",
            1 in levels,
            "whole_app includes at least one level1 page",
        )
        report.add(
            "SCHEMA.scope_whole_app_no_host_anchors",
            "ERROR",
            not anchor_ids,
            "whole_app leaves host_anchors empty",
        )

    for page in pages:
        pid = page_name(page)
        ptype = page.get("type")
        level = as_level(page.get("level"))
        primary = page.get("primary_action")
        secondary = page.get("secondary_actions") or []
        nav = page.get("navigation") or {}
        progress = page.get("progress") or {}
        feedback = page.get("feedback") or {}
        density = page.get("density") or {}
        zones = density.get("zones") or []

        report.add(
            "R1.1",
            "ERROR",
            isinstance(primary, dict) and bool(primary.get("label")),
            f"{pid}: primary_action.label is present",
        )
        if ptype in {"home", "course_detail", "profile"}:
            status = primary.get("status") if isinstance(primary, dict) else None
            report.add("R1.2", "WARNING", bool(status), f"{pid}: primary_action.status is present")
        report.add(
            "R1.3",
            "ERROR",
            isinstance(secondary, list) and len(secondary) <= 4,
            f"{pid}: secondary_actions count <= 4",
        )
        placements_ok = isinstance(secondary, list) and all(
            (not isinstance(action, dict)) or action.get("placement", "action_bar") in PLACEMENTS
            for action in secondary
        )
        report.add("R1.4", "ERROR", placements_ok, f"{pid}: secondary placement values are valid")

        if scope == "whole_app" and ptype == "home":
            target = primary.get("target") if isinstance(primary, dict) else None
            target_page = next((p for p in pages if p.get("id") == target), None)
            ok = isinstance(target_page, dict) and target_page.get("type") == "learning"
            report.add("R2.1", "ERROR", ok, f"{pid}: home primary target points to learning")

        if level != 1:
            report.add(
                "R3.2",
                "ERROR",
                bool(nav.get("has_back")) and bool(nav.get("back_target")),
                f"{pid}: non-level1 page has back_target",
            )

        if ptype == "modal":
            jumps = page.get("jumps") or []
            close_jump = any(isinstance(j, dict) and j.get("reversible") is True for j in jumps)
            report.add(
                "R4.4",
                "ERROR",
                bool(nav.get("has_back")) or close_jump,
                f"{pid}: modal has a close path",
            )

        if nav.get("has_back"):
            report.add(
                "R4.5",
                "ERROR",
                target_ok(nav.get("back_target"), page_ids, anchor_ids),
                f"{pid}: back_target {target_label(nav.get('back_target'))} resolves",
            )

        if ptype in {"quiz", "learning"}:
            report.add("R5.1", "ERROR", feedback.get("type") == "immediate", f"{pid}: feedback is immediate")
        if ptype in {"quiz", "learning", "result"}:
            report.add("R5.2", "ERROR", bool(feedback.get("next_action")), f"{pid}: feedback.next_action is set")

        button_count = density.get("button_count")
        report.add(
            "R6.1",
            "ERROR",
            isinstance(button_count, int) and button_count <= 7,
            f"{pid}: density.button_count <= 7",
        )
        zones_len_ok = isinstance(zones, list) and len(zones) <= 4
        zones_kind_ok = isinstance(zones, list) and all(
            isinstance(z, dict) and z.get("kind") in ZONE_KINDS and z.get("id")
            for z in zones
        )
        report.add("R6.2a", "ERROR", zones_len_ok, f"{pid}: zones count <= 4")
        report.add("R6.2b", "ERROR", zones_kind_ok, f"{pid}: every zone has a valid id/kind")

        if ptype in {"home", "learning", "result", "profile"}:
            report.add("R7.1", "ERROR", progress.get("visible") is True, f"{pid}: progress.visible is true")
        if ptype in {"learning", "quiz", "result"}:
            elements = set(progress.get("elements") or [])
            report.add(
                "R7.2",
                "WARNING",
                bool(elements & {"chapter_locator", "overall"}),
                f"{pid}: progress has chapter_locator or overall",
            )
        if scope == "whole_app" and level == 1:
            report.add("R8.2", "ERROR", nav.get("tab_bar") is True, f"{pid}: level1 page has tab bar")

        if ptype not in PAGE_TYPES:
            report.add("SCHEMA.type", "ERROR", False, f"{pid}: page.type {ptype!r} is not supported")
        if level not in LEVELS:
            report.add("SCHEMA.level", "ERROR", False, f"{pid}: page.level {level!r} is not supported")
        if feedback.get("type") not in FEEDBACK_TYPES:
            report.add("SCHEMA.feedback", "ERROR", False, f"{pid}: feedback.type is invalid")
        progress_ok = all(e in PROGRESS_ELEMENTS for e in progress.get("elements") or [])
        report.add("SCHEMA.progress", "ERROR", progress_ok, f"{pid}: progress.elements are valid")

    report.add("R8.1", "ERROR", len(page_ids) == len(pages), "page ids are unique and present")

    for page in pages:
        pid = page_name(page)
        for jump in page.get("jumps") or []:
            if not isinstance(jump, dict):
                report.add("R4.1", "ERROR", False, f"{pid}: jump is an object")
                continue
            report.add("R4.1", "ERROR", jump.get("reversible") is True, f"{pid}: jump is reversible")
            report.add(
                "R4.2",
                "ERROR",
                target_ok(jump.get("target"), page_ids, anchor_ids),
                f"{pid}: jump target {target_label(jump.get('target'))} resolves",
            )
        primary = page.get("primary_action") or {}
        if isinstance(primary, dict):
            report.add(
                "SCHEMA.primary_target",
                "ERROR",
                target_ok(primary.get("target"), page_ids, anchor_ids, allow_null=True),
                f"{pid}: primary target {target_label(primary.get('target'))} resolves or is null",
            )

    for page in pages:
        pid = page_name(page)
        ptype = page.get("type")
        has_out = bool(outgoing_targets(page))
        if ptype not in {"modal"}:
            report.add("R4.3", "ERROR", has_out, f"{pid}: page has an outgoing path")

    if scope == "whole_app":
        home_ids = [p.get("id") for p in pages if p.get("type") == "home"]
        learning_ids = {p.get("id") for p in pages if p.get("type") == "learning"}
        report.add("R2.2", "ERROR", any(shortest_path(pages, h, learning_ids) <= 2 for h in home_ids), "home reaches learning in <= 2 steps")

    if tab_bar_mode == "inherit":
        tab_targets = {
            j.get("target")
            for p in pages
            if (p.get("navigation") or {}).get("tab_bar") is True
            for j in (p.get("jumps") or [])
            if isinstance(j, dict) and str(j.get("from", "")).startswith("tab")
        }
        tab_targets.update(p.get("id") for p in pages if as_level(p.get("level")) == 1 and (p.get("navigation") or {}).get("tab_bar"))
        report.add("R3.1", "ERROR", 3 <= len(tab_targets) <= 5, f"tab count is {len(tab_targets)}")

    referenced = {t for p in pages for t in outgoing_targets(p) if isinstance(t, str)}
    for page in pages:
        pid = page_name(page)
        if page.get("type") == "home":
            continue
        report.add("R8.3", "WARNING", pid in referenced, f"{pid}: page is referenced by another page")

    return report


def shortest_path(pages: list[dict[str, Any]], start: Any, goals: set[Any]) -> int:
    if start in goals:
        return 0
    edges: dict[Any, set[Any]] = {}
    page_ids = {p.get("id") for p in pages}
    for page in pages:
        edges[page.get("id")] = {t for t in outgoing_targets(page) if t in page_ids}
    seen = {start}
    queue: list[tuple[Any, int]] = [(start, 0)]
    while queue:
        node, dist = queue.pop(0)
        for nxt in edges.get(node, set()):
            if nxt in goals:
                return dist + 1
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, dist + 1))
    return 10**9


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an EPPS prototype spec.")
    parser.add_argument("spec", type=Path, help="Path to epps.json, epps.yaml, or prototype.md")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON report")
    args = parser.parse_args()

    proto, pages = normalize(load_doc(args.spec))
    report = validate(proto, pages)
    if args.json:
        print(json.dumps({"ok": report.ok(), "items": report.items}, ensure_ascii=False, indent=2))
    else:
        report.print()
    return 0 if report.ok() else 1


if __name__ == "__main__":
    raise SystemExit(main())
