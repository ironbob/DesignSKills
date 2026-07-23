#!/usr/bin/env python3
"""Validate the analysis.md for tech-mechanism-analysis.

``analysis.md`` is the human-readable render of ``analysis.json``; this gate
checks its *format & coverage*. It does not verify file:line reachability
(language-agnostic, costly) — that is human self-review + ``validate_evidence``.

  R-F     front-matter required fields
  R-SEC   required sections present (机制概述/全链路分段/数值举例/架构问题/逻辑问题/已知缺口)
  R-DEBT  every #### DEBT-ARCH|DEBT-LOGIC block names the four elements
          (需求 / 为什么…难 / 演进|松绑 / 代价|影响)
  R-NUM   数值举例 section shows actual computation (when numerical_examples>0)
  R-L     全链路 section has ≥3 distinct file:line backlinks (when stages present)
  R-NOBUG DEBT blocks must not carry severity grading (critical/major/minor/严重度)
  R-B     banned words (0 hit)
  R-U     ⚠ 未确认 matched by the 已知缺口 section

Exits non-zero on ERROR or WARNING pass rate < 80%.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_META = (
    "target", "title", "mechanism_type", "languages", "analyzed_at",
    "covered_files", "chain_segments", "numerical_examples",
    "defects_arch", "defects_logic", "open_questions",
)

LINK_RE = re.compile(r"[\w/.-]+\.\w+:\d+(?:-\d+)?")
BROKEN_LINK_RE = re.compile(r"`[^`\n]*\.\w+:(?!\d)[^`\n]*`")

BANNED = [
    "体验好", "功能完善", "功能强大", "适当处理", "待定", "待补",
    "后续再说", "良好体验", "非常重要", "很关键", "扩展性强", "灵活性好",
    "等等", "TBD", "TODO",
]
BANNED_RE = re.compile("|".join(re.escape(w) for w in BANNED))

# DEBT four-element markers (each block must hit all four)
REQR_RE = re.compile(r"需求")
WHY_RE = re.compile(r"为什么|难在|让它难|难以|困难|变难")
EVO_RE = re.compile(r"演进|松绑|方向")
COST_RE = re.compile(r"代价|影响|改动面")
# severity grading must NOT appear in DEBT blocks
GRADE_RE = re.compile(r"\b(critical|major|minor)\b|严重度|严重级|分级")

DEBT_HEADER_RE = re.compile(r"^#{3,4}\s+(DEBT-(?:ARCH|LOGIC)-\d+)\b", re.M)

REQUIRED_SECTION_KEYWORDS = [
    ("机制概述", "机制概述"),
    ("全链路分段", "全链路"),
    ("数值举例", "数值"),
    ("架构问题", "架构问题"),
    ("逻辑问题", "逻辑问题"),
    ("已知缺口", "已知缺口"),
]


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


def h2_section(body: str, keyword: str) -> str:
    """Text from the `##` header containing keyword until the next `##` header.

    Includes h3/h4 subsections (defect blocks, worked examples live there)."""
    m = re.search(rf"(?m)^##\s+.*{re.escape(keyword)}.*$", body)
    if not m:
        return ""
    nxt = re.search(r"(?m)^##\s+", body[m.end():])
    end = m.end() + nxt.start() if nxt else len(body)
    return body[m.start():end]


def debt_blocks(body: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in DEBT_HEADER_RE.finditer(body):
        start = m.start()
        nxt = re.search(r"^###+\s", body[m.end():], re.M)
        end = m.end() + nxt.start() if nxt else len(body)
        out.append((m.group(1), body[start:end]))
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
    blocks = debt_blocks(body)

    # ---- R-F front-matter ----
    miss = [k for k in REQUIRED_META if meta.get(k) in (None, "")]
    if miss:
        r.err("R-F1", f"front-matter 缺必填字段：{miss}")
    else:
        r.ok("R-F1")

    # ---- R-SEC required sections ----
    sec_titles = [t for t, _c in secs]
    for label, kw in REQUIRED_SECTION_KEYWORDS:
        present = any(kw in t for t in sec_titles)
        if present:
            r.ok("R-SEC1", f"章节「{label}」存在")
        else:
            r.err("R-SEC1", f"缺章节（关键词「{kw}」）：{label}")

    # ---- R-DEBT four elements per block ----
    if not blocks:
        r.warn("R-DEBT1", "未发现 DEBT 块（#### DEBT-ARCH/LOGIC-NN）——若无设计债应在章节显式声明")
    else:
        bad: list[str] = []
        for bid, blk in blocks:
            miss_e = []
            if not REQR_RE.search(blk):
                miss_e.append("会变难的需求")
            if not WHY_RE.search(blk):
                miss_e.append("为什么难")
            if not EVO_RE.search(blk):
                miss_e.append("演进方向")
            if not COST_RE.search(blk):
                miss_e.append("代价/影响")
            if miss_e:
                bad.append(f"{bid}(缺 {'/'.join(miss_e)})")
        if bad:
            r.err("R-DEBT1", f"DEBT 块缺四要素：{bad}")
        else:
            r.ok("R-DEBT1", f"{len(blocks)} 个 DEBT 块四要素齐全")

    # ---- R-NUM numerical section shows computation ----
    try:
        num_declared = int(meta.get("numerical_examples", 0))
    except (TypeError, ValueError):
        num_declared = 0
    num_sec = h2_section(body, "数值")
    if num_declared > 0:
        if not num_sec.strip():
            r.err("R-NUM1", "frontmatter numerical_examples>0 但缺「数值举例」章节")
        elif not re.search(r"=\s|\d+\s*=|结果[:：]|运算", num_sec):
            r.err("R-NUM1", "数值举例章节未见实际运算（= / 结果 / 运算）")
        else:
            r.ok("R-NUM1", "数值举例章节含实际运算")
    else:
        r.ok("R-NUM1", "无数值环节，跳过数值举例运算检查")

    # ---- R-L backlinks in 全链路 section ----
    chain_sec = h2_section(body, "全链路")
    n_links = len(set(LINK_RE.findall(chain_sec)))
    try:
        chain_n = int(meta.get("chain_segments", 0))
    except (TypeError, ValueError):
        chain_n = 0
    if chain_n > 0 and n_links < 3:
        r.err("R-L1", f"全链路章节唯一回链不足：{n_links}（要求 ≥3）")
    elif chain_n > 0:
        r.ok("R-L1", f"全链路章节 {n_links} 个不同锚点")
    else:
        r.ok("R-L1", "跳过回链检查")

    # ---- R-NOBUG no severity grading in DEBT blocks ----
    graded = [bid for bid, blk in blocks if GRADE_RE.search(blk)]
    if graded:
        r.err("R-NOBUG1", f"DEBT 块出现严重度分级措辞（critical/major/minor/严重度）：{graded}（设计债不打分级）")
    else:
        r.ok("R-NOBUG1", "DEBT 块无严重度分级措辞")

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

    # ---- R-U unconfirmed vs gaps ----
    uc = len(re.findall(r"⚠\s*未确认", body))
    gap_sec = h2_section(body, "已知缺口")
    gap_items = len(re.findall(r"^\s*-\s+", gap_sec, re.M))
    oq = meta.get("open_questions")
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
    ap = argparse.ArgumentParser(description="Validate a tech-mechanism-analysis analysis.md")
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

    print(f"=== validate_report: {args.doc} ===")
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
