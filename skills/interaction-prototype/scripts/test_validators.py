#!/usr/bin/env python3
"""Self-test for the interaction-prototype validators.

Run: python3 skills/interaction-prototype/scripts/test_validators.py

Asserts the validators PASS on known-good inputs and FAIL with the expected
codes on adversarial inputs. Guards the two scripts that are the skill's hard
quality gate against regressions (a quiet rewrite that turns a real check back
into dead code).
"""

from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_html_projection as audit_mod  # noqa: E402
import validate_epps  # noqa: E402


def ec(intent: str, surface: str, priority: str = "low", persistence: str = "contextual", blocking: bool = False) -> dict:
    return {
        "intent": intent,
        "surface": surface,
        "priority": priority,
        "persistence": persistence,
        "blocking": blocking,
    }


def make_spec() -> tuple[dict, list[dict]]:
    proto = {
        "scope_decision": {"inferred_from": "user_confirmation", "confidence": "high", "reason": "fixture"},
        "project_references": {"mode": "none", "confirmed_by_user": True, "question": "参考现有文件?", "items": []},
        "scope": "feature_flow",
        "tab_bar_mode": "hidden",
        "host_anchors": [
            {"id": "host_in", "direction": "entry", "label": "入口"},
            {"id": "host_out", "direction": "exit", "label": "出口"},
        ],
        "sample_state": {"grade": "五年级", "chapter": "第3章"},
    }
    pages = [
        {
            "id": "p_entry",
            "level": 2,
            "type": "course_detail",
            "primary_action": {
                "label": "开始学习",
                "target": "p_learn",
                "status": "第3章 · 30%",
                "element_contract": ec("primary_action", "action_bar", "primary"),
            },
            "secondary_actions": [],
            "navigation": {"has_back": True, "back_target": "host_in", "tab_bar": False},
            "progress": {"visible": True, "elements": ["chapter_locator"]},
            "feedback": {"type": "none", "next_action": "进入学习"},
            "density": {
                "button_count": 2,
                "zones": [{"id": "hero", "kind": "hero_card", "label": "继续", "element_contract": ec("learn_content", "main_content", "primary")}],
            },
            "assistive_elements": [],
            "jumps": [{"trigger": "tap", "from": "hero", "target": "p_learn", "reversible": True}],
        },
        {
            "id": "p_learn",
            "level": 3,
            "type": "learning",
            "primary_action": {
                "label": "完成",
                "target": "next_question",
                "status": None,
                "element_contract": ec("primary_action", "action_bar", "primary"),
            },
            "secondary_actions": [
                {"label": "发音", "target": None, "behavior": "play_audio", "icon": "volume", "placement": "inline", "element_contract": ec("secondary_action", "inline", "secondary")}
            ],
            "navigation": {"has_back": True, "back_target": "p_entry", "tab_bar": False},
            "progress": {"visible": True, "elements": ["chapter_locator", "overall"]},
            "feedback": {"type": "immediate", "next_action": "下一题"},
            "density": {
                "button_count": 4,
                "zones": [{"id": "word", "kind": "word_card", "label": "词", "element_contract": ec("learn_content", "main_content", "primary")}],
            },
            "assistive_elements": [
                {"id": "g", "kind": "hint_block", "label": "引导", "trigger": "first_enter", "target": None, "element_contract": ec("guidance", "coachmark", "low", "first_time_only")}
            ],
            "jumps": [],
        },
    ]
    return proto, pages


GOOD_HTML = """
<section class="screen active" id="p_entry" data-level="2" data-type="course_detail" data-tabbar="false">
  <div class="topbar"><button class="back" data-host="host_in">‹</button><span>五年级</span></div>
  <div class="content"><div class="zone" data-zone-id="hero" data-zone-kind="hero_card">继续学习</div></div>
  <div class="action-bar"><button class="btn-primary" data-target="p_learn">开始</button></div>
</section>
<section class="screen" id="p_learn" data-level="3" data-type="learning" data-tabbar="false">
  <div class="topbar"><button class="back" data-target="p_entry">‹</button></div>
  <div class="content">
    <div class="zone" data-zone-id="word" data-zone-kind="word_card"><button data-behavior="play_audio">发音</button></div>
    <div class="coachmark" data-assistive-id="g" data-assistive-kind="hint_block">引导</div>
  </div>
  <div class="action-bar"><button class="btn-primary" data-behavior="next_question">完成</button></div>
</section>
"""


def feed(html: str) -> audit_mod.PrototypeHTMLParser:
    parser = audit_mod.PrototypeHTMLParser()
    parser.feed(html)
    return parser


def run_audit(proto, pages, html):
    return audit_mod.audit(proto, pages, feed(html))


def failing_codes(audit) -> set[str]:
    return {i["code"] for i in audit.items if i["status"] == "FAIL"}


class Checker:
    def __init__(self) -> None:
        self.n = 0
        self.failed: list[str] = []

    def check(self, name: str, cond: bool, detail: str = "") -> None:
        self.n += 1
        if cond:
            print(f"  PASS  {name}")
        else:
            self.failed.append(name)
            print(f"  FAIL  {name}  {detail}")

    def ok(self) -> bool:
        return not self.failed


def main() -> int:
    c = Checker()
    proto, pages = make_spec()

    print("[validate_epps] known-good spec -> PASS")
    report = validate_epps.validate(proto, copy.deepcopy(pages))
    if not report.ok():
        fails = [i for i in report.items if i["status"] == "FAIL"]
        c.check("validate good spec ok", False, str(fails[:3]))
    else:
        c.check("validate good spec ok", True)

    print("[validate_epps] dangling primary target -> FAIL")
    bad = copy.deepcopy(pages)
    bad[0]["primary_action"]["target"] = "ghost_page"
    report = validate_epps.validate(proto, bad)
    codes = {i["rule"] for i in report.items if i["status"] == "FAIL"}
    c.check("validate dangling target fails", not report.ok(), f"rules={codes}")
    c.check("  flags primary_target", "SCHEMA.primary_target" in codes, f"rules={codes}")

    print("[audit] known-good HTML -> PASS")
    a = run_audit(proto, pages, GOOD_HTML)
    c.check("audit good html ok", a.ok(), str([i for i in a.items if i["status"] == "FAIL"][:3]))

    print("[audit] grade drift (四年级 vs 五年级) -> FAIL")
    a = run_audit(proto, pages, GOOD_HTML.replace("五年级", "四年级"))
    c.check("grade drift detected", not a.ok())
    c.check("  SAMPLE_STATE.grade_drift flagged", "SAMPLE_STATE.grade_drift" in failing_codes(a), str(failing_codes(a)))

    print("[audit] double play_audio render -> FAIL")
    doubled = GOOD_HTML.replace(
        '<button data-behavior="play_audio">发音</button>',
        '<button data-behavior="play_audio">发音</button><button data-behavior="play_audio">发音2</button>',
    )
    a = run_audit(proto, pages, doubled)
    c.check("double behavior detected", not a.ok())
    c.check("  BEHAVIOR.single_point flagged", "BEHAVIOR.single_point" in failing_codes(a), str(failing_codes(a)))

    print("[audit] primary affordance missing from HTML -> FAIL")
    missing_primary = GOOD_HTML.replace(
        '<button class="btn-primary" data-behavior="next_question">完成</button>',
        '<button class="btn-primary">完成</button>',
    )
    a = run_audit(proto, pages, missing_primary)
    c.check("missing primary render detected", not a.ok())
    c.check("  ACTION.rendered flagged", "ACTION.rendered" in failing_codes(a), str(failing_codes(a)))

    print("[audit] unresolved {{sample_state.*}} placeholder -> FAIL")
    placeholder = GOOD_HTML.replace(
        '<div class="zone" data-zone-id="hero" data-zone-kind="hero_card">继续学习</div>',
        '<div class="zone" data-zone-id="hero" data-zone-kind="hero_card">{{sample_state.grade}} 继续学习</div>',
    )
    a = run_audit(proto, pages, placeholder)
    c.check("placeholder detected", not a.ok())
    c.check("  SAMPLE_STATE.placeholder flagged", "SAMPLE_STATE.placeholder" in failing_codes(a), str(failing_codes(a)))

    print("[audit] chapter drift (第5章 vs 第3章) -> FAIL")
    a = run_audit(proto, pages, GOOD_HTML.replace("五年级", "五年级 第5章"))
    c.check("chapter drift detected", not a.ok())
    c.check("  SAMPLE_STATE.chapter_drift flagged", "SAMPLE_STATE.chapter_drift" in failing_codes(a), str(failing_codes(a)))

    print()
    if c.ok():
        print(f"ALL {c.n} CHECKS PASSED")
        return 0
    print(f"{len(c.failed)} CHECK(S) FAILED: {c.failed}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
