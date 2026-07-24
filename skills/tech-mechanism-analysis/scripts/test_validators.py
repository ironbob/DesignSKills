#!/usr/bin/env python3
"""Regression and adversarial tests for tech-mechanism-analysis gates."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import validate_analysis
import validate_report
from render_report import render_report

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parents[1]
FULL_JSON = SKILL_DIR / "examples/2026-07-23-example-analysis.json"
LITE_MD = SKILL_DIR / "examples/2026-07-24-example-lite.md"


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.full = json.loads(FULL_JSON.read_text(encoding="utf-8"))

    def test_valid_full_contract(self) -> None:
        report = validate_analysis.validate(copy.deepcopy(self.full))
        self.assertEqual([], report.errors)

    def test_chain_must_match_template_in_order(self) -> None:
        data = copy.deepcopy(self.full)
        data["chain_stages"][1]["segment"] = "produce"
        report = validate_analysis.validate(data)
        self.assertTrue(any("[CHAIN.EXACT]" in item for item in report.errors))

    def test_ids_require_full_match(self) -> None:
        data = copy.deepcopy(self.full)
        data["numerical_examples"][0]["id"] = "NUM-01-junk"
        report = validate_analysis.validate(data)
        self.assertTrue(any("[NUM[0].ID]" in item for item in report.errors))

    def test_short_placeholder_fields_fail(self) -> None:
        data = copy.deepcopy(self.full)
        data["defects"][0]["hard_requirement"] = "x"
        report = validate_analysis.validate(data)
        self.assertTrue(any("HARD_REQUIREMENT" in item for item in report.errors))

    def test_valid_lite_report(self) -> None:
        errors, _ = validate_report.validate(LITE_MD, REPO_ROOT)
        self.assertEqual([], errors)

    def test_thin_lite_report_fails(self) -> None:
        source = self.full["covered_files"][0]
        thin = f"""---
mode: lite
target: keyframe-easing
title: 占位报告
analyzed_at: 2026-07-24
covered_files:
  - {source}
chain_segments: 4
numerical_examples: 1
design_observations: 1
open_questions: 0
---
## 机制概述
x
## 范围与假设
x
## 全链路
x `{source}:1`
## 数值示例
NUM-01: 1 = 1
## 设计观察
x
## 已知缺口
- x
"""
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "thin.md"
            path.write_text(thin, encoding="utf-8")
            errors, _ = validate_report.validate(path, REPO_ROOT)
        self.assertGreaterEqual(len(errors), 3)

    def test_contract_rejects_manual_drift(self) -> None:
        expected = render_report(self.full)
        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            analysis = temp_path / "analysis.json"
            report = temp_path / "analysis.md"
            analysis.write_text(json.dumps(self.full, ensure_ascii=False), encoding="utf-8")
            report.write_text(expected.replace("技术机制深度分析", "手工修改", 1), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3", str(SKILL_DIR / "scripts/validate_contract.py"),
                    str(analysis), str(report),
                ],
                text=True,
                capture_output=True,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("不是当前 JSON 的确定性渲染", result.stdout)

    def test_evidence_outside_covered_files_fails(self) -> None:
        data = copy.deepcopy(self.full)
        data["chain_stages"][0]["evidence"][0] = {
            "file": "skills/tech-mechanism-analysis/SKILL.md",
            "line": 1,
            "note": "skill frontmatter",
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3", str(SKILL_DIR / "scripts/validate_evidence.py"),
                    str(path), "--root", str(REPO_ROOT),
                ],
                text=True,
                capture_output=True,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("[EVIDENCE.SCOPE]", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
