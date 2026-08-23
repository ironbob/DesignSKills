#!/usr/bin/env python3
"""Planning-artifact gate for expert-doc-writer stages 1-4.

Completeness/coverage checks over the planning markdown files in a
workspace. Structural (not semantic): tables well-formed, required
columns filled, cross-file references resolve. Semantic quality stays
with the run's own stage self-review: default decisions must actually
be made and recorded in the ledger (candidates, choice, reason).

  S1  01-写作情境.md  thesis exists & is an assertion; reader table
                     complete; D-x list non-empty; every A-x answered
  S2  02-事实台账.md  fact table has 来源 or an open G-x; 置信 in enum;
                     every G-x has a disposition (挖/降级/放弃)
  S3  03-故事线.md    message chain rows filled; every D-x covered by a
                     section; F-x refs exist in 02; >=1 decision-core
                     section; mermaid argument graph present
  S4  04-表达形式清单.md rows complete; type in T1..T12; data figures
                     carry conclusion-caption draft; text blocks only
                     T10/T11; tool red-lines (Mermaid=data -> ERROR)

Usage: check_plan.py <workspace> [1 2 3 4 ...]
Exit:  0 pass (no ERROR), 1 any ERROR, 2 workspace/files missing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CONF = {"实测", "推算", "传闻"}
DISPOSITION = ("补", "挖", "降级", "放弃")
TEXT_TYPES = {"T10", "T11"}
VALID_TYPES = {f"T{i}" for i in range(1, 14)}
# tool red-line: data types must go to ECharts, structure types to Mermaid
NEEDS_ECHARTS = {f"T{i}" for i in (6, 7, 8, 9)}
NEEDS_MERMAID = {f"T{i}" for i in (1, 2, 3, 4)}
ECHARTS_HINT = ("echarts", "柱", "折线", "堆叠", "直方", "箱线", "散点")
MERMAID_HINT = ("mermaid", "flowchart", "sequence", "state", "时序", "流程图", "状态图", "组件图", "分层")


def tables(md: str) -> list[list[list[str]]]:
    """Markdown tables -> list of (rows of cells)."""
    out: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in md.splitlines():
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                continue  # separator row
            current.append(cells)
        else:
            if current:
                out.append(current)
                current = []
    if current:
        out.append(current)
    return out


def find_table(md: str, *header_words: str) -> list[list[str]] | None:
    for t in tables(md):
        if t and all(w in t[0][0] + "".join(t[0]) for w in header_words):
            return t
    # fallback: header words each present somewhere in the header row
    for t in tables(md):
        if not t:
            continue
        header = "".join(t[0])
        if all(w in header for w in header_words):
            return t
    return None


class Report:
    def __init__(self, stage: str) -> None:
        self.stage = stage
        self.lines: list[str] = []

    def err(self, msg: str, error: bool = True) -> None:
        self.lines.append(f"[{self.stage}]{' ERROR' if error else ' WARN'} {msg}")

    @property
    def errors(self) -> int:
        return sum(1 for l in self.lines if " ERROR " in l)


def stage1(md: str, r: Report) -> set[str]:
    # thesis
    m = re.search(r"一句话论点", md)
    if not m:
        r.err("缺『一句话论点』小节")
    else:
        tail = md[m.end(): m.end() + 600]
        first_line, _, rest = tail.partition("\n")
        inline = first_line.strip().lstrip("：:-*—> ")
        if inline and not re.search(r"待拍板|待答|待补|候选", inline):
            cand = inline  # thesis written inline after the heading colon
        else:
            cand = next((l.strip(" -*—>") for l in rest.splitlines()
                         if l.strip() and not l.strip().startswith("#")), "")
        if not cand or re.search(r"待拍板|待A|待补|_待", cand):
            r.err(f"论点未选定（须按默认决策策略记录候选+选定）：「{cand[:30]}」")
        elif len(cand) < 8:
            r.err(f"论点过短不像断言：「{cand}」")
        elif re.search(r"关于|介绍|概述", cand[:12]):
            r.err(f"论点是主题不是断言：「{cand[:24]}」", error=False)
    # reader table
    t = find_table(md, "读者", "场景") or find_table(md, "已知")
    if not t or len(t) < 2:
        r.err("读者画像表缺或无数据行")
    else:
        for row in t[1:]:
            if any(not c for c in row):
                r.err(f"画像行有空列：{' | '.join(row)}")
    # decision list + blocking answers
    d_ids = set(re.findall(r"D-\d+", md))
    if not d_ids:
        r.err("决策清单 D-x 为空")
    for a in sorted(set(re.findall(r"A-\d+", md))):
        # D-001: explicit marker convention — a blocking question is answered only
        # when its ledger line carries ✅ or 已答, not by mere second occurrence
        answered = any(("✅" in l or "已答" in l) and a in l for l in md.splitlines())
        if not answered:
            r.err(f"阻塞问题 {a} 未答复（台账条目须带 ✅/已答 标记）")
    return d_ids


def stage2(md: str, r: Report) -> set[str]:
    f_ids: set[str] = set()
    t = find_table(md, "来源", "置信")
    if not t or len(t) < 2:
        r.err("事实表缺或无数据行")
    else:
        header = "".join(t[0])
        src_i = next((i for i, h in enumerate(t[0]) if "来源" in h), None)
        conf_i = next((i for i, h in enumerate(t[0]) if "置信" in h), None)
        for row in t[1:]:
            row = row + [""] * (len(t[0]) - len(row))
            fid = row[0]
            if re.fullmatch(r"F-\d+", fid):
                f_ids.add(fid)
            src = row[src_i] if src_i is not None else ""
            if not src and "G-" not in "".join(row):
                r.err(f"{fid} 无来源且未挂缺口 G-x")
            conf = row[conf_i] if conf_i is not None else ""
            if conf and conf not in CONF:
                r.err(f"{fid} 置信档非法：「{conf}」")
            if conf == "传闻":
                r.err(f"{fid} 置信=传闻，不得默认入稿", error=False)
    for g in sorted(set(re.findall(r"G-\d+", md))):
        ctx = [l for l in md.splitlines() if g in l]
        if not any(any(d in l for d in DISPOSITION) for l in ctx):
            r.err(f"{g} 缺处置（挖/降级/放弃三选一）")
    return f_ids


def stage3(md: str, r: Report, d_ids: set[str], f_ids: set[str]) -> None:
    t = find_table(md, "message") or find_table(md, "节名")
    if not t or len(t) < 2:
        r.err("message 链表缺或无数据行")
        return
    header = "".join(t[0])
    msg_i = next((i for i, h in enumerate(t[0]) if "message" in h.lower() or "一句话" in h), 0)
    covered: set[str] = set()
    for row in t[1:]:
        row = row + [""] * (len(t[0]) - len(row))
        msg = row[msg_i] if msg_i < len(row) else ""
        if not msg:
            r.err(f"节「{row[0]}」message 为空")
        covered |= set(re.findall(r"D-\d+", "".join(row)))
    for d in sorted(d_ids - covered):
        r.err(f"{d} 无节覆盖（决策清单是覆盖基准）")
    if not (d_ids - covered) and not d_ids:
        r.err("03 未引用任何 D-x，覆盖检查失效")
    dangling = set(re.findall(r"F-\d+", md)) - f_ids - set(re.findall(r"G-\d+", md))
    for f in sorted(dangling):
        r.err(f"{f} 不在 02 事实台账（悬空引用）")
    if "★" not in md and "决策核心" not in md:
        r.err("无 ★决策核心 节标注（阶段 7 先行依据）")
    if "```mermaid" not in md:
        r.err("缺 Mermaid 论证链图", error=False)


def stage4(md: str, r: Report, f_ids: set[str], s3_sections: list[str]) -> None:
    t = find_table(md, "内容类型")
    if not t or len(t) < 2:
        r.err("形式清单表缺或无数据行")
        return
    header = t[0]
    idx = {name: next((i for i, h in enumerate(header) if name in h), None)
           for name in ("节", "内容类型", "形式", "标题")}
    data_rows = 0
    planned_sections: set[str] = set()
    for row in t[1:]:
        row = row + [""] * (len(header) - len(row))
        get = lambda k: row[idx[k]] if idx[k] is not None and idx[k] < len(row) else ""
        sec, typ, form, cap = get("节"), get("内容类型"), get("形式"), get("标题")
        planned_sections.add(sec)
        if sec:
            for s in s3_sections:
                if (sec in s) or (s and s in sec):
                    planned_sections.add(s)
        if not typ or not re.fullmatch(r"T\d+", typ):
            r.err(f"节「{sec}」内容类型缺失/非法：「{typ}」")
            continue
        if typ not in VALID_TYPES:
            r.err(f"节「{sec}」类型 {typ} 不在目录 T1–T12")
        form_l = form.lower()
        if typ in NEEDS_ECHARTS and not any(h in form_l or h in form for h in ECHARTS_HINT):
            r.err(f"节「{sec}」{typ} 数据图未走 ECharts：「{form}」")
        if typ in NEEDS_MERMAID and not any(h in form_l or h in form for h in MERMAID_HINT):
            r.err(f"节「{sec}」{typ} 结构图未走 Mermaid：「{form}」")
        if typ in NEEDS_ECHARTS or "echarts" in form_l:
            data_rows += 1
            if not cap or cap.startswith("待") or cap == "（无）":
                r.err(f"节「{sec}」数据图缺结论式标题草案")
        if any(k in form for k in ("段落", "文字", "callout", "清单")) and typ not in TEXT_TYPES:
            r.err(f"节「{sec}」纯文字形式配了 {typ}（文字只属 T10/T11）")
    for f in sorted(set(re.findall(r"F-\d+", md)) - f_ids):
        r.err(f"{f} 不在 02 事实台账（悬空引用）")
    for s in s3_sections:
        if s and s not in planned_sections:
            r.err(f"03 节「{s}」在 04 无形式规划", error=False)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ws = Path(sys.argv[1])
    wanted = {int(a) for a in sys.argv[2:] if a.isdigit()} or {1, 2, 3, 4}

    def load(prefix: str) -> str:
        hits = sorted(ws.glob(f"{prefix}-*.md"))
        return hits[0].read_text(encoding="utf-8") if hits else ""

    md1, md2, md3, md4 = load("01"), load("02"), load("03"), load("04")
    reports: list[Report] = []

    d_ids: set[str] = set()
    if 1 in wanted:
        r = Report("S1")
        if not md1:
            r.err("01-写作情境.md 不存在")
        else:
            d_ids = stage1(md1, r)
        reports.append(r)
    f_ids: set[str] = set()
    if 2 in wanted:
        r = Report("S2")
        if not md2:
            r.err("02-事实台账.md 不存在")
        else:
            f_ids = stage2(md2, r)
        reports.append(r)
    s3_sections: list[str] = []
    if 3 in wanted:
        r = Report("S3")
        if not md3:
            r.err("03-故事线.md 不存在")
        else:
            if not d_ids and md1:
                d_ids = set(re.findall(r"D-\d+", md1))
            if not f_ids and md2:
                f_ids = set(re.findall(r"F-\d+", md2))
            stage3(md3, r, d_ids, f_ids)
            t = find_table(md3, "message") or find_table(md3, "节名")
            if t:
                s3_sections = [row[0] for row in t[1:] if row and row[0]]
        reports.append(r)
    if 4 in wanted:
        r = Report("S4")
        if not md4:
            r.err("04-表达形式清单.md 不存在")
        else:
            if not f_ids and md2:
                f_ids = set(re.findall(r"F-\d+", md2))
            stage4(md4, r, f_ids, s3_sections)
        reports.append(r)

    total_e = total_w = 0
    for r in reports:
        for line in r.lines:
            print(line)
        total_e += r.errors
        total_w += len(r.lines) - r.errors
    print(f"— {'PASS' if not total_e else 'FAIL'}: {total_e} ERROR / {total_w} WARN")
    return 1 if total_e else 0


if __name__ == "__main__":
    sys.exit(main())
