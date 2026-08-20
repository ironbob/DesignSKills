#!/usr/bin/env python3
"""Run contract, document, and structural gates with compact output."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_contract import validate as validate_contract
from validate_doc import validate as validate_doc
from validate_gate import run as validate_gate


def _report_summary(report: Any) -> dict[str, Any]:
    denominator = len(report.passed) + len(report.warns)
    warning_pass_rate = len(report.passed) / denominator if denominator else 1.0
    return {
        "errors": len(report.errors),
        "warnings": len(report.warns),
        "passed": len(report.passed),
        "warning_pass_rate": warning_pass_rate,
        "ok": not report.errors and warning_pass_rate >= 0.80,
        "error_details": report.errors,
        "warning_details": report.warns,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate all arch-first delivery artifacts")
    parser.add_argument("contract", type=Path)
    parser.add_argument("doc", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--logging-ratio", type=float, default=0.6)
    parser.add_argument("--no-source-dependency-check", action="store_true",
                        help="Disable source-reference versus depends_on comparison")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--summary", action="store_true", help="Compact output (default)")
    mode.add_argument("--verbose", action="store_true", help="Print every successful rule")
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    for path, label in ((args.contract, "contract"), (args.doc, "doc")):
        if not path.exists():
            parser.error(f"{label} does not exist: {path}")
    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        parser.error(f"invalid contract JSON: {exc}")
    if not isinstance(contract, dict):
        parser.error("contract top level must be an object")

    contract_report = validate_contract(contract, args.contract)
    doc_report = validate_doc(args.doc)
    gate_report = validate_gate(
        contract,
        args.doc.read_text(encoding="utf-8"),
        args.root.resolve(),
        args.logging_ratio,
        not args.no_source_dependency_check,
    )
    contract_summary = _report_summary(contract_report)
    doc_summary = _report_summary(doc_report)
    declared = (contract.get("gate") or {}).get("verdict")
    gate_ok = gate_report["verdict"] == "go" and declared == gate_report["verdict"]
    result = {
        "contract": contract_summary,
        "document": doc_summary,
        "gates": {
            "architecture": gate_report["architecture"],
            "logging": gate_report["logging"],
            "coverage": gate_report["coverage"],
            "verification": gate_report["verification"],
            "verdict": gate_report["verdict"],
            "declared_verdict": declared,
            "issues": gate_report["issues"],
            "ok": gate_ok,
        },
    }
    result["ok"] = contract_summary["ok"] and doc_summary["ok"] and gate_ok

    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.verbose:
        print(f"=== validate_all: {args.contract} + {args.doc} ===")
        for label, report in (("contract", contract_report), ("document", doc_report)):
            print(f"\n[{label}]")
            for line in report.errors + report.warns + report.passed:
                print(line)
        print("\n[gates]")
        for issue in gate_report["issues"]:
            print(f"[{issue['severity']}] {issue['gate']}/{issue['role_or_step']}: {issue['problem']}")
    else:
        print(
            f"contract: {'PASS' if contract_summary['ok'] else 'FAIL'} "
            f"({contract_summary['passed']} passed, {contract_summary['warnings']} warnings, "
            f"{contract_summary['errors']} errors)"
        )
        print(
            f"document: {'PASS' if doc_summary['ok'] else 'FAIL'} "
            f"({doc_summary['passed']} passed, {doc_summary['warnings']} warnings, "
            f"{doc_summary['errors']} errors)"
        )
        print(
            "gates: " + ("PASS" if gate_ok else "FAIL") + " "
            f"(architecture={gate_report['architecture']}, logging={gate_report['logging']}, "
            f"coverage={gate_report['coverage']}, verification={gate_report['verification']})"
        )
        if not result["ok"]:
            for detail in contract_summary["error_details"] + doc_summary["error_details"]:
                print(detail)
            for issue in gate_report["issues"]:
                print(f"[{issue['severity']}] {issue['gate']}/{issue['role_or_step']}: {issue['problem']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
