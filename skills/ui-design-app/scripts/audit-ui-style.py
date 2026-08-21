#!/usr/bin/env python3
"""Scan a UI project and emit a compact, deterministic style-audit summary."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


TEXT_EXTENSIONS = {".css", ".scss", ".sass", ".less", ".html", ".vue", ".svelte", ".jsx", ".tsx"}
SKIP_DIRS = {".git", "node_modules", "dist", "build", "coverage", "vendor", ".next", ".nuxt"}
MAX_FILE_BYTES = 2_000_000
BASE_RULES = {
    "hardcoded_color": re.compile(r"(?<![-\w])#[0-9a-fA-F]{3,8}\b|\b(?:rgb|hsl)a?\([^)]*\)"),
    "important": re.compile(r"!important\b"),
    "background_shorthand": re.compile(r"(?m)^\s*background\s*:"),
    "gradient": re.compile(r"(?:linear|radial|conic)-gradient\("),
    "backdrop_filter": re.compile(r"(?:-webkit-)?backdrop-filter\s*:"),
    "overflow_hidden": re.compile(r"overflow(?:-[xy])?\s*:\s*hidden"),
    "fixed_containing_block": re.compile(
        r"(?:transform|filter|perspective|container-type|contain|will-change)\s*:\s*[^;]+"
    ),
}
STATE_PATTERNS = {
    "hover": re.compile(r":hover\b"),
    "active": re.compile(r":active\b"),
    "disabled": re.compile(r":disabled\b|\[aria-disabled"),
    "focus_visible": re.compile(r":focus-visible\b"),
}
STYLE_TOKEN_PREFIX = {
    "finder": "--finder-",
    "linear": "--ln-",
    "things": "--th-",
    "geist": "--ge-",
    "figma": "--fig-",
    "codex": "--cx-",
}
# 圆角上限（px）：超过即计入 <style>_large_radius；未列出的风格无此规则。
# linear 禁大圆角（紧凑效率）；geist 卡片最大 8-10；finder/things/figma 大圆角是身份，不设限。
STYLE_RADIUS_LIMIT = {"linear": 8.0, "geist": 10.0}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        yield path


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Project directory")
    parser.add_argument("--style", choices=tuple(STYLE_TOKEN_PREFIX), required=True)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--max-examples", type=int, default=12)
    args = parser.parse_args()

    root = Path(args.project).expanduser().resolve()
    if not root.is_dir():
        parser.error(f"project is not a directory: {root}")

    findings: dict[str, list[str]] = defaultdict(list)
    counts: dict[str, int] = defaultdict(int)
    states: dict[str, int] = defaultdict(int)
    files_scanned = 0
    token_prefix = STYLE_TOKEN_PREFIX[args.style]
    token_uses = 0

    for path in iter_files(root):
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(root)
        lines = text.splitlines()
        is_token_file = path.name == "tokens.css"
        token_uses += text.count(f"var({token_prefix}")
        for state, pattern in STATE_PATTERNS.items():
            states[state] += len(pattern.findall(text))
        for rule, pattern in BASE_RULES.items():
            for match in pattern.finditer(text):
                matched_line = lines[line_number(text, match.start()) - 1] if lines else ""
                if rule == "hardcoded_color" and is_token_file:
                    continue
                if rule == "important" and ("animation-duration" in matched_line or "transition-duration" in matched_line):
                    continue
                counts[rule] += 1
                if len(findings[rule]) < args.max_examples:
                    findings[rule].append(f"{relative}:{line_number(text, match.start())}")

        radius_limit = STYLE_RADIUS_LIMIT.get(args.style)
        if radius_limit is not None:
            radius_rule = f"{args.style}_large_radius"
            for match in re.finditer(r"border-radius\s*:\s*(\d+(?:\.\d+)?)px", text):
                matched_line = lines[line_number(text, match.start()) - 1] if lines else ""
                if float(match.group(1)) > radius_limit and "scrollbar" not in matched_line:
                    counts[radius_rule] += 1
                    if len(findings[radius_rule]) < args.max_examples:
                        findings[radius_rule].append(
                            f"{relative}:{line_number(text, match.start())}"
                        )

    missing_states = [name for name, count in states.items() if count == 0]
    report = {
        "project": str(root),
        "style": args.style,
        "files_scanned": files_scanned,
        "semantic_token_uses": token_uses,
        "state_selector_counts": dict(states),
        "missing_state_selectors": missing_states,
        "findings": {
            rule: {"count": counts[rule], "examples": examples}
            for rule, examples in sorted(findings.items())
        },
    }

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Style audit: {args.style} · {files_scanned} files · {token_uses} semantic-token uses")
        for rule, payload in report["findings"].items():
            print(f"- {rule}: {payload['count']} ({', '.join(payload['examples'])})")
        if missing_states:
            print(f"- missing state selectors: {', '.join(missing_states)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
