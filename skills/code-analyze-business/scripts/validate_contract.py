#!/usr/bin/env python3
"""Validate the cross-document contract between requirements.json and test-cases.json.

This is where the relational guarantees that freeform markdown cannot express get
actually enforced:
  XC-E1  referential integrity: every case.req must be a real feature id
  XC-C1  orphan features: every feature is covered by >=1 case
  XC-C2  global type presence: {Happy, Error, Edge} each >=1 across all cases
  XC-C3  per-feature type depth (WARN): P0 ~ {Happy,Error,Edge}, P1 ~ {Happy,Edge}
  XC-C4  completeness coverage: union(covers) >= the items analysis marks 有
         (gated on analysis.md; degrades to WARN requiring all 5 when absent)
  XC-W1  covers keys outside the canonical 5 (WARN)

Exits non-zero when any ERROR fails or the WARNING pass rate < 80%.

Pure stdlib (json + re).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Chinese completeness label -> canonical key (mirrors analysis-template 完整性自检)
COMPLETENESS = {
    "异常分支": "exception",
    "触发条件": "trigger",
    "并发时序": "concurrency",
    "外部依赖": "external",
    "幂等": "idempotency",
}
CANONICAL = set(COMPLETENESS.values())


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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def split_frontmatter(text: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.S)
    return text[m.end():] if m else text


def analysis_applicable(body: str) -> set[str]:
    """Canonical completeness keys the analysis 完整性自检 marks 有."""
    appl = set()
    for cn, key in COMPLETENESS.items():
        m = re.search(rf"{re.escape(cn)}\s*[:：]\s*(有|无|不适用)", body)
        if m and m.group(1) == "有":
            appl.add(key)
    return appl


def validate(req: dict, tc: dict, analysis: Path | None) -> Report:
    r = Report()
    features = req.get("features") if isinstance(req, dict) else None
    cases = tc.get("cases") if isinstance(tc, dict) else None
    if not isinstance(features, list):
        r.err("XC-E1", "requirements.json 无 features 数组")
        features = []
    if not isinstance(cases, list):
        r.err("XC-E1", "test-cases.json 无 cases 数组")
        cases = []

    feat_by_id = {}
    for f in features:
        if isinstance(f, dict) and "id" in f:
            feat_by_id[f["id"]] = f
    feat_ids = set(feat_by_id)

    # XC-E1 referential integrity
    dangling = sorted({c.get("req") for c in cases
                       if isinstance(c, dict) and c.get("req") not in feat_ids})
    if dangling:
        r.err("XC-E1", f"case.req 指向不存在的 feature：{dangling[:10]}")
    else:
        r.ok("XC-E1", f"{len(cases)} 条 case 的 req 均指向真实 feature")

    # cases grouped by feature
    cases_by_feat: dict[str, list[dict]] = {fid: [] for fid in feat_ids}
    for c in cases:
        if isinstance(c, dict) and c.get("req") in cases_by_feat:
            cases_by_feat[c["req"]].append(c)

    # XC-C1 orphan features
    orphans = sorted(fid for fid, cs in cases_by_feat.items() if not cs)
    if orphans:
        r.err("XC-C1", f"功能无任何用例覆盖（孤儿）：{orphans[:10]}")
    else:
        r.ok("XC-C1", f"{len(feat_ids)} 个功能均有用例覆盖")

    # XC-C2 global type presence
    types_present = {c.get("type") for c in cases if isinstance(c, dict)}
    missing_types = {"Happy", "Error", "Edge"} - types_present
    if missing_types:
        r.err("XC-C2", f"缺用例类型：{sorted(missing_types)}（Happy/Error/Edge 各须 ≥1）")
    else:
        r.ok("XC-C2", "Happy/Error/Edge 三类齐全")

    # XC-C3 per-feature type depth (WARN, aggregated into one)
    under: list[str] = []
    for fid, f in feat_by_id.items():
        cs = cases_by_feat.get(fid, [])
        ts = {c.get("type") for c in cs if isinstance(c, dict)}
        pri = f.get("priority")
        if pri == "P0" and not {"Happy", "Error", "Edge"} <= ts:
            under.append(f"{fid}(P0 缺 {sorted({'Happy','Error','Edge'}-ts)})")
        elif pri == "P1" and not {"Happy", "Edge"} <= ts:
            under.append(f"{fid}(P1 缺 {sorted({'Happy','Edge'}-ts)})")
    if under:
        r.warn("XC-C3", f"{len(under)} 个功能未达类型深度建议：{under[:8]}（务实档：软提示）")
    else:
        r.ok("XC-C3", "所有功能类型深度达标")

    # XC-C4 completeness coverage
    covered = set()
    bad_keys = set()
    for c in cases:
        if isinstance(c, dict) and isinstance(c.get("covers"), list):
            for k in c["covers"]:
                if k in CANONICAL:
                    covered.add(k)
                else:
                    bad_keys.add(k)

    if analysis is not None:
        abody = split_frontmatter(analysis.read_text(encoding="utf-8"))
        required = analysis_applicable(abody)
        if required:
            miss = sorted(required - covered)
            if miss:
                r.err("XC-C4", f"完整性覆盖不足（analysis 标记「有」但无对应用例 covers）：{miss}")
            else:
                r.ok("XC-C4", f"完整性 5 项中 analysis 标「有」的 {sorted(required)} 均已覆盖")
        else:
            r.ok("XC-C4", "analysis 完整性自检无「有」项，跳过覆盖要求")
    else:
        required = CANONICAL
        miss = sorted(required - covered)
        if miss:
            r.warn("XC-C4", f"未给 analysis，按全 5 项要求；缺 covers：{miss}（降级为 WARN）")
        else:
            r.ok("XC-C4", "完整性 5 项均已覆盖（未给 analysis，按全 5 项）")

    # XC-W1 covers keys outside canonical
    if bad_keys:
        r.warn("XC-W1", f"covers 出现规范 5 项之外的键：{sorted(bad_keys)[:10]}")
    else:
        r.ok("XC-W1", "covers 键均在规范 5 项内")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate the req.json ↔ test-cases.json contract")
    ap.add_argument("req_json", type=Path, help="requirements.json")
    ap.add_argument("tc_json", type=Path, help="test-cases.json")
    ap.add_argument("analysis", type=Path, nargs="?", default=None,
                    help="Optional analysis.md (gates completeness coverage on 有/不适用)")
    args = ap.parse_args()
    for p in (args.req_json, args.tc_json):
        if not p.exists():
            sys.stderr.write(f"{p}: 文件不存在\n")
            return 2
    if args.analysis is not None and not args.analysis.exists():
        sys.stderr.write(f"{args.analysis}: 文件不存在\n")
        return 2

    try:
        req = load_json(args.req_json)
        tc = load_json(args.tc_json)
    except Exception as exc:
        sys.stderr.write(f"JSON 解析失败：{exc}\n")
        return 2

    r = validate(req, tc, args.analysis)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_contract: {args.req_json.name} ↔ {args.tc_json.name} ===")
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
