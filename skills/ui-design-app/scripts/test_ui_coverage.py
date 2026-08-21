#!/usr/bin/env python3
"""Regression tests for the evidence coverage gate."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate-ui-coverage.py")
SPEC = importlib.util.spec_from_file_location("validate_ui_coverage", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def resolve(value: object) -> None:
    if isinstance(value, dict):
        if "status" in value:
            value["status"] = "verified"
            value["evidence"] = "tests/ui.spec.ts:42"
        for child in value.values():
            resolve(child)
    elif isinstance(value, list):
        for child in value:
            resolve(child)


class UiCoverageTests(unittest.TestCase):
    def report(self) -> dict:
        def section(*ids: str) -> dict:
            return {"count": len(ids), "items": [{"id": value} for value in ids]}

        return {
            "inventory": {
                "source_files": section("src/App.tsx"),
                "routes": section("/"),
                "components": section("App"),
                "interactive_elements": section("button"),
                "overlays": section("dialog"),
                "themes": section("dark"),
                "breakpoints": section("max-width: 600px"),
            },
            "coverage": {
                "blockers": [
                    {"kind": "unsupported_ui_extension", "count": 1, "examples": ["src/Panel.cs"]},
                    {"kind": "runtime_inventory_unverified", "count": 1, "examples": ["runtime"]},
                ]
            },
        }

    def test_draft_is_incomplete(self) -> None:
        report = self.report()
        manifest = MODULE.build_manifest(report, Path("report.json"))
        result = MODULE.validate(report, manifest)
        self.assertFalse(result["complete"])
        self.assertGreater(result["total_units"], 0)
        self.assertTrue(any(item["kind"] == "unverified" for item in result["blockers"]))

    def test_resolved_manifest_passes_with_reasoned_waiver(self) -> None:
        report = self.report()
        manifest = MODULE.build_manifest(report, Path("report.json"))
        resolve(manifest)
        manifest["waivers"] = [{
            "kind": "unsupported_ui_extension",
            "target": "src/Panel.cs",
            "reason": "Desktop-only diagnostic panel is outside the shipped application.",
        }]
        result = MODULE.validate(report, manifest)
        self.assertTrue(result["complete"], result["blockers"])
        self.assertEqual(result["resolved_units"], result["total_units"])

    def test_missing_component_state_blocks_full_claim(self) -> None:
        report = self.report()
        manifest = MODULE.build_manifest(report, Path("report.json"))
        resolve(manifest)
        manifest["waivers"] = [{
            "kind": "unsupported_ui_extension", "target": "*", "reason": "Reviewed outside scanner"
        }]
        manifest["components"][0]["states"] = manifest["components"][0]["states"][:-1]
        result = MODULE.validate(report, manifest)
        self.assertFalse(result["complete"])
        self.assertTrue(any(item["kind"] == "missing_component_state" for item in result["blockers"]))

    def test_runtime_discovered_extra_state_must_also_resolve(self) -> None:
        report = self.report()
        manifest = MODULE.build_manifest(report, Path("report.json"))
        resolve(manifest)
        manifest["waivers"] = [{
            "kind": "unsupported_ui_extension", "target": "*", "reason": "Reviewed outside scanner"
        }]
        manifest["components"][0]["states"].append({
            "id": "editing", "status": "unverified", "evidence": "", "reason": ""
        })
        result = MODULE.validate(report, manifest)
        self.assertFalse(result["complete"])
        self.assertTrue(any(item["target"].endswith(":editing") for item in result["blockers"]))


if __name__ == "__main__":
    unittest.main()
