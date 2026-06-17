#!/usr/bin/env python3
"""Validate a code-analyze-business test-case document.

Parses the YAML front-matter (requires PyYAML) and the Markdown body, then runs
the rules mirrored in references/test-case-generation.md:
  R-F  front-matter required fields (incl. total_cases + by_type)
  R-L  every TC-<MODULE>-<n> case backlinks a file:line in Expected Result
  R-C  all three types present (Happy Path / Error Flow / Edge Case), each ≥1
  R-B  banned words (0 hit)
  R-U  total_cases + by_type meta match the actual case counts in the body
Exits non-zero when any ERROR fails or the WARNING pass rate < 80%.

NOTE: this script only checks format & coverage, NOT whether a file:line truly
exists or whether a case truly exercises the right behavior. Real depth is
human review.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_META = (
    "business", "title", "analyzed_at", "status",
    "source_analysis", "source_requirements",
    "total_cases", "by_type",
)

# path.ext:line  or  path.ext:line-line
LINK_RE = re.compile(r"[\w/.-]+\.\w+:\d+(?:-\d+)?")

BANNED = [
    "体验好", "功能完善", "功能强大", "适当处理", "待定", "待补",
    "后续再说", "良好体验", "非常重要", "很关键", "等等", "TBD", "TODO",
]
BANNED_RE = re.compile("|".join(re.escape(w) for w in BANNED))

# a test-case heading: ### TC-REFUND-01: ...
TC_RE = re.compile(r"^###\s+TC-([A-Z]+)-(\d+)", re.M)
TYPE_RE = re.compile(r"\*\*Type:\*\*\s*(Happy Path|Error Flow|Edge Case)")
TYPES = ("Happy Path", "Error Flow", "Edge Case")
TYPE_KEY = {"Happy Path": "happy", "Error Flow": "error", "Edge Case": "edge"}


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

    # ---- R-L2 TC heading id shape (R-L1 anchor check retired → validate_test_cases_json.py) ----
    tc_secs = [(t, c) for t, c in secs if t.startswith("TC-")]
    if not tc_secs:
        r.err("R-L2", "未找到任何用例（标题须为 ### TC-<MODULE>-<n>: ...）")
    else:
        bad_id = [t for t, _ in tc_secs if not re.match(r"TC-[A-Z]+-\d+", t.split(":")[0])]
        if bad_id:
            r.err("R-L2", f"用例标题格式不符 TC-<MODULE>-<n>：{bad_id[:3]}")
        else:
            r.ok("R-L2", f"{len(tc_secs)} 个用例 ID 格式正确")

        # ---- R-L3 Expected Result 应为业务断言，file:line 放独立实现锚点行（soft）----
        code_in_er = []
        for t, c in tc_secs:
            for ln in c.splitlines():
                s = ln.strip()
                if s.startswith("**Expected Result:**") and LINK_RE.search(s):
                    code_in_er.append(t.split(":")[0])
                    break
        if code_in_er:
            r.warn("R-L3", f"{len(code_in_er)} 个用例的 Expected Result 行含 file:line（应改业务断言，代码放独立实现锚点行）：{code_in_er[:5]}")
        else:
            r.ok("R-L3", "Expected Result 均为业务断言")

    # ---- type counts (R-C1 global-type check retired → validate_contract.py XC-C2;
    #      counts retained for the R-U reconciliation below) ----
    type_counts = {t: 0 for t in TYPES}
    for m in TYPE_RE.finditer(body):
        type_counts[m.group(1)] = type_counts.get(m.group(1), 0) + 1

    # ---- R-B banned words ----
    hits = BANNED_RE.findall(body)
    if hits:
        r.err("R-B1", f"正文含 banned 词：{sorted(set(hits))}")
    else:
        r.ok("R-B1")

    # ---- R-U total_cases + by_type meta vs actual ----
    actual = {TYPE_KEY[t]: type_counts[t] for t in TYPES}
    tc_total = len(tc_secs)
    total = meta.get("total_cases")
    by_type = meta.get("by_type") or {}
    if not isinstance(by_type, dict):
        by_type = {}
    try:
        total_num = int(total) if total is not None else None
    except (ValueError, TypeError):
        total_num = None
        r.warn("R-U1", f"total_cases={total} 非整数")
    mismatch = []
    if total_num is not None and total_num != tc_total:
        mismatch.append(f"total_cases={total_num} 与实际 {tc_total} 不符")
    for k in ("happy", "error", "edge"):
        if k in by_type and by_type[k] != actual[k]:
            mismatch.append(f"by_type.{k}={by_type[k]} 与实际 {actual[k]} 不符")
    if mismatch:
        r.warn("R-U1", "；".join(mismatch))
    else:
        r.ok("R-U1", f"总数 {tc_total}、分布 {actual} 一致")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a code-analyze-business test-case doc")
    ap.add_argument("doc", type=Path, help="Path to the test-cases .md")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2

    r = validate(args.doc)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_test_cases: {args.doc} ===")
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
