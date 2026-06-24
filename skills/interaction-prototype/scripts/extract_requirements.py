#!/usr/bin/env python3
"""Extract atomic requirement items from a requirements markdown doc.

The requirements markdown is the SINGLE SOURCE OF TRUTH for coverage. This
parser turns its feature-checklist tables into a list of atomic requirement
items that ``validate_page_plan.py`` checks against the spec's ``page_plan``
(each page's ``delivers`` lists the requirement ids it covers).

Expected doc shape (produced by ``clarify-requirements``): one or more
``### 模块：<name>`` headings, each followed by a markdown table whose columns
are, positionally: ``优先级 | 功能 | 简述 | 验收标准``. The parser is tolerant of
header wording and column count; missing trailing columns become empty strings.

ID stability contract
---------------------
Requirement ids are index-based — ``REQ-M<module_index>-<row_index>`` — and are
therefore STABLE ONLY WHILE THE MARKDOWN ORDER IS STABLE. Reordering modules or
rows shifts ids, which is intentional: it forces the spec's ``page_plan``
delivers/links to be re-reconciled against the requirements doc. Do not persist
these ids as long-lived identifiers; always re-extract.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
# A separator row cell is like ---, :---, ---:, :---:.
SEPARATOR_CELL_RE = re.compile(r"^:?-+:?$")
# Aggregate detection keys off the ACCEPTANCE column, requiring the Chinese
# type-count word 种 (not 个). "同一单元至少出现 2 种题型" → aggregate, min 2;
# "≥3 个干扰选项" and "新学习项数 + 复习数" use 个/+ and are NOT aggregate. A
# feature merely containing 混合 (e.g. "每日新学+复习混合") is a single-page
# capability, not a count-over-siblings requirement.
AGGREGATE_RE = re.compile(r"(?:至少|不少于)[^\d]{0,6}(\d+)\s*种|≥\s*(\d+)\s*种|(\d+)\s*种(?:以上|及)")
MODULE_PREFIX_RE = re.compile(r"^模块[：:]\s*")


def _clean(cell: str) -> str:
    """Strip markdown emphasis/whitespace from a table cell."""
    return re.sub(r"[*_`]", "", cell).strip()


def _split_row(line: str) -> list[str]:
    trimmed = line.strip()
    if trimmed.startswith("|"):
        trimmed = trimmed[1:]
    if trimmed.endswith("|"):
        trimmed = trimmed[:-1]
    return [part.strip() for part in trimmed.split("|")]


def _is_separator(cells: list[str]) -> bool:
    relevant = [c for c in cells if c]
    return bool(relevant) and all(SEPARATOR_CELL_RE.match(c) for c in relevant)


def extract_requirements(md_text: str) -> list[dict[str, Any]]:
    """Parse a requirements markdown doc into atomic requirement items.

    Returns a list of dicts with keys: id, module, module_index, feature,
    summary, acceptance, priority, aggregate, min_covered.
    """
    reqs: list[dict[str, Any]] = []
    current_heading: str | None = None
    # module_index is assigned lazily to the first heading that yields a row,
    # so headings with no table never consume an index (keeps ids clean: the
    # 7th module really is M07, not M12).
    heading_index: dict[str, int] = {}
    row_counter: dict[int, int] = {}
    next_module_index = 1
    # ``True`` once the current table's header row has been consumed; the next
    # ``|``-row is the first data row.
    header_consumed = False

    for raw in md_text.splitlines():
        stripped = raw.strip()
        heading = HEADING_RE.match(stripped)
        if heading:
            current_heading = heading.group(2).strip()
            header_consumed = False
            continue
        if not stripped.startswith("|"):
            # Any non-table line (incl. blank) ends the current table.
            header_consumed = False
            continue

        cells = _split_row(stripped)
        if _is_separator(cells):
            continue
        if not header_consumed:
            # First | -row of a table is the header; skip it.
            header_consumed = True
            continue
        if current_heading is None:
            # A table with no preceding heading — nothing to attribute it to.
            continue

        if current_heading not in heading_index:
            heading_index[current_heading] = next_module_index
            row_counter[next_module_index] = 0
            next_module_index += 1
        module_index = heading_index[current_heading]
        row_counter[module_index] += 1

        module_name = MODULE_PREFIX_RE.sub("", current_heading)
        priority = _clean(cells[0]) if len(cells) > 0 else ""
        feature = _clean(cells[1]) if len(cells) > 1 else ""
        summary = _clean(cells[2]) if len(cells) > 2 else ""
        acceptance = _clean(cells[3]) if len(cells) > 3 else ""

        # Aggregate detection keys off the acceptance column, requiring the
        # type-count word 种 (see AGGREGATE_RE). Only a requirement that counts
        # "N 种" distinct things is modeled as count-over-siblings.
        agg_match = AGGREGATE_RE.search(acceptance)
        aggregate = bool(agg_match)
        min_covered = int(agg_match.group(1) or agg_match.group(2)) if aggregate else 2

        reqs.append(
            {
                "id": f"REQ-M{module_index:02d}-{row_counter[module_index]:02d}",
                "module": module_name,
                "module_index": module_index,
                "feature": feature,
                "summary": summary,
                "acceptance": acceptance,
                "priority": priority,
                "aggregate": aggregate,
                "min_covered": min_covered,
            }
        )

    return reqs


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract requirement items from a requirements markdown doc.")
    parser.add_argument("requirements", type=Path, help="Path to the requirements markdown doc")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    reqs = extract_requirements(args.requirements.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(reqs, ensure_ascii=False, indent=2))
    else:
        for r in reqs:
            tag = " [aggregate]" if r["aggregate"] else ""
            print(f"{r['id']}  {r['priority']:<3} {r['module']} · {r['feature']}{tag}")
        print(f"\n{len(reqs)} requirement(s) extracted from {len({r['module'] for r in reqs})} module(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
