#!/usr/bin/env python3
"""Validate a ui-layout-qa full-audit page inventory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PLATFORMS = {"web", "desktop", "mobile"}
REACHABILITY = {"reachable", "conditional", "blocked"}
RESULTS = {"verified", "audited_unverified", "not_applicable", "blocked", "pending"}
BASE_CHECKS = {"default", "long_text", "narrow"}


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any) -> bool:
    return isinstance(value, list) and all(nonempty_string(item) for item in value)


def validate_inventory(document: Any) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    summary: dict[str, Any] = {
        "pages": 0,
        "reachable_or_conditional": 0,
        "blocked_pages": 0,
        "pending_checks": 0,
        "blocked_checks": 0,
        "audited_unverified_checks": 0,
        "verified_checks": 0,
        "not_applicable_checks": 0,
    }

    if not isinstance(document, dict):
        return ["root must be a JSON object"], summary
    if not nonempty_string(document.get("audit_scope")):
        errors.append("audit_scope must be a non-empty string")
    pages = document.get("pages")
    if not isinstance(pages, list) or not pages:
        return errors + ["pages must be a non-empty array"], summary

    seen_ids: set[str] = set()
    for index, page in enumerate(pages):
        prefix = f"pages[{index}]"
        if not isinstance(page, dict):
            errors.append(f"{prefix} must be an object")
            continue
        page_id = page.get("id")
        if not nonempty_string(page_id):
            errors.append(f"{prefix}.id must be a non-empty string")
            page_id = None
        elif page_id in seen_ids:
            errors.append(f"duplicate page id: {page_id}")
        else:
            seen_ids.add(page_id)
        if not nonempty_string(page.get("name")):
            errors.append(f"{prefix}.name must be a non-empty string")
        if page.get("platform") not in PLATFORMS:
            errors.append(f"{prefix}.platform must be one of {sorted(PLATFORMS)}")
        if not string_list(page.get("entry_evidence")) or not page.get("entry_evidence"):
            errors.append(f"{prefix}.entry_evidence must be a non-empty array of strings")
        reachability = page.get("reachability")
        if reachability not in REACHABILITY:
            errors.append(f"{prefix}.reachability must be one of {sorted(REACHABILITY)}")
            continue

        summary["pages"] += 1
        if reachability == "blocked":
            summary["blocked_pages"] += 1
            reason = page.get("reason")
            if not nonempty_string(reason):
                errors.append(f"{prefix}.reason is required when reachability is blocked")
            continue
        summary["reachable_or_conditional"] += 1

        required_states = page.get("required_states", [])
        if not string_list(required_states):
            errors.append(f"{prefix}.required_states must be an array of non-empty strings")
            required_states = []
        if len(set(required_states)) != len(required_states):
            errors.append(f"{prefix}.required_states must not contain duplicates")

        checks = page.get("checks")
        if not isinstance(checks, list):
            errors.append(f"{prefix}.checks must be an array")
            continue
        check_names: set[str] = set()
        for check_index, check in enumerate(checks):
            check_prefix = f"{prefix}.checks[{check_index}]"
            if not isinstance(check, dict):
                errors.append(f"{check_prefix} must be an object")
                continue
            name = check.get("name")
            result = check.get("result")
            if not nonempty_string(name):
                errors.append(f"{check_prefix}.name must be a non-empty string")
                continue
            if name in check_names:
                errors.append(f"{prefix}.checks has duplicate name: {name}")
            check_names.add(name)
            if result not in RESULTS:
                errors.append(f"{check_prefix}.result must be one of {sorted(RESULTS)}")
                continue
            if result == "verified":
                if not string_list(check.get("evidence")) or not check.get("evidence"):
                    errors.append(f"{check_prefix}.evidence is required for verified")
                summary["verified_checks"] += 1
            elif result in {"not_applicable", "blocked", "audited_unverified"}:
                if not nonempty_string(check.get("reason")):
                    errors.append(f"{check_prefix}.reason is required for {result}")
                summary[f"{result}_checks"] = summary.get(f"{result}_checks", 0) + 1
            elif result == "pending":
                summary["pending_checks"] += 1

        required_checks = BASE_CHECKS | {f"state:{state}" for state in required_states}
        missing = sorted(required_checks - check_names)
        if missing:
            errors.append(f"{prefix}.checks is missing required entries: {', '.join(missing)}")

    return errors, summary


def completion_failures(document: dict[str, Any], require_verified: bool) -> list[str]:
    failures: list[str] = []
    for page in document.get("pages", []):
        if not isinstance(page, dict):
            continue
        page_id = page.get("id", "<invalid>")
        reachability = page.get("reachability")
        if reachability == "blocked":
            failures.append(f"{page_id}: page is blocked")
            continue
        for check in page.get("checks", []):
            if not isinstance(check, dict):
                continue
            result = check.get("result")
            name = check.get("name", "<invalid>")
            if result in {"pending", "blocked"}:
                failures.append(f"{page_id}/{name}: {result}")
            elif require_verified and result == "audited_unverified":
                failures.append(f"{page_id}/{name}: audited_unverified")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path, help="Path to page-inventory.json")
    parser.add_argument(
        "--require-coverage-complete",
        action="store_true",
        help="Fail if a page or required check is blocked or pending.",
    )
    parser.add_argument(
        "--require-verified",
        action="store_true",
        help="Also fail when a required check is audited_unverified.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    if args.require_verified:
        args.require_coverage_complete = True

    try:
        document = json.loads(args.inventory.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read inventory: {exc}", file=sys.stderr)
        return 2

    errors, summary = validate_inventory(document)
    completion = []
    if not errors and args.require_coverage_complete:
        completion = completion_failures(document, args.require_verified)
    result = {
        "valid": not errors,
        "coverage_complete": not errors and not completion_failures(document, False),
        "fully_verified": not errors and not completion_failures(document, True),
        "summary": summary,
        "errors": errors,
        "completion_failures": completion,
    }

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Inventory valid: {'yes' if result['valid'] else 'no'}")
        print(f"Coverage complete: {'yes' if result['coverage_complete'] else 'no'}")
        print(f"Fully verified: {'yes' if result['fully_verified'] else 'no'}")
        print("Summary: " + ", ".join(f"{key}={value}" for key, value in summary.items()))
        for error in errors:
            print(f"ERROR: {error}")
        for failure in completion:
            print(f"INCOMPLETE: {failure}")
    return 1 if errors or completion else 0


if __name__ == "__main__":
    raise SystemExit(main())
