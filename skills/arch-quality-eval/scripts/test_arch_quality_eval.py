#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
EXAMPLE = SKILL / "examples" / "2026-06-20-example-findings.json"
FIXTURE_ROOT = SKILL / "examples" / "fixtures" / "order-service"


def run_script(name: str, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *(str(arg) for arg in args)],
        capture_output=True,
        text=True,
        check=False,
    )


class ArchQualityEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_example_pipeline(self) -> None:
        self.assertEqual(run_script("validate_findings.py", EXAMPLE).returncode, 0)
        self.assertEqual(
            run_script("validate_evidence.py", EXAMPLE, "--root", FIXTURE_ROOT).returncode,
            0,
        )
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "report.md"
            self.assertEqual(run_script("render_report.py", EXAMPLE, "--output", report).returncode, 0)
            self.assertEqual(run_script("validate_report.py", report).returncode, 0)
            self.assertEqual(run_script("validate_contract.py", EXAMPLE, report).returncode, 0)

    def test_contract_rejects_finding_that_is_only_mentioned(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "report.md"
            run_script("render_report.py", EXAMPLE, "--output", report)
            text = report.read_text(encoding="utf-8")
            text = re.sub(
                r"^#### FINDING-S02\b.*?(?=^#### |^## )",
                "FINDING-S02 仅在优先级表中保留。\n\n",
                text,
                count=1,
                flags=re.M | re.S,
            )
            report.write_text(text, encoding="utf-8")
            result = run_script("validate_contract.py", EXAMPLE, report)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("CONTRACT.ID", result.stdout)

    def test_single_finding_report_needs_one_own_anchor(self) -> None:
        single = copy.deepcopy(self.data)
        single["findings"] = [single["findings"][-1]]
        single["summary"] = {"critical": 0, "major": 0, "minor": 1, "verdict": "go"}
        single["core_smell_coverage"] = {
            "circular-dependency": "not-detected",
            "god-class-or-package": "not-detected",
            "cross-layer": "not-detected",
            "shotgun-surgery": "not-detected",
            "inappropriate-exposure": "detected",
        }
        with tempfile.TemporaryDirectory() as temp:
            findings = Path(temp) / "single-findings.json"
            report = Path(temp) / "single-report.md"
            findings.write_text(json.dumps(single, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run_script("render_report.py", findings, "--output", report).returncode, 0)
            result = run_script("validate_report.py", report)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_zero_finding_report_pipeline(self) -> None:
        healthy = copy.deepcopy(self.data)
        healthy["findings"] = []
        healthy["summary"] = {"critical": 0, "major": 0, "minor": 0, "verdict": "go"}
        healthy["core_smell_coverage"] = {key: "not-detected" for key in healthy["core_smell_coverage"]}
        with tempfile.TemporaryDirectory() as temp:
            findings = Path(temp) / "healthy-findings.json"
            report = Path(temp) / "healthy-report.md"
            findings.write_text(json.dumps(healthy, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run_script("validate_findings.py", findings).returncode, 0)
            self.assertEqual(run_script("render_report.py", findings, "--output", report).returncode, 0)
            self.assertEqual(run_script("validate_report.py", report).returncode, 0)
            self.assertEqual(run_script("validate_contract.py", findings, report).returncode, 0)

    def test_convention_finding_pipeline(self) -> None:
        conventional = copy.deepcopy(self.data)
        finding = conventional["findings"][-1]
        finding["id"] = "FINDING-C01"
        finding["axis"] = "convention"
        finding["category"] = "convention-violation"
        finding["convention_violated"] = "CONV-API1"
        finding.pop("principle_violated", None)
        conventional["findings"] = [finding]
        conventional["conventions_fed"] = True
        conventional["convention_rules"] = [
            {"id": "CONV-API1", "rule": "内部重算方法不得作为公共 API 暴露"}
        ]
        conventional["summary"] = {"critical": 0, "major": 0, "minor": 1, "verdict": "go"}
        conventional["core_smell_coverage"] = {key: "not-detected" for key in conventional["core_smell_coverage"]}
        with tempfile.TemporaryDirectory() as temp:
            findings = Path(temp) / "convention-findings.json"
            report = Path(temp) / "convention-report.md"
            findings.write_text(json.dumps(conventional, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run_script("validate_findings.py", findings).returncode, 0)
            self.assertEqual(run_script("render_report.py", findings, "--output", report).returncode, 0)
            self.assertEqual(run_script("validate_report.py", report).returncode, 0)
            self.assertEqual(run_script("validate_contract.py", findings, report).returncode, 0)

    def test_non_positive_threshold_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.data)
        invalid["no_go_threshold"] = 0
        with tempfile.TemporaryDirectory() as temp:
            findings = Path(temp) / "invalid.json"
            findings.write_text(json.dumps(invalid, ensure_ascii=False), encoding="utf-8")
            result = run_script("validate_findings.py", findings)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("正整数", result.stdout)

    def test_evidence_rejects_unrelated_note(self) -> None:
        invalid = copy.deepcopy(self.data)
        invalid["findings"][-1]["evidence"][0]["note"] = "MissingAlpha MissingBeta"
        with tempfile.TemporaryDirectory() as temp:
            findings = Path(temp) / "invalid-evidence.json"
            findings.write_text(json.dumps(invalid, ensure_ascii=False), encoding="utf-8")
            result = run_script("validate_evidence.py", findings, "--root", FIXTURE_ROOT)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("E-NOTE", result.stdout)

    def test_scan_finds_internal_dependency_edges(self) -> None:
        result = run_script(
            "scan_architecture.py", ".", "--root", FIXTURE_ROOT,
            "--include-tests", "--git-history", 0,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        scan = json.loads(result.stdout)
        self.assertEqual(scan["language"], "JVM")
        self.assertEqual(len(scan["covered_files"]), 4)
        edges = {(edge["from"], edge["target"], edge["line"]) for edge in scan["dependency_edges"]}
        self.assertTrue(any(target == "PromotionService" and line == 42 for _src, target, line in edges))
        self.assertTrue(any(target == "OrderRepository" and line == 12 for _src, target, line in edges))

    def test_scan_cpp_marks_limited_capability(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "alpha.hpp").write_text(
                "#pragma once\nnamespace demo { class Alpha {}; }\n", encoding="utf-8"
            )
            (root / "beta.cpp").write_text(
                '#include "alpha.hpp"\nnamespace demo { Alpha make(); }\n', encoding="utf-8"
            )
            result = run_script(
                "scan_architecture.py", ".", "--root", root, "--git-history", 0,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            scan = json.loads(result.stdout)
            self.assertEqual(scan["language"], "C++")
            self.assertTrue(scan["cpp_limitation_noted"])
            self.assertIn("demo", scan["structure"]["namespaces"])


if __name__ == "__main__":
    unittest.main()
