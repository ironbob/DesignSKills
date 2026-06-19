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
import extract_requirements  # noqa: E402
import validate_epps  # noqa: E402
import validate_page_plan  # noqa: E402


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


COVERAGE_MD = """\
### 模块：练习
| 优先级 | 功能 | 简述 | 验收标准 |
|--------|------|------|----------|
| P0 | 语境填空 | 挖空选词 | 每题 1 空 |
| P0 | 词义选择 | 四选一 | 4 选 1 |
| P0 | 拼写听写 | 输入判对错 | 接受文本输入 |
| P0 | 即时反馈 | 提交即判 | 立即判对错 |
| P0 | 题型混合 | 混合出题 | 同一单元至少出现 2 种题型 |
"""

EMPTY_MD = "## 没有模块也没有表格\n\n只有正文段落，解析应得到 0 条需求。"


def pp_page(pid: str, kind: str = "standalone", delivers: list[str] | None = None,
            variant_of: str | None = None, rationale: str = "r") -> dict:
    entry = {"page_id": pid, "kind": kind, "delivers": delivers or [], "rationale": rationale}
    if kind == "variant":
        entry["variant_of"] = variant_of if variant_of is not None else "g"
    return entry


def pp_report(pages, md, page_plan, html=None):
    reqs = extract_requirements.extract_requirements(md)
    return validate_page_plan.validate_page_plan(pages, reqs, page_plan, html)


def pp_failing(report) -> set[str]:
    return {i["rule"] for i in report.items if i["status"] == "FAIL"}


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

    print("[page_plan] valid plan (siblings on >=2 distinct pages) -> PASS")
    pages_pp = [{"id": "p1"}, {"id": "p2"}]
    plan = {"pages": [pp_page("p1", "standalone", ["REQ-M01-01", "REQ-M01-02"]),
                      pp_page("p2", "standalone", ["REQ-M01-03", "REQ-M01-04"])],
            "cross_cutting": []}
    r = pp_report(pages_pp, COVERAGE_MD, plan)
    c.check("page_plan valid ok", r.ok(), str(pp_failing(r)))
    c.check("  no PLAN.coverage fail", "PLAN.coverage" not in pp_failing(r), str(pp_failing(r)))

    print("[page_plan] missing page_plan block -> FAIL")
    r = pp_report([{"id": "p1"}], COVERAGE_MD, None)
    c.check("missing plan fails", not r.ok())
    c.check("  PLAN.present flagged", "PLAN.present" in pp_failing(r), str(pp_failing(r)))

    print("[page_plan] collapsed variants (all on 1 page) -> aggregate FAIL")
    plan_coll = {"pages": [pp_page("p1", "variant", ["REQ-M01-01", "REQ-M01-02", "REQ-M01-03", "REQ-M01-04"], "quiz")],
                 "cross_cutting": []}
    r = pp_report([{"id": "p1"}], COVERAGE_MD, plan_coll)
    c.check("collapse fails", not r.ok(), str(pp_failing(r)))
    c.check("  aggregate REQ-M01-05 fails", any("REQ-M01-05" in i["message"] and i["status"] == "FAIL" for i in r.items), str(pp_failing(r)))

    print("[page_plan] cross_cutting excludes a P0 from coverage -> not flagged")
    plan_cc = {"pages": [pp_page("p1", "standalone", ["REQ-M01-01", "REQ-M01-02"]),
                         pp_page("p2", "standalone", ["REQ-M01-03"])],
               "cross_cutting": [{"req_id": "REQ-M01-04", "covered_by": "p1", "covered_by_kind": "engine", "rationale": "behavior"}]}
    r = pp_report([{"id": "p1"}, {"id": "p2"}], COVERAGE_MD, plan_cc)
    c.check("cross_cutting P0 excluded ok", r.ok(), str(pp_failing(r)))

    print("[page_plan] aggregate req placed in cross_cutting -> aggregate_guard FAIL")
    plan_badcc = {"pages": [pp_page("p1", "standalone", ["REQ-M01-01", "REQ-M01-02"]),
                            pp_page("p2", "standalone", ["REQ-M01-03", "REQ-M01-04"])],
                  "cross_cutting": [{"req_id": "REQ-M01-05", "covered_by": "p1", "covered_by_kind": "engine", "rationale": "x"}]}
    r = pp_report([{"id": "p1"}, {"id": "p2"}], COVERAGE_MD, plan_badcc)
    c.check("aggregate in cross_cutting fails", not r.ok())
    c.check("  PLAN.cross_cutting.aggregate_guard flagged", "PLAN.cross_cutting.aggregate_guard" in pp_failing(r), str(pp_failing(r)))

    print("[page_plan] dangling delivers id -> FAIL")
    plan_dang = {"pages": [pp_page("p1", "standalone", ["REQ-M01-01", "REQ-XX-99"]),
                           pp_page("p2", "standalone", ["REQ-M01-02", "REQ-M01-03"])],
                 "cross_cutting": []}
    r = pp_report([{"id": "p1"}, {"id": "p2"}], COVERAGE_MD, plan_dang)
    c.check("dangling delivers fails", not r.ok())
    c.check("  PLAN.dangling.delivers flagged", "PLAN.dangling.delivers" in pp_failing(r), str(pp_failing(r)))

    print("[page_plan] variant missing variant_of -> FAIL")
    plan_novof = {"pages": [{"page_id": "p1", "kind": "variant", "delivers": ["REQ-M01-01"], "rationale": "r"},
                            pp_page("p2", "standalone", ["REQ-M01-02", "REQ-M01-03", "REQ-M01-04"])],
                  "cross_cutting": []}
    r = pp_report([{"id": "p1"}, {"id": "p2"}], COVERAGE_MD, plan_novof)
    c.check("variant missing variant_of fails", not r.ok())
    c.check("  PLAN.structure.variant flagged", "PLAN.structure.variant" in pp_failing(r), str(pp_failing(r)))

    print("[page_plan] planned page not rendered (no zone) -> flat_render FAIL")
    plan_fr = {"pages": [pp_page("p1", "standalone", ["REQ-M01-01", "REQ-M01-02"]),
                         pp_page("p2", "standalone", ["REQ-M01-03", "REQ-M01-04"])],
               "cross_cutting": []}
    no_zone_html = feed('<section class="screen" id="p1" data-level="3" data-type="misc"><div class="topbar">x</div></section>'
                        '<section class="screen" id="p2" data-level="3" data-type="misc"><div class="zone" data-zone-id="z" data-zone-kind="text_block">y</div></section>')
    r = pp_report([{"id": "p1"}, {"id": "p2"}], COVERAGE_MD, plan_fr, html=no_zone_html)
    c.check("unrendered plan page fails", not r.ok())
    c.check("  PLAN.flat_render flagged", "PLAN.flat_render" in pp_failing(r), str(pp_failing(r)))

    print("[page_plan] empty requirements source -> source guard FAIL")
    r = pp_report([{"id": "p1"}], EMPTY_MD, plan)
    c.check("empty source fails", not r.ok())
    c.check("  PLAN.source_present flagged", "PLAN.source_present" in pp_failing(r), str(pp_failing(r)))

    print()
    if c.ok():
        print(f"ALL {c.n} CHECKS PASSED")
        return 0
    print(f"{len(c.failed)} CHECK(S) FAILED: {c.failed}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
