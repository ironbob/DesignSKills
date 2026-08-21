#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
EXAMPLE = SKILL / "examples" / "2026-06-20-example-findings.json"
HEALTHY_EXAMPLE = SKILL / "examples" / "2026-08-20-healthy-order-findings.json"
FIXTURE_ROOT = SKILL / "examples" / "fixtures" / "order-service"
FORMAL_EXAMPLES = (
    ("2026-06-20-example", "order-service"),
    ("2026-08-20-cpp-player", "cpp-player"),
    ("2026-08-20-healthy-order", "healthy-order"),
    ("2026-08-20-convention-api", "convention-api"),
)


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

    def test_all_formal_examples_pass_four_gates(self) -> None:
        for prefix, fixture_name in FORMAL_EXAMPLES:
            with self.subTest(example=prefix):
                findings = SKILL / "examples" / f"{prefix}-findings.json"
                report = SKILL / "examples" / f"{prefix}-report.md"
                fixture = SKILL / "examples" / "fixtures" / fixture_name
                self.assertEqual(run_script("validate_findings.py", findings).returncode, 0)
                self.assertEqual(
                    run_script("validate_evidence.py", findings, "--root", fixture).returncode,
                    0,
                )
                self.assertEqual(run_script("validate_report.py", report).returncode, 0)
                self.assertEqual(run_script("validate_contract.py", findings, report).returncode, 0)

    def test_contract_rejects_finding_that_is_only_mentioned(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "report.md"
            run_script("render_report.py", EXAMPLE, "--output", report)
            text = report.read_text(encoding="utf-8")
            text = re.sub(
                r"^#### FINDING-D02\b.*?(?=^#### |^## )",
                "FINDING-D02 仅在优先级表中保留。\n\n",
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
        single["summary"] = {
            "critical": 0, "major": 0, "minor": 1,
            "confirmed_critical": 0, "verdict": "inconclusive",
        }
        linked = set(single["findings"][0]["principles_violated"])
        for key, item in single["design_principle_coverage"].items():
            item["status"] = "concern" if key in linked else (
                "inconclusive" if key == "change-isolation" else "no-material-concern"
            )
        with tempfile.TemporaryDirectory() as temp:
            findings = Path(temp) / "single-findings.json"
            report = Path(temp) / "single-report.md"
            findings.write_text(json.dumps(single, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run_script("render_report.py", findings, "--output", report).returncode, 0)
            result = run_script("validate_report.py", report)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_zero_finding_report_pipeline(self) -> None:
        healthy = json.loads(HEALTHY_EXAMPLE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            findings = Path(temp) / "healthy-findings.json"
            report = Path(temp) / "healthy-report.md"
            findings.write_text(json.dumps(healthy, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run_script("validate_findings.py", findings).returncode, 0)
            self.assertEqual(run_script("render_report.py", findings, "--output", report).returncode, 0)
            self.assertEqual(run_script("validate_report.py", report).returncode, 0)
            self.assertEqual(run_script("validate_contract.py", findings, report).returncode, 0)

    def test_convention_finding_pipeline(self) -> None:
        conventional = json.loads(
            (SKILL / "examples" / "2026-08-20-convention-api-findings.json").read_text(encoding="utf-8")
        )
        finding = conventional["findings"][0]
        finding["id"] = "FINDING-C01"
        finding["axis"] = "convention"
        finding["category"] = "convention-violation"
        finding["principles_violated"] = []
        conventional["findings"] = [finding]
        conventional["design_principle_coverage"]["information-hiding"]["status"] = "no-material-concern"
        with tempfile.TemporaryDirectory() as temp:
            findings = Path(temp) / "convention-findings.json"
            report = Path(temp) / "convention-report.md"
            findings.write_text(json.dumps(conventional, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(run_script("validate_findings.py", findings).returncode, 0)
            self.assertEqual(run_script("render_report.py", findings, "--output", report).returncode, 0)
            self.assertEqual(run_script("validate_report.py", report).returncode, 0)
            self.assertEqual(run_script("validate_contract.py", findings, report).returncode, 0)

    def test_v2_limited_coverage_requires_inconclusive(self) -> None:
        limited = json.loads(HEALTHY_EXAMPLE.read_text(encoding="utf-8"))
        limited["coverage"]["sufficient_for_verdict"] = False
        limited["design_principle_coverage"]["change-isolation"]["status"] = "inconclusive"
        limited["summary"]["verdict"] = "go"
        with tempfile.TemporaryDirectory() as temp:
            findings = Path(temp) / "limited.json"
            findings.write_text(json.dumps(limited, ensure_ascii=False), encoding="utf-8")
            rejected = run_script("validate_findings.py", findings)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("inconclusive", rejected.stdout)
            limited["summary"]["verdict"] = "inconclusive"
            findings.write_text(json.dumps(limited, ensure_ascii=False), encoding="utf-8")
            accepted = run_script("validate_findings.py", findings)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)

    def test_v2_convention_overlap_is_one_structural_finding(self) -> None:
        findings = SKILL / "examples" / "2026-08-20-convention-api-findings.json"
        data = json.loads(findings.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 2)
        self.assertEqual(len(data["findings"]), 1)
        self.assertEqual(data["findings"][0]["convention_rule_ids"], ["CONV-API1"])
        self.assertEqual(data["summary"]["minor"], 1)

    def test_language_neutral_player_scans_have_equivalent_dependencies(self) -> None:
        jvm_fixture = SKILL / "examples" / "fixtures" / "jvm-player"
        cpp_fixture = SKILL / "examples" / "fixtures" / "cpp-player"
        jvm_result = run_script(
            "scan_architecture.py", ".", "--root", jvm_fixture,
            "--include-tests", "--git-history", 0,
        )
        self.assertEqual(jvm_result.returncode, 0, jvm_result.stdout + jvm_result.stderr)
        cpp_args = [
            "scan_architecture.py", ".", "--root", cpp_fixture,
            "--include-tests", "--git-history", 0,
        ]
        if shutil.which("clang++"):
            cpp_args.extend(["--cpp-mode", "clang"])
        cpp_result = run_script(*cpp_args)
        self.assertEqual(cpp_result.returncode, 0, cpp_result.stdout + cpp_result.stderr)
        jvm = json.loads(jvm_result.stdout)
        cpp = json.loads(cpp_result.stdout)
        jvm_targets = {
            edge["target"].split(".")[-1]
            for edge in jvm["dependency_edges"]
            if edge.get("from", "").endswith("PlayerController.java")
        }
        cpp_targets = {
            edge["to_type"].split("::")[-1]
            for edge in (cpp.get("cpp_semantics") or {}).get("semantic_edges", [])
            if edge.get("from_type", "").endswith("PlayerController")
        }
        self.assertTrue({"PlaybackService", "MediaStore"}.issubset(jvm_targets))
        if shutil.which("clang++"):
            self.assertTrue({"PlaybackService", "MediaStore"}.issubset(cpp_targets))

    def test_scan_index_can_be_queried_without_loading_all_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            index = Path(temp) / "scan.json"
            scanned = run_script(
                "scan_architecture.py", ".", "--root", FIXTURE_ROOT,
                "--include-tests", "--git-history", 0, "--output", index,
            )
            self.assertEqual(scanned.returncode, 0, scanned.stdout + scanned.stderr)
            result = run_script("query_scan.py", index, "--type", "OrderRepository")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            subset = json.loads(result.stdout)
            self.assertGreater(subset["total_edge_count"], 0)
            self.assertTrue(subset["edges"])
            self.assertTrue(all(
                "OrderRepository" in json.dumps(edge, ensure_ascii=False)
                for edge in subset["edges"]
            ))

    def test_parallel_scan_is_fact_equivalent_to_serial(self) -> None:
        result = run_script(
            "benchmark_scan.py", ".", "--root", FIXTURE_ROOT, "--jobs", 4,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        benchmark = json.loads(result.stdout)
        self.assertTrue(benchmark["equivalent"])
        self.assertEqual(benchmark["files"], 4)

    def test_high_fanout_composition_root_is_only_a_hotspot_signal(self) -> None:
        fixture = SKILL / "examples" / "fixtures" / "false-positive-guards"
        result = run_script(
            "scan_architecture.py", ".", "--root", fixture,
            "--include-tests", "--git-history", 0,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        scan = json.loads(result.stdout)
        self.assertTrue(scan["hotspots"][0]["file"].endswith("ApplicationBootstrap.java"))
        self.assertNotIn("findings", scan, "Scanner metrics must remain clues, not architecture judgments")

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
            self.assertEqual(scan["semantic_backend"], "text-search")
            forced = run_script(
                "scan_architecture.py", ".", "--root", root,
                "--git-history", 0, "--cpp-mode", "clang",
            )
            self.assertNotEqual(forced.returncode, 0)
            self.assertIn("clang AST 模式不可用", forced.stderr)

    def test_cpp_formal_fixture_prefers_clang_ast(self) -> None:
        fixture = SKILL / "examples" / "fixtures" / "cpp-player"
        args = [
            "scan_architecture.py", ".", "--root", fixture, "--include-tests",
            "--cpp-mode", "clang", "--git-history", 0,
        ]
        result = run_script(*args)
        if not shutil.which("clang++"):
            self.assertNotEqual(result.returncode, 0)
            return
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        scan = json.loads(result.stdout)
        self.assertEqual(scan["semantic_backend"], "clang-ast")
        semantics = scan["cpp_semantics"]
        self.assertEqual(semantics["translation_units"], 1)
        edges = semantics["semantic_edges"]
        self.assertTrue(any(edge["to_type"] == "media::infra::MediaStore" for edge in edges))
        self.assertTrue(any(edge["kind"] == "member-reference" and edge["line"] == 14 for edge in edges))


if __name__ == "__main__":
    unittest.main()
