#!/usr/bin/env python3
"""Validate the functional gate and score applicable style-identity dimensions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
FUNCTION_KEYS = (
    "navigation",
    "operations",
    "data_relationships",
    "critical_states",
    "keyboard_focus",
    "responsive",
    "theme_capability",
    "accessibility",
)
WEIGHT_LINE = re.compile(r"`(?P<body>[a-z0-9 -]+(?:\s*/\s*[a-z0-9 -]+)+)`", re.IGNORECASE)
WEIGHT_ITEM = re.compile(r"([a-z][a-z-]*)\s+(\d+(?:\.\d+)?)", re.IGNORECASE)


def gate_value(value) -> tuple[bool, object]:
    if isinstance(value, bool):
        return value, None
    if isinstance(value, dict) and isinstance(value.get("passed"), bool):
        return value["passed"], value.get("evidence")
    raise ValueError("must be a boolean or an object with boolean 'passed'")


def load_weights(style: str) -> dict[str, float]:
    identity = SKILL_ROOT / "references" / "styles" / style / "identity.md"
    if not identity.is_file():
        raise ValueError(f"unknown style or missing identity.md: {style}")
    text = identity.read_text(encoding="utf-8")
    for match in WEIGHT_LINE.finditer(text):
        weights = {name: float(value) for name, value in WEIGHT_ITEM.findall(match.group("body"))}
        if len(weights) >= 7 and abs(sum(weights.values()) - 100) < 0.001:
            return weights
    raise ValueError(f"identity.md has no parseable 100-point weight line: {style}")


def dimension_value(name: str, value) -> tuple[bool, float | None, object]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return True, float(value), None
    if not isinstance(value, dict):
        raise ValueError(f"dimension '{name}' must be a number or object")
    applicable = value.get("applicable", True)
    if not isinstance(applicable, bool):
        raise ValueError(f"dimension '{name}'.applicable must be boolean")
    if not applicable:
        return False, None, value.get("reason")
    score = value.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ValueError(f"dimension '{name}'.score must be numeric")
    return True, float(score), value.get("evidence")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--input", help="JSON evaluation file")
    source_group.add_argument("--spec-json", help="Inline JSON evaluation")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    try:
        if args.input:
            source = Path(args.input).expanduser().resolve()
            data = json.loads(source.read_text(encoding="utf-8"))
        else:
            data = json.loads(args.spec_json)
        style = str(data.get("style", ""))
        weights = load_weights(style)
        gate = data.get("functional_gate")
        if not isinstance(gate, dict):
            raise ValueError("functional_gate must be an object")
        missing_gate = [key for key in FUNCTION_KEYS if key not in gate]
        if missing_gate:
            raise ValueError(f"functional_gate missing: {', '.join(missing_gate)}")

        gate_results = {}
        for key in FUNCTION_KEYS:
            passed, evidence = gate_value(gate[key])
            gate_results[key] = {"passed": passed, "evidence": evidence}

        dimensions = data.get("dimensions")
        if not isinstance(dimensions, dict):
            raise ValueError("dimensions must be an object")
        missing_dimensions = [name for name in weights if name not in dimensions]
        if missing_dimensions:
            raise ValueError(f"dimensions missing: {', '.join(missing_dimensions)}")

        dimension_results = {}
        weighted_total = 0.0
        applicable_weight = 0.0
        for name, weight in weights.items():
            applicable, score, evidence = dimension_value(name, dimensions[name])
            if score is not None and not 0 <= score <= 100:
                raise ValueError(f"dimension '{name}' score must be between 0 and 100")
            dimension_results[name] = {
                "applicable": applicable,
                "score": score,
                "weight": weight,
                "evidence": evidence,
            }
            if applicable:
                weighted_total += score * weight
                applicable_weight += weight
        if applicable_weight == 0:
            raise ValueError("at least one style dimension must be applicable")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))

    score = round(weighted_total / applicable_weight, 1)
    gate_passed = all(result["passed"] for result in gate_results.values())
    missing_evidence = [
        f"functional_gate.{name}"
        for name, result in gate_results.items()
        if result["passed"] and not result["evidence"]
    ]
    missing_evidence.extend(
        f"dimensions.{name}"
        for name, result in dimension_results.items()
        if result["applicable"] and not result["evidence"]
    )
    missing_evidence.extend(
        f"dimensions.{name}.reason"
        for name, result in dimension_results.items()
        if not result["applicable"] and not result["evidence"]
    )
    evidence_verified = not missing_evidence
    rating = "stable" if score >= 90 else "deliverable" if score >= 80 else "theme-only" if score >= 70 else "incomplete"
    status = "pass" if gate_passed and score >= 80 and evidence_verified else "blocked" if not gate_passed else "unverified" if not evidence_verified else "revise"
    report = {
        "style": style,
        "status": status,
        "functional_gate_passed": gate_passed,
        "failed_functional_checks": [name for name, result in gate_results.items() if not result["passed"]],
        "style_score": score,
        "style_rating": rating,
        "applicable_weight": applicable_weight,
        "evidence_verified": evidence_verified,
        "missing_evidence": missing_evidence,
        "functional_gate": gate_results,
        "dimensions": dimension_results,
    }

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Style transfer: {style} · {status}")
        print(f"- functional gate: {'pass' if gate_passed else 'fail'}")
        if not gate_passed:
            print(f"- failed: {', '.join(report['failed_functional_checks'])}")
        print(f"- style identity: {score}/100 ({rating}, applicable weight {applicable_weight:g})")
        if missing_evidence:
            print(f"- missing evidence: {', '.join(missing_evidence)}")
        for name, result in dimension_results.items():
            value = "N/A" if not result["applicable"] else f"{result['score']:g}"
            print(f"  - {name}: {value} · weight {result['weight']:g}")
    return 0 if status == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
