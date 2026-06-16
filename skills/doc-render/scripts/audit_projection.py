#!/usr/bin/env python3
"""Audit that a rendered backend faithfully projects a doc.md blueprint.

Manifest-driven (references/<backend>/projection.manifest.yaml). Parses the
doc.md declared blocks (figures[] ids + body fenced chart/kpi/timeline blocks
with their kinds + admonitions/badges/tables markers are emitted by the
renderer) and the rendered file's <!-- doc:proj id=.. kind=.. --> markers, then
diffs the two sets per backend. Also flags unresolved {{d:}}/[ref:] placeholders.

Usage:
  python audit_projection.py <doc.md> <render-dir> --backend {all,markdown,confluence}
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None

BACKENDS = ["markdown", "confluence"]
PROJ_RE = re.compile(r"<!--\s*doc:proj\s+id=(\S+)\s+kind=(\S+)\s*-->")


def load_doc(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    meta: dict[str, Any] = {}
    if m and yaml:
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except Exception:
            meta = {}
    body = text[m.end():] if m else text
    return {"meta": meta, "body": body}


def declared_blocks(doc: dict[str, Any]) -> dict[str, str]:
    """id -> kind for every DECLARED block that MUST project.

    First-class data-viz: figures[] (id+kind). Body fenced chart/kpi/timeline
    blocks that carry their own id are also declared. Inline elements without a
    source id (callouts, badges, tables) are projected by the renderer with its
    own markers but are not enforced as a declared set — only placeholders must
    resolve and declared blocks must not be missing.
    """
    out: dict[str, str] = {}
    for f in (doc["meta"].get("figures") or []):
        if isinstance(f, dict) and f.get("id"):
            out[f["id"]] = f.get("kind", "")
    for blk in re.finditer(r"```(chart|kpi|timeline)([^\n`]*)\n", doc["body"]):
        lang = blk.group(1)
        attrs = blk.group(2)
        bid = re.search(r"id=(\S+)", attrs)
        if not bid:
            continue
        if lang == "chart":
            kind = re.search(r"kind=(\S+)", attrs)
            out[bid.group(1)] = f"chart:{kind.group(1)}" if kind else "chart"
        else:
            out[bid.group(1)] = lang
    return out


def projected_blocks(render_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in PROJ_RE.finditer(render_text):
        out[m.group(1)] = m.group(2)
    return out


def audit_one(doc: dict[str, Any], render_path: Path, backend: str) -> tuple[list[str], list[str], list[str]]:
    """Return (errors, warns, info) for one backend."""
    errs: list[str] = []
    warns: list[str] = []
    info: list[str] = []
    if not render_path.exists():
        return ([f"{backend}: 产物不存在 {render_path}"], [], [])
    text = render_path.read_text(encoding="utf-8")

    declared = declared_blocks(doc)
    projected = projected_blocks(text)

    missing = {k: v for k, v in declared.items() if k not in projected}
    extra = {k: v for k, v in projected.items() if k not in declared}
    mismatch = {k: (declared[k], projected[k]) for k in (declared.keys() & projected.keys()) if declared[k] and projected[k] and declared[k] != projected[k]}

    for k, v in missing.items():
        errs.append(f"{backend}: 声明的块未投影 id={k} kind={v}")
    for k, v in extra.items():
        # callouts/status/tables/timeline are projected without a source id — informational.
        info.append(f"{backend}: 额外投影标记（行内元素，正常）id={k} kind={v}")
    for k, (d, p) in mismatch.items():
        warns.append(f"{backend}: 块 id={k} kind 不一致 声明={d} 投影={p}")

    d_hits = re.findall(r"\{\{d:[^}]+\}\}", text)
    if d_hits:
        errs.append(f"{backend}: 成品有未解析数字占位 {set(d_hits)}（必须从 datasets 解析）")
    r_hits = re.findall(r"\[ref:[^\]]+\]", text)
    if r_hits:
        warns.append(f"{backend}: 成品有未解析引用占位 {set(r_hits)}")

    return errs, warns, info


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit doc.md -> backend projection")
    ap.add_argument("doc", type=Path, help="Path to doc.md")
    ap.add_argument("render_dir", type=Path, help="render output directory")
    ap.add_argument("--backend", choices=["all", *BACKENDS], default="all")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 不存在\n")
        return 2

    doc = load_doc(args.doc)
    targets = BACKENDS if args.backend == "all" else [args.backend]

    all_errs: list[str] = []
    all_warns: list[str] = []
    print(f"=== audit_projection: {args.doc} ===")
    print(f"声明块: {declared_blocks(doc)}")
    for b in targets:
        sub = args.render_dir / "render" / b
        candidates = sorted(sub.glob("*")) if sub.exists() else sorted(args.render_dir.glob(f"{b}/*"))
        rp = next((c for c in candidates if c.is_file()), None)
        errs, warns, info = audit_one(doc, rp or (args.render_dir / b), b)
        all_errs += errs
        all_warns += warns
        print(f"\n[{b}] 产物={rp}  ERROR={len(errs)} WARNING={len(warns)}")
        for e in errs:
            print("  🔴 " + e)
        for w in warns:
            print("  🟡 " + w)
        for i in info:
            print("  ℹ️  " + i)

    print(f"\n总 ERROR: {len(all_errs)}  WARNING: {len(all_warns)}")
    if all_errs:
        print("结果：不合格（投影不通过）")
        return 1
    print("结果：对账通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
