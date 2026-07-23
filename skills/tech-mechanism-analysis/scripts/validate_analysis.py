#!/usr/bin/env python3
"""Validate the analysis.json contract for tech-mechanism-analysis.

``analysis.json`` is the single source of truth — the machine-readable deep
analysis contract. ``analysis.md`` is its render; ``validate_contract.py``
cross-checks the two. This gate checks the *internal* structure & consistency:

  T-F      top-level required fields + types
  T-TYPE   mechanism_type ∈ {data-flow,lifecycle,call-chain,state-machine,other}
  T-LANG   languages non-empty; language_precision matches + precision enum
  T-COV    covered_files non-empty
  T-CHAIN  chain_template non-empty; chain_stages non-empty; each segment ∈
           chain_template; stage id unique; key_structures/evidence non-empty;
           numerical is bool
  T-NUM    numerical_examples: NUM-NN unique; stage_id ⇒ a numerical=true stage;
           computation_steps/faithfulness_note/result/evidence non-empty
  T-NUMCOV every numerical=true stage has ≥1 numerical_example (hard)
  T-DEBT   defects: DEBT-(ARCH|LOGIC)-NN unique; axis ⇔ id prefix; stage_id ⇒
           real stage; cross_stage bool; four elements non-empty; evidence
  T-BAN    NO severity/bug/mermaid/repro key anywhere (recursive) — design-debt≠bug
  T-GAP    gaps is a string list
  T-DIAG   diagrams (optional): applicable bool; true ⇒ type enum + nodes/edges;
           no mermaid key

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

REQUIRED_TOP = (
    "target", "analyzed_at", "languages", "language_precision", "covered_files",
    "responsibility", "mechanism_type", "mechanism_type_basis", "chain_template",
    "chain_stages", "numerical_examples", "defects", "gaps",
)
MECH_TYPES = {"data-flow", "lifecycle", "call-chain", "state-machine", "other"}
PRECISIONS = {"high", "medium", "low"}
TARGET_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STAGE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
NUM_RE = re.compile(r"^NUM-\d+$")
DEBT_RE = re.compile(r"^DEBT-(ARCH|LOGIC)-\d+$")
AXES = {"architecture", "logic"}
DIAG_TYPES = {"sequence", "flowchart", "state"}
# Forbidden anywhere: design-debt ≠ bug (no severity/bug), mermaid stays in md only.
FORBIDDEN_KEYS = {"severity", "bug", "mermaid", "repro"}


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


def _string_list(value: Any, *, nonempty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (not nonempty or bool(value))
        and all(_nonempty_str(item) for item in value)
    )


def _evidence_ok(ev: Any) -> bool:
    if not isinstance(ev, list) or not ev:
        return False
    return all(isinstance(e, dict) and _nonempty_str(e.get("file")) for e in ev)


def _find_forbidden(obj: Any, path: list[str], found: list[tuple[str, str]]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                found.append((".".join(path + [k]), k))
            _find_forbidden(v, path + [str(k)], found)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _find_forbidden(v, path + [str(i)], found)


def validate(data: Any, path: Path) -> Report:
    r = Report()
    if not isinstance(data, dict):
        r.err("T-F1", "顶层不是 JSON 对象")
        return r

    # ---- T-F top-level required fields ----
    miss = [k for k in REQUIRED_TOP if data.get(k) in (None, "")]
    if miss:
        r.err("T-F1", f"缺必填顶层字段：{miss}")
    else:
        r.ok("T-F1")
    r.ok_or("T-F2", isinstance(data.get("target"), str) and bool(TARGET_RE.fullmatch(data["target"])),
            f"target={data.get('target')}", "target 须为 kebab-case")
    try:
        date.fromisoformat(data.get("analyzed_at", ""))
        r.ok("T-F3", f"analyzed_at={data.get('analyzed_at')}")
    except (TypeError, ValueError):
        r.err("T-F3", f"analyzed_at 须为 YYYY-MM-DD，实际 {data.get('analyzed_at')!r}")
    r.ok_or("T-F4", _nonempty_str(data.get("responsibility")),
            "responsibility 有", "responsibility 须为非空字符串")
    r.ok_or("T-F5", _nonempty_str(data.get("mechanism_type_basis")),
            "mechanism_type_basis 有", "mechanism_type_basis 须为非空字符串（类型判定依据）")
    r.ok_or("T-F6", _string_list(data.get("gaps")),
            f"gaps {len(data.get('gaps')) if isinstance(data.get('gaps'), list) else 0} 条",
            "gaps 须为不重复的字符串数组（可为空）")

    # ---- T-TYPE ----
    r.ok_or("T-TYPE1", data.get("mechanism_type") in MECH_TYPES,
            f"mechanism_type={data.get('mechanism_type')}",
            f"mechanism_type 非法：{data.get('mechanism_type')!r}")

    # ---- T-LANG ----
    langs = data.get("languages")
    r.ok_or("T-LANG1", _string_list(langs, nonempty=True),
            f"languages {len(langs) if isinstance(langs, list) else 0} 种",
            "languages 须为非空数组（多语言全列）")
    lp = data.get("language_precision")
    lp_ok = isinstance(lp, list) and len(lp) > 0 and all(
        isinstance(p, dict) and _nonempty_str(p.get("language"))
        and p.get("precision") in PRECISIONS and _nonempty_str(p.get("note")) for p in lp)
    r.ok_or("T-LP1", lp_ok,
            f"language_precision {len(lp) if isinstance(lp, list) else 0} 条",
            "language_precision 须为非空数组，每项 {language, precision∈high/medium/low, note}")
    if lp_ok and _string_list(langs, nonempty=True):
        lp_langs = [p["language"] for p in lp]
        r.ok_or("T-LP2", len(lp_langs) == len(set(lp_langs)) and set(lp_langs) == set(langs),
                "language_precision 与 languages 一一对应",
                f"language_precision 语言集合 {lp_langs} 与 languages {langs} 不一致或重复")

    # ---- T-COV ----
    cov = data.get("covered_files")
    r.ok_or("T-COV1", _string_list(cov, nonempty=True),
            f"covered_files {len(cov) if isinstance(cov, list) else 0} 个",
            "covered_files 须为非空数组（模块 A 边界）")

    # ---- T-CHAIN ----
    tmpl = data.get("chain_template")
    r.ok_or("T-CHAIN1", _string_list(tmpl, nonempty=True),
            f"chain_template {len(tmpl) if isinstance(tmpl, list) else 0} 段",
            "chain_template 须为非空字符串数组")
    tmpl_set = set(tmpl) if isinstance(tmpl, list) else set()
    stages = data.get("chain_stages")
    stage_ids: list[str] = []
    numerical_stage_ids: set[str] = set()
    if not isinstance(stages, list) or not stages:
        r.err("T-CHAIN2", "chain_stages 须为非空数组（至少一段）")
        stages = []
    else:
        r.ok("T-CHAIN2", f"chain_stages {len(stages)} 段")
    for i, st in enumerate(stages):
        if not isinstance(st, dict):
            r.err("T-CHAIN3", f"chain_stages[{i}] 不是对象")
            continue
        ctx = f"chain_stages[{i}] ({st.get('id', '?')})"
        sid = st.get("id")
        r.ok_or("T-CHAIN4", isinstance(sid, str) and bool(STAGE_ID_RE.fullmatch(sid)),
                f"{sid}: stage id 合法", f"{ctx}: id 非法 {sid!r}")
        if isinstance(sid, str):
            if sid in stage_ids:
                r.err("T-CHAIN5", f"{ctx}: stage id 重复（{sid}）")
            stage_ids.append(sid)
        r.ok_or("T-CHAIN6", st.get("segment") in tmpl_set,
                f"{sid}: segment={st.get('segment')} ∈ template",
                f"{ctx}: segment {st.get('segment')!r} 不在 chain_template {sorted(tmpl_set)} 内")
        for fld in ("name", "what", "how", "why"):
            r.ok_or("T-CHAIN7", _nonempty_str(st.get(fld)),
                    f"{sid}: {fld} 有", f"{ctx}: 缺 {fld}")
        r.ok_or("T-CHAIN8", _string_list(st.get("key_structures"), nonempty=True),
                f"{sid}: key_structures 有",
                f"{ctx}: key_structures 须为非空字符串数组")
        r.ok_or("T-CHAIN9", isinstance(st.get("numerical"), bool),
                f"{sid}: numerical={st.get('numerical')}",
                f"{ctx}: numerical 须为 bool")
        r.ok_or("T-CHAIN10", _evidence_ok(st.get("evidence")),
                f"{sid}: evidence 齐全",
                f"{ctx}: evidence 须为非空数组且每项含 file")
        if st.get("numerical") is True and isinstance(sid, str):
            numerical_stage_ids.add(sid)
    valid_stage_ids = set(stage_ids)

    # ---- T-NUM numerical_examples ----
    nums = data.get("numerical_examples")
    num_ids: list[str] = []
    if nums is None:
        nums = []
    if not isinstance(nums, list):
        r.err("T-NUM1", "numerical_examples 须为数组")
        nums = []
    else:
        r.ok("T-NUM1", f"numerical_examples {len(nums)} 条")
    covered_num_stages: set[str] = set()
    for i, nx in enumerate(nums):
        if not isinstance(nx, dict):
            r.err("T-NUM2", f"numerical_examples[{i}] 不是对象")
            continue
        ctx = f"numerical_examples[{i}] ({nx.get('id', '?')})"
        nid = nx.get("id")
        r.ok_or("T-NUM3", isinstance(nid, str) and bool(NUM_RE.match(nid)),
                f"{nid}: id 合法", f"{ctx}: id 非法 {nid!r}（须 NUM-NN）")
        if isinstance(nid, str):
            if nid in num_ids:
                r.err("T-NUM4", f"{ctx}: id 重复（{nid}）")
            num_ids.append(nid)
        stg = nx.get("stage_id")
        r.ok_or("T-NUM5", stg in numerical_stage_ids,
                f"{nid}: stage_id={stg}（数值段）",
                f"{ctx}: stage_id {stg!r} 须指向一个 numerical=true 的段（{sorted(numerical_stage_ids) or '无'}）")
        if stg in numerical_stage_ids:
            covered_num_stages.add(stg)
        for fld in ("operation", "sample_data", "result", "faithfulness_note"):
            r.ok_or("T-NUM6", _nonempty_str(nx.get(fld)),
                    f"{nid}: {fld} 有", f"{ctx}: 缺 {fld}")
        r.ok_or("T-NUM7", _string_list(nx.get("computation_steps"), nonempty=True),
                f"{nid}: computation_steps {len(nx.get('computation_steps')) if isinstance(nx.get('computation_steps'), list) else 0} 步",
                f"{ctx}: computation_steps 须为非空字符串数组（逐步运算）")
        r.ok_or("T-NUM8", _evidence_ok(nx.get("evidence")),
                f"{nid}: evidence 齐全",
                f"{ctx}: evidence 须为非空数组且每项含 file")

    # ---- T-NUMCOV every numerical stage has ≥1 example ----
    uncovered = sorted(numerical_stage_ids - covered_num_stages)
    r.ok_or("T-NUMCOV", not uncovered,
            f"全部 {len(numerical_stage_ids)} 个数值段均有工作举例",
            f"以下数值段缺工作举例：{uncovered}（数值环节必须给真实数值工作举例）")

    # ---- T-DEBT defects ----
    defects = data.get("defects")
    debt_ids: list[str] = []
    if not isinstance(defects, list):
        r.err("T-DEBT1", "defects 须为数组（无设计债时用空数组 []）")
        defects = []
    else:
        r.ok("T-DEBT1", f"defects {len(defects)} 条")
    for i, d in enumerate(defects):
        if not isinstance(d, dict):
            r.err("T-DEBT2", f"defects[{i}] 不是对象")
            continue
        ctx = f"defects[{i}] ({d.get('id', '?')})"
        did = d.get("id")
        m = DEBT_RE.match(did) if isinstance(did, str) else None
        r.ok_or("T-DEBT3", bool(m), f"{did}: id 合法",
                f"{ctx}: id 非法 {did!r}（须 DEBT-ARCH-NN 或 DEBT-LOGIC-NN）")
        if m:
            expect_axis = "architecture" if m.group(1) == "ARCH" else "logic"
            r.ok_or("T-DEBT4", d.get("axis") == expect_axis,
                    f"{did}: 前缀⇒axis {expect_axis} 一致",
                    f"{ctx}: id 前缀⇒{expect_axis} 与 axis={d.get('axis')!r} 不一致")
        if isinstance(did, str):
            if did in debt_ids:
                r.err("T-DEBT5", f"{ctx}: id 重复（{did}）")
            debt_ids.append(did)
        r.ok_or("T-DEBT6", d.get("axis") in AXES,
                f"{did}: axis={d.get('axis')}",
                f"{ctx}: axis 非法 {d.get('axis')!r}")
        r.ok_or("T-DEBT7", d.get("stage_id") in valid_stage_ids,
                f"{did}: stage_id={d.get('stage_id')}",
                f"{ctx}: stage_id {d.get('stage_id')!r} 未在 chain_stages 声明")
        r.ok_or("T-DEBT8", isinstance(d.get("cross_stage"), bool),
                f"{did}: cross_stage={d.get('cross_stage')}",
                f"{ctx}: cross_stage 须为 bool")
        for fld in ("hard_requirement", "why_hard", "evolution_direction", "cost_impact"):
            r.ok_or("T-DEBT9", _nonempty_str(d.get(fld)),
                    f"{did}: {fld} 有",
                    f"{ctx}: 缺 {fld}（缺陷四要素，缺一不可）")
        r.ok_or("T-DEBT10", _evidence_ok(d.get("evidence")),
                f"{did}: evidence 齐全",
                f"{ctx}: evidence 须为非空数组且每项含 file")

    # ---- T-BAN forbidden keys (severity/bug/mermaid/repro) ----
    found: list[tuple[str, str]] = []
    _find_forbidden(data, [], found)
    if found:
        r.err("T-BAN1", f"出现禁止键（设计债≠bug / mermaid 不进 json）：{[(p, k) for p, k in found]}")
    else:
        r.ok("T-BAN1", "无 severity/bug/mermaid/repro 键")

    # ---- T-DIAG diagrams (optional) ----
    diag = data.get("diagrams")
    if diag is None:
        r.ok("T-DIAG1", "无 diagrams（P2 可选，跳过）")
    elif not isinstance(diag, dict):
        r.err("T-DIAG1", "diagrams 须为对象")
    else:
        r.ok_or("T-DIAG2", isinstance(diag.get("applicable"), bool),
                "diagrams.applicable 是 bool",
                "diagrams.applicable 须为 bool")
        if "mermaid" in diag:
            r.err("T-DIAG3", "diagrams 内禁止 mermaid 键")
        if diag.get("applicable") is True:
            r.ok_or("T-DIAG4", diag.get("type") in DIAG_TYPES,
                    f"diagrams.type={diag.get('type')}",
                    f"diagrams.type 非法 {diag.get('type')!r}（须 sequence/flowchart/state）")
            nodes = diag.get("nodes")
            r.ok_or("T-DIAG5", isinstance(nodes, list) and nodes,
                    f"diagrams.nodes {len(nodes) if isinstance(nodes, list) else 0} 个",
                    "applicable=true 须有非空 nodes")
            if isinstance(nodes, list) and nodes:
                nids = [n.get("id") for n in nodes if isinstance(n, dict)]
                nid_set = set(nids)
                for j, n in enumerate(nodes):
                    if not isinstance(n, dict) or not _nonempty_str(n.get("label")) or not _evidence_ok(n.get("evidence")):
                        r.err("T-DIAG6", f"diagrams.nodes[{j}]: 须有 id+label+非空 evidence")
                edges = diag.get("edges")
                if isinstance(edges, list):
                    for j, e in enumerate(edges):
                        if not isinstance(e, dict):
                            continue
                        if e.get("from") not in nid_set or e.get("to") not in nid_set:
                            r.err("T-DIAG7", f"diagrams.edges[{j}]: 端点须引用已声明 node")
        else:
            r.ok_or("T-DIAG4", _nonempty_str(diag.get("reason")),
                    "diagrams.reason 有", "applicable=false 须有 reason")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a tech-mechanism-analysis analysis.json")
    ap.add_argument("doc", type=Path, help="Path to analysis.json")
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

    print(f"=== validate_analysis: {args.doc} ===")
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
