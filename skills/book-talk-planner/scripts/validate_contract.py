#!/usr/bin/env python3
"""Cross-check outline.json ⇄ outline.md for book-talk-planner.

防 json 契约源与人读渲染之间漂移：

  CONTRACT-ID    每 json topic.id 在 md 以 `### <id> ·` 出现；反之 md 的 id 都在 json
  CONTRACT-COUNT md 选题标题数 == len(json.topics)
  CONTRACT-META  json.meta 与 md frontmatter 的 book/input_mode/form/verdict 一致

有 ERROR 退出非 0。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TOPIC_HEAD = re.compile(r"^###\s+(T\d+)\s*·", re.MULTILINE)


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.passed: list[str] = []

    def err(self, rule: str, msg: str) -> None:
        self.errors.append(f"🔴 [{rule}] {msg}")

    def ok(self, rule: str, msg: str = "") -> None:
        self.passed.append(f"✅ [{rule}]" + (f" {msg}" if msg else ""))


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


def validate(data: Any, md_text: str) -> Report:
    r = Report()

    meta = data.get("meta", {}) if isinstance(data, dict) else {}
    topics = data.get("topics", []) if isinstance(data, dict) else []
    json_ids = [t.get("id") for t in topics if isinstance(t, dict) and isinstance(t.get("id"), str)]
    md_ids = TOPIC_HEAD.findall(md_text)

    # ---- CONTRACT-ID ----
    json_set, md_set = set(json_ids), set(md_ids)
    only_json = json_set - md_set
    only_md = md_set - json_set
    if only_json or only_md:
        if only_json:
            r.err("CONTRACT-ID", f"json 有、md 无的 id：{sorted(only_json)}")
        if only_md:
            r.err("CONTRACT-ID", f"md 有、json 无的 id：{sorted(only_md)}")
    else:
        r.ok("CONTRACT-ID", f"id 双向一致（{len(json_set)} 个）")

    # ---- CONTRACT-COUNT ----
    if len(json_ids) == len(md_ids):
        r.ok("CONTRACT-COUNT", f"选题数一致：json {len(json_ids)} == md {len(md_ids)}")
    else:
        r.err("CONTRACT-COUNT", f"选题数不一致：json {len(json_ids)} ≠ md {len(md_ids)}")

    # ---- CONTRACT-META ----
    fm = parse_frontmatter(md_text)
    pairs = {
        "book": meta.get("book"),
        "input_mode": meta.get("input_mode"),
        "form": meta.get("selectability", {}).get("form") if isinstance(meta.get("selectability"), dict) else None,
        "verdict": meta.get("selectability", {}).get("verdict") if isinstance(meta.get("selectability"), dict) else None,
    }
    drift = []
    for key, jv in pairs.items():
        mv = fm.get(key)
        if str(jv) != str(mv):
            drift.append(f"{key}: json={jv!r} md={mv!r}")
    if drift:
        r.err("CONTRACT-META", "json↔md 元信息漂移：" + "; ".join(drift))
    else:
        r.ok("CONTRACT-META", "book/input_mode/form/verdict 一致")

    # ---- CONTRACT-SOURCE ----
    ks = meta.get("knowledge_source")
    decl = ks.get("declaration") if isinstance(ks, dict) else None
    if isinstance(decl, str) and decl.strip() and decl in md_text:
        r.ok("CONTRACT-SOURCE", "knowledge_source.declaration 已渲染且一致")
    elif isinstance(decl, str) and decl.strip():
        r.err("CONTRACT-SOURCE", "json 的 knowledge_source.declaration 未在 md 出现（渲染漂移）")
    else:
        r.ok("CONTRACT-SOURCE", "无 declaration（由 outline 门 O-SOURCE 负责）")

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-check outline.json ⇄ outline.md")
    ap.add_argument("json_path", type=Path, help="outline.json")
    ap.add_argument("md_path", type=Path, help="outline.md")
    args = ap.parse_args()
    for p in (args.json_path, args.md_path):
        if not p.exists():
            sys.stderr.write(f"{p}: 文件不存在\n")
            return 2
    try:
        data = json.loads(args.json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.json_path}: JSON 解析失败：{exc}\n")
        return 2
    md_text = args.md_path.read_text(encoding="utf-8")

    r = validate(data, md_text)
    print(f"=== validate_contract: {args.json_path.name} ⇄ {args.md_path.name} ===")
    for line in r.errors + r.passed:
        print(line)
    print(f"\nERROR: {len(r.errors)}  PASSED: {len(r.passed)}")
    if r.errors:
        print("\n结果：契约漂移，不合格")
        return 1
    print("\n结果：契约一致，合格")
    return 0


if __name__ == "__main__":
    sys.exit(main())
