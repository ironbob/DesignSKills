#!/usr/bin/env python3
"""Validate a code-analyze-business test-cases JSON contract file.

The `<biz>-test-cases.json` is the machine-validated contract source for the case
list; the companion `<biz>-test-cases.md` is the human render. Checks JSON
internal consistency and, when the .md is passed too, reconciles the two (case
count, id set, per-case 需求来源↔req, 实现锚点↔anchor, by_type/total).

Rules (mirrors the skill plan):
  TJ-F  required top-level keys (incl. total_cases / by_type / cases[])
  TJ-E  each case: id ~ TC-<MODULE>-<n>, type enum, req/anchor present, covers list; ids unique
  TJ-E3/E4  total_cases / by_type match actual counts
  TJ-R  md reconciliation: TC count / id set / 需求来源 / 实现锚点 / by_type
Exits non-zero when any ERROR fails or the WARNING pass rate < 80%.

Pure stdlib (json + re) — no PyYAML.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TC_ID_RE = re.compile(r"^TC-[A-Z]+-\d+$")
TYPES = ("Happy", "Error", "Edge")
TYPE_SET = set(TYPES)
TYPE_KEY = {"Happy": "happy", "Error": "error", "Edge": "edge"}
LINK_RE = re.compile(r"[\w/.-]+\.\w+:\d+(?:-\d+)?")

REQUIRED_TOP = ("business", "source_analysis", "source_requirements",
                "total_cases", "by_type", "cases")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warns: list[str] = []
        self.passed: list[str] = []

    def err(self, rule: str, msg: str = "") -> None:
        self.errors.append(f"🔴 [{rule}] {msg}".rstrip())

    def warn(self, rule: str, msg: str = "") -> None:
        self.warns.append(f"🟡 [{rule}] {msg}".rstrip())

    def ok(self, rule: str, msg: str = "") -> None:
        self.passed.append((f"✅ [{rule}]" + (f" {msg}" if msg else "")).rstrip())


def frontmatter_and_body(text: str) -> tuple[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    return (m.group(1), text[m.end():]) if m else ("", text)


def md_cases(body: str) -> dict[str, tuple[str | None, str | None]]:
    """{tc_id: (req|None, anchor|None)} parsed from ### TC-... sections."""
    out: dict[str, tuple[str | None, str | None]] = {}
    for m in re.finditer(r"^###\s+(TC-[A-Z]+-\d+)", body, re.M):
        cid = m.group(1)
        start = m.end()
        nxt = re.search(r"^###\s", body[start:], re.M)
        sec = body[start: start + nxt.start()] if nxt else body[start:]
        rm = re.search(r"\*\*需求来源[:：]\*\*\s*(REQ-[A-Z]+-\d+)", sec)
        am = re.search(r"\*\*实现锚点[:：]\*\*\s*`?([^\s`\n]+)", sec)
        anchor = None
        if am:
            lm = LINK_RE.search(am.group(1))
            anchor = lm.group(0) if lm else am.group(1)
        out[cid] = (rm.group(1) if rm else None, anchor)
    return out


def validate(tc_json: Path, tc_md: Path | None) -> Report:
    r = Report()
    try:
        data = json.loads(tc_json.read_text(encoding="utf-8"))
    except Exception as exc:
        r.err("TJ-F1", f"JSON 解析失败：{exc}")
        return r
    if not isinstance(data, dict):
        r.err("TJ-F1", "JSON 顶层不是对象")
        return r

    miss = [k for k in REQUIRED_TOP if data.get(k) in (None, "") or k not in data]
    if miss:
        r.err("TJ-F1", f"缺顶层必填键：{miss}")
    else:
        r.ok("TJ-F1")
    cases = data.get("cases")
    if not isinstance(cases, list):
        r.err("TJ-F1", "cases 不是数组")
        cases = []

    ids: list[str] = []
    bad_shape: list[str] = []
    bad_type: list[str] = []
    no_req: list[str] = []
    no_anchor: list[str] = []
    bad_covers: list[str] = []
    for c in cases:
        if not isinstance(c, dict):
            r.err("TJ-E1", f"case 不是对象：{c}")
            continue
        cid = c.get("id", "")
        if isinstance(cid, str) and TC_ID_RE.match(cid):
            ids.append(cid)
        else:
            bad_shape.append(str(cid))
        if c.get("type") not in TYPE_SET:
            bad_type.append(str(cid))
        if not (isinstance(c.get("req"), str) and c.get("req")):
            no_req.append(str(cid))
        anc = c.get("anchor")
        if not (isinstance(anc, str) and LINK_RE.search(anc)):
            no_anchor.append(str(cid))
        if not isinstance(c.get("covers"), list):
            bad_covers.append(str(cid))
    if bad_shape or bad_type or no_req or no_anchor or bad_covers:
        if bad_shape:
            r.err("TJ-E1", f"case id 形不符 TC-<MODULE>-<n>：{bad_shape[:8]}")
        if bad_type:
            r.err("TJ-E1", f"type 非 Happy/Error/Edge：{bad_type[:8]}")
        if no_req:
            r.err("TJ-E1", f"req 缺失：{no_req[:8]}")
        if no_anchor:
            r.err("TJ-E1", f"anchor 缺失或非 file:line：{no_anchor[:8]}")
        if bad_covers:
            r.err("TJ-E1", f"covers 非数组：{bad_covers[:8]}")
    elif cases:
        r.ok("TJ-E1", f"{len(cases)} 条 case 字段合法")

    dups = sorted({x for x in ids if ids.count(x) > 1})
    if dups:
        r.err("TJ-E2", f"case id 重复：{dups}")
    elif ids:
        r.ok("TJ-E2", f"{len(ids)} 个 id 唯一")

    total = data.get("total_cases")
    try:
        tnum = int(total) if total is not None else None
    except (ValueError, TypeError):
        tnum = None
    if tnum is not None:
        if tnum != len(cases):
            r.err("TJ-E3", f"total_cases={tnum} 与实际 case 数 {len(cases)} 不符")
        else:
            r.ok("TJ-E3", f"total_cases={tnum} 一致")

    by_type = data.get("by_type") or {}
    if not isinstance(by_type, dict):
        by_type = {}
    actual = {TYPE_KEY[t]: 0 for t in TYPES}
    for c in cases:
        if isinstance(c, dict) and c.get("type") in TYPE_SET:
            actual[TYPE_KEY[c["type"]]] += 1
    mismatch = [f"{k}={by_type.get(k)}≠实际{actual[k]}" for k in actual if k in by_type and by_type.get(k) != actual[k]]
    if mismatch:
        r.err("TJ-E4", "by_type 不符：" + "；".join(mismatch))
    else:
        r.ok("TJ-E4", f"by_type={actual} 一致")

    if tc_md is not None:
        fm, body = frontmatter_and_body(tc_md.read_text(encoding="utf-8"))
        mdc = md_cases(body)
        md_ids = set(mdc)
        json_ids = set(ids)

        if len(mdc) != len(cases):
            r.warn("TJ-R1", f"md ### TC- 数 {len(mdc)} ≠ json cases {len(cases)}")
        else:
            r.ok("TJ-R1", f"用例数一致 {len(mdc)}")
        if md_ids != json_ids:
            r.warn("TJ-R2", f"id 集合不一致：仅 md {sorted(md_ids - json_ids)} 仅 json {sorted(json_ids - md_ids)}")
        else:
            r.ok("TJ-R2", "id 集合一致")

        req_map = {c["id"]: c.get("req") for c in cases if isinstance(c, dict) and "id" in c}
        anc_map = {c["id"]: (LINK_RE.search(c["anchor"]).group(0) if isinstance(c.get("anchor"), str) and LINK_RE.search(c["anchor"]) else c.get("anchor")) for c in cases if isinstance(c, dict) and "id" in c}
        req_mism = [f"{i}(md:{mdc[i][0]}≠json:{req_map.get(i)})" for i in mdc if i in req_map and mdc[i][0] != req_map.get(i)]
        anc_mism = [f"{i}(md:{mdc[i][1]}≠json:{anc_map.get(i)})" for i in mdc if i in anc_map and mdc[i][1] != anc_map.get(i)]
        if req_mism:
            r.warn("TJ-R3", f"需求来源 与 json req 不符：{req_mism[:8]}")
        else:
            r.ok("TJ-R3", "需求来源 与 json req 一致")
        if anc_mism:
            r.warn("TJ-R4", f"实现锚点 与 json anchor 不符：{anc_mism[:8]}")
        else:
            r.ok("TJ-R4", "实现锚点 与 json anchor 一致")

        md_total_m = re.search(r"^total_cases:\s*(\d+)", fm, re.M)
        md_total = int(md_total_m.group(1)) if md_total_m else None
        md_bt = {k: None for k in ("happy", "error", "edge")}
        btm = re.search(r"^by_type:\s*\{([^}]*)\}", fm, re.M)
        if btm:
            for k in md_bt:
                km = re.search(rf"\b{k}\s*:\s*(\d+)", btm.group(1))
                md_bt[k] = int(km.group(1)) if km else None
        drift = []
        if md_total is not None and tnum is not None and md_total != tnum:
            drift.append(f"md total_cases={md_total}≠json {tnum}")
        for k in md_bt:
            if md_bt[k] is not None and by_type.get(k) is not None and md_bt[k] != by_type.get(k):
                drift.append(f"md by_type.{k}={md_bt[k]}≠json {by_type.get(k)}")
        if drift:
            r.warn("TJ-R5", "md/json 计数漂移：" + "；".join(drift))
        else:
            r.ok("TJ-R5", "md/json 计数一致")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a test-cases.json contract")
    ap.add_argument("tc_json", type=Path, help="Path to test-cases.json")
    ap.add_argument("tc_md", type=Path, nargs="?", default=None, help="Optional test-cases.md for reconciliation")
    args = ap.parse_args()
    if not args.tc_json.exists():
        sys.stderr.write(f"{args.tc_json}: 文件不存在\n")
        return 2

    r = validate(args.tc_json, args.tc_md)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_test_cases_json: {args.tc_json} ===")
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
