#!/usr/bin/env python3
"""Regression tests for risk-sized design-decision requirements."""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

from test_validate_contract_ui import contract
from validate_contract import validate


class DesignDecisionContractTests(unittest.TestCase):
    def test_standard_profile_requires_two_candidates(self) -> None:
        data = contract()
        data["design_decision"]["profile"] = "standard"
        data["design_decision"]["review"].update({"mode": "independent", "reviewer": "second pass"})
        report = validate(data, Path("in-memory.json"))
        self.assertTrue(any("C-DD4" in error for error in report.errors))

        second = copy.deepcopy(data["design_decision"]["candidates"][0])
        second["id"] = "ALT-2"
        second["summary"] = "Direct view with a repository"
        data["design_decision"]["candidates"].append(second)
        report = validate(data, Path("in-memory.json"))
        self.assertFalse(any("C-DD4" in error for error in report.errors))

    def test_high_risk_requires_spike_and_user_or_peer_review(self) -> None:
        data = contract()
        data["design_decision"]["profile"] = "high_risk"
        second = copy.deepcopy(data["design_decision"]["candidates"][0])
        second["id"] = "ALT-2"
        data["design_decision"]["candidates"].append(second)
        report = validate(data, Path("in-memory.json"))
        self.assertTrue(any("C-DD8" in error for error in report.errors))
        self.assertTrue(any("C-DD10" in error for error in report.errors))

        data["design_decision"]["risk_spikes"] = [{
            "question": "Can cancellation follow view lifetime?", "method": "minimal prototype",
            "result": "Task cancelled on disposal", "status": "passed",
        }]
        data["design_decision"]["review"].update({"mode": "peer", "reviewer": "UI owner"})
        report = validate(data, Path("in-memory.json"))
        self.assertFalse(any("C-DD8" in error for error in report.errors))
        self.assertFalse(any("high_risk 必须" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
