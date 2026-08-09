from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from validate_acceptance import validate as validate_acceptance  # noqa: E402
from validate_blueprint import validate as validate_blueprint  # noqa: E402
from validate_change_assessment import validate as validate_change_assessment  # noqa: E402
from validate_delivery import validate as validate_delivery  # noqa: E402
from validate_repair import validate as validate_repair  # noqa: E402
from validate_text_ui import validate as validate_text_ui  # noqa: E402


def blueprint() -> dict:
    return {
        "meta": {
            "mode": "create",
            "platform": "iOS",
            "framework": "SwiftUI",
            "screen_job": "完成当前任务",
            "scope": "single_screen",
            "source_screenshots": ["reference.png"],
            "text_ui_guard": {
                "manifest": "text-ui-manifest.json",
                "result": "user_confirmed",
                "confirmed_screenshot_ids": ["SHOT-01"],
                "confirmation_evidence": "用户消息：文本图确认",
            },
        },
        "structure_skeleton": {"node_id": "N1", "kind": "screen"},
        "entries": [
            {"id": "ENTRY-01", "kind": "button", "semantic": "提交", "screenshot_anchor": "bottom"}
        ],
        "icons": [
            {"id": "ICON-01", "semantic": "返回", "screenshot_anchor": "top-left"}
        ],
        "key_dimensions": [
            {"id": "DIM-01", "what": "spacing", "ratio_note": "间距约为正文字号 0.5x"}
        ],
        "states": [
            {"id": "STATE-01", "kind": "selected", "source": "screenshot", "screenshot_anchor": "center"}
        ],
        "bitmaps": [
            {"id": "BMP-01", "semantic": "用户头像", "handling": "placeholder"}
        ],
    }


def text_ui_manifest(confirmed: bool = True) -> dict:
    status = "user_confirmed" if confirmed else "pending"
    return {
        "meta": {"screen": "screen", "source_count": 2, "text_ui_count": 2},
        "screenshots": [
            {
                "id": "SHOT-01",
                "source": "default.png",
                "state_label": "default",
                "text_ui_file": "text-ui/SHOT-01-default.txt",
                "revision": 1,
                "confirmation": {
                    "status": status,
                    "confirmed_by": "user" if confirmed else None,
                    "evidence": "用户消息：确认 SHOT-01" if confirmed else None,
                },
            },
            {
                "id": "SHOT-02",
                "source": "error.png",
                "state_label": "error",
                "text_ui_file": "text-ui/SHOT-02-error.txt",
                "revision": 1,
                "confirmation": {
                    "status": status,
                    "confirmed_by": "user" if confirmed else None,
                    "evidence": "用户消息：确认 SHOT-02" if confirmed else None,
                },
            },
        ],
    }


def prepare_text_ui(root: Path) -> None:
    (root / "text-ui").mkdir()
    drawing = "\n".join([
        "┌──────────────────┐",
        "│ [icon:back] 标题 │",
        "├──────────────────┤",
        "│   [ 主按钮 ]     │",
        "└──────────────────┘",
    ])
    (root / "text-ui" / "SHOT-01-default.txt").write_text(drawing, encoding="utf-8")
    (root / "text-ui" / "SHOT-02-error.txt").write_text(drawing, encoding="utf-8")


class TextUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        prepare_text_ui(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_one_text_drawing_per_screenshot_passes(self) -> None:
        self.assertTrue(validate_text_ui(text_ui_manifest(), "confirmed", self.root).ok())

    def test_pending_confirmation_blocks_confirmed_phase(self) -> None:
        self.assertFalse(validate_text_ui(text_ui_manifest(False), "confirmed", self.root).ok())

    def test_mismatched_counts_fail(self) -> None:
        doc = text_ui_manifest()
        doc["meta"]["text_ui_count"] = 1
        self.assertFalse(validate_text_ui(doc, "confirmed", self.root).ok())

    def test_two_screenshots_cannot_share_one_text_file(self) -> None:
        doc = text_ui_manifest()
        doc["screenshots"][1]["text_ui_file"] = doc["screenshots"][0]["text_ui_file"]
        self.assertFalse(validate_text_ui(doc, "confirmed", self.root).ok())

    def test_rejected_draft_must_be_revised(self) -> None:
        doc = text_ui_manifest(False)
        doc["screenshots"][0]["confirmation"]["status"] = "rejected"
        self.assertFalse(validate_text_ui(doc, "draft", self.root).ok())

    def test_blueprint_cross_checks_confirmed_text_ui(self) -> None:
        doc = blueprint()
        doc["meta"]["source_screenshots"] = ["default.png", "error.png"]
        doc["meta"]["text_ui_guard"]["confirmed_screenshot_ids"] = ["SHOT-01", "SHOT-02"]
        self.assertTrue(validate_blueprint(doc, text_ui_manifest(), self.root).ok())

    def test_blueprint_rejects_text_ui_order_mismatch(self) -> None:
        doc = blueprint()
        doc["meta"]["source_screenshots"] = ["error.png", "default.png"]
        doc["meta"]["text_ui_guard"]["confirmed_screenshot_ids"] = ["SHOT-01", "SHOT-02"]
        self.assertFalse(validate_blueprint(doc, text_ui_manifest(), self.root).ok())


def prepare_code_root(root: Path) -> None:
    (root / "docs").mkdir()
    (root / "docs" / "contract.json").write_text("{}", encoding="utf-8")
    (root / "docs" / "architecture.md").write_text("# architecture", encoding="utf-8")
    (root / "Screen.swift").write_text(
        "\n".join(
            [
                "struct ScreenRoot {}",
                "let MainButton = Button()",
                'let ShareIcon = Image(systemName: "chevron.left")',
                "let SpacingToken = 8",
                "let SelectedState = true",
            ]
        ),
        encoding="utf-8",
    )


def delivery() -> dict:
    anchor = lambda widget: {"file": "Screen.swift", "widget": widget}
    return {
        "meta": {
            "change_scope": {
                "production_files": ["Screen.swift"],
                "assessment_revision": 1,
            },
            "architecture_guard": {
                "mode": "arch_first",
                "assessment": "change-assessment.json",
                "assessment_revision": 1,
                "skill": "arch-first-code-gen",
                "invocation": "same_agent",
                "confirmation_mode": "user_confirmed",
                "result": "passed",
                "design_contract": "docs/contract.json",
                "architecture_doc": "docs/architecture.md",
                "validation_evidence": "contract/doc/gate exit 0",
            }
        },
        "entries": [
            {"entry_id": "ENTRY-01", "status": "delivered", "code_anchor": anchor("MainButton")}
        ],
        "icons": [
            {
                "icon_id": "ICON-01",
                "status": "delivered",
                "code_anchor": anchor("ShareIcon"),
                "asset": {
                    "type": "system",
                    "source": "SF Symbols",
                    "name": "chevron.left",
                    "code_reference": "chevron.left",
                },
            }
        ],
        "structure_nodes": [
            {"node_id": "N1", "status": "delivered", "code_anchor": anchor("ScreenRoot")}
        ],
        "dimensions": [
            {"dimension_id": "DIM-01", "status": "delivered", "code_anchor": anchor("SpacingToken")}
        ],
        "states": [
            {"state_id": "STATE-01", "status": "delivered", "code_anchor": anchor("SelectedState")}
        ],
    }


def change_assessment(path: str = "arch_first") -> dict:
    risks = {
        "navigation_change": False,
        "state_ownership_change": False,
        "data_flow_change": False,
        "api_or_persistence_change": False,
        "new_dependency": False,
        "cross_layer_change": False,
        "shared_component_or_token_change": False,
        "multiple_screens": False,
        "architecture_role_change": False,
    }
    if path == "arch_first":
        risks["state_ownership_change"] = True
    return {
        "meta": {
            "mode": "create",
            "target_screen": "Screen",
            "stage": "pre_code",
            "revision": 1,
            "user_forced_arch_first": False,
        },
        "estimate": {
            "production_files": 1,
            "change_size": "small",
            "ui_only": path == "direct_ui",
            "logic_change": "none",
        },
        "evidence": ["Screen.swift inspected"],
        "risk_flags": risks,
        "decision": {"path": path, "rationale": "test assessment"},
    }


def direct_delivery() -> dict:
    doc = delivery()
    doc["meta"]["architecture_guard"] = {
        "mode": "direct_ui",
        "assessment": "change-assessment.json",
        "assessment_revision": 1,
        "implementation_owner": "pic-to-ui",
        "result": "passed",
        "validation_evidence": "assessment exit 0; actual scope rechecked",
    }
    return doc


def manifest() -> dict:
    return {
        "icons": [
            {
                "icon_id": "ICON-01",
                "status": "delivered",
                "semantic": "返回",
                "asset": {
                    "type": "system",
                    "source": "SF Symbols",
                    "name": "chevron.left",
                    "code_reference": "chevron.left",
                    "license": "Apple SF Symbols License",
                },
            }
        ],
        "bitmaps": [
            {
                "bitmap_id": "BMP-01",
                "semantic": "用户头像",
                "handling": "placeholder",
                "suggested_source": "用户上传",
                "license": "not-applicable",
            }
        ],
    }


class BlueprintTests(unittest.TestCase):
    def test_complete_blueprint_passes(self) -> None:
        self.assertTrue(validate_blueprint(blueprint()).ok())

    def test_bare_empty_categories_fail(self) -> None:
        doc = blueprint()
        for key in ("entries", "icons", "key_dimensions", "states"):
            doc[key] = []
        self.assertFalse(validate_blueprint(doc).ok())

    def test_empty_categories_with_structured_reasons_pass(self) -> None:
        doc = blueprint()
        doc["bitmaps"] = []
        for key in ("entries", "icons", "key_dimensions", "states"):
            doc[key] = []
        doc["empty_reasons"] = {
            "entries": "纯展示屏，无入口",
            "icons": "参考截图无图标",
            "key_dimensions": "截图只有一块自适应内容，无关键比例",
            "states": "只提供默认态截图",
        }
        self.assertTrue(validate_blueprint(doc).ok())


class DeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        prepare_code_root(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_real_code_and_assets_pass(self) -> None:
        self.assertTrue(validate_delivery(blueprint(), delivery(), manifest(), change_assessment(), self.root).ok())

    def test_direct_ui_path_passes_without_architecture_artifacts(self) -> None:
        (self.root / "docs" / "contract.json").unlink()
        (self.root / "docs" / "architecture.md").unlink()
        self.assertTrue(validate_delivery(blueprint(), direct_delivery(), manifest(), change_assessment("direct_ui"), self.root).ok())

    def test_actual_scope_must_match_assessment(self) -> None:
        assessment = change_assessment("direct_ui")
        assessment["estimate"]["production_files"] = 2
        self.assertFalse(validate_delivery(blueprint(), direct_delivery(), manifest(), assessment, self.root).ok())

    def test_p0_flagged_blocks_delivery(self) -> None:
        doc = delivery()
        doc["entries"][0] = {"entry_id": "ENTRY-01", "status": "flagged", "reason": "未实现"}
        self.assertFalse(validate_delivery(blueprint(), doc, manifest(), change_assessment(), self.root).ok())

    def test_user_waiver_is_explicit_exception(self) -> None:
        doc = delivery()
        doc["entries"][0] = {
            "entry_id": "ENTRY-01",
            "status": "waived",
            "reason": "用户接受本轮不交付",
            "waiver": {"approved_by": "user", "evidence": "用户消息：允许省略 ENTRY-01"},
        }
        self.assertTrue(validate_delivery(blueprint(), doc, manifest(), change_assessment(), self.root).ok())

    def test_invented_code_anchor_fails(self) -> None:
        doc = delivery()
        doc["entries"][0]["code_anchor"] = {"file": "missing.swift", "widget": "InventedWidget"}
        self.assertFalse(validate_delivery(blueprint(), doc, manifest(), change_assessment(), self.root).ok())

    def test_missing_icon_code_reference_fails(self) -> None:
        doc = delivery()
        doc["icons"][0]["asset"]["code_reference"] = "not-in-code"
        asset_doc = manifest()
        asset_doc["icons"][0]["asset"]["code_reference"] = "not-in-code"
        self.assertFalse(validate_delivery(blueprint(), doc, asset_doc, change_assessment(), self.root).ok())

    def test_manifest_license_is_required(self) -> None:
        asset_doc = manifest()
        del asset_doc["icons"][0]["asset"]["license"]
        self.assertFalse(validate_delivery(blueprint(), delivery(), asset_doc, change_assessment(), self.root).ok())


class ChangeAssessmentTests(unittest.TestCase):
    def test_small_pure_ui_uses_direct_path(self) -> None:
        self.assertTrue(validate_change_assessment(change_assessment("direct_ui")).ok())

    def test_large_pure_ui_can_still_use_direct_path(self) -> None:
        doc = change_assessment("direct_ui")
        doc["estimate"]["production_files"] = 8
        doc["estimate"]["change_size"] = "large"
        self.assertTrue(validate_change_assessment(doc).ok())

    def test_architecture_risk_requires_arch_first(self) -> None:
        doc = change_assessment("direct_ui")
        doc["risk_flags"]["data_flow_change"] = True
        self.assertFalse(validate_change_assessment(doc).ok())

    def test_medium_non_ui_change_requires_arch_first(self) -> None:
        doc = change_assessment("arch_first")
        doc["risk_flags"]["state_ownership_change"] = False
        doc["estimate"].update({"production_files": 4, "change_size": "medium", "ui_only": False, "logic_change": "local_wiring"})
        self.assertTrue(validate_change_assessment(doc).ok())

    def test_ui_only_cannot_hide_logic_change(self) -> None:
        doc = change_assessment("direct_ui")
        doc["estimate"]["logic_change"] = "local_wiring"
        self.assertFalse(validate_change_assessment(doc).ok())

    def test_user_can_force_arch_first_for_small_ui_change(self) -> None:
        doc = change_assessment("direct_ui")
        doc["meta"].update({
            "user_forced_arch_first": True,
            "force_evidence": "用户显式调用 $arch-first-code-gen",
        })
        doc["decision"]["path"] = "arch_first"
        self.assertTrue(validate_change_assessment(doc).ok())


class RepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        prepare_code_root(self.root)
        self.bp = blueprint()
        self.bp["meta"]["mode"] = "repair"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def audit(self) -> dict:
        return {
            "meta": {
                "mode": "repair",
                "target_screen": "Screen",
                "implementation_root": ".",
                "reference_screenshots": ["reference.png"],
                "baseline": {"status": "unavailable", "reason": "模拟器不可用"},
            },
            "mismatches": [
                {
                    "id": "MISMATCH-01",
                    "category": "structure",
                    "priority": "P0",
                    "target_ids": ["N1"],
                    "screenshot_evidence": "shot#1:center",
                    "current_evidence": "代码使用了错误容器",
                    "diagnosis": "根容器约束错误",
                    "current_code_anchor": {"file": "Screen.swift", "widget": "ScreenRoot"},
                    "status": "open",
                }
            ],
        }

    def test_audit_with_real_anchor_passes(self) -> None:
        self.assertTrue(validate_repair(self.audit(), "audit", self.root, self.bp).ok())

    def test_improved_cannot_be_resolved(self) -> None:
        doc = self.audit()
        item = doc["mismatches"][0]
        item["status"] = "resolved"
        item["resolution"] = {"summary": "修正容器", "code_anchor": {"file": "Screen.swift", "widget": "ScreenRoot"}}
        item["verification"] = {"method": "visual_inspection", "result": "improved", "evidence": "仍有残差"}
        self.assertFalse(validate_repair(doc, "closure", self.root, self.bp).ok())

    def test_flagged_requires_impact_and_next_action(self) -> None:
        doc = self.audit()
        doc["mismatches"][0].update({"status": "flagged", "reason": "无法渲染"})
        self.assertFalse(validate_repair(doc, "closure", self.root, self.bp).ok())


def acceptance() -> dict:
    dimensions = ("structure", "entries", "dimensions", "style", "icons", "states", "a11y")
    return {
        "meta": {"mode": "create", "report": "report.md"},
        "gates": [
            {"name": "text-ui-confirmation", "status": "passed", "evidence": "confirmed exit 0"},
            {"name": "blueprint", "status": "passed", "evidence": "exit 0"},
            {"name": "coding-path", "status": "passed", "evidence": "arch_first revision 1"},
            {"name": "delivery", "status": "passed", "evidence": "exit 0"},
        ],
        "render_diff": {
            "status": "executed",
            "reference": "evidence/reference.png",
            "after": "evidence/after.png",
            "comparison": "evidence/diff.png",
            "result": "matched",
        },
        "self_check": [
            {"dimension": value, "status": "passed", "evidence": f"{value} checked"}
            for value in dimensions
        ],
        "tests": [{"command": "build", "result": "passed", "evidence": "exit 0"}],
        "flags": [],
        "waivers": [],
    }


class AcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "evidence").mkdir()
        (self.root / "report.md").write_text("# Report", encoding="utf-8")
        for name in ("reference.png", "after.png", "diff.png"):
            (self.root / "evidence" / name).write_bytes(b"png")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_complete_acceptance_passes(self) -> None:
        self.assertTrue(validate_acceptance(acceptance(), self.root, delivery()).ok())

    def test_missing_diff_file_fails(self) -> None:
        doc = acceptance()
        doc["render_diff"]["after"] = "evidence/missing.png"
        self.assertFalse(validate_acceptance(doc, self.root, delivery()).ok())

    def test_unknown_self_check_dimension_fails(self) -> None:
        doc = acceptance()
        doc["self_check"].append({"dimension": "performance", "status": "passed", "evidence": "checked"})
        self.assertFalse(validate_acceptance(doc, self.root, delivery()).ok())

    def test_unavailable_diff_must_be_unverified(self) -> None:
        doc = acceptance()
        doc["render_diff"] = {"status": "unavailable", "reason": "模拟器不可用", "result": "matched"}
        self.assertFalse(validate_acceptance(doc, self.root, delivery()).ok())

    def test_p0_flag_blocks_acceptance(self) -> None:
        doc = acceptance()
        doc["flags"] = [{"id": "FLAG-01", "priority": "P0", "reason": "入口缺失", "next_action": "实现入口"}]
        self.assertFalse(validate_acceptance(doc, self.root, delivery()).ok())

    def test_delivery_flag_must_be_in_acceptance(self) -> None:
        delivery_doc = delivery()
        delivery_doc["dimensions"][0] = {
            "dimension_id": "DIM-01", "status": "flagged", "reason": "设备尺寸未知"
        }
        self.assertFalse(validate_acceptance(acceptance(), self.root, delivery_doc).ok())

    def test_repair_acceptance_requires_repair_audit(self) -> None:
        doc = acceptance()
        doc["meta"]["mode"] = "repair"
        doc["gates"].extend(
            [
                {"name": "repair-audit", "status": "passed", "evidence": "exit 0"},
                {"name": "repair-closure", "status": "passed", "evidence": "exit 0"},
            ]
        )
        self.assertFalse(validate_acceptance(doc, self.root, delivery()).ok())


if __name__ == "__main__":
    unittest.main()
