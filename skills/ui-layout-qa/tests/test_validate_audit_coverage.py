import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_audit_coverage.py"
SPEC = importlib.util.spec_from_file_location("validate_audit_coverage", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def page(checks, **overrides):
    result = {
        "id": "projects",
        "name": "Projects",
        "platform": "web",
        "entry_evidence": ["routes.ts: /projects"],
        "reachability": "reachable",
        "required_states": ["empty"],
        "checks": checks,
    }
    result.update(overrides)
    return result


class ValidateAuditCoverageTests(unittest.TestCase):
    def test_complete_inventory_is_valid_and_coverage_complete(self):
        document = {
            "audit_scope": "app",
            "pages": [
                page(
                    [
                        {"name": "default", "result": "verified", "evidence": ["preview"]},
                        {"name": "long_text", "result": "verified", "evidence": ["fixture"]},
                        {"name": "narrow", "result": "audited_unverified", "reason": "preview unavailable"},
                        {"name": "state:empty", "result": "not_applicable", "reason": "no empty state"},
                    ]
                )
            ],
        }
        errors, summary = MODULE.validate_inventory(document)
        self.assertEqual(errors, [])
        self.assertEqual(summary["pages"], 1)
        self.assertEqual(MODULE.completion_failures(document, False), [])
        self.assertEqual(MODULE.completion_failures(document, True), ["projects/narrow: audited_unverified"])

    def test_pending_and_blocked_prevent_coverage_completion(self):
        document = {
            "audit_scope": "app",
            "pages": [
                page(
                    [
                        {"name": "default", "result": "verified", "evidence": ["preview"]},
                        {"name": "long_text", "result": "pending"},
                        {"name": "narrow", "result": "blocked", "reason": "device unavailable"},
                        {"name": "state:empty", "result": "not_applicable", "reason": "no empty state"},
                    ]
                ),
                page([], id="admin", name="Admin", reachability="blocked", reason="missing account"),
            ],
        }
        errors, _ = MODULE.validate_inventory(document)
        self.assertEqual(errors, [])
        self.assertEqual(
            MODULE.completion_failures(document, False),
            ["projects/long_text: pending", "projects/narrow: blocked", "admin: page is blocked"],
        )

    def test_missing_required_check_and_duplicate_page_fail_validation(self):
        document = {
            "audit_scope": "app",
            "pages": [
                page([{"name": "default", "result": "verified", "evidence": ["preview"]}]),
                page([{"name": "default", "result": "verified", "evidence": ["preview"]}]),
            ],
        }
        errors, _ = MODULE.validate_inventory(document)
        self.assertTrue(any("duplicate page id" in error for error in errors))
        self.assertTrue(any("long_text" in error for error in errors))
        self.assertTrue(any("state:empty" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
