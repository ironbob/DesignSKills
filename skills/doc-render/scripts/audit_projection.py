#!/usr/bin/env python3
"""Audit that a rendered backend faithfully projects a doc.md blueprint.

Manifest-driven: for each backend it reads
``references/<backend>/projection.manifest.yaml`` (the platform registry is the
set of ``references/<backend>/`` dirs that contain such a manifest), compiles its
``block.pattern`` to find projection markers, and uses its ``unresolved`` regexes
to flag leftover placeholders. Adding a new text backend = add a dir + a manifest,
zero Python here.

Parses the doc.md declared blocks (figures[] ids + body fenced chart/kpi/timeline
blocks with their kinds) and the rendered file's projection markers, then diffs
the two sets per backend.

Usage:
  python audit_projection.py <doc.md> <render-dir> [--backend {all,<discovered>}]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - depends on host packages
    yaml = None

# skills/doc-render (script lives in scripts/)
SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = SKILL_ROOT / "references"
MANIFEST_NAME = "projection.manifest.yaml"


def require_yaml() -> None:
    if yaml is None:
        sys.stderr.write(
            "audit_projection.py 需要 PyYAML（读取 manifest 与 doc.md front-matter）。"
            "pip install pyyaml\n"
        )
        sys.exit(2)


def discover_backends() -> list[str]:
    """The platform registry: every references/<name>/ with a manifest."""
    if not REFERENCES.is_dir():
        return []
    return sorted(
        d.name for d in REFERENCES.iterdir()
        if d.is_dir() and (d / MANIFEST_NAME).exists()
    )


def load_manifest(backend: str) -> dict[str, Any]:
    """Read & compile one backend's projection.manifest.yaml."""
    p = REFERENCES / backend / MANIFEST_NAME
    if not p.exists():
        sys.stderr.write(f"{backend}: 未找到 manifest {p}\n")
        sys.exit(2)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        sys.stderr.write(f"{backend}: manifest 顶层应为映射：{p}\n")
        sys.exit(2)

    parse = data.get("parse", "text_regex")
    if parse != "text_regex":
        # Only text_regex is built in. A genuinely new strategy is the one
        # Python change that adding a backend can require (see platforms.md §四).
        sys.stderr.write(
            f"{backend}: parse='{parse}' 暂不支持（仅 text_regex）。新增策略需改抽取器。\n"
        )
        sys.exit(2)

    block_pat = (data.get("block") or {}).get("pattern")
    if not block_pat:
        sys.stderr.write(f"{backend}: manifest 缺 block.pattern：{p}\n")
        sys.exit(2)
    try:
        block_re = re.compile(block_pat)
    except re.error as exc:
        sys.stderr.write(f"{backend}: block.pattern 非法正则：{exc}\n")
        sys.exit(2)
    if not {"id", "kind"} <= set(block_re.groupindex):
        sys.stderr.write(
            f"{backend}: block.pattern 必须含命名组 id 与 kind：{block_re.pattern}\n"
        )
        sys.exit(2)

    unresolved_res = []
    for pat in (data.get("unresolved") or []):
        try:
            unresolved_res.append(re.compile(pat))
        except re.error as exc:
            sys.stderr.write(f"{backend}: unresolved 正则非法 {pat!r}：{exc}\n")
            sys.exit(2)
    return {"path": p, "block_re": block_re, "unresolved_res": unresolved_res}


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


def projected_blocks(render_text: str, block_re: re.Pattern[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in block_re.finditer(render_text):
        out[m.group("id")] = m.group("kind")
    return out


def audit_one(
    doc: dict[str, Any], render_path: Path, backend: str, manifest: dict[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    """Return (errors, warns, info) for one backend, using its manifest."""
    errs: list[str] = []
    warns: list[str] = []
    info: list[str] = []
    if not render_path.exists():
        return ([f"{backend}: 产物不存在 {render_path}"], [], [])
    text = render_path.read_text(encoding="utf-8")

    declared = declared_blocks(doc)
    projected = projected_blocks(text, manifest["block_re"])

    missing = {k: v for k, v in declared.items() if k not in projected}
    extra = {k: v for k, v in projected.items() if k not in declared}
    mismatch = {
        k: (declared[k], projected[k])
        for k in (declared.keys() & projected.keys())
        if declared[k] and projected[k] and declared[k] != projected[k]
    }

    for k, v in missing.items():
        errs.append(f"{backend}: 声明的块未投影 id={k} kind={v}")
    for k, v in extra.items():
        # callouts/status/tables/timeline are projected without a source id — informational.
        info.append(f"{backend}: 额外投影标记（行内元素，正常）id={k} kind={v}")
    for k, (d, p) in mismatch.items():
        warns.append(f"{backend}: 块 id={k} kind 不一致 声明={d} 投影={p}")

    # Unresolved placeholders are declared per-backend in the manifest; any left
    # in a deliverable is a defect.
    for ure in manifest["unresolved_res"]:
        hits = ure.findall(text)
        if hits:
            errs.append(f"{backend}: 成品有未解析占位 {set(hits)}（必须解析后交付）")

    return errs, warns, info


def main() -> int:
    require_yaml()
    backends = discover_backends()
    ap = argparse.ArgumentParser(description="Audit doc.md -> backend projection")
    ap.add_argument("doc", type=Path, help="Path to doc.md")
    ap.add_argument("render_dir", type=Path, help="render output directory")
    ap.add_argument("--backend", choices=["all", *backends], default="all",
                    help=f"backend (discovered: {', '.join(backends) or 'none'})")
    args = ap.parse_args()
    if not args.doc.exists():
        sys.stderr.write(f"{args.doc}: 不存在\n")
        return 2

    doc = load_doc(args.doc)
    targets = backends if args.backend == "all" else [args.backend]
    manifests = {b: load_manifest(b) for b in targets}

    all_errs: list[str] = []
    all_warns: list[str] = []
    print(f"=== audit_projection: {args.doc} ===")
    print(f"发现后端(注册表): {backends}")
    print(f"声明块: {declared_blocks(doc)}")
    for b in targets:
        sub = args.render_dir / "render" / b
        candidates = sorted(sub.glob("*")) if sub.exists() else sorted(args.render_dir.glob(f"{b}/*"))
        rp = next((c for c in candidates if c.is_file()), None)
        errs, warns, info = audit_one(doc, rp or (args.render_dir / b), b, manifests[b])
        all_errs += errs
        all_warns += warns
        print(f"\n[{b}]  manifest={manifests[b]['path'].relative_to(SKILL_ROOT)}")
        print(f"     产物={rp}  ERROR={len(errs)} WARNING={len(warns)}")
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
