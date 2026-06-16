#!/usr/bin/env python3
"""Validate an analyze-business analysis document.

Parses the YAML front-matter (requires PyYAML, same as validate_doc.py) and the
Markdown body, then runs the rules mirrored in references/quality-rules.md:
  R-F  front-matter required fields
  R-L  backlink (file:line) coverage & format
  R-B  banned words (0 hit)
  R-C  completeness checklist (5 keywords)
  R-M  mermaid fence + evidence comment
  R-U  ⚠ 未确认 matched by the known-gaps section
Exits non-zero when any ERROR fails or the WARNING pass rate < 80%.

NOTE: this script only checks format & coverage, NOT whether a file:line truly
exists in some codebase (that is language-agnostic and costly to verify
statically). Real reachability is left to human self-review.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_META = (
    "business", "title", "summary", "codebase",
    "entry_type", "analyzed_at", "status", "open_questions",
)

# path.ext:line  or  path.ext:line-line
LINK_RE = re.compile(r"[\w/.-]+\.\w+:\d+(?:-\d+)?")
# backtick-wrapped broken link: `src/x.py:` (colon not followed by a digit)
BROKEN_LINK_RE = re.compile(r"`[^`\n]*\.\w+:(?!\d)[^`\n]*`")

BANNED = [
    "体验好", "功能完善", "功能强大", "适当处理", "待定", "待补",
    "后续再说", "良好体验", "非常重要", "很关键", "等等", "TBD", "TODO",
]
BANNED_RE = re.compile("|".join(re.escape(w) for w in BANNED))

COMPLETENESS = ["异常", "触发", "并发", "外部", "幂等"]

MERMAID_RE = re.compile(r"```mermaid\n(.*?)```", re.S)
EVIDENCE_RE = re.compile(r"<!--\s*evidence:", re.I)

# section keyword -> minimum backlinks required in that section
SECTION_RULES = [("触发", 2), ("主流程", 3), ("数据", 2), ("依赖", 2)]


def load_meta(text: str, path: Path) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        sys.stderr.write(f"{path}: 未找到 YAML front-matter（--- ... ---）。\n")
        sys.exit(2)
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on host packages
        sys.stderr.write(f"{path}: 需要 PyYAML 来解析 front-matter（pip install pyyaml）。{exc}\n")
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
    oq = meta.get("open_questions")

    # ---- R-L1 backlink coverage per key section ----
    secmap: dict[str, str] = {}
    for t, c in secs:
        tl = t.lower()
        for kw, _ in SECTION_RULES:
            if kw in tl and kw not in secmap:
                secmap[kw] = c
    for kw, need in SECTION_RULES:
        c = secmap.get(kw)
        if c is None:
            r.warn("R-L1", f"未找到「{kw}」相关章节，跳过该节回链校验")
            continue
        n = len(LINK_RE.findall(c))
        if n < need:
            r.err("R-L1", f"「{kw}」节回链不足：{n} 条（要求 ≥{need}）")
        else:
            r.ok("R-L1", f"{kw}节 {n} 条回链")

    # ---- R-L2 broken backtick links ----
    broken = BROKEN_LINK_RE.findall(body)
    if broken:
        r.warn("R-L2", f"疑似残缺回链（反引号内 扩展名: 后无行号）：{broken[:3]}")
    else:
        r.ok("R-L2")

    # ---- R-B banned words ----
    hits = BANNED_RE.findall(body)
    if hits:
        r.err("R-B1", f"正文含 banned 词：{sorted(set(hits))}")
    else:
        r.ok("R-B1")

    # ---- R-C completeness keywords ----
    missing = [k for k in COMPLETENESS if k not in body]
    if missing:
        r.warn("R-C1", f"完整性清单关键词未覆盖：{missing}（若不适用请显式写「不适用」）")
    else:
        r.ok("R-C1")

    # ---- R-M mermaid + evidence ----
    mblocks = list(MERMAID_RE.finditer(body))
    bad = []
    for mb in mblocks:
        pre = body[max(0, mb.start() - 200):mb.start()]
        if not EVIDENCE_RE.search(pre):
            bad.append(mb.start())
    if bad:
        r.warn("R-M1", f"{len(bad)} 个 mermaid 图前未紧邻 <!-- evidence: --> 注释")
    elif mblocks:
        r.ok("R-M1", f"{len(mblocks)} 图均有 evidence")
    else:
        r.warn("R-M1", "未发现 mermaid 图（主流程应配图）")

    # ---- R-U unconfirmed vs known-gaps ----
    uc = len(re.findall(r"⚠\s*未确认", body))
    gap_sec = ""
    for t, c in secs:
        if "已知缺口" in t:
            gap_sec = c
            break
    gap_items = len(re.findall(r"^\s*-\s+", gap_sec, re.M))
    if uc == 0 and oq in (None, 0):
        r.ok("R-U1")
    elif not gap_sec.strip():
        r.warn("R-U1", "正文有 ⚠ 未确认 但缺「已知缺口」节")
    elif gap_items < uc:
        r.warn("R-U1", f"⚠ 未确认 {uc} 处，但「已知缺口」仅 {gap_items} 条")
    else:
        r.ok("R-U1", f"{uc} 处未确认均有缺口登记")
    try:
        if oq is not None and int(oq) != uc:
            r.warn("R-U1", f"open_questions={oq} 与正文 ⚠ 未确认 {uc} 处不一致")
    except (ValueError, TypeError):
        pass

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate an analyze-business analysis doc")
    ap.add_argument("doc", type=Path, help="Path to the analysis .md")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2

    r = validate(args.doc)
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
