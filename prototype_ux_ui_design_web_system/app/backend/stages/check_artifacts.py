#!/usr/bin/env python3
"""Artifact integrity gate for ui-prototype-gen HTML outputs.

Three checks, all earned the hard way on a real project:
  TAG    div/span open/close balance (a stray </div> breaks a whole frame)
  CANVAS files that define a .frame rule must lock BOTH its width and height
         to the project canvas (default mobile 390x844; adaptive size hides
         density/overflow problems and misplaces overlays)
  COPY   banned-copy sweep over visible text (欢迎/示例/占位/lorem/... exist
         only when the model hedges by addition)

Usage: check_artifacts.py <path>... [--canvas-width 390] [--canvas-height 844]
       canvas args = the project's target canvas (web tool passes the locked
       platform preset); standalone skill defaults to mobile 390x844.
Exit:  0 all green, 1 any ERROR, 2 nothing to check.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 负面文案清单：与 references/html-conventions.md §4 一一对应，改任何一侧必须
# 同步另一处（scripts/test_check_artifacts.py 有配平断言防再漂移）。
BANNED_COPY = [
    "欢迎", "欢迎使用", "本页面", "本页用于", "该页面", "示例文本", "示例：",
    "占位", "待补充", "待填写", "lorem", "ipsum", "TODO", "FIXME",
    "点击这里", "此处显示", "xxx", "XXX", "???", "测试数据", "假数据",
    "这是", "以上是",
]


def strip_to_text(html: str) -> str:
    html = re.sub(r"<(script|style)\b.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r"<[^>]+>", " ", html)


def _locked(css_rule: str, prop: str, value: int) -> bool:
    """规则里存在 `prop:value px` 声明（min-/max- 前缀不冒充锁定值）。"""
    decl = re.sub(r"\s+", "", css_rule)
    return re.search(rf"(?<![a-zA-Z-]){prop}:{value}px(?![0-9])", decl) is not None


def check_file(path: Path, canvas_w: int, canvas_h: int) -> list[str]:
    problems: list[str] = []
    try:
        html = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"[IO] {path.name}: {exc}"]

    # TAG — balance of container tags
    for tag in ("div", "span"):
        opens = len(re.findall(rf"<{tag}[\s>]", html))
        closes = len(re.findall(rf"</{tag}>", html))
        if opens != closes:
            problems.append(f"[TAG] {path.name}: <{tag}> {opens} open / {closes} close")

    # CANVAS — only applies when the file defines screen frames (.frame rules)
    css = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    if css and re.search(r"\.frame\s*\{", css.group(1)):
        rule = re.search(r"\.frame\s*\{[^}]*\}", css.group(1))
        missing = [
            f"{prop}:{value}px"
            for prop, value in (("width", canvas_w), ("height", canvas_h))
            if rule is None or not _locked(rule.group(0), prop, value)
        ]
        if missing:
            problems.append(f"[CANVAS] {path.name}: .frame 未锁定 " + " / ".join(missing))

    # COPY — banned words over visible text (case-insensitive for latin)
    text = strip_to_text(html)
    low = text.lower()
    for word in BANNED_COPY:
        if word.lower() in low:
            problems.append(f"[COPY] {path.name}: 命中负面清单 '{word}'")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="HTML artifact gate: tag/canvas/copy")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--canvas-width", type=int, default=390, help="项目目标画布宽（默认 390=手机）")
    parser.add_argument("--canvas-height", type=int, default=844, help="项目目标画布高（默认 844=手机）")
    args = parser.parse_args()

    files: list[Path] = []
    for p in args.paths:
        if p.is_dir():
            files += sorted(p.glob("*.html"))
        elif p.is_file() and p.suffix == ".html":
            files.append(p)
        else:
            print(f"[IO] 跳过非 HTML 路径: {p}", file=sys.stderr)
    if not files:
        print("[IO] 没有 HTML 文件可检查", file=sys.stderr)
        return 2

    all_problems: list[str] = []
    for f in files:
        all_problems += check_file(f, args.canvas_width, args.canvas_height)

    for line in all_problems:
        print(line)
    status = "PASS" if not all_problems else "FAIL"
    print(f"— {status}: {len(files)} 个文件，{len(all_problems)} 处问题")
    return 1 if all_problems else 0


if __name__ == "__main__":
    sys.exit(main())
