#!/usr/bin/env python3
"""Validate a code-analyze-business reverse-engineered requirements document.

Parses the YAML front-matter (requires PyYAML) and the Markdown body, then runs
the rules mirrored in references/reverse-prd.md + references/quality-rules.md:
  R-F  front-matter required fields (incl. source_analysis + gaps)
  R-L  feature-list: each row carries a 实现状态 mark + a backlink to analysis
  R-D  「实现与需求偏差」section present and non-empty (reverse-PRD specific)
  R-B  banned words (0 hit)
  R-U  gaps meta matches the ❌-缺口 count in the body
Exits non-zero when any ERROR fails or the WARNING pass rate < 80%.

NOTE: this script only checks format & coverage, NOT whether a file:line truly
exists or whether an 实现状态 verdict is correct. Real depth is human review.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_META = (
    "business", "title", "summary", "codebase",
    "entry_type", "analyzed_at", "status",
    "source_analysis", "gaps",
)

# path.ext:line  or  path.ext:line-line
LINK_RE = re.compile(r"[\w/.-]+\.\w+:\d+(?:-\d+)?")

BANNED = [
    "体验好", "功能完善", "功能强大", "适当处理", "待定", "待补",
    "后续再说", "良好体验", "非常重要", "很关键", "等等", "TBD", "TODO",
]
BANNED_RE = re.compile("|".join(re.escape(w) for w in BANNED))

# a feature-list row carries a priority token P0/P1/P2
PRIORITY_RE = re.compile(r"\bP[012]\b")
# reverse-PRD 实现状态 marks: ✅ 已实现 / ⚠️ 部分 / ❌ 缺口 (⚠ matches ⚠️ too)
STATUS_RE = re.compile(r"✅|⚠|❌|已实现|部分|缺口")
SEP_RE = re.compile(r"^\|[\s:|\-]+\|$")


def load_meta(text: str, path: Path) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        sys.stderr.write(f"{path}: 未找到 YAML front-matter（--- ... ---）。\n")
        sys.exit(2)
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"{path}: 需要 PyYAML（pip install pyyaml）。{exc}\n")
        sys.exit(2)
    try:
        data = yaml.safe_load(m.group(1)) or {}
    except Exception as exc:
        sys.stderr.write(f"{path}: front-matter YAML 解析失败：{exc}\n")
        sys.exit(2)
    return data if isinstance(data, dict) else {}


def split_frontmatter(text: str) -> str:
    m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.S)
    return text[m.end():] if m else text


def sections(body: str) -> list[tuple[str, str]]:
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"^#{2,6}\s+(.+?)\s*$", body, re.M)]
    out = []
    for i, (s, t) in enumerate(heads):
        e = heads[i + 1][0] if i + 1 < len(heads) else len(body)
        out.append((t, body[s:e]))
    return out


def has_backlink(line: str) -> bool:
    """A feature-list row backlinks to analysis via a §n section ref OR a file:line."""
    return bool(LINK_RE.search(line) or re.search(r"§\s*\d", line))


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


def validate(path: Path) -> Report:
    text = path.read_text(encoding="utf-8")
    meta = load_meta(text, path)
    body = split_frontmatter(text)
    r = Report()
    secs = sections(body)

    # ---- R-F front-matter required fields ----
    miss = [k for k in REQUIRED_META if meta.get(k) in (None, "")]
    if miss:
        r.err("R-F1", f"front-matter 缺必填字段：{miss}")
    else:
        r.ok("R-F1")
    gaps = meta.get("gaps")

    # ---- R-L feature-list rows: 实现状态 mark + backlink ----
    feat_rows = [
        ln.strip() for ln in body.splitlines()
        if ln.strip().startswith("|") and not SEP_RE.match(ln.strip()) and PRIORITY_RE.search(ln)
    ]
    if not feat_rows:
        r.err("R-L1", "未找到功能清单数据行（表格行须含 P0/P1/P2 优先级）")
    else:
        no_status = [str(i + 1) for i, ln in enumerate(feat_rows) if not STATUS_RE.search(ln)]
        if no_status:
            r.err("R-L1", f"功能清单第 {','.join(no_status)} 行缺实现状态（须含 ✅/⚠/❌ 或 已实现/部分/缺口）")
        else:
            r.ok("R-L1", f"功能清单 {len(feat_rows)} 行均有实现状态")
        no_link = [str(i + 1) for i, ln in enumerate(feat_rows) if not has_backlink(ln)]
        if no_link:
            r.err("R-L2", f"功能清单第 {','.join(no_link)} 行缺回链（须含 analysis §n 或 file:line）")
        else:
            r.ok("R-L2", "功能清单每行均回链 analysis")

    # ---- R-D 「实现与需求偏差」section present + non-empty (reverse-PRD specific) ----
    dev_sec = ""
    for t, c in secs:
        if "偏差" in t:
            dev_sec = c
            break
    if not dev_sec.strip():
        r.err("R-D1", "缺「实现与需求偏差」节（反推 PRD 独有，不可省）")
    else:
        items = len(re.findall(r"^\s*-\s+", dev_sec, re.M))
        if items < 1:
            r.err("R-D1", "「实现与需求偏差」节无条目（须至少 1 条：过度实现或需求缺口）")
        else:
            r.ok("R-D1", f"偏差节 {items} 条")

    # ---- R-B banned words ----
    hits = BANNED_RE.findall(body)
    if hits:
        r.err("R-B1", f"正文含 banned 词：{sorted(set(hits))}")
    else:
        r.ok("R-B1")

    # ---- R-U gaps meta vs ❌-缺口 count ----
    gap_count = len(re.findall(r"❌", body))
    known_sec = ""
    for t, c in secs:
        if "已知缺口" in t or "未决" in t:
            known_sec = c
            break
    try:
        gnum = int(gaps) if gaps is not None else None
    except (ValueError, TypeError):
        r.warn("R-U1", f"gaps={gaps} 非整数")
        gnum = None
    if gnum is not None and gnum != gap_count:
        r.warn("R-U1", f"gaps={gnum} 与正文 ❌ 缺口 {gap_count} 处不一致")
    elif gap_count > 0 and not known_sec.strip():
        r.warn("R-U1", "正文有 ❌ 缺口但缺「已知缺口 / 未决」节")
    else:
        r.ok("R-U1", f"gaps={gap_count} 一致")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a code-analyze-business requirements doc")
    ap.add_argument("doc", type=Path, help="Path to the requirements .md")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2

    r = validate(args.doc)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_requirements: {args.doc} ===")
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
