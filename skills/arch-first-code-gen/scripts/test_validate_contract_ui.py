#!/usr/bin/env python3
"""Regression tests for cross-stack UI/MVVM contract rules."""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

from validate_contract import validate


def contract(stack: str = "JVM") -> dict:
    return {
        "feature": "profile-screen",
        "title": "Profile screen",
        "stack": stack,
        "analyzed_at": "2026-08-09",
        "existing_alignment": {
            "recognized_style": "Existing feature-oriented UI with direct views",
            "new_code_follows": "Keep feature boundaries and existing dependency injection",
        },
        "design_decision": {
            "profile": "light",
            "quality_attributes": [{
                "name": "testability", "priority": "high",
                "scenario": "Profile loading state changes can be tested without a live view",
                "acceptance": "Success, failure, and retry states are deterministic",
            }],
            "candidates": [{
                "id": "ALT-1", "summary": "Feature-scoped MVVM",
                "strengths": ["Testable state"], "weaknesses": ["One additional role"],
                "risks": ["Lifecycle ownership"],
            }],
            "selected_id": "ALT-1",
            "selection_reason": "Meets the high-priority testability scenario and follows dependency injection",
            "top_down_check": "Loading flow requires a presentation-state owner",
            "bottom_up_check": "Existing dependency injection can construct the ViewModel",
            "risk_spikes": [],
            "review": {"mode": "self", "reviewer": "Codex", "findings": "No blocking issue", "disposition": "accepted"},
        },
        "ui_architecture": {
            "framework": "test UI framework",
            "current_patterns": ["Direct View"],
            "target_patterns": ["MVVM"],
            "state_management": "Screen ViewModel owns the single UI-state source",
            "view_model_policy": "required",
            "mvvm_suitability": "suitable",
            "migration_impact": "low",
            "impact_scope": ["ProfileScreen"],
            "migration_confirmation": "not_required",
            "decision_reason": "Async loading and retry state benefit from independent state-transition tests",
        },
        "roles": [
            {
                "id": "ROLE-L01",
                "name": "ProfileView",
                "role_kind": "layer",
                "layer": "view",
                "domain_role": None,
                "responsibility": "Render UI state and forward user intents",
                "hidden_secret": "UI rendering details",
                "change_triggers": ["Layout or interaction rendering changes"],
                "data_owned": "Short-lived local visual state only",
                "depends_on": ["ROLE-L02"],
                "industry_basis": "Declarative View",
                "design_principles": ["SRP"],
                "code_units": ["ui/ProfileView.ext"],
            },
            {
                "id": "ROLE-L02",
                "name": "ProfileViewModel",
                "role_kind": "layer",
                "layer": "view_model",
                "domain_role": None,
                "responsibility": "Own presentation state and orchestrate loading",
                "hidden_secret": "Presentation-state transitions",
                "change_triggers": ["Loading, retry, or presentation rules change"],
                "data_owned": "Profile screen UI state",
                "depends_on": [],
                "industry_basis": "MVVM Presentation Model",
                "design_principles": ["SRP", "DIP"],
                "code_units": ["ui/ProfileViewModel.ext"],
            },
        ],
        "interfaces": [{
            "id": "IFC-1", "name": "ProfileViewModel.load", "provider": "ROLE-L02",
            "consumers": ["ROLE-L01"], "input": "Load intent", "output": "Observable profile UI state",
            "preconditions": ["ViewModel is active"], "postconditions": ["State is success or failure"],
            "invariants": ["One UI-state source"], "errors": ["Repository errors map to failure state"],
            "data_ownership": "ViewModel owns screen state", "transaction": "not_applicable",
            "concurrency": "Cancel work when owner is disposed",
        }],
        "design_contract_checks": [{
            "id": "DC-1", "item": "ViewModel remains the single state owner",
            "principle": "information_hiding", "role_scope": ["ROLE-L02"],
        }],
        "business_process": [],
        "logging_standard": {"library": "project logger", "key_nodes_instrumented": ["入口", "异常"]},
        "verification": {
            "commands": [{"command": "unit tests", "status": "passed", "result": "all passed", "evidence": "test output"}],
            "checks": [{"target": "UI state transitions", "method": "existing_test", "status": "passed", "evidence": "test output"}],
            "unverified": [],
        },
        "summary": {"roles_count": 2, "interfaces_count": 1, "process_steps": 0,
                    "verification_checks": 1, "layer_roles": 2, "domain_roles": 0},
        "gate": {
            "architecture": "go",
            "logging": "go",
            "coverage": "go",
            "verification": "go",
            "verdict": "go",
            "issues": [],
            "notes": "UI architecture decision reviewed",
        },
    }


class CrossStackUiContractTests(unittest.TestCase):
    def test_low_impact_mvvm_passes_for_every_supported_stack(self) -> None:
        for stack in ("JVM", "C++", "FastAPI+Vue", "Swift/iOS"):
            with self.subTest(stack=stack):
                report = validate(contract(stack), Path("in-memory.json"))
                self.assertEqual([], report.errors)

    def test_high_impact_mvvm_requires_explicit_user_confirmation(self) -> None:
        data = contract()
        data["design_decision"]["profile"] = "high_risk"
        second = copy.deepcopy(data["design_decision"]["candidates"][0])
        second["id"] = "ALT-2"
        data["design_decision"]["candidates"].append(second)
        data["design_decision"]["risk_spikes"] = [{
            "question": "Can migration preserve lifecycle ownership?", "method": "prototype",
            "result": "Ownership remains feature-scoped", "status": "passed",
        }]
        data["design_decision"]["review"].update({"mode": "peer", "reviewer": "UI owner"})
        data["ui_architecture"]["migration_impact"] = "high"
        data["ui_architecture"]["migration_confirmation"] = "pending"
        report = validate(data, Path("in-memory.json"))
        self.assertTrue(any("C-UI14" in error for error in report.errors))

        data["ui_architecture"]["migration_confirmation"] = "user_confirmed"
        report = validate(data, Path("in-memory.json"))
        self.assertFalse(any("C-UI14" in error for error in report.errors))

    def test_simple_direct_view_does_not_require_view_model(self) -> None:
        data = contract("Swift/iOS")
        data["ui_architecture"].update({
            "current_patterns": ["Direct View"],
            "target_patterns": ["Direct View"],
            "view_model_policy": "not_used",
            "mvvm_suitability": "not_suitable",
            "migration_impact": "none",
            "impact_scope": [],
            "decision_reason": "Pure display with short-lived local visual state",
        })
        data["roles"] = [copy.deepcopy(data["roles"][0])]
        data["roles"][0]["depends_on"] = []
        data["interfaces"] = []
        data["summary"].update({"roles_count": 1, "interfaces_count": 0, "layer_roles": 1})
        report = validate(data, Path("in-memory.json"))
        self.assertEqual([], report.errors)

    def test_ui_roles_require_ui_architecture_decision(self) -> None:
        data = contract()
        del data["ui_architecture"]
        report = validate(data, Path("in-memory.json"))
        self.assertTrue(any("C-UI0" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
