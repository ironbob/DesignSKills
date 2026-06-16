#!/usr/bin/env python3
"""Audit whether prototype.html is a strict projection of an EPPS spec."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from validate_epps import LEGAL_BEHAVIOR_TARGETS, load_doc, normalize


def attrs_to_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {k: "" if v is None else v for k, v in attrs}


class PrototypeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sections: dict[str, dict[str, Any]] = {}
        self.screen_texts: dict[str, list[str]] = {}
        self.modals: set[str] = set()
        self.actions: list[dict[str, str]] = []
        self.zone_stack: list[dict[str, str]] = []
        self.element_stack: list[bool] = []
        self.current_screen: str | None = None
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = attrs_to_dict(attrs)
        if tag in ("script", "style"):
            self.skip_depth += 1
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
            self.screen_texts.setdefault(sid, [])
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

    def handle_data(self, data: str) -> None:
        if self.skip_depth or self.current_screen is None:
            return
        text = data.strip()
        if text:
            self.screen_texts.setdefault(self.current_screen, []).append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self.skip_depth:
            self.skip_depth -= 1
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

        # Reverse direction: every spec-promised affordance must actually be
        # rendered on this screen (catches a primary/back/secondary declared in
        # spec but invisible in HTML — ACTION.declared only checks HTML -> spec).
        rendered_nav = {a["value"] for a in section["actions"] if a["kind"] in ("target", "host")}
        rendered_behavior_counts: Counter[str] = Counter(
            a["value"] for a in section["actions"] if a["kind"] == "behavior"
        )
        required = required_affordances(page)
        missing: list[str] = []
        for kind, value in required:
            if kind == "nav":
                if value not in rendered_nav:
                    missing.append(f"nav:{value}")
            elif rendered_behavior_counts.get(value, 0) == 0:
                missing.append(f"behavior:{value}")
        audit.add(not missing, "ACTION.rendered", f"{pid}: spec affordances missing from HTML: {missing}")

        # Affordance single-point: a declared behaviour must render at most once
        # per screen (catches e.g. a play_audio button drawn both in the card and
        # in the action bar). ACTION.declared passes both copies; this flags the
        # duplicate.
        declared_behavior_counts: Counter[str] = Counter(v for k, v in required if k == "behavior")
        over_rendered = {
            b: rendered_behavior_counts[b]
            for b, count in declared_behavior_counts.items()
            if rendered_behavior_counts.get(b, 0) > count
        }
        audit.add(
            not over_rendered,
            "BEHAVIOR.single_point",
            f"{pid}: behavior rendered more times than declared (affordance not single-point): {over_rendered}",
        )

    modal_ids = {str(p.get("id")) for p in pages if p.get("type") == "modal"}
    missing_modals = modal_ids - html.modals - section_ids
    audit.add(not missing_modals, "MODAL.present", f"missing modal projections: {sorted(missing_modals)}")

    drift = find_sample_state_drift(html, proto.get("sample_state") or {})
    if drift:
        for code, message in drift:
            audit.add(False, code, message)
    else:
        audit.add(
            True,
            "SAMPLE_STATE.consistent",
            "no sample-state drift detected (placeholder/grade/chapter)",
        )
    return audit


GRADE_RE = re.compile(r"([一二三四五六七八九十百零两\d]{1,3})\s*年级")
CHAPTER_RE = re.compile(r"第\s*([0-9一二三四五六七八九十]+)\s*章")
PLACEHOLDER_RE = re.compile(r"\{\{sample_state\.[^}]+\}\}")


def find_sample_state_drift(html: PrototypeHTMLParser, sample_state: dict[str, Any]) -> list[tuple[str, str]]:
    """Detect sample-state drift that strict projection cannot catch.

    Implements the cases the skill advertises as mechanically checked:
      * an unresolved ``{{sample_state.*}}`` token surviving into the final HTML,
      * a grade literal (e.g. ``四年级``) that contradicts ``sample_state.grade``,
      * a chapter literal (``第N章``) that contradicts ``sample_state.chapter``.
    Broader free-text diff (any other value) stays a human-review step — these
    three shapes are tight enough to flag without false positives.
    """
    findings: list[tuple[str, str]] = []
    texts = {sid: " ".join(parts) for sid, parts in html.screen_texts.items()}
    joined = "\n".join(texts.values())

    placeholders = PLACEHOLDER_RE.findall(joined)
    if placeholders:
        findings.append((
            "SAMPLE_STATE.placeholder",
            f"unresolved {{{{sample_state.*}}}} tokens rendered in HTML: {placeholders}",
        ))

    grade = sample_state.get("grade")
    if isinstance(grade, str):
        match = GRADE_RE.search(grade)
        if match:
            canonical = match.group(0)
            drifted = [
                f"{sid}: {num}年级"
                for sid, text in texts.items()
                for num in GRADE_RE.findall(text)
                if f"{num}年级" != canonical
            ]
            if drifted:
                findings.append((
                    "SAMPLE_STATE.grade_drift",
                    f"grade literal contradicts sample_state.grade={grade!r}: {drifted}",
                ))

    chapter = sample_state.get("chapter")
    if isinstance(chapter, str):
        match = CHAPTER_RE.search(chapter)
        if match:
            canonical_num = match.group(1)
            drifted = [
                f"{sid}: 第{num}章"
                for sid, text in texts.items()
                for num in CHAPTER_RE.findall(text)
                if num != canonical_num
            ]
            if drifted:
                findings.append((
                    "SAMPLE_STATE.chapter_drift",
                    f"chapter literal contradicts sample_state.chapter={chapter!r}: {drifted}",
                ))

    return findings


def required_affordances(page: dict[str, Any]) -> list[tuple[str, str]]:
    """Affordances a page's spec promises to render on its own screen.

    Covers primary action, back target (non-modals only — a modal closes to
    reveal its parent rather than rendering a data-target), and secondary /
    assistive targets. Returns ``(kind, value)`` where kind is ``nav`` (needs a
    ``data-target``/``data-host``) or ``behavior`` (needs a ``data-behavior``).

    Jump targets are intentionally excluded: a jump is often realised indirectly
    by a behaviour (e.g. ``next_question`` advancing the flow) rather than a
    direct ``data-target``, so requiring one would false-positive.
    """
    required: list[tuple[str, str]] = []
    primary = page.get("primary_action") or {}
    primary_target = primary.get("target") if isinstance(primary, dict) else None
    if primary_target in LEGAL_BEHAVIOR_TARGETS:
        required.append(("behavior", str(primary_target)))
    elif primary_target is not None:
        required.append(("nav", str(primary_target)))

    nav = page.get("navigation") or {}
    if page.get("type") != "modal" and nav.get("back_target"):
        required.append(("nav", str(nav.get("back_target"))))

    for group in ("secondary_actions", "assistive_elements"):
        for item in page.get(group) or []:
            if not isinstance(item, dict):
                continue
            behavior = item.get("behavior")
            target = item.get("target")
            if behavior:
                required.append(("behavior", str(behavior)))
            elif target in LEGAL_BEHAVIOR_TARGETS:
                required.append(("behavior", str(target)))
            elif target is not None:
                required.append(("nav", str(target)))
    return required


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
