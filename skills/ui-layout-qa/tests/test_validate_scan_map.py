import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_scan_map.py"
SPEC = importlib.util.spec_from_file_location("validate_scan_map", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


MAP = """Target: projects
Source: routes.ts:/projects
Unknown: none
+------------------+
| Project list     |
+------------------+
"""


def manifest(status="pending", **confirmation_overrides):
    confirmation = {"status": status}
    confirmation.update(confirmation_overrides)
    return {
        "mode": "full_audit",
        "scan_scope": "app",
        "overview_file": "scan-map-overview.txt",
        "targets": [
            {
                "id": "projects",
                "label": "Projects",
                "map_file": "scan-map/projects.txt",
                "source_anchors": ["routes.ts:/projects"],
                "evidence_types": ["code"],
                "unknowns": [],
                "revision": 1,
                "confirmation": confirmation,
            }
        ],
    }


class ValidateScanMapTests(unittest.TestCase):
    def with_map(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        map_path = root / "scan-map" / "projects.txt"
        map_path.parent.mkdir()
        map_path.write_text(MAP, encoding="utf-8")
        (root / "scan-map-overview.txt").write_text("Scan scope: app\n- projects\n", encoding="utf-8")
        return directory, root

    def test_draft_map_passes_with_pending_confirmation(self):
        directory, root = self.with_map()
        self.addCleanup(directory.cleanup)
        errors, summary = MODULE.validate_manifest(manifest(), root, "draft")
        self.assertEqual(errors, [])
        self.assertEqual(summary["pending"], 1)

    def test_confirmed_map_requires_user_evidence(self):
        directory, root = self.with_map()
        self.addCleanup(directory.cleanup)
        errors, _ = MODULE.validate_manifest(manifest("user_confirmed"), root, "confirmed")
        self.assertTrue(any("confirmed_by" in error for error in errors))
        self.assertTrue(any("evidence" in error for error in errors))

    def test_confirmed_map_passes_with_explicit_user_evidence(self):
        directory, root = self.with_map()
        self.addCleanup(directory.cleanup)
        document = manifest(
            "user_confirmed",
            confirmed_by="user",
            evidence="User message: maps are correct",
        )
        errors, summary = MODULE.validate_manifest(document, root, "confirmed")
        self.assertEqual(errors, [])
        self.assertEqual(summary["confirmed"], 1)

    def test_missing_map_or_drawing_fails(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        self.addCleanup(directory.cleanup)
        errors, _ = MODULE.validate_manifest(manifest(), root, "draft")
        self.assertTrue(any("does not exist" in error for error in errors))

    def test_overview_is_required(self):
        directory, root = self.with_map()
        self.addCleanup(directory.cleanup)
        (root / "scan-map-overview.txt").unlink()
        errors, _ = MODULE.validate_manifest(manifest(), root, "draft")
        self.assertTrue(any("overview_file does not exist" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
