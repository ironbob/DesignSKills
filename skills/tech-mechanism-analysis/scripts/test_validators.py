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
from unittest.mock import patch

import validate_analysis
import validate_report
from render_report import render_report

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parents[1]
FULL_JSON = SKILL_DIR / "examples/2026-07-23-example-analysis.json"
FULL_MD = SKILL_DIR / "examples/2026-07-23-example-analysis.md"
ASYNC_JSON = SKILL_DIR / "examples/2026-07-24-async-analysis.json"
LITE_MD = SKILL_DIR / "examples/2026-07-24-example-lite.md"


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.full = json.loads(FULL_JSON.read_text(encoding="utf-8"))
        cls.async_full = json.loads(ASYNC_JSON.read_text(encoding="utf-8"))

    def test_valid_full_contract(self) -> None:
        report = validate_analysis.validate(copy.deepcopy(self.full))
        self.assertEqual([], report.errors)

    def test_keyframe_example_covers_empty_and_time_boundaries(self) -> None:
        flow = next(
            stage for stage in self.full["chain_stages"]
            if stage["id"] == "stage-flow"
        )
        self.assertTrue(flow["numerical"])
        self.assertTrue({26, 27, 29}.issubset({
            item["line"] for item in flow["evidence"]
        }))
        by_id = {
            example["id"]: example
            for example in self.full["numerical_examples"]
        }
        self.assertIn("空关键帧", by_id["NUM-02"]["operation"])
        self.assertIn("早于首", by_id["NUM-03"]["operation"])
        self.assertIn("晚于末", by_id["NUM-04"]["operation"])
        self.assertIn("0", by_id["NUM-02"]["result"])
        self.assertIn("10", by_id["NUM-03"]["result"])
        self.assertIn("20", by_id["NUM-04"]["result"])
        boundary_kinds = {
            item["kind"] for item in self.full["boundary_inventory"]
        }
        self.assertTrue(
            {
                "empty-input", "lower-bound", "upper-bound",
                "cancellation", "exception", "concurrency", "flow-control",
            }
            <= boundary_kinds
        )
        self.assertEqual(3, len(self.full["behavior_cases"]))
        self.assertEqual(3, len(self.full["acceptance_cases"]))
        self.assertEqual([], self.full["behavior_conflicts"])

    def test_case_traceability_requires_reciprocal_acceptance_links(self) -> None:
        data = copy.deepcopy(self.full)
        data["acceptance_cases"][0]["behavior_case_ids"] = ["CASE-02"]
        report = validate_analysis.validate(data)
        self.assertTrue(
            any("[TRACE.CASE-01.ACCEPT]" in item for item in report.errors)
        )
        self.assertTrue(
            any("[TRACE.ACCEPT-01]" in item for item in report.errors)
        )

    def test_verified_case_requires_runtime_verification_method(self) -> None:
        data = copy.deepcopy(self.full)
        data["behavior_cases"][0]["verification"]["method"] = "inspection"
        report = validate_analysis.validate(data)
        self.assertTrue(
            any("[CASE[0].VERIFICATION_MODE]" in item for item in report.errors)
        )

    def test_case_source_anchors_are_required(self) -> None:
        data = copy.deepcopy(self.full)
        data["behavior_cases"][0]["source_anchors"] = []
        report = validate_analysis.validate(data)
        self.assertTrue(any("[CASE[0].ANCHORS]" in item for item in report.errors))

    def test_operational_boundaries_must_have_explicit_conclusions(self) -> None:
        data = copy.deepcopy(self.full)
        data["boundary_inventory"] = [
            item
            for item in data["boundary_inventory"]
            if item["kind"] != "flow-control"
        ]
        report = validate_analysis.validate(data)
        self.assertTrue(
            any(
                "[BOUNDARY.OPERATIONAL_COVERAGE]" in item
                for item in report.errors
            )
        )

    def test_boundary_coverage_map_is_independently_required(self) -> None:
        data = copy.deepcopy(self.full)
        del data["boundary_coverage"]["cancellation"]
        report = validate_analysis.validate(data)
        self.assertTrue(
            any(
                "[BOUNDARY.COVERAGE_MAP]" in item
                for item in report.errors
            )
        )

    def test_unbounded_queue_means_backpressure_is_unsupported(self) -> None:
        boundary = next(
            item
            for item in self.async_full["boundary_inventory"]
            if item["kind"] == "flow-control"
        )
        self.assertEqual("applicable", boundary["applicability"])
        self.assertEqual("unsupported", boundary["handling"])
        self.assertIn("无界", boundary["observed_behavior"])
        self.assertIn(
            boundary["id"],
            self.async_full["boundary_coverage"]["backpressure"],
        )

    def test_boundary_applicability_must_match_verification_status(self) -> None:
        data = copy.deepcopy(self.full)
        boundary = next(
            item
            for item in data["boundary_inventory"]
            if item["kind"] == "cancellation"
        )
        boundary["applicability"] = "not-applicable"
        boundary["status"] = "unverified"
        report = validate_analysis.validate(data)
        self.assertTrue(
            any(
                "[BOUNDARY[3].APPLICABILITY_STATUS]" in item
                for item in report.errors
            )
        )

    def test_multi_branch_conflict_is_validated_and_rendered(self) -> None:
        data = copy.deepcopy(self.full)
        alternate = copy.deepcopy(data["behavior_cases"][0])
        alternate["id"] = "CASE-04"
        alternate["title"] = "属性绑定入口的空轨道行为"
        alternate["boundary_ids"] = []
        alternate["entry_point"] = "PropertyBinding.update"
        alternate["branch_path"] = "sampleAt 返回后写入动态属性"
        alternate["observed_observable"] = "另一入口产生与直接采样不兼容的结果"
        alternate["verification"] = {
            "status": "static-only",
            "method": "inspection",
            "procedure": "读取 PropertyBinding.update 的委托与写入路径",
            "observed_result": "静态记录另一入口的可观察结果",
        }
        alternate["source_anchors"] = [
            {
                "file": self.full["covered_files"][1],
                "line": 10,
                "note": "属性绑定入口写入采样结果",
            }
        ]
        alternate["acceptance_case_ids"] = ["ACCEPT-04"]
        data["behavior_cases"].append(alternate)
        acceptance = copy.deepcopy(data["acceptance_cases"][0])
        acceptance["id"] = "ACCEPT-04"
        acceptance["title"] = "属性绑定入口保持空轨道契约"
        acceptance["behavior_case_ids"] = ["CASE-04"]
        acceptance["source_anchors"] = [
            {
                "file": self.full["covered_files"][1],
                "line": 10,
                "note": "属性绑定写入是最终可观察效果",
            }
        ]
        data["acceptance_cases"].append(acceptance)
        data["behavior_conflicts"] = [
            {
                "id": "CONFLICT-01",
                "title": "同一空轨道语义在两个入口结果不一致",
                "case_ids": ["CASE-01", "CASE-04"],
                "comparison_dimension": "empty-track-output",
                "contradiction": "直接采样与属性绑定入口对同一空轨道条件产生不兼容结果",
                "impact": "调用方无法依赖统一的空轨道默认值",
                "intent_status": "unknown",
                "resolution": "确认并统一 empty-keyframe-track 契约",
                "source_anchors": [
                    {
                        "file": self.full["covered_files"][0],
                        "line": 26,
                        "note": "直接采样入口返回零值",
                    },
                    {
                        "file": self.full["covered_files"][1],
                        "line": 10,
                        "note": "属性绑定入口暴露另一结果",
                    },
                ],
            }
        ]
        report = validate_analysis.validate(data)
        self.assertEqual([], report.errors)
        rendered = render_report(data)
        self.assertIn("## 多入口/分支行为矛盾", rendered)
        self.assertIn("CONFLICT-01", rendered)

    def test_left_and_right_boundaries_have_distinct_semantics(self) -> None:
        case_semantics = {
            item["id"]: item["semantic_key"]
            for item in self.full["behavior_cases"]
        }
        self.assertFalse(
            validate_analysis.conflict_semantics_match(
                ["CASE-02", "CASE-03"],
                case_semantics,
            )
        )
        self.assertEqual([], self.full["behavior_conflicts"])

    def test_conflict_must_compare_distinct_routes(self) -> None:
        data = copy.deepcopy(self.full)
        duplicate = copy.deepcopy(data["behavior_cases"][0])
        duplicate["id"] = "CASE-04"
        duplicate["acceptance_case_ids"] = ["ACCEPT-04"]
        data["behavior_cases"].append(duplicate)
        acceptance = copy.deepcopy(data["acceptance_cases"][0])
        acceptance["id"] = "ACCEPT-04"
        acceptance["behavior_case_ids"] = ["CASE-04"]
        data["acceptance_cases"].append(acceptance)
        data["behavior_conflicts"] = [
            {
                "id": "CONFLICT-01",
                "title": "重复路径不能构成矛盾",
                "case_ids": ["CASE-01", "CASE-04"],
                "comparison_dimension": "return-value",
                "contradiction": "记录声称同一路径存在互斥返回结果",
                "impact": "会制造无法定位的伪矛盾",
                "intent_status": "unknown",
                "resolution": "改为引用真实的不同入口或分支",
                "source_anchors": [
                    {
                        "file": self.full["covered_files"][0],
                        "line": 26,
                        "note": "两条用例实际锚定同一空轨道分支",
                    }
                ],
            }
        ]
        report = validate_analysis.validate(data)
        self.assertTrue(
            any("[CONFLICT[0].ROUTES]" in item for item in report.errors)
        )

    def test_malformed_conflict_references_report_errors_without_crashing(self) -> None:
        data = copy.deepcopy(self.full)
        data["behavior_conflicts"] = [
            {
                "id": "CONFLICT-01",
                "title": "非法引用结构",
                "case_ids": 42,
                "comparison_dimension": "error-contract",
                "contradiction": "引用结构不是数组，无法建立行为对比",
                "impact": "矛盾记录失去可追溯性",
                "intent_status": "unknown",
                "resolution": "改为引用至少两个真实行为用例",
                "source_anchors": [
                    {
                        "file": self.full["covered_files"][0],
                        "line": 26,
                        "note": "示例锚点用于验证错误报告路径",
                    }
                ],
            }
        ]
        report = validate_analysis.validate(data)
        self.assertTrue(
            any("[CONFLICT[0].CASE_REFS]" in item for item in report.errors)
        )

    def test_mmdc_resolution_does_not_require_npx(self) -> None:
        def fake_which(name: str) -> str | None:
            if name == "npx":
                return "/usr/bin/npx"
            return None

        with patch("validate_report.shutil.which", side_effect=fake_which):
            command = validate_report.resolve_mmdc_command()
        self.assertIsNone(command)

    def test_missing_mermaid_renderer_is_nonblocking(self) -> None:
        with patch("validate_report.resolve_mmdc_command", return_value=None):
            errors, passed = validate_report.validate(FULL_MD, REPO_ROOT)
        self.assertFalse(any("[MERMAID" in item for item in errors))
        self.assertTrue(
            any(
                "[MERMAID.RENDER]" in item and "不阻塞" in item
                for item in passed
            )
        )

    def test_mermaid_render_failure_is_nonblocking(self) -> None:
        failed = type(
            "Result",
            (),
            {"returncode": 1, "stderr": "browser unavailable", "stdout": ""},
        )()
        with (
            patch(
                "validate_report.resolve_mmdc_command",
                return_value=(["/fake/mmdc"], "mmdc"),
            ),
            patch("validate_report.subprocess.run", return_value=failed),
        ):
            errors, passed = validate_report.validate(FULL_MD, REPO_ROOT)
        self.assertFalse(any("[MERMAID" in item for item in errors))
        self.assertTrue(
            any(
                "[MERMAID.RENDER]" in item and "不阻塞" in item
                for item in passed
            )
        )

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

    def test_lite_contains_boundary_case_acceptance_trace(self) -> None:
        text = LITE_MD.read_text(encoding="utf-8")
        self.assertIn("## 边界清单", text)
        self.assertIn("## 可验证行为用例", text)
        self.assertIn("## 验收用例", text)
        self.assertIn("## 多入口/分支行为矛盾", text)
        self.assertIn("`BOUNDARY-01`", text)
        self.assertIn("`ACCEPT-01`", text)

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
