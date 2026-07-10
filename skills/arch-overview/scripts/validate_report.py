#!/usr/bin/env python3
"""Validate the overview.md for arch-overview.

``overview.md`` is the human-readable render of ``overview.json``; this gate
checks its *format & coverage*. It does NOT verify a file:line truly exists
(that is validate_evidence.py's job).

  R-F     front-matter required fields
  R-GRADE overall_grade valid
  R-DIM   4 dimension sections present (layering / cohesion / extensibility / readability)
  R-DIAG  3 view sections present. Mermaid block count is checked against JSON
          applicability by validate_contract.py.
  R-IND   industry-practice declarations: "LLM内置经验" appears ≥4 (once per dimension)
          + "未核对" + "延伸阅读" present
  R-HR    亮点 + 风险 sections present
  R-L     backlink (file:line) coverage ≥ 3 distinct anchors
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
    "target", "title", "scope_level", "languages", "analyzed_at",
    "covered_files", "overall_grade", "grade_layering", "grade_cohesion",
    "grade_extensibility", "grade_readability", "open_questions",
)
GRADES = {"优", "良", "中", "差"}

LINK_RE = re.compile(r"[\w/.-]+\.\w+:\d+(?:-\d+)?")
MERMAID_RE = re.compile(r"```mermaid\b", re.I)

BANNED = [
    "体验好", "功能完善", "功能强大", "适当处理", "待定", "待补",
    "后续再说", "良好体验", "非常重要", "很关键", "等等", "TBD", "TODO",
]
BANNED_RE = re.compile("|".join(re.escape(w) for w in BANNED))

DIM_KEYWORDS = [
    ("layering", ["分层", "依赖方向"]),
    ("cohesion", ["职责内聚", "内聚", "边界"]),
    ("extensibility", ["可扩展"]),
    ("readability", ["可读性", "命名表意", "命名"]),
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

    # ---- R-F front-matter ----
    miss = [k for k in REQUIRED_META if meta.get(k) in (None, "")]
    if miss:
        r.err("R-F1", f"front-matter 缺必填字段：{miss}")
    else:
        r.ok("R-F1")

    # ---- R-GRADE ----
    grade = meta.get("overall_grade")
    if grade in GRADES:
        r.ok("R-GRADE1", f"overall_grade={grade}")
    else:
        r.err("R-GRADE1", f"overall_grade 非法：{grade!r}（须 优/良/中/差）")

    # ---- R-DIM 4 dimension sections ----
    miss_dim = [k for k, kws in DIM_KEYWORDS if not any(kw in body for kw in kws)]
    if miss_dim:
        r.err("R-DIM1", f"缺维度章节/关键词：{miss_dim}（须 4 维全覆盖）")
    else:
        r.ok("R-DIM1", "4 维章节齐全")

    # ---- R-DIAG 3 view sections ----
    n_mermaid = len(MERMAID_RE.findall(body))
    if n_mermaid <= 3:
        r.ok("R-DIAG1", f"{n_mermaid} 个 mermaid 块；适用性由契约门对账")
    else:
        r.err("R-DIAG1", f"mermaid 块过多：{n_mermaid}（每视角最多一个）")
    view_kw = {
        "视角①分层/模块依赖": ["分层", "模块依赖"],
        "视角②C4/Container": ["C4", "Container", "Component"],
        "视角③运行时/数据流": ["运行时", "时序", "数据流", "sequenceDiagram"],
    }
    miss_view = [name for name, kws in view_kw.items() if not any(kw in body for kw in kws)]
    if miss_view:
        r.err("R-DIAG2", f"缺视角关键词：{miss_view}")
    else:
        r.ok("R-DIAG2", "3 视角关键词齐全")

    # ---- R-IND industry-practice provenance ----
    n_prov = len(re.findall(r"LLM内置经验", body))
    if n_prov >= 4:
        r.ok("R-IND1", f"LLM内置经验 出现 {n_prov} 次（≥4，每维一次）")
    elif n_prov >= 1:
        r.warn("R-IND1", f"LLM内置经验 仅 {n_prov} 次（建议每维度业界对照各声明一次）")
    else:
        r.err("R-IND1", "正文未声明 provenance「LLM内置经验」（业界做法须声明来源）")
    if "未核对" in body:
        r.ok("R-IND2", "含「未核对」核对状态声明")
    else:
        r.err("R-IND2", "业界做法须声明「未核对」（未核对原文）")
    if "延伸阅读" in body:
        r.ok("R-IND3", "含「延伸阅读」方向")
    else:
        r.warn("R-IND3", "建议附「延伸阅读」方向供自行核实")

    # ---- R-HR 亮点 + 风险 sections ----
    has_hl = "亮点" in body
    has_risk = "风险" in body
    if has_hl:
        r.ok("R-HR1", "含亮点章节")
    else:
        r.err("R-HR1", "缺「亮点」章节")
    if has_risk:
        r.ok("R-HR2", "含风险章节")
    else:
        r.err("R-HR2", "缺「风险」章节")

    # ---- R-L backlink coverage ----
    n_links = len(set(LINK_RE.findall(body)))
    if n_links >= 3:
        r.ok("R-L1", f"{n_links} 个不同回链锚点")
    else:
        r.err("R-L1", f"唯一回链不足：{n_links}（要求 ≥3 个 file:line 锚点）")

    # ---- R-B banned words ----
    hits = BANNED_RE.findall(body)
    if hits:
        r.err("R-B1", f"正文含 banned 词：{sorted(set(hits))}")
    else:
        r.ok("R-B1")

    # ---- R-U unconfirmed vs gaps ----
    uc = len(re.findall(r"⚠\s*未确认", body))
    oq = meta.get("open_questions")
    has_gap = "已知缺口" in body
    if uc == 0:
        r.ok("R-U1", "无 ⚠ 未确认")
    elif not has_gap:
        r.warn("R-U1", "正文有 ⚠ 未确认 但缺「已知缺口」节")
    else:
        r.ok("R-U1", f"{uc} 处未确认，有已知缺口节")
    try:
        if oq is not None and int(oq) != uc:
            r.warn("R-U1", f"open_questions={oq} 与正文 ⚠ 未确认 {uc} 处不一致")
    except (ValueError, TypeError):
        pass

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate an arch-overview overview.md")
    ap.add_argument("doc", type=Path, help="Path to the overview .md")
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
