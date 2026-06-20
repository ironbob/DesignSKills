#!/usr/bin/env python3
"""Self-consistency validator for an edu-data-gen toolkit (the 工具包自校验 gate).

Checks that content_list / schema / prompts / scripts / config are mutually
consistent BEFORE user confirmation and sample validation. No LLM calls.

Usage: python validate_toolkit.py <toolkit_dir>
Exit non-zero on any ERROR.
"""

from __future__ import annotations

import argparse
import json
import py_compile
import re
import sys
from pathlib import Path


VALID_ENTITIES = {"material", "knowledge_point", "explanation", "item"}
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|待定|占位|FIXME|xxx)\b", re.I)


def ok(msg):  return ("✓", msg)
def err(msg): return ("✗", msg)
def warn(msg):return ("⚠", msg)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="toolkit dir")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    results: list[tuple[str, str]] = []
    errors = 0

    def add(r):
        nonlocal errors
        results.append(r)
        if r[0] == "✗":
            errors += 1

    if not root.is_dir():
        print(f"[validate_toolkit] not a dir: {root}", file=sys.stderr)
        return 2

    # --- config ---
    cfg_path = root / "config.json"
    cfg = None
    if not cfg_path.exists():
        add(err("config.json missing"))
    else:
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            add(ok("config.json parses"))
        except Exception as e:
            add(err(f"config.json invalid JSON: {e}"))
            cfg = None

    if cfg:
        for key in ["product", "llm", "paths", "file_split", "difficulty_distribution", "gates"]:
            if key not in cfg:
                add(err(f"config missing key: {key}"))
            else:
                add(ok(f"config has {key}"))
        if cfg.get("llm", {}).get("provider") != "claude_code":
            add(err("config.llm.provider must be 'claude_code' (claude_code_direct provider registry name)"))
        else:
            add(ok("config.llm.provider = claude_code"))
        if not cfg.get("llm", {}).get("generate_model"):
            add(err("config.llm.generate_model missing"))
        if cfg.get("paths", {}).get("content_list") is None:
            add(err("config.paths.content_list missing"))

    paths = (cfg or {}).get("paths", {})
    cl_path = root / paths.get("content_list", "content_list.json")
    schemas_dir = root / paths.get("schemas_dir", "schema")
    prompts_dir = root / paths.get("prompts_dir", "prompts")

    # --- content_list ---
    content_list = []
    if not cl_path.exists():
        add(err(f"content_list missing: {cl_path}"))
    else:
        try:
            content_list = json.loads(cl_path.read_text(encoding="utf-8"))
            assert isinstance(content_list, list) and content_list
            add(ok(f"content_list.json: {len(content_list)} content point(s)"))
        except Exception as e:
            add(err(f"content_list invalid: {e}"))

    entities_used = set()
    for cp in content_list:
        cid = cp.get("id", "<no-id>")
        ent = cp.get("entity")
        if ent not in VALID_ENTITIES:
            add(err(f"{cid}: entity '{ent}' not in {sorted(VALID_ENTITIES)}"))
        else:
            entities_used.add(ent)
        for f in ("id", "entity", "grade", "bloom"):
            if f not in cp:
                add(err(f"{cid}: missing field '{f}'"))
        # placeholder scan
        blob = json.dumps(cp, ensure_ascii=False)
        if PLACEHOLDER_RE.search(blob):
            add(warn(f"{cid}: contains placeholder (TBD/待定/…)"))
        # referenced prompt template
        tmpl = cp.get("prompt_template", f"{ent}.md")
        if not (prompts_dir / tmpl).exists():
            add(err(f"{cid}: prompt template missing: prompts/{tmpl}"))
        # schema for entity
        if ent and not (schemas_dir / f"{ent}.json").exists():
            add(err(f"{cid}: schema missing: schema/{ent}.json"))

    # --- scripts present + compile ---
    for script in ("generate.py", "validate.py"):
        sp = root / script
        if not sp.exists():
            add(err(f"{script} missing"))
            continue
        try:
            py_compile.compile(str(sp), doraise=True)
            add(ok(f"{script} compiles"))
        except py_compile.PyCompileError as e:
            add(err(f"{script} compile error: {e}"))

    # --- file_split coverage ---
    if cfg:
        fs = cfg.get("file_split", {})
        groups = fs.get("by_field_group", {}) if fs.get("mode", "by_field_group") == "by_field_group" else {}
        for ent in entities_used:
            if fs.get("mode") == "by_field_group" and ent not in groups:
                add(warn(f"entity '{ent}' used but no file_split rule (will single-file)"))
            else:
                add(ok(f"file_split rule for '{ent}'"))

    # --- gates + difficulty ---
    if cfg:
        if not cfg.get("gates"):
            add(warn("config.gates empty (no gates enabled)"))
        dd = cfg.get("difficulty_distribution", {})
        if not dd:
            add(warn("difficulty_distribution empty (G4 will skip)"))
        else:
            add(ok(f"difficulty_distribution covers bands: {sorted(dd)}"))

    # --- report ---
    print(f"\n=== 工具包自校验：{root} ===")
    for flag, msg in results:
        print(f"  {flag} {msg}")
    print(f"\n{'PASS' if errors == 0 else 'FAIL'}  ({errors} error(s))")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
