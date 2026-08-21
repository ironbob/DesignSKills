#!/usr/bin/env python3
"""Regression tests for scaffolding, single-source rendering, and compact validation."""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from init_contract import build_contract
from render_arch import render
from run_verification import execute
from validate_contract import validate as validate_contract
from validate_doc import validate as validate_doc
from validate_gate import run as validate_gate


class ContractScaffoldTests(unittest.TestCase):
    def _args(self, profile: str) -> argparse.Namespace:
        return argparse.Namespace(
            profile=profile,
            stack="JVM",
            feature="sample-feature",
            title="Sample feature",
            analyzed_at="2026-08-20",
            proposal_revision=2,
            candidate="ALT-1",
            profile_evidence="User selected the profile",
            design_evidence="User confirmed revision 2 after proposal",
            ui_framework=None,
        )

    def test_profile_scaffolds_are_risk_sized(self) -> None:
        light = build_contract(self._args("light"))
        standard = build_contract(self._args("standard"))
        high = build_contract(self._args("high_risk"))
        self.assertEqual(1, len(light["design_decision"]["candidates"]))
        self.assertEqual(2, len(standard["design_decision"]["candidates"]))
        self.assertEqual(2, len(high["design_decision"]["candidates"]))
        self.assertEqual([], light["design_decision"]["risk_spikes"])
        self.assertEqual(1, len(high["design_decision"]["risk_spikes"]))
        self.assertEqual(3, light["design_decision"]["complexity_budget"]["recommended_max_roles"])
        self.assertEqual("later_user_message", high["interaction_confirmation"]["design_confirmation"]["source"])
        self.assertEqual("no-go", high["gate"]["verdict"])
        self.assertEqual(2, high["contract_version"])
        self.assertEqual("Code Complete, Second Edition", high["guidance"]["primary_source"])
        self.assertEqual(9, len(high["construction_review"]["items"]))


class VerificationRunnerTests(unittest.TestCase):
    def _contract(self, cwd: str = ".") -> dict:
        return {
            "verification": {
                "commands": [{
                    "id": "VCMD-1",
                    "argv": ["python3", "-c", "print('verified')"],
                    "inputs": ["input.txt"],
                    "cwd": cwd,
                    "timeout_seconds": 10,
                    "required": True,
                    "covers": ["affected_tests"],
                    "status": "pending",
                    "execution": None,
                }],
                "checks": [{
                    "target": "runner",
                    "method": "static_check",
                    "status": "pending",
                    "evidence": "pending",
                    "command_ids": ["VCMD-1"],
                }],
            },
        }

    def test_runner_records_machine_evidence_without_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            data = self._contract()
            (Path(temp) / "input.txt").write_text("input", encoding="utf-8")
            failures, executed = execute(data, Path(temp).resolve(), set(), 200)
        self.assertEqual(0, failures)
        self.assertEqual(["VCMD-1"], executed)
        command = data["verification"]["commands"][0]
        self.assertEqual("passed", command["status"])
        self.assertEqual(0, command["execution"]["exit_code"])
        self.assertEqual("passed", data["verification"]["checks"][0]["status"])

    def test_runner_rejects_cwd_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "input.txt").write_text("input", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escapes root"):
                execute(self._contract("../outside"), Path(temp).resolve(), set(), 200)

    def test_missing_executable_is_recorded_as_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            data = self._contract()
            (Path(temp) / "input.txt").write_text("input", encoding="utf-8")
            data["verification"]["commands"][0]["argv"] = ["definitely-not-an-executable"]
            failures, _ = execute(data, Path(temp).resolve(), set(), 200)
        command = data["verification"]["commands"][0]
        self.assertEqual(1, failures)
        self.assertEqual("failed", command["status"])
        self.assertIsNone(command["execution"]["exit_code"])
        self.assertTrue(command["execution"]["stderr_tail"])

    def test_validator_detects_command_drift_after_execution(self) -> None:
        skill_root = Path(__file__).resolve().parents[1]
        path = skill_root / "examples/2026-06-28-example-design-contract.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["verification"]["commands"][0]["argv"].append("drift")
        report = validate_contract(data, path)
        self.assertTrue(any("argv 已在执行后漂移" in item for item in report.errors))


class RenderAndValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_root = Path(__file__).resolve().parents[1]
        self.repo_root = self.skill_root.parents[1]
        self.example_contract_path = self.skill_root / "examples/2026-06-28-example-design-contract.json"
        self.contract = json.loads(self.example_contract_path.read_text(encoding="utf-8"))

    def test_rendered_example_passes_document_and_gate_validation(self) -> None:
        document = render(self.contract)
        with tempfile.TemporaryDirectory() as temp:
            doc_path = Path(temp) / "arch.md"
            doc_path.write_text(document, encoding="utf-8")
            report = validate_doc(doc_path)
            self.assertEqual([], report.errors)
            gates = validate_gate(self.contract, document, self.repo_root, 0.6)
            self.assertEqual("go", gates["verdict"], gates["issues"])

    def test_validate_all_summary_is_three_lines(self) -> None:
        script = Path(__file__).with_name("validate_all.py")
        with tempfile.TemporaryDirectory() as temp:
            doc_path = Path(temp) / "arch.md"
            doc_path.write_text(render(self.contract), encoding="utf-8")
            completed = subprocess.run(
                ["python3", str(script), str(self.example_contract_path), str(doc_path),
                 "--root", str(self.repo_root), "--summary"],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertEqual(3, len(completed.stdout.strip().splitlines()), completed.stdout)


if __name__ == "__main__":
    unittest.main()
