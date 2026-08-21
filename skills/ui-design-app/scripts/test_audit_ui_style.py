#!/usr/bin/env python3
"""Regression tests for deterministic UI surface discovery."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("audit-ui-style.py")


class AuditUiStyleTests(unittest.TestCase):
    def run_audit(self, project: Path, workers: int) -> dict:
        result = subprocess.run(
            [
                "python3", str(SCRIPT), "--project", str(project), "--style", "finder",
                "--format", "json", "--workers", str(workers),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_multistack_inventory_and_parallel_determinism(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "src/App.tsx": """
                    export function App() { return <main><button aria-disabled={false}>Save</button><Dialog /></main> }
                    const Card = () => <a href='/item'>Open</a>
                    const routes = [{ path: '/reports' }]
                """,
                "src/components/Menu.vue": """
                    <template><nav><button role=\"menu\">Menu</button></nav></template>
                    <style>.item:hover { color: #fff } .item:focus-visible { outline: 2px solid blue }</style>
                """,
                "src/app/settings/page.tsx": "export default function SettingsPage(){ return <input disabled={false} /> }",
                "src/NativeView.swift": "struct NativeView: View { var body: some View { Button(\"Save\") {} } }",
                "src/theme.css": ":root { color: #111; } @media (max-width: 600px) { .x { padding: 4px } }",
                "src/ui/panel.cs": "public class PanelView {}",
                "node_modules/ignored.tsx": "export function ShouldNotAppear(){ return <button/> }",
                "docs/styles/notes.md": "# Design notes",
            }
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")

            serial = self.run_audit(root, 1)
            parallel = self.run_audit(root, 4)
            for report in (serial, parallel):
                report["scan"].pop("mode")
                report["scan"].pop("workers_used")
            self.assertEqual(serial, parallel)

            inventory = serial["inventory"]
            component_names = {item["name"] for item in inventory["components"]["items"]}
            route_ids = {item["id"] for item in inventory["routes"]["items"]}
            element_kinds = {item["kind"] for item in inventory["interactive_elements"]["items"]}
            source_ids = {item["id"] for item in inventory["source_files"]["items"]}
            self.assertTrue({"App", "Card", "Dialog", "Menu", "SettingsPage", "NativeView"}.issubset(component_names))
            self.assertTrue({"/reports", "/settings"}.issubset(route_ids))
            self.assertTrue({"button", "input", "a", "nav", "main", "role:menu", "native:button"}.issubset(element_kinds))
            self.assertTrue(all(":" in item["id"] and item["line"] > 0 for item in inventory["interactive_elements"]["items"]))
            self.assertIn("src/theme.css", source_ids)
            self.assertNotIn("node_modules/ignored.tsx", source_ids)
            skipped = self.run_audit(root, 1)["scan"]["skipped"]
            self.assertIn("src/ui/panel.cs", skipped["unsupported_ui_extension"]["examples"])
            self.assertNotIn("docs/styles/notes.md", skipped.get("unsupported_ui_extension", {}).get("examples", []))
            self.assertEqual(serial["coverage"]["status"], "static_incomplete")


if __name__ == "__main__":
    unittest.main()
