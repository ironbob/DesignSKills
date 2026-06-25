#!/usr/bin/env python3
"""Validate the outline.md render for book-talk-planner.

检查 outline.md（outline.json 的人读渲染）的**结构完整性**：

  R-META    frontmatter 六项（book/input_mode/form/verdict/viral_potential/topic_count）
  R-SEL     含「可讲性判断」段
  R-IDH     `### T\\d+ ·` 选题标题数量 == frontmatter.topic_count
  R-COVER   distinct 视角 ≥ 3（从「视角」行的 angle id 计）
  R-CRED    出现「可信度」处须有 [credible]/[uncertain]/[unverified] 标记
  R-BANNED  无 banned / placeholder 词

json↔md 的 id/计数对账由 validate_contract.py 负责。有 ERROR 或 WARNING 通过率 <80% 退出非 0。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FRONT_FIELDS = ("book", "input_mode", "form", "verdict", "viral_potential", "topic_count")
BANNED_RE = re.compile(r"TBD|TODO|FIXME|待定|待补|占位|适当处理|后续再说|xxx", re.IGNORECASE)
TOPIC_HEAD = re.compile(r"^###\s+(T\d+)\s*·", re.MULTILINE)
ANGLE_IN_LINE = re.compile(r"视角.*?（`([a-z][a-z0-9-]*)`）")
CRED_MARK = re.compile(r"\[(credible|uncertain|unverified)\]")


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

    def ok_or(self, rule: str, cond: bool, msg_ok: str, msg_err: str, warn: bool = False) -> None:
        if cond:
            self.ok(rule, msg_ok)
        elif warn:
            self.warn(rule, msg_err)
        else:
            self.err(rule, msg_err)


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip("\"'")
    return fm


def validate(text: str) -> Report:
    r = Report()

    # ---- R-BANNED ----
    hits = BANNED_RE.findall(text)
    if hits:
        r.err("R-BANNED", f"banned/placeholder 命中 {hits}")
    else:
        r.ok("R-BANNED", "无 banned/placeholder")

    # ---- R-META frontmatter ----
    fm = parse_frontmatter(text)
    miss = [k for k in FRONT_FIELDS if k not in fm or fm[k] == ""]
    r.ok_or("R-META", not miss, f"frontmatter 齐全（{len(FRONT_FIELDS)} 项）", f"frontmatter 缺：{miss}")

    # ---- R-SEL ----
    r.ok_or("R-SEL", "可讲性判断" in text, "含可讲性判断段", "缺「## 一、可讲性判断」段")

    # ---- R-IDH topic headings vs topic_count ----
    heads = TOPIC_HEAD.findall(text)
    tc = fm.get("topic_count", "")
    try:
        tc_int = int(tc)
    except ValueError:
        tc_int = None
    if tc_int is not None:
        r.ok_or("R-IDH", len(heads) == tc_int,
                f"选题标题 {len(heads)} == topic_count {tc_int}",
                f"选题标题 {len(heads)} ≠ frontmatter.topic_count {tc_int}")
    else:
        r.warn("R-IDH", f"frontmatter.topic_count 非整数 {tc!r}，跳过计数核对")

    # ---- R-COVER distinct angles ----
    angles = set()
    for line in text.splitlines():
        m = ANGLE_IN_LINE.search(line)
        if m:
            angles.add(m.group(1))
    r.ok_or("R-COVER", len(angles) >= 3,
            f"distinct 视角 {len(angles)}（≥3）",
            f"distinct 视角仅 {len(angles)} < 3")

    # ---- R-CRED ----
    if "可信度" in text:
        marks = CRED_MARK.findall(text)
        r.ok_or("R-CRED", len(marks) > 0,
                f"可信度标记 {len(marks)} 处", "有「可信度」段但无 [credible]/[uncertain]/[unverified] 标记")
    else:
        r.ok("R-CRED", "无可信度敏感论断，跳过")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a book-talk-planner outline.md")
    ap.add_argument("doc", type=Path, help="Path to outline.md")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2
    text = args.doc.read_text(encoding="utf-8")

    r = validate(text)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_render: {args.doc} ===")
    for line in r.errors + r.warns + r.passed:
        print(line)
    print(f"\nERROR: {len(r.errors)}  WARNING: {len(r.warns)}  PASSED: {len(r.passed)}")
    print(f"WARNING 通过率: {wp * 100:.0f}%  质量分: {quality * 100:.0f}%")

    if r.errors or wp < 0.80:
        print("\n结果：不合格")
        return 1
    print("\n结果：合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
