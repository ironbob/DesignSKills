#!/usr/bin/env python3
"""Render arch-overview Mermaid diagrams from structured overview.json data.

The structured diagram objects are the only source of truth.  This module is
also imported by validators so a hand-edited Mermaid block cannot drift from
its nodes, edges, participants, or flows.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VIEW_ORDER = ("layering", "c4", "runtime")


def _quote(value: Any) -> str:
    text = str(value).replace("\\", "\\\\").replace('"', "\\\"")
    return text.replace("\r", "").replace("\n", "<br/>")


def _edge_arrow(style: str | None) -> str:
    return {"normal": "-->", "dashed": "-.->", "strong": "==>"}.get(
        style or "normal", "-->"
    )


def _edge_line(edge: dict[str, Any], indent: str = "  ") -> str:
    arrow = _edge_arrow(edge.get("style"))
    label = edge.get("label")
    middle = f'{arrow}|"{_quote(label)}"|' if label else arrow
    return f"{indent}{edge['from']} {middle} {edge['to']}"


def render_layering(view: dict[str, Any]) -> str:
    lines = [f"flowchart {view.get('direction', 'TD')}"]
    nodes = view.get("nodes") or []
    grouped: set[str] = set()
    for group in view.get("groups") or []:
        gid = group["id"]
        lines.append(f'  subgraph {gid}["{_quote(group["label"])}"]')
        for node in nodes:
            if node.get("group") == gid:
                lines.append(f'    {node["id"]}["{_quote(node["label"])}"]')
                grouped.add(node["id"])
        lines.append("  end")
    for node in nodes:
        if node["id"] not in grouped:
            lines.append(f'  {node["id"]}["{_quote(node["label"])}"]')
    lines.extend(_edge_line(edge) for edge in view.get("edges") or [])
    return "\n".join(lines)


def _c4_node(node: dict[str, Any]) -> str:
    nid = node["id"]
    label = _quote(node["label"])
    kind = node["kind"]
    if kind == "actor":
        return f'  {nid}(["{label}"])'
    if kind == "store":
        return f'  {nid}[("{label}")]'
    if kind == "external":
        return f'  {nid}{{{{"{label}"}}}}'
    return f'  {nid}["{label}"]'


def render_c4(view: dict[str, Any]) -> str:
    lines = [f"flowchart {view.get('direction', 'LR')}"]
    lines.extend(_c4_node(node) for node in view.get("nodes") or [])
    lines.extend(_edge_line(edge) for edge in view.get("edges") or [])
    return "\n".join(lines)


def render_runtime(view: dict[str, Any]) -> str:
    diagram_type = view.get("type", "sequence")
    participants = view.get("participants") or []
    flows = view.get("flows") or []
    if diagram_type == "flowchart":
        lines = [f"flowchart {view.get('direction', 'LR')}"]
        lines.extend(
            f'  {item["id"]}["{_quote(item["label"])}"]' for item in participants
        )
        lines.extend(_edge_line(flow) for flow in flows)
        return "\n".join(lines)

    arrows = {"sync": "->>", "response": "-->>", "async": "-)", "dashed": "-->>"}
    lines = ["sequenceDiagram"]
    lines.extend(
        f'  participant {item["id"]} as {_quote(item["label"])}'
        for item in participants
    )
    for flow in flows:
        arrow = arrows.get(flow.get("kind", "sync"), "->>")
        lines.append(
            f'  {flow["from"]}{arrow}{flow["to"]}: {_quote(flow["action"])}'
        )
    return "\n".join(lines)


def render_view(name: str, view: dict[str, Any]) -> str | None:
    if not view.get("applicable"):
        return None
    if name == "layering":
        return render_layering(view)
    if name == "c4":
        return render_c4(view)
    if name == "runtime":
        return render_runtime(view)
    raise ValueError(f"unknown diagram view: {name}")


def render_all(data: dict[str, Any]) -> dict[str, str]:
    diagrams = data.get("diagrams") or {}
    rendered: dict[str, str] = {}
    for name in VIEW_ORDER:
        result = render_view(name, diagrams.get(name) or {})
        if result is not None:
            rendered[name] = result
    return rendered


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Render Mermaid from structured arch-overview diagram data"
    )
    ap.add_argument("overview", type=Path, help="Path to overview.json")
    ap.add_argument("--view", choices=(*VIEW_ORDER, "all"), default="all")
    ap.add_argument(
        "--format", choices=("source", "markdown"), default="markdown",
        help="Emit raw Mermaid for one view, or fenced Markdown",
    )
    args = ap.parse_args()
    try:
        data = json.loads(args.overview.read_text(encoding="utf-8"))
        rendered = render_all(data)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        sys.stderr.write(f"render_mermaid: {exc}\n")
        return 2

    names = VIEW_ORDER if args.view == "all" else (args.view,)
    selected = [(name, rendered[name]) for name in names if name in rendered]
    if args.format == "source":
        if len(names) != 1:
            sys.stderr.write("--format source requires one --view\n")
            return 2
        if not selected:
            reason = (data.get("diagrams") or {}).get(names[0], {}).get("reason", "不适用")
            sys.stderr.write(f"{names[0]}: {reason}\n")
            return 1
        print(selected[0][1])
        return 0

    for index, (name, source) in enumerate(selected):
        if index:
            print()
        print(f"<!-- generated:{name} -->")
        print("```mermaid")
        print(source)
        print("```")
    return 0


if __name__ == "__main__":
    sys.exit(main())
