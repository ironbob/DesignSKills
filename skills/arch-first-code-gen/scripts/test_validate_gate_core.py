#!/usr/bin/env python3
"""Regression tests for architecture, reference, and verification gates."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
import json
from pathlib import Path

from validate_gate import run


class GateCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "A.java").write_text(
            "class A { void call() {} void log() { logger.info(); } }", encoding="utf-8"
        )
        (self.root / "B.java").write_text(
            "class B { void save() {} void log() { logger.info(); } }", encoding="utf-8"
        )
        self.contract = {
            "stack": "JVM",
            "design_decision": {"profile": "light"},
            "roles": [
                {"id": "ROLE-L01", "name": "A", "layer": "controller",
                 "depends_on": ["ROLE-L02"], "code_units": ["A.java"]},
                {"id": "ROLE-L02", "name": "B", "layer": "service",
                 "depends_on": [], "code_units": ["B.java"]},
            ],
            "interfaces": [{"id": "IFC-1", "name": "B.save", "provider": "ROLE-L02",
                            "consumers": ["ROLE-L01"]}],
            "business_process": [{"step": 1, "roles": ["ROLE-L01"],
                                  "code_refs": ["A.java:call"], "doc_ref": "FLOW-1"}],
            "verification": {
                "commands": [{"command": "tests", "status": "passed", "evidence": "stdout"}],
                "checks": [{"target": "flow", "status": "passed", "evidence": "stdout"}],
                "unverified": [],
            },
            "gate": {"verdict": "go"},
        }
        self.doc = """---
roles_count: 2
process_steps: 1
design_profile: light
verdict: go
---
## 角色职责清单
| 角色 | 职责 |
|---|---|
| A | entry |
| B | service |
## 接口契约
B.save
## 流程
FLOW-1
"""

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_clean_graph_and_real_refs_pass(self) -> None:
        result = run(self.contract, self.doc, self.root, 0.6)
        self.assertEqual("go", result["verdict"])

    def test_dependency_cycle_is_no_go(self) -> None:
        self.contract["roles"][1]["depends_on"] = ["ROLE-L01"]
        result = run(self.contract, self.doc, self.root, 0.6)
        self.assertEqual("no-go", result["architecture"])
        self.assertTrue(any("存在环" in issue["problem"] for issue in result["issues"]))

    def test_obvious_reverse_layer_dependency_is_no_go(self) -> None:
        self.contract["roles"][0]["layer"] = "domain"
        result = run(self.contract, self.doc, self.root, 0.6)
        self.assertEqual("no-go", result["architecture"])
        self.assertTrue(any("反向/跨层" in issue["problem"] for issue in result["issues"]))

    def test_missing_symbol_and_doc_ref_are_no_go(self) -> None:
        self.contract["business_process"][0]["code_refs"] = ["A.java:notThere"]
        self.contract["business_process"][0]["doc_ref"] = "FLOW-MISSING"
        result = run(self.contract, self.doc, self.root, 0.6)
        self.assertEqual("no-go", result["coverage"])
        problems = [issue["problem"] for issue in result["issues"]]
        self.assertTrue(any("符号不存在" in problem for problem in problems))
        self.assertTrue(any("doc_ref 未在文档出现" in problem for problem in problems))

    def test_failed_verification_is_no_go(self) -> None:
        self.contract["verification"]["checks"][0]["status"] = "failed"
        result = run(self.contract, self.doc, self.root, 0.6)
        self.assertEqual("no-go", result["verification"])

    def test_strict_cli_returns_nonzero_for_no_go(self) -> None:
        self.contract["roles"][1]["depends_on"] = ["ROLE-L01"]
        contract_path = self.root / "contract.json"
        doc_path = self.root / "arch.md"
        contract_path.write_text(json.dumps(self.contract), encoding="utf-8")
        doc_path.write_text(self.doc, encoding="utf-8")
        script = Path(__file__).with_name("validate_gate.py")
        completed = subprocess.run(
            ["python3", str(script), str(contract_path), str(doc_path),
             "--root", str(self.root), "--strict"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(1, completed.returncode, completed.stdout + completed.stderr)


class ExampleFixtureTests(unittest.TestCase):
    def test_example_fixture_compiles(self) -> None:
        javac = shutil.which("javac")
        if not javac:
            self.skipTest("javac not installed")
        skill_root = Path(__file__).resolve().parents[1]
        fixture_root = skill_root / "examples/fixtures/order-create/src"
        sources = sorted(str(path) for path in fixture_root.rglob("*.java"))
        with tempfile.TemporaryDirectory() as output:
            completed = subprocess.run(
                [javac, "-d", output, *sources], capture_output=True, text=True, check=False
            )
            if completed.returncode == 0:
                completed = subprocess.run(
                    ["java", "-cp", output, "com.x.order.OrderAggregateTest"],
                    capture_output=True, text=True, check=False,
                )
        self.assertEqual(0, completed.returncode, completed.stderr)


if __name__ == "__main__":
    unittest.main()
