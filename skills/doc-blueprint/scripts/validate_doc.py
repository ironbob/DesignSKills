#!/usr/bin/env python3
"""Validate a doc-blueprint document (doc.md).

Parses the YAML front-matter (requires PyYAML, same as validate_epps.py) and the
intent-annotated Markdown body, then runs the rule table in
references/validation-rules.md:
  R-A  intent      R-S  structure   R-W  writing rules
  R-C  consistency  R-E  expressiveness
Exits non-zero when any ERROR fails or the WARNING pass rate is below 80%.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

# -- doc_type -> required section slots (mirrors doc-type-library/README.md) --
DOC_TYPE_SLOTS: dict[str, set[str]] = {
    "postmortem": {"summary", "impact", "timeline", "root_cause", "actions", "lessons"},
    "rfc": {"context", "current_state", "proposal", "alternatives", "decision", "impact"},
    "prd": {"problem", "goals", "success_metrics", "scope", "out_of_scope"},
    "adr": {"context", "decision", "rationale", "consequences"},
    "runbook": {"trigger", "precheck", "steps", "expected", "rollback", "escalation"},
    "business_case": {"opportunity", "solution", "cost", "benefit", "risk", "resources"},
    "weekly": {"done", "risks", "next", "need_help"},
    "changelog": {"change", "impact", "window", "mitigation", "contact"},
    "announcement": {"what", "impact", "status", "mitigation", "followup"},
    "meeting": {"topics", "decisions", "actions", "open_issues"},
    "article": {"problem", "solution", "repro", "pitfalls", "conclusion"},
    "custom": {"context", "core", "support", "conclusion"},
}

CHART_KINDS = {"chart:bar", "chart:line", "chart:pie"}
BLOCK_KINDS = CHART_KINDS | {"diagram", "kpi", "timeline", "callout", "status", "table", "code", "quote", "prose", "list"}
BADGE_LEVELS = {"healthy", "degraded", "down", "blocked", "done", "todo"}
CALLOUT_VARIANTS = {"note", "tip", "warning", "important", "decision"}

PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|待定|待补|之后再说|适当展开|适当处理|xxx+)\b", re.I)
SUPERLATIVE_RE = re.compile(r"(最优|最好|最佳|业界领先|遥遥领先|效果很好|性能优秀|体验极佳)")
DREF_RE = re.compile(r"\{\{d:([a-zA-Z0-9_]+)\}\}")
REF_RE = re.compile(r"\[ref:([a-zA-Z0-9_]+)\]")
BADGE_RE = re.compile(r"\[badge:([a-zA-Z0-9_]+)")
SECTION_RE = re.compile(r"<!--\s*doc:section\s+slot=([a-zA-Z0-9_]+)", re.I)


def load_meta(text: str, path: Path) -> dict[str, Any]:
    """Split front-matter and parse with PyYAML (conditional import)."""
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
    """Return the body (Markdown after front-matter)."""
    m = re.match(r"^---\s*\n.*?\n---\s*\n", text, re.S)
    return text[m.end():] if m else text


def parse_fenced_blocks(body: str) -> list[dict[str, str]]:
    """Extract fenced code blocks: [{lang, attrs(str), content}]."""
    out = []
    for m in re.finditer(r"```([^\n`]*)\n(.*?)```", body, re.S):
        info = m.group(1).strip()
        parts = info.split(None, 1)
        out.append({"lang": parts[0] if parts else "", "attrs": parts[1] if len(parts) > 1 else "", "content": m.group(2)})
    return out


def attrs_to_dict(attrs: str) -> dict[str, str]:
    """Parse `kind=bar id=x data_ref=y title="..."` into a dict (best-effort)."""
    d: dict[str, str] = {}
    for m in re.finditer(r'(\w+)=("([^"]*)"|(\S+))', attrs):
        d[m.group(1)] = m.group(3) if m.group(3) is not None else m.group(4)
    return d


def collect_callouts(body: str) -> list[dict[str, str]]:
    """Collect admonition blocks: [{variant, text}]."""
    out = []
    for m in re.finditer(r"^>\s*\[!(\w+)\][^\n]*\n((?:>.*\n?)+)", body, re.M):
        variant = m.group(1).lower()
        text = re.sub(r"^>\s?", "", m.group(2), flags=re.M).strip()
        out.append({"variant": variant, "text": text})
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

    def ok(self, rule: str) -> None:
        self.passed.append(f"✅ [{rule}]")


def validate(path: Path) -> Report:
    text = path.read_text(encoding="utf-8")
    meta = load_meta(text, path)
    body = split_frontmatter(text)
    r = Report()

    doc = meta.get("doc") or {}
    datasets = meta.get("datasets") or []
    figures = meta.get("figures") or []
    sources = meta.get("sources") or {}

    dataset_ids = {d.get("id") for d in datasets if isinstance(d, dict)}
    figure_ids = {f.get("id") for f in figures if isinstance(f, dict)}

    # ---- schema-level gate (front-matter required) ----
    for key in ("id", "title", "doc_type", "intent", "desired_action"):
        if not doc.get(key):
            r.err("SCHEMA", f"doc.{key} 缺失")
    if not datasets:
        r.warn("SCHEMA", "datasets 为空——正文若引用数字需先声明")
    if not isinstance(sources, dict) or "brief" not in sources:
        r.err("SCHEMA", "sources.brief 缺失（写作输入来源门禁）")

    doc_type = doc.get("doc_type")
    action = doc.get("desired_action") or ""

    # ---- R-A1 desired_action judgeable (non-empty + has a verb-ish object) ----
    if action and len(action) < 6:
        r.warn("R-A1", f"desired_action 可能不可判定：「{action}」，应是可观察动作")
    else:
        r.ok("R-A1")

    # ---- R-A2 doc_type vs action (heuristic) ----
    action_map = {
        "business_case": ("批", "立项", "预算", "资源"),
        "rfc": ("评审", "通过", "方案"),
        "prd": ("确认", "范围", "开发"),
        "runbook": ("执行", "操作"),
        "weekly": ("知晓", "了解", "同步"),
        "changelog": ("知晓", "准备"),
    }
    if doc_type in action_map and action:
        if not any(k in action for k in action_map[doc_type]):
            r.warn("R-A2", f"doc_type={doc_type} 与 desired_action「{action}」可能不匹配")
        else:
            r.ok("R-A2")
    else:
        r.ok("R-A2")

    # ---- R-S1 required slots present ----
    slots_found = set(SECTION_RE.findall(body))
    required = DOC_TYPE_SLOTS.get(doc_type, set())
    missing = required - slots_found
    if doc_type and required:
        if missing:
            r.err("R-S1", f"doc_type={doc_type} 缺必备章节 slot：{sorted(missing)}（找到：{sorted(slots_found & required)}）")
        else:
            r.ok("R-S1")
    elif doc_type:
        r.warn("R-S1", f"doc_type={doc_type} 无内置必备章节定义，跳过结构校验")

    # ---- R-W1 superlatives (heuristic) ----
    sups = SUPERLATIVE_RE.findall(body)
    if sups:
        r.warn("R-W1", f"正文含裸最高级/无证据判断：{set(sups)}——需引用 datasets/证据或改写")
    else:
        r.ok("R-W1")

    # ---- R-W2 datasets have caliber+source ----
    bad_ds = [d.get("id") for d in datasets if isinstance(d, dict) and not (d.get("caliber") and d.get("source"))]
    if bad_ds:
        r.err("R-W2", f"datasets 缺 caliber/source：{bad_ds}")
    else:
        r.ok("R-W2")

    # ---- R-W3 decisions have rationale (+ alternatives for rfc/adr/prd/business_case) ----
    callouts = collect_callouts(body)
    decisions = [c for c in callouts if c["variant"] == "decision"]
    bad_dec = [c["text"][:24] for c in decisions if "理由" not in c["text"] and "因为" not in c["text"] and "由于" not in c["text"]]
    if bad_dec:
        r.err("R-W3", f"[!decision] 缺理由：{bad_dec}")
    elif doc_type in {"rfc", "adr", "prd", "business_case"} and "备选" not in body:
        r.warn("R-W3", f"{doc_type} 应含备选方案与权衡（未检出'备选'）")
    else:
        r.ok("R-W3") if decisions or doc_type not in {"rfc", "adr", "prd", "business_case"} else r.ok("R-W3")

    # ---- R-W5 no placeholder ----
    phs = PLACEHOLDER_RE.findall(body)
    if phs:
        r.err("R-W5", f"正文含 placeholder：{set(p.upper() if p.isascii() else p for p in phs)}")
    else:
        r.ok("R-W5")

    # ---- R-C1 referenced datasets exist; flag bare numbers lightly ----
    refs = set(DREF_RE.findall(body))
    unknown_refs = refs - dataset_ids
    if unknown_refs:
        r.err("R-C1", f"正文 {{d:id}} 引用了未声明的 datasets：{sorted(unknown_refs)}")
    else:
        r.ok("R-C1")

    # ---- R-C2 figures data_ref valid; chart/kpi blocks map to figures/datasets ----
    bad_fig = []
    for f in figures:
        if not isinstance(f, dict):
            continue
        dr = f.get("data_ref")
        if dr and dr != "inline" and dr not in dataset_ids:
            bad_fig.append(f"{f.get('id')}.data_ref={dr}")
    if bad_fig:
        r.err("R-C2", f"figures.data_ref 指向未声明 datasets：{bad_fig}")
    else:
        r.ok("R-C2")

    # chart/kpi/timeline fenced blocks
    block_kinds_found = set()
    for blk in parse_fenced_blocks(body):
        lang = blk["lang"].lower()
        if lang in {"chart", "kpi", "timeline"}:
            a = attrs_to_dict(blk["attrs"])
            block_kinds_found.add(f"{lang}:{a.get('kind', '')}" if lang == "chart" else lang)
            bid = a.get("id")
            if bid and bid not in figure_ids and lang in {"chart", "kpi"}:
                r.err("R-C2", f"{lang} 块 id={bid} 未在 figures[] 声明")
            dr = a.get("data_ref") or a.get("value_ref")
            if dr and dr != "inline" and dr not in dataset_ids:
                r.err("R-C2", f"{lang} 块 {bid or '?'} 的 data_ref/value_ref={dr} 未在 datasets 声明")

    # ---- R-E1 chart kind legal ----
    for blk in parse_fenced_blocks(body):
        if blk["lang"].lower() == "chart":
            a = attrs_to_dict(blk["attrs"])
            kind = f"chart:{a.get('kind')}" if a.get("kind") else None
            if kind and kind not in CHART_KINDS:
                r.err("R-E1", f"chart kind={a.get('kind')} 非法（应为 bar/line/pie）")
            elif not a.get("kind"):
                r.err("R-E1", "chart 块缺 kind=bar/line/pie")
    r.ok("R-E1") if not any("R-E1" in e for e in r.errors) else None

    # ---- R-E4 badges have a legend ----
    badges = BADGE_RE.findall(body)
    levels_used = set(b.lower() for b in badges)
    illegal = levels_used - BADGE_LEVELS
    if illegal:
        r.err("R-E1", f"[badge:L] level 非法：{illegal}（应为 {sorted(BADGE_LEVELS)}）")
    if levels_used and not re.search(r"图例|绿\s*=|🟢|颜色含义|=\s*(已恢复|健康)", body):
        r.warn("R-E4", f"使用了状态徽章 {sorted(levels_used)} 但未见图例说明 level 含义")
    elif levels_used:
        r.ok("R-E4")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a doc-blueprint doc.md")
    ap.add_argument("doc", type=Path, help="Path to doc.md")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 文件不存在\n")
        return 2

    r = validate(args.doc)
    total_applicable = len(r.errors) + len(r.warns) + len(r.passed)
    warn_pass = 1.0 if not r.warns else (r.warns.count(False) or 0)
    # WARNING pass rate = passed/(passed+warns)
    wp = len(r.passed) / (len(r.passed) + len(r.warns)) if (len(r.passed) + len(r.warns)) else 1.0
    quality = len(r.passed) / total_applicable if total_applicable else 0.0

    print(f"=== validate_doc: {args.doc} ===")
    for line in r.errors + r.warns + r.passed:
        print(line)
    print(f"\nERROR: {len(r.errors)}  WARNING: {len(r.warns)}  PASSED: {len(r.passed)}")
    print(f"WARNING 通过率: {wp*100:.0f}%  质量分: {quality*100:.0f}%")

    if r.errors or wp < 0.80:
        print("\n结果：不合格（有 ERROR 或 WARNING 通过率 <80%）")
        return 1
    print("\n结果：合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
