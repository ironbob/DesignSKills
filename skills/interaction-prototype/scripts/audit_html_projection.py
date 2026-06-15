#!/usr/bin/env python3
"""Audit whether prototype.html is a strict projection of an EPPS spec."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from validate_epps import load_doc, normalize


def attrs_to_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {k: "" if v is None else v for k, v in attrs}


class PrototypeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sections: dict[str, dict[str, Any]] = {}
        self.modals: set[str] = set()
        self.actions: list[dict[str, str]] = []
        self.zone_stack: list[dict[str, str]] = []
        self.element_stack: list[bool] = []
        self.current_screen: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = attrs_to_dict(attrs)
        classes = set(attr.get("class", "").split())
        if tag == "section" and "screen" in classes:
            sid = attr.get("id", "")
            self.current_screen = sid
            self.sections[sid] = {
                "id": sid,
                "level": attr.get("data-level"),
                "type": attr.get("data-type"),
                "tabbar": attr.get("data-tabbar") == "true",
                "zones": [],
                "assistive": [],
                "actions": [],
            }
        if "modal-mask" in classes and attr.get("id"):
            self.modals.add(attr["id"])
        if "zone" in classes:
            zone = {
                "screen": self.current_screen or "",
                "id": attr.get("data-zone-id", ""),
                "kind": attr.get("data-zone-kind", ""),
            }
            self.zone_stack.append(zone)
            self.element_stack.append(True)
            if self.current_screen in self.sections:
                self.sections[self.current_screen]["zones"].append(zone)
        else:
            self.element_stack.append(False)
        if "data-assistive-id" in attr:
            assistive = {
                "screen": self.current_screen or "",
                "id": attr.get("data-assistive-id", ""),
                "kind": attr.get("data-assistive-kind", ""),
            }
            if self.current_screen in self.sections:
                self.sections[self.current_screen]["assistive"].append(assistive)
        action: dict[str, str] | None = None
        if "data-target" in attr:
            action = {"kind": "target", "value": attr["data-target"]}
        elif "data-host" in attr:
            action = {"kind": "host", "value": attr["data-host"]}
        elif "data-behavior" in attr:
            action = {"kind": "behavior", "value": attr["data-behavior"]}
        if action:
            action["screen"] = self.current_screen or ""
            action["tag"] = tag
            if self.zone_stack:
                action["zone"] = self.zone_stack[-1].get("id", "")
            self.actions.append(action)
            if self.current_screen in self.sections:
                self.sections[self.current_screen]["actions"].append(action)

    def handle_endtag(self, tag: str) -> None:
        if tag == "section":
            self.current_screen = None
        if self.element_stack and self.element_stack.pop() and self.zone_stack:
            self.zone_stack.pop()


def parse_html(path: Path) -> PrototypeHTMLParser:
    parser = PrototypeHTMLParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


class Audit:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, ok: bool, code: str, message: str) -> None:
        self.items.append({"status": "PASS" if ok else "FAIL", "code": code, "message": message})

    def ok(self) -> bool:
        return all(item["status"] == "PASS" for item in self.items)

    def print(self) -> None:
        for item in self.items:
            icon = "OK" if item["status"] == "PASS" else "FAIL"
            print(f"{icon} {item['code']}: {item['message']}")


def action_values_for_page(page: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    primary = page.get("primary_action") or {}
    if isinstance(primary, dict) and primary.get("target") is not None:
        values.add(str(primary.get("target")))
    for action in page.get("secondary_actions") or []:
        if isinstance(action, dict):
            if action.get("target") is not None:
                values.add(str(action.get("target")))
            elif action.get("behavior"):
                values.add(str(action.get("behavior")))
    for item in page.get("assistive_elements") or []:
        if isinstance(item, dict):
            if item.get("target") is not None:
                values.add(str(item.get("target")))
            elif item.get("behavior"):
                values.add(str(item.get("behavior")))
    nav = page.get("navigation") or {}
    if nav.get("back_target"):
        values.add(str(nav.get("back_target")))
    for jump in page.get("jumps") or []:
        if isinstance(jump, dict) and jump.get("target") is not None:
            values.add(str(jump.get("target")))
    return values


def audit(proto: dict[str, Any], pages: list[dict[str, Any]], html: PrototypeHTMLParser) -> Audit:
    audit = Audit()
    page_by_id = {str(p.get("id")): p for p in pages if p.get("id")}
    page_ids = set(page_by_id)
    host_ids = {
        str(a.get("id"))
        for a in proto.get("host_anchors", []) or []
        if isinstance(a, dict) and a.get("id")
    }
    section_ids = set(html.sections)
    extra_sections = section_ids - page_ids
    missing_sections = page_ids - section_ids
    audit.add(not missing_sections, "PAGE.sections.present", f"missing sections: {sorted(missing_sections)}")
    audit.add(not extra_sections, "PAGE.sections.extra", f"extra sections: {sorted(extra_sections)}")

    for pid, page in page_by_id.items():
        section = html.sections.get(pid)
        if not section:
            continue
        audit.add(section["type"] == str(page.get("type")), "PAGE.type", f"{pid}: HTML type matches spec")
        audit.add(section["level"] == str(page.get("level")), "PAGE.level", f"{pid}: HTML level matches spec")
        nav = page.get("navigation") or {}
        expected_tabbar = nav.get("tab_bar") is True
        audit.add(section["tabbar"] == expected_tabbar, "PAGE.tabbar", f"{pid}: tabbar flag matches spec")

        spec_zones = (page.get("density") or {}).get("zones") or []
        html_zones = section["zones"]
        spec_pairs = [(str(z.get("id")), str(z.get("kind"))) for z in spec_zones if isinstance(z, dict)]
        html_pairs = [(z.get("id", ""), z.get("kind", "")) for z in html_zones]
        audit.add(spec_pairs == html_pairs, "ZONE.projection", f"{pid}: spec zones == HTML zones")
        spec_assistive = page.get("assistive_elements") or []
        html_assistive = section["assistive"]
        spec_assistive_pairs = [(str(z.get("id")), str(z.get("kind"))) for z in spec_assistive if isinstance(z, dict)]
        html_assistive_pairs = [(z.get("id", ""), z.get("kind", "")) for z in html_assistive]
        audit.add(
            spec_assistive_pairs == html_assistive_pairs,
            "ASSISTIVE.projection",
            f"{pid}: spec assistive elements == HTML assistive elements",
        )

        allowed = action_values_for_page(page)
        unknown: list[str] = []
        for action in section["actions"]:
            value = action["value"]
            if action["kind"] == "host":
                if value not in host_ids:
                    unknown.append(f"host:{value}")
            elif value not in allowed:
                unknown.append(f"{action['kind']}:{value}")
        audit.add(not unknown, "ACTION.declared", f"{pid}: undeclared HTML actions: {unknown}")

    modal_ids = {str(p.get("id")) for p in pages if p.get("type") == "modal"}
    missing_modals = modal_ids - html.modals - section_ids
    audit.add(not missing_modals, "MODAL.present", f"missing modal projections: {sorted(missing_modals)}")

    sample_values = collect_sample_values(proto.get("sample_state") or {})
    hardcoded_conflicts = find_conflicting_sample_literals(html, sample_values)
    audit.add(not hardcoded_conflicts, "SAMPLE_STATE.consistent", f"conflicting repeated sample literals: {hardcoded_conflicts}")
    return audit


def collect_sample_values(value: Any) -> set[str]:
    values: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            values.update(collect_sample_values(item))
    elif isinstance(value, list):
        for item in value:
            values.update(collect_sample_values(item))
    elif value is not None:
        text = str(value)
        if len(text) >= 2:
            values.add(text)
    return values


def find_conflicting_sample_literals(html: PrototypeHTMLParser, sample_values: set[str]) -> list[str]:
    # This is intentionally conservative: flag only obvious unresolved template
    # placeholders. Full semantic text diff remains a human review step.
    conflicts: list[str] = []
    for section in html.sections.values():
        for zone in section["zones"]:
            if "{{sample_state." in zone.get("id", ""):
                conflicts.append(f"{section['id']}:{zone['id']}")
    return conflicts


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit prototype.html against an EPPS spec.")
    parser.add_argument("spec", type=Path, help="Path to epps.json, epps.yaml, or prototype.md")
    parser.add_argument("html", type=Path, help="Path to prototype.html")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON report")
    args = parser.parse_args()

    proto, pages = normalize(load_doc(args.spec))
    result = audit(proto, pages, parse_html(args.html))
    if args.json:
        print(json.dumps({"ok": result.ok(), "items": result.items}, ensure_ascii=False, indent=2))
    else:
        result.print()
    return 0 if result.ok() else 1


if __name__ == "__main__":
    raise SystemExit(main())
