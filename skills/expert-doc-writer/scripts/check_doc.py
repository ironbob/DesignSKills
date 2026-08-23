#!/usr/bin/env python3
"""Doc artifact gate for expert-doc-writer outputs.

Two source modes. HTML mode (--html, default for .html) is the legacy
hand-written single-file target; MD mode (--md, for .md) checks the
VitePress chassis sources (section md + component data):

  WALL   text-wall paragraphs: >300c ERROR / >180c WARN; ordered
         connectors (首先/然后/接着/最后/...) >=3 in one paragraph ->
         ERROR (flow narration belongs in a Mermaid diagram)
  CHART  numeric-dense paragraph (>=5 ERROR / >=3 WARN) with no visual
         component nearby -> numbers as prose belong in a chart
  FIG    [HTML] figure needs conclusion-style figcaption + .figure-source;
         [MD] every <FigureChart> needs caption=/source=/fallback= and a
         non-neutral caption
  SRC    mermaid fences balanced (parity + brackets + quotes);
         [HTML] .figure-chart needs data-kind + fallback text
  NAV    [HTML] TOC anchors resolve; [MD] {#anchor} unique, @include
         targets exist
  COPY   banned-copy sweep (hedge/placeholder words)
  TAG    [HTML only] div/span/section/figure balance

Usage: check_doc.py <path>... [--md|--html] [--lite] [--strict]
Exit:  0 pass (no ERROR), 1 any ERROR, 2 nothing to check.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BANNED_COPY = [
    "欢迎查阅", "本文将介绍", "本文将阐述", "综上所述", "示例数据", "假数据",
    "示例：", "占位", "待补充", "待填写", "lorem", "ipsum", "TODO", "FIXME",
    "xxx", "???", "此处省略", "以上是",
]

NEUTRAL_CAPTION = [
    re.compile(r"^(图|表)\s*\d"),
    re.compile(r"(对比|趋势|统计|分布|情况|示意|概览)$"),
]

# ordered flow connectors: three or more in one paragraph = flow narration
FLOW_CONNECTORS = re.compile(r"首先|然后|接着|其次|随后|紧接着|下一步|最后|第[一二三四五六七八九十]+步")

# dates/times are not data numbers: strip before counting
DATE_PATTERNS = [
    re.compile(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}"),
    re.compile(r"\d{4}\s*年(度)?"),
    re.compile(r"\d{1,2}:\d{2}(:\d{2})?"),
    re.compile(r"[FDPGU]-\d+"),          # ledger ids are refs, not data
    re.compile(r"[T]-?\d+"),              # type ids
]
NUMBER = re.compile(r"\d+(?:\.\d+)?")
PROXIMITY = 600  # chars around a paragraph to look for a figure/table


def strip_tags(fragment: str) -> str:
    txt = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"<[^>]+>", " ", txt)


def count_data_numbers(text: str) -> int:
    for pat in DATE_PATTERNS:
        text = pat.sub(" ", text)
    return len(NUMBER.findall(text))


def check_file(path: Path, lite: bool) -> list[str]:
    problems: list[str] = []
    try:
        html = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"[IO] {path.name}: {exc}"]

    def err(code: str, msg: str, error: bool = True) -> None:
        problems.append(f"[{code}]{' ERROR' if error else ' WARN'} {path.name}: {msg}")

    # TAG — container balance
    for tag in ("div", "span", "section", "figure", "figcaption"):
        opens = len(re.findall(rf"<{tag}[\s>]", html))
        closes = len(re.findall(rf"</{tag}>", html))
        if opens != closes:
            err("TAG", f"<{tag}> {opens} open / {closes} close")

    # COPY — banned words over visible text
    low = strip_tags(html).lower()
    for word in BANNED_COPY:
        if word.lower() in low:
            err("COPY", f"命中负面清单 '{word}'")

    if lite:
        return problems

    # WALL + CHART — per <p> prose discipline
    for m in re.finditer(r"<p\b[^>]*>(.*?)</p>", html, flags=re.DOTALL | re.IGNORECASE):
        text = strip_tags(m.group(1)).strip()
        if not text:
            continue
        if len(text) > 300:
            err("WALL", f"段落 {len(text)} 字（>{300}）：「{text[:24]}…」")
        elif len(text) > 180:
            err("WALL", f"段落 {len(text)} 字（>{180}）：「{text[:24]}…」", error=False)
        flows = len(FLOW_CONNECTORS.findall(text))
        if flows >= 3:
            err("WALL", f"流程叙述（{flows} 个顺序连接词）：「{text[:24]}…」应转 Mermaid 流程图")
        nums = count_data_numbers(text)
        if nums >= 3:
            nearby = html[max(0, m.start() - PROXIMITY): m.end() + PROXIMITY]
            # visual anchors: figures/tables plus HTML visual components (KPI row, matrix, timeline)
            has_visual = any(marker in nearby for marker in
                             ("<figure", "<table", "kpi-row", "class=\"matrix", "class=\"timeline"))
            if not has_visual:
                err("CHART", f"段落含 {nums} 个数值且邻近无图/表：「{text[:24]}…」",
                    error=nums >= 5)

    # FIG — figure furniture
    for m in re.finditer(r"<figure\b[^>]*>(.*?)</figure>", html, flags=re.DOTALL | re.IGNORECASE):
        inner = m.group(1)
        cap = re.search(r"<figcaption\b[^>]*>(.*?)</figcaption>", inner, flags=re.DOTALL | re.IGNORECASE)
        if not cap:
            err("FIG", "figure 缺 figcaption（结论式标题）")
        else:
            cap_text = strip_tags(cap.group(1)).strip()
            if not cap_text:
                err("FIG", "figcaption 为空")
            elif any(p.search(cap_text) for p in NEUTRAL_CAPTION):
                err("FIG", f"中性图题「{cap_text}」→ 应为结论式标题", error=False)
        if "figure-source" not in inner:
            err("FIG", "figure 缺 .figure-source 来源/口径脚注", error=False)

    # SRC — diagram/chart containers
    for m in re.finditer(r'<pre[^>]*class="[^"]*mermaid[^"]*"[^>]*>(.*?)</pre>', html, flags=re.DOTALL | re.IGNORECASE):
        block = m.group(1)
        for op, cl in (("(", ")"), ("[", "]"), ("{", "}")):
            if block.count(op) != block.count(cl):
                err("SRC", f"mermaid 块 {op}{cl} 不配平")
        if block.count('"') % 2:
            err("SRC", "mermaid 块引号不配平")

    for m in re.finditer(r'<div[^>]*class="[^"]*figure-chart[^"]*"[^>]*>(.*?)</div>', html, flags=re.DOTALL | re.IGNORECASE):
        inner = strip_tags(m.group(1)).strip()
        tag = m.group(0)
        if "data-kind" not in tag:
            err("SRC", "figure-chart 缺 data-kind（图型统计依据）", error=False)
        fallback = re.sub(r'<pre\b.*?</pre>', " ", m.group(1), flags=re.DOTALL | re.IGNORECASE)
        if len(strip_tags(fallback).strip()) < 4:
            err("SRC", "figure-chart 缺降级文本（JS 失败/打印时空白）")

    # NAV — toc anchors resolve
    ids = re.findall(r'id="([^"]+)"', html)
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        err("NAV", f"重复 id: {sorted(dup)}")
    for href in re.findall(r'href="#([^"]+)"', html):
        if href and href not in ids:
            err("NAV", f"锚点 #{href} 无对应 id")

    return problems


MD_VISUAL_HINTS = ("<FigureChart", "<KpiRow", "<CompareMatrix", "```mermaid", "<table", "| ---", "|---")
MD_PROSE_SKIP = ("#", "|", "<", "`", "-", "!", ">", "<!--", "[!")

def check_md_file(path: Path, lite: bool, anchors: dict) -> list[str]:
    problems: list[str] = []
    try:
        md = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"[IO] {path.name}: {exc}"]

    def err(code: str, msg: str, error: bool = True) -> None:
        problems.append(f"[{code}]{' ERROR' if error else ' WARN'} {path.name}: {msg}")

    # COPY over all text
    low = md.lower()
    for word in BANNED_COPY:
        if word.lower() in low:
            err("COPY", f"命中负面清单 '{word}'")

    if lite:
        return problems

    lines = md.splitlines()

    # NAV — unique anchors + @include targets exist
    for a in re.findall(r"\{#([^}]+)\}", md):
        if a in anchors:
            err("NAV", f"锚点 #{a} 重复（{anchors[a]} 已用）")
        anchors[a] = path.name
    for inc in re.findall(r"@include:\s*(\S+?)\s*-->", md):
        if not (path.parent / inc).exists():
            err("NAV", f"@include 目标不存在: {inc}")

    # SRC — mermaid fence parity + inner balance
    fences = re.findall(r"```mermaid\n(.*?)```", md, flags=re.DOTALL)
    if len(re.findall(r"```mermaid", md)) != len(fences):
        err("SRC", "mermaid 代码围栏未闭合")
    for block in fences:
        for op, cl in (("(", ")"), ("[", "]"), ("{", "}")):
            if block.count(op) != block.count(cl):
                err("SRC", f"mermaid 块 {op}{cl} 不配平")
        if block.count('"') % 2:
            err("SRC", "mermaid 块引号不配平")

    # FIG — <FigureChart> furniture
    for tag in re.findall(r"<FigureChart[\s\S]*?/>", md):
        for attr in ("caption=", "source=", "fallback="):
            if attr not in tag:
                err("FIG", f"FigureChart 缺 {attr.rstrip('=')} 属性")
        cap = re.search(r'caption="([^"]*)"', tag)
        if cap and any(p.search(cap.group(1)) for p in NEUTRAL_CAPTION):
            err("FIG", f"中性图题「{cap.group(1)}」→ 应为结论式标题", error=False)

    # WALL + CHART — prose paragraph blocks
    blocks: list[tuple[int, str]] = []
    cur: list[str] = []
    start = 0
    for i, line in enumerate(lines):
        if line.strip():
            if not cur:
                start = i
            cur.append(line)
        else:
            if cur:
                blocks.append((start, "\n".join(cur)))
                cur = []
    if cur:
        blocks.append((start, "\n".join(cur)))

    for start, block in blocks:
        first = block.lstrip()
        if any(first.startswith(s) for s in MD_PROSE_SKIP):
            continue  # headings / tables / components / code / lists
        text = re.sub(r"\{#[^}]+\}", " ", block)
        text = re.sub(r"[*_`]", " ", text).strip()
        if not text:
            continue
        if len(text) > 300:
            err("WALL", f"段落 {len(text)} 字（>300）：「{text[:24]}…」")
        elif len(text) > 180:
            err("WALL", f"段落 {len(text)} 字（>180）：「{text[:24]}…」", error=False)
        flows = len(FLOW_CONNECTORS.findall(text))
        if flows >= 3:
            err("WALL", f"流程叙述（{flows} 个顺序连接词）：「{text[:24]}…」应转 Mermaid 流程图")
        nums = count_data_numbers(text)
        if nums >= 3:
            ctx = "\n".join(lines[max(0, start - 4): start + len(block.splitlines()) + 5])
            if not any(h in ctx for h in MD_VISUAL_HINTS):
                err("CHART", f"段落含 {nums} 个数值且邻近无视觉件：「{text[:24]}…」", error=nums >= 5)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="Doc gate: tag/wall/chart/fig/src/nav/copy over HTML or MD sources")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--md", action="store_true", help="markdown/VitePress source mode")
    parser.add_argument("--lite", action="store_true", help="loose mode: COPY-only (plus TAG in HTML)")
    parser.add_argument("--strict", action="store_true", help="WARN also fails")
    args = parser.parse_args()

    suffix = ".md" if args.md else ".html"
    files: list[Path] = []
    for p in args.paths:
        if p.is_dir():
            found = p.rglob(f"*{suffix}") if args.md else p.glob(f"*{suffix}")
            files += sorted(f for f in found if "node_modules" not in f.parts)
        elif p.is_file() and p.suffix == suffix:
            files.append(p)
        else:
            print(f"[IO] 跳过非 {suffix} 路径: {p}", file=sys.stderr)
    if not files:
        print(f"[IO] 没有 {suffix} 文件可检查", file=sys.stderr)
        return 2

    all_problems: list[str] = []
    if args.md:
        anchors: dict[str, str] = {}
        for f in files:
            all_problems += check_md_file(f, args.lite, anchors)
    else:
        for f in files:
            all_problems += check_file(f, args.lite)

    for line in all_problems:
        print(line)
    errors = sum(1 for p in all_problems if " ERROR " in p or p.startswith("[IO]"))
    warns = len(all_problems) - errors
    mode = "LITE" if args.lite else "FULL"
    ok = not errors and (not args.strict or not warns)
    status = "PASS" if ok else "FAIL"
    print(f"— {status} [{mode}]: {len(files)} 个文件，{errors} ERROR / {warns} WARN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
