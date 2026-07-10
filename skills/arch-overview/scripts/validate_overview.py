#!/usr/bin/env python3
"""Validate the overview.json contract for arch-overview.

``overview.json`` is the single source of truth — the machine-readable overview
contract. ``overview.md`` is its render; ``validate_contract.py`` cross-checks
the two. This gate checks the *internal* structure & consistency of overview.json:

  O-F     top-level required fields + types
  O-SCOPE scope_level ∈ {module, app}
  O-LANG  languages non-empty; language_precision[].precision ∈ {high,medium,low}
  O-COV   covered_files non-empty
  O-GRADE overall_grade ∈ {优,良,中,差}
  O-DIM   dimensions exactly 4; keys == {layering,cohesion,extensibility,readability}
          each grade valid; assessment/evidence non-empty
  O-IP    each dimension.industry_practice has what/when/gap/provenance/verified/
          further_reading; provenance == "LLM内置经验"; verified == false;
          further_reading non-empty
  O-HL    highlights: id matches HL-<n>, dimension valid, evidence non-empty
  O-RISK  risks: id matches RISK-<n>, dimension valid, note + evidence present
  O-ID    all highlight/risk ids unique
  O-DIAG  diagrams has layering/c4/runtime; applicable is bool; true ⇒ complete
          groups/nodes/edges or participants/flows; false ⇒ reason non-empty;
          stored Mermaid is rejected and deterministic rendering must succeed
  O-EV    every evidence item carries a `file`

Exits non-zero when any ERROR fails or the WARNING pass rate < 80%.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
import re
import sys
from pathlib import Path
from typing import Any

from render_mermaid import render_view

REQUIRED_TOP = (
    "target", "analyzed_at", "scope_level", "languages", "language_precision",
    "covered_files", "responsibility", "overall_grade", "dimensions",
    "highlights", "risks", "diagrams", "gaps",
)
SCOPE_LEVELS = {"module", "app"}
GRADES = {"优", "良", "中", "差"}
PRECISIONS = {"high", "medium", "low"}
C4_LEVELS = {"container", "component"}
DIM_KEYS = ("layering", "cohesion", "extensibility", "readability")
DIM_KEY_SET = set(DIM_KEYS)
IP_FIELDS = ("what", "when", "gap", "provenance", "verified", "further_reading")
PROVENANCE = "LLM内置经验"
HL_RE = re.compile(r"^HL-\d+$")
RISK_RE = re.compile(r"^RISK-\d+$")
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
TARGET_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
EDGE_STYLES = {"normal", "dashed", "strong"}
C4_KINDS = {"service", "component", "store", "external", "actor"}
RUNTIME_TYPES = {"sequence", "flowchart"}
FLOW_KINDS = {"sync", "response", "async", "dashed"}


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warns: list[str] = []
        self.passed: list[str] = []

    def err(self, rule: str, msg: str) -> None:
        self.errors.append(f"🔴 [{rule}] {msg}")

    def warn(self, rule: str, msg: str) -> None:
        self.warns.append(f"🟡 [{rule}] {msg}")

    def ok(self, rule: str, msg: str = "") -> None:
        self.passed.append(f"✅ [{rule}]" + (f" {msg}" if msg else ""))

    def ok_or(self, rule: str, cond: bool, msg_ok: str, msg_err: str,
              warn: bool = False) -> None:
        if cond:
            self.ok(rule, msg_ok)
        elif warn:
            self.warn(rule, msg_err)
        else:
            self.err(rule, msg_err)


def _nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _evidence_ok(ev: Any) -> bool:
    """evidence must be a non-empty list, each item a dict with a `file`."""
    if not isinstance(ev, list) or not ev:
        return False
    return all(isinstance(e, dict) and _nonempty_str(e.get("file")) for e in ev)


def _string_list(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(_nonempty_str(item) for item in value)
        and len(value) == len(set(value))
    )


def _validate_nodes_and_edges(
    r: Report, ctx: str, view: dict[str, Any], *, c4: bool = False
) -> set[str]:
    nodes = view.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        r.err("O-DIAG3", f"{ctx}: applicable=true 须有非空 nodes")
        return set()
    node_ids: list[str] = []
    for index, node in enumerate(nodes):
        nctx = f"{ctx}.nodes[{index}]"
        if not isinstance(node, dict):
            r.err("O-NODE1", f"{nctx}: 须为对象")
            continue
        nid = node.get("id")
        if not isinstance(nid, str) or not ID_RE.fullmatch(nid):
            r.err("O-NODE1", f"{nctx}: id 非法 {nid!r}")
        else:
            node_ids.append(nid)
        if not _nonempty_str(node.get("label")):
            r.err("O-NODE1", f"{nctx}: 缺 label")
        if c4 and node.get("kind") not in C4_KINDS:
            r.err("O-NODE1", f"{nctx}: kind 非法 {node.get('kind')!r}")
        if not _evidence_ok(node.get("evidence")):
            r.err("O-EV1", f"{nctx}: evidence 须非空且每项含 file")
    if len(node_ids) != len(set(node_ids)):
        r.err("O-NODE2", f"{ctx}: node id 重复")
    ids = set(node_ids)

    edges = view.get("edges")
    if not isinstance(edges, list):
        r.err("O-EDGE1", f"{ctx}: edges 须为数组（可为空）")
        return ids
    for index, edge in enumerate(edges):
        ectx = f"{ctx}.edges[{index}]"
        if not isinstance(edge, dict):
            r.err("O-EDGE1", f"{ectx}: 须为对象")
            continue
        if edge.get("from") not in ids or edge.get("to") not in ids:
            r.err(
                "O-EDGE2",
                f"{ectx}: 端点须引用已声明节点，实际 {edge.get('from')}->{edge.get('to')}",
            )
        if edge.get("style", "normal") not in EDGE_STYLES:
            r.err("O-EDGE1", f"{ectx}: style 非法 {edge.get('style')!r}")
        if not _evidence_ok(edge.get("evidence")):
            r.err("O-EV1", f"{ectx}: evidence 须非空且每项含 file")
    return ids


def validate(data: Any, path: Path) -> Report:
    r = Report()
    if not isinstance(data, dict):
        r.err("O-F1", "顶层不是 JSON 对象")
        return r

    # ---- O-F top-level required fields ----
    miss = [k for k in REQUIRED_TOP if data.get(k) in (None, "")]
    if miss:
        r.err("O-F1", f"缺必填顶层字段：{miss}")
    else:
        r.ok("O-F1")
    r.ok_or("O-F2", isinstance(data.get("target"), str) and bool(TARGET_RE.fullmatch(data["target"])),
            f"target={data.get('target')}", "target 须为 kebab-case")
    try:
        date.fromisoformat(data.get("analyzed_at", ""))
        r.ok("O-F3", f"analyzed_at={data.get('analyzed_at')}")
    except (TypeError, ValueError):
        r.err("O-F3", f"analyzed_at 须为 YYYY-MM-DD，实际 {data.get('analyzed_at')!r}")
    r.ok_or("O-F4", _nonempty_str(data.get("responsibility")),
            "responsibility 有", "responsibility 须为非空字符串")
    r.ok_or("O-F5", _string_list(data.get("gaps")),
            f"gaps {len(data.get('gaps')) if isinstance(data.get('gaps'), list) else 0} 条",
            "gaps 须为不重复的字符串数组（可为空）")

    # ---- O-SCOPE ----
    r.ok_or("O-SCOPE1", data.get("scope_level") in SCOPE_LEVELS,
            f"scope_level={data.get('scope_level')}",
            f"scope_level 非法：{data.get('scope_level')!r}（须 module 或 app）")

    # ---- O-LANG ----
    langs = data.get("languages")
    r.ok_or("O-LANG1", _string_list(langs, nonempty=True),
            f"languages {len(langs) if isinstance(langs, list) else 0} 种",
            "languages 须为非空数组（多语言全列）")
    lp = data.get("language_precision")
    lp_ok = isinstance(lp, list) and len(lp) > 0 and all(
        isinstance(p, dict) and _nonempty_str(p.get("language"))
        and p.get("precision") in PRECISIONS and _nonempty_str(p.get("note")) for p in lp)
    r.ok_or("O-LP1", lp_ok,
            f"language_precision {len(lp) if isinstance(lp, list) else 0} 条",
            "language_precision 须为非空数组，每项 {language, precision∈high/medium/low}")
    if lp_ok and _string_list(langs, nonempty=True):
        lp_langs = [p["language"] for p in lp]
        r.ok_or("O-LP2", len(lp_langs) == len(set(lp_langs)) and set(lp_langs) == set(langs),
                "language_precision 与 languages 一一对应",
                f"language_precision 语言集合 {lp_langs} 与 languages {langs} 不一致或重复")

    # ---- O-COV ----
    cov = data.get("covered_files")
    r.ok_or("O-COV1", _string_list(cov, nonempty=True),
            f"covered_files {len(cov) if isinstance(cov, list) else 0} 个",
            "covered_files 须为非空数组（模块 A 边界）")

    # ---- O-GRADE ----
    r.ok_or("O-GRADE1", data.get("overall_grade") in GRADES,
            f"overall_grade={data.get('overall_grade')}",
            f"overall_grade 非法：{data.get('overall_grade')!r}（须 优/良/中/差）")

    # ---- O-DIM dimensions ----
    dims = data.get("dimensions")
    if not isinstance(dims, list):
        r.err("O-DIM1", "dimensions 须为数组（恰好 4 条）")
        dims = []
    else:
        r.ok_or("O-DIM1", len(dims) == 4,
                f"dimensions {len(dims)} 条（须 4）",
                f"dimensions 须恰好 4 条，实际 {len(dims)}")
    keys_seen = [d.get("key") for d in dims if isinstance(d, dict)]
    r.ok_or("O-DIM2", set(keys_seen) == DIM_KEY_SET and len(keys_seen) == 4,
            "4 维 key 齐全无重复",
            f"维度 key 集合 {sorted(set(keys_seen))} 与要求 {list(DIM_KEYS)} 不符")
    for d in dims:
        if not isinstance(d, dict):
            continue
        ctx = f"dimension:{d.get('key')}"
        r.ok_or("O-DIM3", d.get("grade") in GRADES,
                f"{ctx}: grade={d.get('grade')}",
                f"{ctx}: grade 非法 {d.get('grade')!r}")
        r.ok_or("O-DIM4", _nonempty_str(d.get("assessment")),
                f"{ctx}: assessment 有", f"{ctx}: 缺 assessment")
        r.ok_or("O-DIM5", _evidence_ok(d.get("evidence")),
                f"{ctx}: evidence 齐全", f"{ctx}: evidence 须为非空数组且每项含 file")
        ip = d.get("industry_practice")
        if not isinstance(ip, dict):
            r.err("O-IP1", f"{ctx}: industry_practice 须为对象")
        else:
            miss_ip = [f for f in IP_FIELDS if f not in ip or (
                f == "further_reading" and not (isinstance(ip.get(f), list) and ip.get(f))
            ) or (f != "further_reading" and not _nonempty_str(ip.get(f)) and not isinstance(ip.get(f), bool))]
            # verified is bool (allowed False) — re-check precisely
            miss_ip = []
            for f in IP_FIELDS:
                v = ip.get(f)
                if f == "verified":
                    if not isinstance(v, bool):
                        miss_ip.append(f)
                elif f == "further_reading":
                    if not (isinstance(v, list) and v):
                        miss_ip.append(f)
                else:
                    if not _nonempty_str(v):
                        miss_ip.append(f)
            r.ok_or("O-IP1", not miss_ip,
                    f"{ctx}: industry_practice 6 字段齐全",
                    f"{ctx}: industry_practice 缺字段 {miss_ip}")
            r.ok_or("O-IP2", ip.get("provenance") == PROVENANCE,
                    f"{ctx}: provenance={ip.get('provenance')}",
                    f"{ctx}: provenance 须为 {PROVENANCE!r}（不假装权威）")
            r.ok_or("O-IP3", ip.get("verified") is False,
                    f"{ctx}: verified=false",
                    f"{ctx}: verified 须为 false（未核对原文）")

    # ---- O-HL / O-RISK / O-ID ----
    ids: list[str] = []
    for label, items, id_re, need_note in (
        ("highlights", data.get("highlights"), HL_RE, False),
        ("risks", data.get("risks"), RISK_RE, True),
    ):
        lst = items
        if not isinstance(lst, list):
            r.err(f"O-{label.split('-')[0][:4].upper()}", f"{label} 须为数组（可为空）")
            lst = []
        else:
            r.ok(f"O-{label[:4].upper()}", f"{label} {len(lst)} 条")
        for i, it in enumerate(lst):
            if not isinstance(it, dict):
                r.err("O-F1", f"{label}[{i}] 不是对象")
                continue
            ctx = f"{label}[{i}] ({it.get('id', '?')})"
            fid = it.get("id")
            r.ok_or("O-ID1", isinstance(fid, str) and bool(id_re.match(fid)),
                    f"{fid}: id 合法", f"{ctx}: id 非法 {fid!r}")
            if isinstance(fid, str):
                if fid in ids:
                    r.err("O-ID2", f"{ctx}: id 重复（{fid}）")
                ids.append(fid)
            r.ok_or("O-F1", it.get("dimension") in DIM_KEY_SET,
                    f"{fid}: dimension={it.get('dimension')}",
                    f"{ctx}: dimension 非法 {it.get('dimension')!r}")
            r.ok_or("O-F1", _nonempty_str(it.get("title")),
                    f"{fid}: title 有", f"{ctx}: 缺 title")
            r.ok_or("O-F1", _evidence_ok(it.get("evidence")),
                    f"{fid}: evidence 齐全", f"{ctx}: evidence 须非空且每项含 file")
            if need_note:
                r.ok_or("O-F1", _nonempty_str(it.get("note")),
                        f"{fid}: note 有", f"{ctx}: risks 须有 note（前瞻性描述）")

    # ---- O-DIAG diagrams ----
    diag = data.get("diagrams")
    if not isinstance(diag, dict):
        r.err("O-DIAG1", "diagrams 须为对象")
        diag = {}
    r.ok_or("O-DIAG1", all(k in diag for k in ("layering", "c4", "runtime")),
            "3 视角键齐全",
            f"diagrams 缺视角键：{[k for k in ('layering','c4','runtime') if k not in diag]}")
    for view in ("layering", "c4", "runtime"):
        v = diag.get(view)
        if not isinstance(v, dict):
            r.err("O-DIAG2", f"diagrams.{view} 须为对象")
            continue
        ctx = f"diagrams.{view}"
        if "mermaid" in v:
            r.err("O-DIAG0", f"{ctx}: 禁止保存 mermaid；须由结构化字段生成")
        r.ok_or("O-DIAG2", isinstance(v.get("applicable"), bool),
                f"{ctx}: applicable={v.get('applicable')}",
                f"{ctx}: applicable 须为 bool")
        appl = v.get("applicable")
        if appl is True:
            if view == "runtime":
                r.ok_or("O-DIAG5", v.get("type") in RUNTIME_TYPES,
                        f"{ctx}: type={v.get('type')}",
                        f"{ctx}: type 须 sequence 或 flowchart")
                participants = v.get("participants")
                flows = v.get("flows")
                pids: list[str] = []
                if not isinstance(participants, list) or not participants:
                    r.err("O-DIAG3", f"{ctx}: applicable=true 须有非空 participants")
                else:
                    for index, item in enumerate(participants):
                        pctx = f"{ctx}.participants[{index}]"
                        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not ID_RE.fullmatch(item["id"]):
                            r.err("O-NODE1", f"{pctx}: id 非法")
                            continue
                        pids.append(item["id"])
                        if not _nonempty_str(item.get("label")) or not _evidence_ok(item.get("evidence")):
                            r.err("O-NODE1", f"{pctx}: 须有 label + 非空 evidence")
                    if len(pids) != len(set(pids)):
                        r.err("O-NODE2", f"{ctx}: participant id 重复")
                if not isinstance(flows, list) or not flows:
                    r.err("O-DIAG3", f"{ctx}: applicable=true 须有非空 flows")
                else:
                    steps: list[str] = []
                    for index, flow in enumerate(flows):
                        fctx = f"{ctx}.flows[{index}]"
                        if not isinstance(flow, dict):
                            r.err("O-FLOW1", f"{fctx}: 须为对象")
                            continue
                        step = str(flow.get("step", ""))
                        steps.append(step)
                        if not step or flow.get("from") not in set(pids) or flow.get("to") not in set(pids):
                            r.err("O-FLOW1", f"{fctx}: step/from/to 非法")
                        if not _nonempty_str(flow.get("action")) or not _evidence_ok(flow.get("evidence")):
                            r.err("O-FLOW1", f"{fctx}: 须有 action + 非空 evidence")
                        if v.get("type") == "sequence" and flow.get("kind", "sync") not in FLOW_KINDS:
                            r.err("O-FLOW1", f"{fctx}: kind 非法 {flow.get('kind')!r}")
                    if len(steps) != len(set(steps)):
                        r.err("O-FLOW1", f"{ctx}: flow step 重复")
            else:
                ids = _validate_nodes_and_edges(r, ctx, v, c4=view == "c4")
                if view == "layering":
                    groups = v.get("groups")
                    if not isinstance(groups, list) or not groups:
                        r.err("O-GROUP1", f"{ctx}: groups 须为非空数组")
                    else:
                        gids = [g.get("id") for g in groups if isinstance(g, dict)]
                        valid_gids = [gid for gid in gids if isinstance(gid, str)]
                        if len(gids) != len(groups) or len(valid_gids) != len(gids) or len(valid_gids) != len(set(valid_gids)) or not all(
                            ID_RE.fullmatch(gid) for gid in valid_gids
                        ):
                            r.err("O-GROUP1", f"{ctx}: group id 非法或重复")
                        for group in groups:
                            if not _nonempty_str(group.get("label")):
                                r.err("O-GROUP1", f"{ctx}: group 缺 label")
                        for node in v.get("nodes") or []:
                            if isinstance(node, dict) and node.get("group") not in set(valid_gids):
                                r.err("O-GROUP2", f"{ctx}: node {node.get('id')} 引用未知 group {node.get('group')!r}")
            if view == "c4":
                r.ok_or("O-DIAG5", v.get("level") in C4_LEVELS,
                        f"{ctx}: level={v.get('level')}",
                        f"{ctx}: level 须 container 或 component")
            try:
                source = render_view(view, v)
                r.ok_or("O-RENDER1", _nonempty_str(source),
                        f"{ctx}: 可由结构化字段生成 Mermaid",
                        f"{ctx}: 生成 Mermaid 为空")
            except (KeyError, TypeError, ValueError) as exc:
                r.err("O-RENDER1", f"{ctx}: Mermaid 生成失败：{exc}")
        elif appl is False:
            r.ok_or("O-DIAG4", _nonempty_str(v.get("reason")),
                    f"{ctx}: reason 有", f"{ctx}: applicable=false 须有 reason")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate an arch-overview overview.json")
    ap.add_argument("doc", type=Path, help="Path to overview.json")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    try:
        data = json.loads(args.doc.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.doc}: JSON 解析失败：{exc}\n")
        return 2

    r = validate(data, args.doc)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_overview: {args.doc} ===")
    for line in r.errors + r.warns + r.passed:
        print(line)
    print(f"\nERROR: {len(r.errors)}  WARNING: {len(r.warns)}  PASSED: {len(r.passed)}")
    print(f"WARNING 通过率: {wp * 100:.0f}%  质量分: {quality * 100:.0f}%")

    if r.errors or wp < 0.80:
        print("\n结果：不合格（有 ERROR 或 WARNING 通过率 <80%）")
        return 1
    print("\n结果：合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
