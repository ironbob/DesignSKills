#!/usr/bin/env python3
"""Create or validate the evidence manifest for a full-app UI style migration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RESOLVED_STATUSES = {"verified", "n/a"}
COMPONENT_STATES = ("default", "hover", "pressed", "focus-visible", "disabled")
JOURNEY_STATES = ("loading", "empty", "error", "offline", "permission")
VIEWPORTS = ("wide", "narrow")
DISCOVERED_SECTIONS = (
    "source_files", "routes", "components", "interactive_elements",
    "overlays", "themes", "breakpoints",
)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def inventory_from(report: dict[str, Any]) -> dict[str, Any]:
    inventory = report.get("inventory", report)
    if not isinstance(inventory, dict):
        raise ValueError("report.inventory must be an object")
    return inventory


def item_ids(inventory: dict[str, Any], section: str) -> list[str]:
    payload = inventory.get(section, {})
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return sorted({str(item["id"]) for item in items if isinstance(item, dict) and item.get("id")})


def blank_entry(identifier: str) -> dict[str, str]:
    return {"id": identifier, "status": "unverified", "evidence": "", "reason": ""}


def build_manifest(report: dict[str, Any], report_path: Path) -> dict[str, Any]:
    inventory = inventory_from(report)
    manifest: dict[str, Any] = {
        "version": 1,
        "generated_from": str(report_path.resolve()),
        "source_files": [blank_entry(value) for value in item_ids(inventory, "source_files")],
        "routes": [blank_entry(value) for value in item_ids(inventory, "routes")],
        "components": [],
        "interactive_elements": [blank_entry(value) for value in item_ids(inventory, "interactive_elements")],
        "overlays": [blank_entry(value) for value in item_ids(inventory, "overlays")],
        "themes": [blank_entry(value) for value in item_ids(inventory, "themes")],
        "breakpoints": [blank_entry(value) for value in item_ids(inventory, "breakpoints")],
        "journey_states": [blank_entry(value) for value in JOURNEY_STATES],
        "viewports": [blank_entry(value) for value in VIEWPORTS],
        "waivers": [],
    }
    if not manifest["themes"]:
        manifest["themes"] = [blank_entry("current-theme")]
    for component in item_ids(inventory, "components"):
        entry: dict[str, Any] = blank_entry(component)
        entry["states"] = [blank_entry(state) for state in COMPONENT_STATES]
        manifest["components"].append(entry)
    return manifest


def validate_entry(entry: Any, location: str, blockers: list[dict[str, str]]) -> bool:
    if not isinstance(entry, dict):
        blockers.append({"kind": "invalid_entry", "target": location, "message": "entry must be an object"})
        return False
    status = entry.get("status")
    if status not in RESOLVED_STATUSES:
        blockers.append({"kind": "unverified", "target": location, "message": "status must be verified or n/a"})
        return False
    if status == "verified" and not str(entry.get("evidence", "")).strip():
        blockers.append({"kind": "missing_evidence", "target": location, "message": "verified requires evidence"})
        return False
    if status == "n/a" and not str(entry.get("reason", "")).strip():
        blockers.append({"kind": "missing_reason", "target": location, "message": "n/a requires a reason"})
        return False
    return True


def indexed_entries(manifest: dict[str, Any], section: str, blockers: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    entries = manifest.get(section, [])
    if not isinstance(entries, list):
        blockers.append({"kind": "invalid_section", "target": section, "message": "section must be an array"})
        return {}
    indexed: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or not str(entry.get("id", "")).strip():
            blockers.append({"kind": "invalid_entry", "target": f"{section}[{index}]", "message": "entry requires id"})
            continue
        identifier = str(entry["id"])
        if identifier in indexed:
            blockers.append({"kind": "duplicate_entry", "target": f"{section}:{identifier}", "message": "id must be unique"})
            continue
        indexed[identifier] = entry
    return indexed


def waiver_matches(waivers: list[Any], kind: str, examples: list[str], count: int) -> bool:
    valid_targets: set[str] = set()
    for waiver in waivers:
        if not isinstance(waiver, dict) or waiver.get("kind") != kind:
            continue
        if not str(waiver.get("reason", "")).strip():
            continue
        target = str(waiver.get("target", ""))
        if target == "*":
            return True
        if target:
            valid_targets.add(target)
    return count == len(examples) and bool(examples) and set(examples).issubset(valid_targets)


def validate(report: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    inventory = inventory_from(report)
    blockers: list[dict[str, str]] = []
    resolved = 0
    total = 0

    if manifest.get("version") != 1:
        blockers.append({"kind": "invalid_version", "target": "version", "message": "manifest version must be 1"})

    indexes = {section: indexed_entries(manifest, section, blockers) for section in DISCOVERED_SECTIONS}
    for section in DISCOVERED_SECTIONS:
        expected = item_ids(inventory, section)
        expected_set = set(expected)
        for identifier in expected:
            total += 1
            entry = indexes[section].get(identifier)
            if entry is None:
                blockers.append({"kind": "missing_discovered_item", "target": f"{section}:{identifier}", "message": "discovered item is absent from manifest"})
            elif validate_entry(entry, f"{section}:{identifier}", blockers):
                resolved += 1
        for identifier in sorted(set(indexes[section]) - expected_set):
            total += 1
            if validate_entry(indexes[section][identifier], f"{section}:{identifier}", blockers):
                resolved += 1

    component_index = indexes["components"]
    for component, entry in sorted(component_index.items()):
        state_entries = entry.get("states", [])
        if not isinstance(state_entries, list):
            blockers.append({"kind": "invalid_section", "target": f"components:{component}:states", "message": "states must be an array"})
            continue
        state_index: dict[str, dict[str, Any]] = {}
        for index, value in enumerate(state_entries):
            if not isinstance(value, dict) or not str(value.get("id", "")).strip():
                blockers.append({"kind": "invalid_entry", "target": f"components:{component}:states[{index}]", "message": "state requires id"})
                continue
            state_id = str(value["id"])
            if state_id in state_index:
                blockers.append({"kind": "duplicate_entry", "target": f"components:{component}:states:{state_id}", "message": "state id must be unique"})
                continue
            state_index[state_id] = value
        for state in COMPONENT_STATES:
            total += 1
            state_entry = state_index.get(state)
            location = f"components:{component}:states:{state}"
            if state_entry is None:
                blockers.append({"kind": "missing_component_state", "target": location, "message": "state is absent from manifest"})
            elif validate_entry(state_entry, location, blockers):
                resolved += 1
        for state in sorted(set(state_index) - set(COMPONENT_STATES)):
            total += 1
            if validate_entry(state_index[state], f"components:{component}:states:{state}", blockers):
                resolved += 1

    for section, required in (("journey_states", JOURNEY_STATES), ("viewports", VIEWPORTS)):
        index = indexed_entries(manifest, section, blockers)
        for identifier in required:
            total += 1
            entry = index.get(identifier)
            if entry is None:
                blockers.append({"kind": "missing_required_item", "target": f"{section}:{identifier}", "message": "required runtime item is absent"})
            elif validate_entry(entry, f"{section}:{identifier}", blockers):
                resolved += 1
        for identifier in sorted(set(index) - set(required)):
            total += 1
            if validate_entry(index[identifier], f"{section}:{identifier}", blockers):
                resolved += 1

    waivers = manifest.get("waivers", [])
    if not isinstance(waivers, list):
        blockers.append({"kind": "invalid_section", "target": "waivers", "message": "waivers must be an array"})
        waivers = []
    for blocker in report.get("coverage", {}).get("blockers", []):
        if not isinstance(blocker, dict):
            continue
        kind = str(blocker.get("kind", "unknown"))
        if kind == "runtime_inventory_unverified":
            continue
        examples = [str(value) for value in blocker.get("examples", [])]
        count = int(blocker.get("count", len(examples)))
        if not waiver_matches(waivers, kind, examples, count):
            blockers.append({
                "kind": "unwaived_scan_blocker",
                "target": kind,
                "message": f"{count} scan item(s) require coverage or a reasoned waiver",
            })

    complete = not blockers and resolved == total
    return {
        "complete": complete,
        "claim_full_coverage": complete,
        "resolved_units": resolved,
        "total_units": total,
        "coverage_ratio": round(resolved / total, 4) if total else 1.0,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, help="JSON output from audit-ui-style.py")
    parser.add_argument("--manifest", help="Evidence manifest to validate")
    parser.add_argument("--init", dest="init_path", help="Write an unverified draft manifest")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    report_path = Path(args.report).expanduser().resolve()
    try:
        report = read_json(report_path)
        if args.init_path:
            output = Path(args.init_path).expanduser().resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(build_manifest(report, report_path), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Draft coverage manifest: {output}")
            return 0
        if not args.manifest:
            parser.error("--manifest is required unless --init is used")
        result = validate(report, read_json(Path(args.manifest).expanduser().resolve()))
    except ValueError as error:
        parser.error(str(error))

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        label = "complete" if result["complete"] else "incomplete"
        print(f"UI coverage: {label} · {result['resolved_units']}/{result['total_units']} units")
        for blocker in result["blockers"][:20]:
            print(f"- {blocker['kind']}: {blocker['target']} — {blocker['message']}")
        if len(result["blockers"]) > 20:
            print(f"- … {len(result['blockers']) - 20} more blocker(s); use --format json")
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
