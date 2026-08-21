#!/usr/bin/env python3
"""Query a full architecture scan without loading the whole fact index into context."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def contains(value: Any, needle: str) -> bool:
    return needle.lower() in json.dumps(value, ensure_ascii=False).lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Query a scan_architecture.py fact index")
    parser.add_argument("index", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--type", dest="type_name", help="Return edges mentioning this type/symbol")
    group.add_argument("--file", help="Return facts and edges mentioning this file")
    group.add_argument("--cycles", action="store_true", help="Return deterministic internal cycle candidates")
    group.add_argument("--hotspots", action="store_true", help="Return the precomputed hotspot summary")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not args.index.exists():
        sys.stderr.write(f"{args.index}: 文件不存在\n")
        return 2
    try:
        data = json.loads(args.index.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"{args.index}: JSON 解析失败：{exc}\n")
        return 2
    edges = data.get("dependency_edges", [])
    semantic_edges = (data.get("cpp_semantics") or {}).get("semantic_edges", [])
    if args.cycles:
        payload = {
            "cycle_candidates": data.get("cycle_candidates", []),
            "total_edge_count": len(edges) + len(semantic_edges),
        }
    elif args.hotspots:
        payload = {
            "hotspots": data.get("hotspots", [])[:args.limit],
            "total_edge_count": len(edges) + len(semantic_edges),
        }
    else:
        needle = args.type_name or args.file or ""
        matched = [edge for edge in [*edges, *semantic_edges] if contains(edge, needle)]
        facts = [fact for fact in data.get("files", []) if contains(fact, needle)] if args.file else []
        payload = {
            "query": needle,
            "total_edge_count": len(edges) + len(semantic_edges),
            "matched_edge_count": len(matched),
            "edges": matched[:args.limit],
            "files": facts[:args.limit],
            "truncated": len(matched) > args.limit,
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
