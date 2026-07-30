#!/usr/bin/env python3
"""Compare a Java shared_ptr Handle implementation with the bundled originals."""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ORIGINAL_DIR = SCRIPT_DIR.parent / "references" / "original-code"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a Markdown report containing unified diffs between the "
            "bundled original NativeObjectRef sources and a new implementation."
        )
    )
    parser.add_argument("--header", required=True, type=Path, help="New C++ header")
    parser.add_argument("--java", required=True, type=Path, help="New Java base class")
    parser.add_argument("--cpp", required=True, type=Path, help="New C++ implementation")
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the Markdown report here; omit to print to stdout",
    )
    return parser.parse_args()


def read_source(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"source file not found: {path}")
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def render_diff(original: Path, new: Path) -> tuple[str, int, int]:
    original_lines = read_source(original)
    new_lines = read_source(new)
    diff_lines = list(
        difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"original/{original.name}",
            tofile=str(new),
            lineterm="\n",
        )
    )
    if not diff_lines:
        return "_No textual differences._\n", 0, 0

    additions = sum(
        1
        for line in diff_lines
        if line.startswith("+") and not line.startswith("+++")
    )
    deletions = sum(
        1
        for line in diff_lines
        if line.startswith("-") and not line.startswith("---")
    )
    body = "".join(diff_lines)
    if body and not body.endswith("\n"):
        body += "\n"
    return f"```diff\n{body}```\n", additions, deletions


def build_report(mappings: list[tuple[str, Path, Path]]) -> str:
    sections: list[str] = [
        "# Original vs new Java shared_ptr Handle\n\n",
        "The original side is the verbatim source snapshot bundled with "
        "`java-sp-handle`.\n\n",
        "## File mapping\n\n",
        "| Layer | Original | New |\n",
        "|---|---|---|\n",
    ]
    for layer, original, new in mappings:
        sections.append(f"| {layer} | `{original}` | `{new}` |\n")

    totals = [0, 0]
    diff_sections: list[str] = []
    for layer, original, new in mappings:
        rendered, additions, deletions = render_diff(original, new)
        totals[0] += additions
        totals[1] += deletions
        diff_sections.extend(
            [
                f"\n## {layer} diff\n\n",
                f"Changed lines: `+{additions}` / `-{deletions}`\n\n",
                rendered,
            ]
        )

    sections.extend(
        [
            "\n## Textual summary\n\n",
            f"- Added lines: {totals[0]}\n",
            f"- Deleted lines: {totals[1]}\n",
            "- Semantic meaning must be explained separately by the implementing "
            "agent; textual similarity is not a correctness claim.\n",
        ]
    )
    sections.extend(diff_sections)
    return "".join(sections)


def main() -> int:
    args = parse_args()
    mappings = [
        (
            "C++ header",
            ORIGINAL_DIR / "NativeObjectRef.h",
            args.header.resolve(),
        ),
        (
            "Java",
            ORIGINAL_DIR / "NativeObjectRef.java",
            args.java.resolve(),
        ),
        (
            "C++ implementation",
            ORIGINAL_DIR / "NativeObjectRef.cpp",
            args.cpp.resolve(),
        ),
    ]
    try:
        report = build_report(mappings)
    except (OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    if args.output is None:
        sys.stdout.write(report)
    else:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(f"Wrote comparison report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
