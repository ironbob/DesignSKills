#!/usr/bin/env python3
"""Validate the requirement→page plan — the third external gate for interaction-prototype.

The other two gates check *quality* (``validate_epps.py`` 22 rules; ``audit_html_projection.py``
HTML↔spec fidelity). This gate checks *completeness AND granularity*: that every
P0/P1 requirement is delivered by the right number of pages, derived from an
explicit ``page_plan`` the model authors.

Why a page_plan (and not the old per-page ``satisfies``): requirements describe
capabilities, not pages. The capability→page mapping is many-to-many — some
capabilities cluster onto one page (学新: example+audio+ordering co-present),
some split into separate pages (题目练习: fill/select/spell are distinct
interaction modes), and some are not pages at all (SM-2 scheduling, persistence).
The model makes that judgment explicitly in ``page_plan``; this gate verifies it.

The aggregate requirement backstops variant-collapse deterministically: a "≥N
种" requirement (e.g. ≥2 question types) is satisfied only when ≥N siblings are
delivered across ≥N *distinct* pages — so collapsing 3 types into one cycling
page yields 1 distinct page < 2 and fails hard.

Granularity heuristics are ADVISORY (they never affect the exit code; they feed
the LLM judge). Only coverage (P0 ERROR / P1 WARNING), structure, parity,
flat-render, dangling, and the aggregate guard are blocking. Codes use the
``PLAN.*`` namespace — an external gate alongside ``SCHEMA.*``, NOT a 23rd rule.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_html_projection import parse_html  # noqa: E402
from extract_requirements import extract_requirements  # noqa: E402
from validate_epps import Report, load_doc, normalize  # noqa: E402

TRACKED_PRIORITIES = {"P0", "P1"}
VALID_KINDS = {"standalone", "variant"}
VALID_COVERED_BY_KIND = {"page", "engine"}


def validate_page_plan(
    pages: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    page_plan: dict[str, Any] | None,
    html: Any = None,
) -> Report:
    """Check the page_plan against extracted requirements and the EPPS pages.

    ``html`` (a ``PrototypeHTMLParser``) enables ``PLAN.flat_render``; without it
    every spec page is assumed rendered (degraded mode).
    """
    report = Report()

    has_plan = isinstance(page_plan, dict)
    report.add(
        "PLAN.present",
        "ERROR",
        has_plan,
        "spec 含 page_plan 块" if has_plan else "spec 缺 page_plan 块——无法判定需求→页面映射",
    )

    report.add(
        "PLAN.source_present",
        "ERROR",
        len(requirements) > 0,
        f"从需求文档抽取到 {len(requirements)} 条需求"
        if requirements
        else "未抽取出任何需求（无 `### 模块：` 标题或无可解析表格）",
    )

    page_ids = {str(p.get("id")) for p in pages if p.get("id")}
    plan_pages = (page_plan or {}).get("pages") if isinstance(page_plan, dict) else None
    cross_cutting = (page_plan or {}).get("cross_cutting") if isinstance(page_plan, dict) else None
    plan_pages = plan_pages if isinstance(plan_pages, list) else []
    cross_cutting = cross_cutting if isinstance(cross_cutting, list) else []

    delivered: dict[str, list[str]] = {}  # req_id -> [page_ids]
    plan_page_ids: list[str] = []

    for entry in plan_pages:
        if not isinstance(entry, dict):
            report.add("PLAN.structure.page", "ERROR", False, f"page_plan.pages 项非对象: {entry!r}")
            continue
        pid = str(entry.get("page_id") or "")
        kind = entry.get("kind")
        delivers = entry.get("delivers")
        rationale = entry.get("rationale")
        ok = (
            bool(pid)
            and kind in VALID_KINDS
            and isinstance(delivers, list)
            and len(delivers) > 0
            and bool(rationale)
        )
        report.add(
            "PLAN.structure.page",
            "ERROR",
            ok,
            f"{pid or '<无 page_id>'}: 需 page_id、kind∈{{standalone,variant}}、非空 delivers、rationale",
        )
        if kind == "variant":
            report.add(
                "PLAN.structure.variant",
                "ERROR",
                bool(entry.get("variant_of")),
                f"{pid}: kind==variant 必须填 variant_of",
            )
        plan_page_ids.append(pid)
        for rid in delivers or []:
            if isinstance(rid, str):
                delivered.setdefault(rid, []).append(pid)

    cc_ids: list[str] = []
    for cc in cross_cutting:
        if not isinstance(cc, dict):
            report.add("PLAN.structure.cross_cutting", "ERROR", False, f"cross_cutting 项非对象: {cc!r}")
            continue
        rid = str(cc.get("req_id") or "")
        ok = (
            bool(rid)
            and bool(cc.get("covered_by"))
            and cc.get("covered_by_kind") in VALID_COVERED_BY_KIND
            and bool(cc.get("rationale"))
        )
        report.add(
            "PLAN.structure.cross_cutting",
            "ERROR",
            ok,
            f"{rid or '<无 req_id>'}: 需 req_id、covered_by、covered_by_kind∈{{page,engine}}、rationale",
        )
        cc_ids.append(rid)

    # parity: every planned page must exist as an EPPS page.
    missing = [pid for pid in plan_page_ids if pid and pid not in page_ids]
    report.add(
        "PLAN.parity.plan_to_pages",
        "ERROR",
        not missing,
        f"page_plan 中不存在于 EPPS pages 的 page_id: {missing}",
    )

    # flat_render: every planned page (incl. each variant) renders a section with ≥1 zone.
    if html is not None:
        rendered = {sid for sid, s in html.sections.items() if s.get("zones")}
        not_drawn = [pid for pid in plan_page_ids if pid not in rendered]
        report.add(
            "PLAN.flat_render",
            "ERROR",
            not not_drawn,
            f"page_plan 页未渲染（或无 zone）的 page_id——必须平铺渲染，含每个 variant: {not_drawn}",
        )

    req_ids = {r["id"] for r in requirements}
    cc_set = set(cc_ids)

    # dangling
    dangling_delivers = sorted(rid for rid in delivered if rid not in req_ids)
    report.add(
        "PLAN.dangling.delivers",
        "ERROR",
        not dangling_delivers,
        f"delivers 中不存在于需求集的 id: {dangling_delivers}",
    )
    dangling_cc = sorted(rid for rid in cc_ids if rid not in req_ids)
    bad_covered_by = [
        str(cc.get("req_id"))
        for cc in cross_cutting
        if isinstance(cc, dict)
        and cc.get("covered_by_kind") == "page"
        and str(cc.get("covered_by") or "") not in page_ids
    ]
    report.add(
        "PLAN.dangling.cross_cutting",
        "ERROR",
        (not dangling_cc) and (not bad_covered_by),
        f"cross_cutting req_id 不在需求集: {dangling_cc}；covered_by_kind==page 但非页 id: {bad_covered_by}",
    )

    # aggregate guard: an aggregate requirement (counts rendered variants) cannot be cross_cutting.
    agg_in_cc = sorted({r["id"] for r in requirements if r.get("aggregate") and r["id"] in cc_set})
    report.add(
        "PLAN.cross_cutting.aggregate_guard",
        "ERROR",
        not agg_in_cc,
        f"聚合需求不得进 cross_cutting（聚合本身计数已渲染变体，排除则自相矛盾）: {agg_in_cc}",
    )

    # coverage: every tracked req not in cross_cutting must be delivered.
    covered_ids = set(delivered)
    for req in requirements:
        rid = req["id"]
        if req.get("priority") not in TRACKED_PRIORITIES:
            continue
        if rid in cc_set:
            continue
        severity = "ERROR" if req.get("priority") == "P0" else "WARNING"
        if req.get("aggregate"):
            # ≥ min_covered siblings delivered across ≥ min_covered DISTINCT pages
            # — this is what catches "N types collapsed onto one cycling page".
            mi = req.get("module_index")
            min_cov = req.get("min_covered", 2)
            siblings = [
                s for s in requirements
                if s.get("module_index") == mi and not s.get("aggregate") and s["id"] != rid
            ]
            distinct_pages: set[str] = set()
            covered_n = 0
            for s in siblings:
                if s["id"] in cc_set:
                    continue
                pages_for = delivered.get(s["id"], [])
                if pages_for:
                    covered_n += 1
                    distinct_pages.update(pages_for)
            ok = covered_n >= min_cov and len(distinct_pages) >= min_cov
            report.add(
                "PLAN.coverage",
                severity,
                ok,
                f"{rid}（{req.get('feature', '')}）：聚合需 ≥{min_cov} 个同模块兄弟、且分散在 ≥{min_cov} 个不同页面，"
                f"实际 {covered_n} 个兄弟 / {len(distinct_pages)} 个页面",
            )
        else:
            covered = rid in covered_ids
            detail = "未覆盖（无页面 delivers）" if not covered else f"已覆盖 by {delivered.get(rid)}"
            report.add(
                "PLAN.coverage",
                severity,
                covered,
                f"{rid}（{req.get('feature', '')}）：{detail}",
            )

    _granularity_hints(report, plan_pages, requirements, cc_set)

    return report


def _granularity_hints(
    report: Report,
    plan_pages: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    cc_set: set[str],
) -> None:
    """Soft, ADVISORY-only hints (never block; feed the LLM judge)."""
    req_mod = {r["id"]: r.get("module_index") for r in requirements}

    # L4: a variant_of group with a single member is suspicious (orphan variant).
    variant_groups: dict[str, list[str]] = defaultdict(list)
    for entry in plan_pages:
        if isinstance(entry, dict) and entry.get("kind") == "variant":
            variant_groups[str(entry.get("variant_of"))].append(str(entry.get("page_id") or ""))
    for vk, members in variant_groups.items():
        if len(members) == 1:
            report.add(
                "PLAN.granularity.variant_group_size",
                "ADVISORY",
                False,
                f"variant_of={vk} 只有 1 个 variant（{members[0]}）：宜改 standalone，或补兄弟变体",
            )

    # A standalone page spanning ≥2 modules is suspicious ONLY if one of those
    # modules is already split across other pages (proves inconsistent grouping).
    module_pages: dict[Any, set[str]] = defaultdict(set)
    for entry in plan_pages:
        if not isinstance(entry, dict):
            continue
        pid = str(entry.get("page_id") or "")
        for rid in entry.get("delivers") or []:
            m = req_mod.get(str(rid))
            if m is not None:
                module_pages[m].add(pid)
    split_modules = {m for m, pids in module_pages.items() if len(pids) > 1}
    for entry in plan_pages:
        if not isinstance(entry, dict) or entry.get("kind") != "standalone":
            continue
        pid = str(entry.get("page_id") or "")
        mods = {req_mod.get(str(rid)) for rid in entry.get("delivers") or []}
        mods.discard(None)
        cross_split = mods & split_modules
        if len(mods) >= 2 and cross_split:
            report.add(
                "PLAN.granularity.cross_module_standalone",
                "ADVISORY",
                False,
                f"{pid}: standalone 跨 ≥2 模块 {sorted(m for m in mods if m is not None)}，"
                f"而模块 {sorted(m for m in cross_split if m is not None)} 已被别处拆分，合并可能不一致",
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the requirement→page plan (third external gate).",
    )
    parser.add_argument("spec", type=Path, help="Path to epps.json / epps.yaml / prototype.md")
    parser.add_argument("requirements", type=Path, help="Path to the requirements markdown doc")
    parser.add_argument(
        "html",
        nargs="?",
        type=Path,
        help="Optional prototype.html; enables the flat-render check",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON report")
    args = parser.parse_args()

    raw = load_doc(args.spec)
    page_plan = raw.get("page_plan") if isinstance(raw, dict) else None
    _proto, pages = normalize(raw)
    requirements = extract_requirements(args.requirements.read_text(encoding="utf-8"))
    html = parse_html(args.html) if args.html else None
    report = validate_page_plan(pages, requirements, page_plan, html)
    if args.json:
        print(json.dumps({"ok": report.ok(), "items": report.items}, ensure_ascii=False, indent=2))
    else:
        report.print()
    return 0 if report.ok() else 1


if __name__ == "__main__":
    raise SystemExit(main())
