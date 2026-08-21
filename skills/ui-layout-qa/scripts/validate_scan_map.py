#!/usr/bin/env python3
"""Validate ui-layout-qa text scan maps and their user-confirmation gate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MODES = {"incremental", "full_audit", "screenshot_observation"}
EVIDENCE_TYPES = {"code", "screenshot", "runtime"}
CONFIRMATION_STATUSES = {"pending", "user_confirmed", "needs_revision"}


def nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def string_list(value: Any) -> bool:
    return isinstance(value, list) and all(nonempty_string(item) for item in value)


def safe_relative_file(root: Path, relative: Any) -> Path | None:
    if not nonempty_string(relative):
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def map_file_errors(path: Path, prefix: str) -> list[str]:
    if not path.is_file():
        return [f"{prefix}.map_file does not exist: {path}"]
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{prefix}.map_file cannot be read: {exc}"]
    lines = [line for line in content.splitlines() if line.strip()]
    errors = []
    if len(lines) < 5:
        errors.append(f"{prefix}.map_file must contain a compact structural drawing of at least 5 non-empty lines")
    for required in ("Target:", "Source:", "Unknown:"):
        if required not in content:
            errors.append(f"{prefix}.map_file must contain {required}")
    if not any(character in content for character in "+|-[]"):
        errors.append(f"{prefix}.map_file must contain a text-drawn structure")
    return errors


def overview_file_errors(path: Path) -> list[str]:
    if not path.is_file():
        return [f"overview_file does not exist: {path}"]
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"overview_file cannot be read: {exc}"]
    if len([line for line in content.splitlines() if line.strip()]) < 2:
        return ["overview_file must contain at least two non-empty lines"]
    return []


def validate_manifest(document: Any, artifact_root: Path, phase: str) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    summary = {"targets": 0, "pending": 0, "confirmed": 0, "needs_revision": 0}
    if not isinstance(document, dict):
        return ["root must be a JSON object"], summary
    if document.get("mode") not in MODES:
        errors.append(f"mode must be one of {sorted(MODES)}")
    if not nonempty_string(document.get("scan_scope")):
        errors.append("scan_scope must be a non-empty string")
    overview_path = safe_relative_file(artifact_root, document.get("overview_file"))
    if overview_path is None:
        errors.append("overview_file must be a safe relative path under artifact_root")
    else:
        errors.extend(overview_file_errors(overview_path))
    targets = document.get("targets")
    if not isinstance(targets, list) or not targets:
        return errors + ["targets must be a non-empty array"], summary

    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    for index, target in enumerate(targets):
        prefix = f"targets[{index}]"
        if not isinstance(target, dict):
            errors.append(f"{prefix} must be an object")
            continue
        target_id = target.get("id")
        if not nonempty_string(target_id):
            errors.append(f"{prefix}.id must be a non-empty string")
        elif target_id in seen_ids:
            errors.append(f"duplicate target id: {target_id}")
        else:
            seen_ids.add(target_id)
        if not nonempty_string(target.get("label")):
            errors.append(f"{prefix}.label must be a non-empty string")
        if not string_list(target.get("source_anchors")) or not target.get("source_anchors"):
            errors.append(f"{prefix}.source_anchors must be a non-empty array of strings")
        evidence_types = target.get("evidence_types")
        if not isinstance(evidence_types, list) or not evidence_types:
            errors.append(f"{prefix}.evidence_types must be a non-empty array")
        elif any(item not in EVIDENCE_TYPES for item in evidence_types):
            errors.append(f"{prefix}.evidence_types must only contain {sorted(EVIDENCE_TYPES)}")
        if not string_list(target.get("unknowns", [])):
            errors.append(f"{prefix}.unknowns must be an array of non-empty strings")
        if not isinstance(target.get("revision"), int) or target["revision"] < 1:
            errors.append(f"{prefix}.revision must be a positive integer")

        relative_file = target.get("map_file")
        path = safe_relative_file(artifact_root, relative_file)
        if path is None:
            errors.append(f"{prefix}.map_file must be a safe relative path under artifact_root")
        else:
            if relative_file in seen_files:
                errors.append(f"duplicate map_file: {relative_file}")
            seen_files.add(relative_file)
            errors.extend(map_file_errors(path, prefix))

        confirmation = target.get("confirmation")
        if not isinstance(confirmation, dict):
            errors.append(f"{prefix}.confirmation must be an object")
            continue
        status = confirmation.get("status")
        if status not in CONFIRMATION_STATUSES:
            errors.append(f"{prefix}.confirmation.status must be one of {sorted(CONFIRMATION_STATUSES)}")
            continue
        summary["targets"] += 1
        if status == "pending":
            summary["pending"] += 1
        elif status == "needs_revision":
            summary["needs_revision"] += 1
        else:
            summary["confirmed"] += 1
            if confirmation.get("confirmed_by") != "user":
                errors.append(f"{prefix}.confirmation.confirmed_by must be user when confirmed")
            if not nonempty_string(confirmation.get("evidence")):
                errors.append(f"{prefix}.confirmation.evidence is required when confirmed")
        if phase == "draft" and status != "pending":
            errors.append(f"{prefix}.confirmation.status must be pending during draft phase")
        if phase == "confirmed" and status != "user_confirmed":
            errors.append(f"{prefix}.confirmation.status must be user_confirmed during confirmed phase")

    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="Path to scan-map-manifest.json")
    parser.add_argument("--phase", choices=("draft", "confirmed"), required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    try:
        document = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read manifest: {exc}", file=sys.stderr)
        return 2

    errors, summary = validate_manifest(document, args.artifact_root, args.phase)
    result = {"valid": not errors, "phase": args.phase, "summary": summary, "errors": errors}
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Scan map valid: {'yes' if result['valid'] else 'no'}")
        print("Summary: " + ", ".join(f"{key}={value}" for key, value in summary.items()))
        for error in errors:
            print(f"ERROR: {error}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
