#!/usr/bin/env python3
"""Validate the report.md for arch-quality-eval.

``report.md`` is the human-readable render of ``findings.json``; this gate
checks its *format & coverage*. It does NOT verify a file:line truly exists
(language-agnostic, costly) — real reachability is human self-review.

Finding blocks are ``#### FINDING-<AXIS><n> ...`` headers; the id prefix encodes
the axis (S=smell, R=readability, C=convention), which drives the per-finding
checks (S/R need a 违反原理 line; C needs a 违反规约 line).

  R-F    front-matter required fields
  R-G    verdict present + valid; critical_count == #critical finding blocks
  R-L1   backlink (file:line) coverage in 坏味道 section ≥ 3 distinct anchors
         when findings are present; zero-finding go reports may have no anchors
  R-L2   broken backtick links (ext: with no line number)
  R-S    every FINDING block graded critical/major/minor
  R-P    every S/R FINDING block names a 违反原理 line; every C one a 违反规约 line
  R-C    坏味道 section + 5 core smells present; 可读性 section + 4 axes present
  R-V    conventions_fed=true ⇒ 项目规约 section; false ⇒ no FINDING-C blocks
  R-PR   every FINDING block has 改进方向 + 优先级
  R-B    banned words (0 hit)
  R-U    ⚠ 未确认 matched by the 已知缺口 section

Exits non-zero on ERROR or WARNING pass rate < 80%.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_META = (
    "module", "title", "language", "analyzed_at", "covered_files",
    "conventions_fed", "no_go_threshold", "verdict", "critical_count",
    "major_count", "minor_count", "open_questions",
)

# path.ext:line or path.ext:line-line
LINK_RE = re.compile(r"[\w/.-]+\.\w+:\d+(?:-\d+)?")
BROKEN_LINK_RE = re.compile(r"`[^`\n]*\.\w+:(?!\d)[^`\n]*`")

BANNED = [
    "体验好", "功能完善", "功能强大", "适当处理", "待定", "待补",
    "后续再说", "良好体验", "非常重要", "很关键", "等等", "TBD", "TODO",
]
BANNED_RE = re.compile("|".join(re.escape(w) for w in BANNED))

CORE_SMELLS = [  # (label keywords to require present in 坏味道 section)
    ("循环依赖", ["循环依赖"]),
    ("God Class/Package", ["God", "上帝类", "上帝包"]),
    ("跨层调用", ["跨层"]),
    ("霰弹式修改", ["霰弹"]),
    ("不恰当暴露", ["暴露"]),
]
READABILITY_AXES = ["职责清晰", "依赖可理解", "命名表意", "分层清晰"]

FINDING_HEADER_RE = re.compile(r"^####\s+(FINDING-[A-Z]\d+)\b(.*)$", re.M)
SEVERITY_RE = re.compile(r"\b(critical|major|minor)\b", re.I)
PRINCIPLE_RE = re.compile(r"违反原理\s*[:：]\s*\S")
CONVENTION_RE = re.compile(r"违反规约\s*[:：]\s*\S")
IMPROVE_RE = re.compile(r"改进方向\s*[:：]")
PRIORITY_RE = re.compile(r"优先级\s*[:：]")


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


def finding_blocks(body: str) -> list[tuple[str, str, str]]:
    """Return (id, header_tail, block_text) for each #### FINDING- header."""
    out: list[tuple[str, str, str]] = []
    for m in FINDING_HEADER_RE.finditer(body):
        start = m.start()
        # next h3/h4 header ends the block
        nxt = re.search(r"^###+\s", body[m.end():], re.M)
        end = m.end() + nxt.start() if nxt else len(body)
        out.append((m.group(1), m.group(2), body[start:end]))
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
    blocks = finding_blocks(body)
    try:
        declared_total = (
            int(meta.get("critical_count", 0))
            + int(meta.get("major_count", 0))
            + int(meta.get("minor_count", 0))
        )
    except (TypeError, ValueError):
        declared_total = None

    # ---- R-F front-matter ----
    miss = [k for k in REQUIRED_META if meta.get(k) in (None, "")]
    if miss:
        r.err("R-F1", f"front-matter 缺必填字段：{miss}")
    else:
        r.ok("R-F1")

    # ---- R-G verdict + critical_count vs body ----
    verdict = str(meta.get("verdict", "")).strip().lower()
    if verdict in ("go", "no-go"):
        r.ok("R-G1", f"verdict={verdict}")
    else:
        r.err("R-G1", f"verdict 非法：{meta.get('verdict')!r}（须 go / no-go）")
    # a block is critical if its header line carries the 'critical' token
    body_critical = sum(
        1 for _bid, tail, _blk in blocks
        if re.search(r"\bcritical\b", tail, re.I)
    )
    declared = meta.get("critical_count")
    try:
        declared_n = int(declared)
    except (TypeError, ValueError):
        declared_n = None
    if declared_n is None:
        r.warn("R-G2", f"critical_count 非整数：{declared!r}")
    elif declared_n != body_critical:
        r.err("R-G2", f"critical_count={declared_n} 与正文 critical finding 块数 {body_critical} 不一致")
    else:
        r.ok("R-G2", f"critical_count={body_critical} 与正文一致")

    # ---- R-S every finding block graded ----
    no_sev: list[str] = []
    for bid, tail, blk in blocks:
        if not SEVERITY_RE.search(tail) and not SEVERITY_RE.search(blk):
            no_sev.append(bid)
    if not blocks and declared_total == 0:
        r.ok("R-S1", "0 个 finding 块：健康 go 报告")
    elif not blocks:
        r.warn("R-S1", "未发现 FINDING 块（#### FINDING-...）")
    elif no_sev:
        r.err("R-S1", f"以下 finding 块未分级 critical/major/minor：{no_sev}")
    else:
        r.ok("R-S1", f"{len(blocks)} 个 finding 块均已分级")

    # ---- R-P principle / convention per axis ----
    bad_p: list[str] = []
    for bid, _tail, blk in blocks:
        prefix = bid[len("FINDING-")].upper() if bid.startswith("FINDING-") else ""
        if prefix in ("S", "R"):
            if not PRINCIPLE_RE.search(blk):
                bad_p.append(f"{bid}(缺 违反原理)")
        elif prefix == "C":
            if not CONVENTION_RE.search(blk):
                bad_p.append(f"{bid}(缺 违反规约)")
    if bad_p:
        r.err("R-P1", f"finding 块缺原理/规约行：{bad_p}（S/R 须「违反原理：…」；C 须「违反规约：…」）")
    else:
        r.ok("R-P1", "finding 块原理/规约齐全")

    # ---- R-PR improvement + priority per finding ----
    bad_pr: list[str] = []
    for bid, _tail, blk in blocks:
        miss_pr = []
        if not IMPROVE_RE.search(blk):
            miss_pr.append("改进方向")
        if not PRIORITY_RE.search(blk):
            miss_pr.append("优先级")
        if miss_pr:
            bad_pr.append(f"{bid}(缺 {'/'.join(miss_pr)})")
    if bad_pr:
        r.err("R-PR1", f"finding 块缺改进/优先级：{bad_pr}")
    else:
        r.ok("R-PR1", "finding 块均有改进方向 + 优先级")

    # ---- R-C axis coverage ----
    smell_sec = ""
    for t, c in secs:
        if "坏味道" in t:
            smell_sec = c
            break
    if not smell_sec.strip():
        r.err("R-C1", "缺「架构坏味道」章节")
    else:
        miss_smell = [name for name, kws in CORE_SMELLS
                      if not any(kw in smell_sec for kw in kws)]
        if miss_smell:
            r.err("R-C1", f"坏味道清单缺核心类别（须二分显式 已检出/未检出）：{miss_smell}")
        else:
            r.ok("R-C1", "5 个核心坏味道类别齐全")
        # backlinks in smell section
        n_links = len(set(LINK_RE.findall(smell_sec)))
        if n_links < 3 and declared_total == 0:
            r.ok("R-L1", "0 个 finding，坏味道节无需 ≥3 个回链")
        elif n_links < 3:
            r.err("R-L1", f"坏味道节唯一回链不足：{n_links}（要求 ≥3，重复回链只算1个）")
        else:
            r.ok("R-L1", f"坏味道节 {n_links} 个不同锚点")

    rd_sec = ""
    for t, c in secs:
        if "可读性" in t:
            rd_sec = c
            break
    if not rd_sec.strip():
        r.err("R-C2", "缺「架构可读性」章节")
    else:
        miss_rd = [a for a in READABILITY_AXES if a not in rd_sec]
        if miss_rd:
            r.err("R-C2", f"可读性节缺轴：{miss_rd}（须 职责清晰/依赖可理解/命名表意/分层清晰）")
        else:
            r.ok("R-C2", "可读性四轴齐全")

    # ---- R-V conventions consistency ----
    conv_fed = meta.get("conventions_fed")
    has_conv_section = any("规约" in t for t, _c in secs)
    has_c_findings = any(bid.startswith("FINDING-C") for bid, _t, _b in blocks)
    if conv_fed is True:
        if has_conv_section:
            r.ok("R-V1", "喂入规约且有项目规约节")
        else:
            r.err("R-V1", "conventions_fed=true 须有「项目规约」章节")
    elif conv_fed is False:
        if has_c_findings:
            r.err("R-V1", "conventions_fed=false 不得出现 FINDING-C 规约违规结论")
        else:
            r.ok("R-V1", "未喂入规约，无规约违规结论（一致）")
    else:
        r.warn("R-V1", "conventions_fed 字段缺失")

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
    gap_sec = ""
    for t, c in secs:
        if "已知缺口" in t:
            gap_sec = c
            break
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
    ap = argparse.ArgumentParser(description="Validate an arch-quality-eval report.md")
    ap.add_argument("doc", type=Path, help="Path to the report .md")
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
