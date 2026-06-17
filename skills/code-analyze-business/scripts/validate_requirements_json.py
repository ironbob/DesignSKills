#!/usr/bin/env python3
"""Validate a code-analyze-business requirements JSON contract file.

The `<biz>-requirements.json` is the machine-validated contract source for the
§4 feature list; the companion `<biz>-requirements.md` is the human render. This
checks JSON internal consistency and, when the .md is passed too, reconciles the
two so they cannot silently drift (counts, id sets, status glyphs, gaps sources).

Rules (mirrors the skill plan):
  RJ-F  required top-level keys (business/source_analysis/gaps/features[])
  RJ-E  each feature: id ~ REQ-<MODULE>-<n>, priority/status enums, anchor; ids unique
  RJ-W  gaps == count(status == gap)
  RJ-R  md reconciliation: feature count / id set / status glyph / gaps three-way
Exits non-zero when any ERROR fails or the WARNING pass rate < 80%.

Pure stdlib (json + re) — no PyYAML. md front-matter is parsed by regex.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQ_ID_RE = re.compile(r"^REQ-[A-Z]+-\d+$")
MD_REQ_RE = re.compile(r"REQ-[A-Z]+-\d+")
PRIORITIES = {"P0", "P1", "P2"}
STATUSES = {"implemented", "partial", "gap"}
LINK_RE = re.compile(r"[\w/.-]+\.\w+:\d+(?:-\d+)?")
SEP_RE = re.compile(r"^\|[\s:|\-]+\|$")

# md glyph / word -> status enum (⚠ matches ⚠️, the base codepoint)
GLYPH_STATUS = [("✅", "implemented"), ("已实现", "implemented"),
                ("❌", "gap"), ("缺口", "gap"),
                ("⚠", "partial"), ("部分", "partial")]

REQUIRED_TOP = ("business", "source_analysis", "gaps", "features")


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


def glyph_to_status(row: str) -> str | None:
    for g, s in GLYPH_STATUS:
        if g in row:
            return s
    return None


def frontmatter_and_body(text: str) -> tuple[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    return (m.group(1), text[m.end():]) if m else ("", text)


def md_feature_rows(body: str) -> list[tuple[str, str | None]]:
    """(req_id, status_enum|None) for each §4 data row carrying a REQ id."""
    rows = []
    for ln in body.splitlines():
        s = ln.strip()
        if not s.startswith("|") or SEP_RE.match(s):
            continue
        m = MD_REQ_RE.search(s)
        if m:
            rows.append((m.group(0), glyph_to_status(s)))
    return rows


def validate(req_json: Path, req_md: Path | None) -> Report:
    r = Report()
    try:
        data = json.loads(req_json.read_text(encoding="utf-8"))
    except Exception as exc:
        r.err("RJ-F1", f"JSON 解析失败：{exc}")
        return r
    if not isinstance(data, dict):
        r.err("RJ-F1", "JSON 顶层不是对象")
        return r

    miss = [k for k in REQUIRED_TOP if data.get(k) in (None, "") or k not in data]
    if miss:
        r.err("RJ-F1", f"缺顶层必填键：{miss}")
    else:
        r.ok("RJ-F1")
    features = data.get("features")
    if not isinstance(features, list):
        r.err("RJ-F1", "features 不是数组")
        features = []
    gaps = data.get("gaps")

    ids: list[str] = []
    bad_shape: list[str] = []
    bad_pri: list[str] = []
    bad_stat: list[str] = []
    no_anchor: list[str] = []
    for f in features:
        if not isinstance(f, dict):
            r.err("RJ-E1", f"feature 不是对象：{f}")
            continue
        fid = f.get("id", "")
        if isinstance(fid, str) and REQ_ID_RE.match(fid):
            ids.append(fid)
        else:
            bad_shape.append(str(fid))
        if f.get("priority") not in PRIORITIES:
            bad_pri.append(str(fid))
        if f.get("status") not in STATUSES:
            bad_stat.append(str(fid))
        anc = f.get("anchor")
        if not (isinstance(anc, str) and LINK_RE.search(anc)):
            no_anchor.append(str(fid))
    if bad_shape or bad_pri or bad_stat or no_anchor:
        if bad_shape:
            r.err("RJ-E1", f"feature id 形不符 REQ-<MODULE>-<n>：{bad_shape[:8]}")
        if bad_pri:
            r.err("RJ-E1", f"priority 非 P0/P1/P2：{bad_pri[:8]}")
        if bad_stat:
            r.err("RJ-E1", f"status 非 implemented/partial/gap：{bad_stat[:8]}")
        if no_anchor:
            r.err("RJ-E1", f"anchor 缺失或非 file:line：{no_anchor[:8]}")
    elif features:
        r.ok("RJ-E1", f"{len(features)} 条 feature 字段合法")

    dups = sorted({x for x in ids if ids.count(x) > 1})
    if dups:
        r.err("RJ-E2", f"feature id 重复：{dups}")
    elif ids:
        r.ok("RJ-E2", f"{len(ids)} 个 id 唯一")

    gap_count = sum(1 for f in features if isinstance(f, dict) and f.get("status") == "gap")
    try:
        gnum = int(gaps) if gaps is not None else None
    except (ValueError, TypeError):
        gnum = None
        r.warn("RJ-W1", f"gaps={gaps} 非整数")
    if gnum is not None:
        if gnum != gap_count:
            r.warn("RJ-W1", f"gaps={gnum} 与 status==gap 计数 {gap_count} 不一致")
        else:
            r.ok("RJ-W1", f"gaps={gap_count} 一致")

    if req_md is not None:
        fm, body = frontmatter_and_body(req_md.read_text(encoding="utf-8"))
        md_rows = md_feature_rows(body)
        if len(md_rows) != len(features):
            r.warn("RJ-R1", f"md §4 REQ 行数 {len(md_rows)} ≠ json features {len(features)}")
        else:
            r.ok("RJ-R1", f"行数一致 {len(md_rows)}")

        md_ids = {i for i, _ in md_rows}
        json_ids = set(ids)
        if md_ids != json_ids:
            r.warn("RJ-R2", f"id 集合不一致：仅 md {sorted(md_ids - json_ids)} 仅 json {sorted(json_ids - md_ids)}")
        else:
            r.ok("RJ-R2", "id 集合一致")

        md_stat = {i: s for i, s in md_rows}
        mism = [f"{f.get('id')}(md:{md_stat.get(f.get('id'))}≠json:{f.get('status')})"
                for f in features if isinstance(f, dict)
                and md_stat.get(f.get("id")) and f.get("status")
                and md_stat.get(f.get("id")) != f.get("status")]
        if mism:
            r.warn("RJ-R3", f"状态符号与 json status 不符：{mism[:8]}")
        else:
            r.ok("RJ-R3", "状态符号与 json 一致")

        fm_m = re.search(r"^gaps:\s*(\d+)", fm, re.M)
        fm_gaps = int(fm_m.group(1)) if fm_m else None
        body_x = len(re.findall(r"❌", body))
        drift = []
        if fm_gaps is not None and gnum is not None and fm_gaps != gnum:
            drift.append(f"frontmatter gaps={fm_gaps}≠json gaps={gnum}")
        if fm_gaps is not None and fm_gaps != body_x:
            drift.append(f"frontmatter gaps={fm_gaps}≠正文❌ {body_x}")
        if drift:
            r.warn("RJ-R4", "gaps 三源不一致：" + "；".join(drift))
        else:
            r.ok("RJ-R4", f"gaps 三源一致 frontmatter/json/正文❌ = {fm_gaps}/{gnum}/{body_x}")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a requirements.json contract")
    ap.add_argument("req_json", type=Path, help="Path to requirements.json")
    ap.add_argument("req_md", type=Path, nargs="?", default=None, help="Optional requirements.md for reconciliation")
    args = ap.parse_args()
    if not args.req_json.exists():
        sys.stderr.write(f"{args.req_json}: 文件不存在\n")
        return 2

    r = validate(args.req_json, args.req_md)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_requirements_json: {args.req_json} ===")
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
