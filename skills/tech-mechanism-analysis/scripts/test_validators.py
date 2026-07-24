#!/usr/bin/env python3
"""Regression and adversarial tests for tech-mechanism-analysis gates."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
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

    def test_full_requires_traceable_scope_confirmation(self) -> None:
        data = copy.deepcopy(self.full)
        del data["scope_confirmations"]
        report = validate_analysis.validate(data)
        self.assertTrue(any("[SCOPE.LIST]" in item for item in report.errors))

    def test_malformed_scope_reports_errors_instead_of_crashing(self) -> None:
        data = copy.deepcopy(self.full)
        data["scope_confirmations"][0]["candidate_files"] = None
        report = validate_analysis.validate(data)
        self.assertTrue(any("[SCOPE[0].FILES]" in item for item in report.errors))

    def test_dates_require_extended_calendar_format(self) -> None:
        for invalid in ("20260724", "2026-W30-5"):
            data = copy.deepcopy(self.full)
            data["analyzed_at"] = invalid
            report = validate_analysis.validate(data)
            self.assertTrue(any("[TOP.DATE]" in item for item in report.errors))

    def test_ids_require_full_match(self) -> None:
        data = copy.deepcopy(self.full)
        data["numerical_examples"][0]["id"] = "NUM-1"
        report = validate_analysis.validate(data)
        self.assertTrue(any("[NUM[0].ID]" in item for item in report.errors))

    def test_unknown_fields_are_rejected(self) -> None:
        data = copy.deepcopy(self.full)
        data["chain_stages"][0]["unexpected_typo"] = "must not be ignored"
        report = validate_analysis.validate(data)
        self.assertTrue(any("[CHAIN[0].KEYS]" in item for item in report.errors))

    def test_unknown_why_must_admit_missing_intent(self) -> None:
        data = copy.deepcopy(self.full)
        stage = data["chain_stages"][3]
        stage["why"] = "作者为了性能选择动态属性写入"
        report = validate_analysis.validate(data)
        self.assertTrue(any("[CHAIN[3].WHY_UNKNOWN]" in item for item in report.errors))

    def test_observed_why_requires_direct_intent_evidence(self) -> None:
        data = copy.deepcopy(self.full)
        stage = data["chain_stages"][0]
        stage["why_basis"] = "observed"
        report = validate_analysis.validate(data)
        self.assertTrue(any("[CHAIN[0].WHY_EVIDENCE]" in item for item in report.errors))

    def test_diagram_requires_evidence_and_safe_ids(self) -> None:
        data = copy.deepcopy(self.full)
        data["diagrams"]["nodes"][0]["evidence"] = []
        data["diagrams"]["nodes"][1]["id"] = "bad id"
        report = validate_analysis.validate(data)
        self.assertTrue(any("[DIAGRAM.NODE[0]]" in item for item in report.errors))
        self.assertTrue(any("[DIAGRAM.NODE_IDS]" in item for item in report.errors))

    def test_cost_quantification_is_required(self) -> None:
        data = copy.deepcopy(self.full)
        del data["defects"][0]["cost_quantification"]
        report = validate_analysis.validate(data)
        self.assertTrue(any("[DEBT[0].COST_KEYS]" in item for item in report.errors))

    def test_short_placeholder_fields_fail(self) -> None:
        data = copy.deepcopy(self.full)
        data["defects"][0]["hard_requirement"] = "x"
        report = validate_analysis.validate(data)
        self.assertTrue(any("HARD_REQUIREMENT" in item for item in report.errors))

    def test_valid_lite_report(self) -> None:
        errors, _ = validate_report.validate(LITE_MD, REPO_ROOT)
        self.assertEqual([], errors)

    def test_lite_requires_three_to_six_unique_stages(self) -> None:
        text = LITE_MD.read_text(encoding="utf-8")
        text = text.replace("chain_segments: 4", "chain_segments: 2")
        text = re.sub(
            r"\n### STAGE-03.*?(?=\n## 数值示例)",
            "",
            text,
            flags=re.S,
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "two-stages.md"
            path.write_text(text, encoding="utf-8")
            errors, _ = validate_report.validate(path, REPO_ROOT)
        self.assertTrue(any("[CHAIN.COUNT]" in item for item in errors))

    def test_each_lite_stage_requires_its_own_backlink(self) -> None:
        text = LITE_MD.read_text(encoding="utf-8").replace(
            "`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:18`",
            "无有效回链",
            1,
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing-stage-evidence.md"
            path.write_text(text, encoding="utf-8")
            errors, _ = validate_report.validate(path, REPO_ROOT)
        self.assertTrue(any("[CHAIN.EVIDENCE]" in item for item in errors))

    def test_each_lite_handoff_requires_its_own_backlink(self) -> None:
        text = LITE_MD.read_text(encoding="utf-8").replace(
            "`skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts:20`",
            "无有效回链",
            1,
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing-handoff-evidence.md"
            path.write_text(text, encoding="utf-8")
            errors, _ = validate_report.validate(path, REPO_ROOT)
        self.assertTrue(any("[CHAIN.HANDOFF]" in item for item in errors))

    def test_extensionless_backlinks_are_supported(self) -> None:
        text = LITE_MD.read_text(encoding="utf-8")
        text = text.replace(
            "skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/keyframe.ts",
            "Makefile",
        ).replace(
            "skills/tech-mechanism-analysis/examples/fixtures/keyframe-easing/src/renderer.ts",
            "Dockerfile",
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Makefile").write_text("\n" * 80, encoding="utf-8")
            (root / "Dockerfile").write_text("\n" * 80, encoding="utf-8")
            report_path = root / "extensionless.md"
            report_path.write_text(text, encoding="utf-8")
            errors, _ = validate_report.validate(report_path, root)
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

    def test_renderer_uses_safe_frontmatter_and_mermaid_text(self) -> None:
        data = copy.deepcopy(self.full)
        data["languages"] = ["TypeScript, strict"]
        data["language_analysis"][0]["language"] = "TypeScript, strict"
        data["diagrams"]["nodes"][0]["label"] = '写入\"; %% `value`'
        rendered = render_report(data)
        self.assertNotIn("status: draft", rendered)
        self.assertIn('"TypeScript, strict"', rendered)
        self.assertIn("&quot;&#59; &#37;&#37; &#96;value&#96;", rendered)

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

    def test_why_evidence_locations_are_checked(self) -> None:
        data = copy.deepcopy(self.full)
        stage = data["chain_stages"][0]
        stage["why_basis"] = "observed"
        stage["why_evidence"] = [
            {
                "file": self.full["covered_files"][0],
                "line": 9999,
                "note": "explicit design intent",
                "source_type": "explicit-comment",
            }
        ]
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad-why-evidence.json"
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
        self.assertIn("[EVIDENCE.LINE]", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
