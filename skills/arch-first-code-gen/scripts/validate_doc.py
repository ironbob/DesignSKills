#!/usr/bin/env python3
"""Validate the <feature>-arch.md render for arch-first-code-gen.

``<feature>-arch.md`` is the human-readable render of ``design-contract.json``;
this gate checks its *format & coverage* (pure stdlib, flat front-matter — no
PyYAML dependency). It does NOT check file existence or cross-check the contract
(that is ``validate_gate.py``'s job).

  R-F    flat front-matter required fields
  R-V    verdict ∈ {go, no-go}
  R-S    「模块结构图」section + a ```mermaid block
  R-F2   「业务流程图」section + a ```mermaid block
  R-R    「角色职责清单」section present; table data rows ≥ frontmatter roles_count
  R-D    「设计依据」section present; every role in the 角色职责 table has a
         设计依据 mention + a 原则 keyword (设计可追溯, PRD §4-D P0)
  R-B    banned words (0 hit)
  R-U    frontmatter open_questions vs 「已知缺口/未决」section bullets

Exits non-zero on ERROR or WARNING pass rate < 80%.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_META = (
    "feature", "title", "stack", "analyzed_at", "roles_count",
    "process_steps", "verdict", "open_questions",
)

BANNED = [
    "体验好", "功能完善", "功能强大", "适当处理", "待定", "待补",
    "后续再说", "良好体验", "非常重要", "很关键", "等等", "TBD", "TODO",
]
BANNED_RE = re.compile("|".join(re.escape(w) for w in BANNED))

PRINCIPLE_KW = ("原则", "SRP", "OCP", "LSP", "ISP", "DIP", "聚合", "DDD",
                "内聚", "依赖方向", "关注点分离", "Tell-Don't-Ask")


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


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}, text
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, text[m.end():]


def section_body(body: str, keyword: str) -> str:
    """Return the body under the first header whose title contains keyword.

    The section ends at the next header of the SAME or HIGHER level (so ###
    subsections inside a ## section are included, not treated as terminators).
    """
    heads = [(m.start(), len(m.group(1)), m.group(2))
             for m in re.finditer(r"^(#{2,6})\s+(.+?)\s*$", body, re.M)]
    for i, (s, lvl, t) in enumerate(heads):
        if keyword in t:
            e = len(body)
            for (s2, lvl2, _t2) in heads[i + 1:]:
                if lvl2 <= lvl:
                    e = s2
                    break
            return body[s:e]
    return ""


def table_roles(body: str) -> list[str]:
    """First-cell names from the first markdown table under 角色职责清单."""
    sec = section_body(body, "角色职责")
    if not sec:
        return []
    names: list[str] = []
    for ln in sec.splitlines():
        if not ln.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if set(first) <= set("-: ") or first in ("角色", "Role", ""):
            continue
        names.append(first)
    return names


def validate(path: Path) -> Report:
    text = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(text)
    r = Report()

    # ---- R-F front-matter ----
    miss = [k for k in REQUIRED_META if meta.get(k) in (None, "")]
    r.err("R-F1", f"front-matter 缺必填字段：{miss}") if miss else r.ok("R-F1")

    # ---- R-V verdict ----
    verdict = meta.get("verdict", "").strip().lower()
    if verdict in ("go", "no-go"):
        r.ok("R-V1", f"verdict={verdict}")
    else:
        r.err("R-V1", f"verdict 非法：{meta.get('verdict')!r}（须 go / no-go）")

    # ---- R-S 结构图 + mermaid ----
    struct_sec = section_body(body, "结构图")
    if not struct_sec.strip():
        r.err("R-S1", "缺「模块结构图」章节")
    elif "```mermaid" not in struct_sec:
        r.err("R-S1", "「模块结构图」缺 mermaid 代码块")
    else:
        r.ok("R-S1", "结构图 + mermaid 齐全")

    # ---- R-F2 流程图 + mermaid ----
    flow_sec = section_body(body, "流程图")
    if not flow_sec.strip():
        r.err("R-F2", "缺「业务流程图」章节")
    elif "```mermaid" not in flow_sec:
        r.err("R-F2", "「业务流程图」缺 mermaid 代码块")
    else:
        r.ok("R-F2", "流程图 + mermaid 齐全")

    # ---- R-R 角色职责清单 table ----
    role_names = table_roles(body)
    try:
        want = int(meta.get("roles_count", 0))
    except ValueError:
        want = 0
    if not section_body(body, "角色职责").strip():
        r.err("R-R1", "缺「角色职责清单」章节")
    elif len(role_names) < want:
        r.err("R-R1", f"角色职责表数据行 {len(role_names)} < frontmatter roles_count={want}")
    else:
        r.ok("R-R1", f"角色职责表 {len(role_names)} 行（≥ roles_count={want}）")

    # ---- R-D 设计依据 per role ----
    design_sec = section_body(body, "设计依据")
    if not design_sec.strip():
        r.err("R-D1", "缺「设计依据」章节（PRD §4-D P0：设计可追溯）")
    else:
        missing = [n for n in role_names if n not in design_sec]
        if missing:
            r.err("R-D1", f"以下角色在「设计依据」节无说明：{missing}")
        elif not any(kw in design_sec for kw in PRINCIPLE_KW):
            r.err("R-D1", "「设计依据」节未出现任何设计原则关键字（须点名 SRP/DDD/…）")
        else:
            r.ok("R-D1", f"设计依据齐全（{len(role_names)} 角色均有点评 + 原则）")

    # ---- R-B banned words ----
    hits = BANNED_RE.findall(body)
    r.err("R-B1", f"正文含 banned 词：{sorted(set(hits))}") if hits else r.ok("R-B1")

    # ---- R-U open_questions vs 已知缺口 ----
    try:
        oq = int(meta.get("open_questions", 0))
    except ValueError:
        oq = None
    gap_sec = section_body(body, "已知缺口")
    if not gap_sec.strip():
        gap_sec = section_body(body, "未决")
    gap_items = len(re.findall(r"^\s*-\s+", gap_sec, re.M)) if gap_sec.strip() else 0
    if oq in (None, 0):
        r.ok("R-U1", "open_questions=0，无需缺口节")
    elif gap_items < oq:
        r.warn("R-U1", f"open_questions={oq} 但「已知缺口/未决」仅 {gap_items} 条")
    else:
        r.ok("R-U1", f"open_questions={oq}，缺口节 {gap_items} 条（≥ 声明数）")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate an arch-first-code-gen arch.md render")
    ap.add_argument("doc", type=Path, help="Path to the <feature>-arch.md")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2

    r = validate(args.doc)
    total = len(r.errors) + len(r.warns) + len(r.passed)
    denom = len(r.passed) + len(r.warns)
    wp = len(r.passed) / denom if denom else 1.0
    quality = len(r.passed) / total if total else 0.0

    print(f"=== validate_doc: {args.doc} ===")
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
