#!/usr/bin/env python3
"""Run behavior and Full-contract checks for non-linear mechanism examples."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import unittest

import validate_analysis
import validate_report
from render_report import render_report

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parents[1]
KEYFRAME_FIXTURE = (
    SKILL_DIR / "examples/fixtures/keyframe-easing/src/keyframe.ts"
)

CASES = {
    "async": {
        "analysis": SKILL_DIR / "examples/2026-07-24-async-analysis.json",
        "report": SKILL_DIR / "examples/2026-07-24-async-analysis.md",
        "fixture": SKILL_DIR / "examples/fixtures/async-event-pipeline/async_pipeline.py",
        "expected_output": ["ALPHA", "BETA"],
        "mechanism_type": "data-flow",
        "segments": ["produce", "schedule", "process", "effect"],
        "report_markers": ["asyncio.gather", "None"],
    },
    "state-machine": {
        "analysis": SKILL_DIR / "examples/2026-07-24-state-machine-analysis.json",
        "report": SKILL_DIR / "examples/2026-07-24-state-machine-analysis.md",
        "fixture": SKILL_DIR / "examples/fixtures/order-state-machine/state_machine.py",
        "expected_output": ["created", "paid", "shipped"],
        "mechanism_type": "state-machine",
        "segments": ["state", "transition", "action", "effect"],
        "report_markers": ['created["created"]', "ALLOWED_TRANSITIONS"],
    },
    "reflection": {
        "analysis": SKILL_DIR / "examples/2026-07-24-reflection-analysis.json",
        "report": SKILL_DIR / "examples/2026-07-24-reflection-analysis.md",
        "fixture": SKILL_DIR / "examples/fixtures/reflection-dispatch/plugin_dispatch.py",
        "expected_output": {"plugin": "upper", "result": "HELLO"},
        "mechanism_type": "call-chain",
        "segments": ["entry", "resolve", "bind", "invoke", "effect"],
        "report_markers": ["getattr", "inspect.signature"],
    },
}


class MechanismExampleTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for TypeScript runtime validation")
    def test_keyframe_protocol_fallbacks(self) -> None:
        script = f"""
import {{ KeyframeTrack }} from {json.dumps(KEYFRAME_FIXTURE.as_uri())};
const empty = new KeyframeTrack().sampleAt(5);
const track = new KeyframeTrack()
  .addKeyframe(1, 10)
  .addKeyframe(2, 20);
console.log(JSON.stringify({{
  empty,
  before: track.sampleAt(0),
  atFirst: track.sampleAt(1),
  inside: track.sampleAt(1.5),
  atLast: track.sampleAt(2),
  after: track.sampleAt(3),
}}));
"""
        result = subprocess.run(
            ["node", "--experimental-strip-types", "--input-type=module", "-e", script],
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(
            {
                "empty": 0,
                "before": 10,
                "atFirst": 10,
                "inside": 15,
                "atLast": 20,
                "after": 20,
            },
            json.loads(result.stdout),
        )

    def test_fixture_runtime_behavior(self) -> None:
        for name, case in CASES.items():
            with self.subTest(case=name):
                result = subprocess.run(
                    ["python3", str(case["fixture"])],
                    text=True,
                    capture_output=True,
                    check=True,
                )
                self.assertEqual(case["expected_output"], json.loads(result.stdout))

    def test_async_empty_stream_terminates(self) -> None:
        namespace = runpy.run_path(str(CASES["async"]["fixture"]))
        self.assertEqual([], asyncio.run(namespace["run_pipeline"]([])))

    def test_state_machine_rejects_invalid_edge(self) -> None:
        namespace = runpy.run_path(str(CASES["state-machine"]["fixture"]))
        machine = namespace["OrderMachine"]()
        with self.assertRaises(ValueError):
            machine.transition(namespace["OrderState"].SHIPPED)

    def test_reflection_binding_and_failure_paths(self) -> None:
        namespace = runpy.run_path(str(CASES["reflection"]["fixture"]))
        self.assertEqual(
            {"plugin": "prefix", "result": ">>hello"},
            namespace["handle"](
                {
                    "method": "prefix",
                    "payload": "hello",
                    "options": {"value": ">>"},
                }
            ),
        )
        with self.assertRaises(LookupError):
            namespace["handle"]({"method": "missing", "payload": "hello"})
        with self.assertRaises(TypeError):
            namespace["handle"](
                {
                    "method": "upper",
                    "payload": "hello",
                    "options": {"unexpected": True},
                }
            )

    def test_full_contract_evidence_render_and_report(self) -> None:
        for name, case in CASES.items():
            with self.subTest(case=name):
                data = json.loads(case["analysis"].read_text(encoding="utf-8"))
                analysis_report = validate_analysis.validate(data)
                self.assertEqual([], analysis_report.errors)
                self.assertEqual(case["mechanism_type"], data["mechanism_type"])
                self.assertEqual(case["segments"], data["chain_template"])
                self.assertGreaterEqual(len(data["boundary_inventory"]), 1)
                self.assertTrue(
                    {
                        "cancellation", "exception", "concurrency",
                    }
                    <= {
                        item["kind"]
                        for item in data["boundary_inventory"]
                    }
                )
                self.assertIn("flow-control", {
                    item["kind"] for item in data["boundary_inventory"]
                })
                self.assertEqual(
                    {
                        "cancellation", "exception",
                        "concurrency", "backpressure",
                    },
                    set(data["boundary_coverage"]),
                )
                self.assertGreaterEqual(len(data["behavior_cases"]), 1)
                self.assertGreaterEqual(len(data["acceptance_cases"]), 1)
                self.assertIn("## 多入口/分支行为矛盾", render_report(data))
                self.assertFalse(
                    any("mmdc" in gap for gap in data["gaps"])
                )

                evidence = subprocess.run(
                    [
                        "python3",
                        str(SKILL_DIR / "scripts/validate_evidence.py"),
                        str(case["analysis"]),
                        "--root",
                        str(REPO_ROOT),
                    ],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(0, evidence.returncode, evidence.stdout + evidence.stderr)
                self.assertIn("WARNING: 0", evidence.stdout)

                rendered = render_report(data)
                self.assertNotIn("status: draft", rendered)
                for marker in (
                    "## 业务流程图",
                    "flowchart LR",
                    "## 时序图",
                    "sequenceDiagram",
                    "## 架构角色图",
                    "flowchart TB",
                    "## 全链路",
                ):
                    self.assertIn(marker, rendered)
                self.assertLess(
                    rendered.index("## 业务流程图"),
                    rendered.index("## 时序图"),
                )
                self.assertLess(
                    rendered.index("## 时序图"),
                    rendered.index("## 架构角色图"),
                )
                self.assertLess(
                    rendered.index("## 架构角色图"),
                    rendered.index("## 全链路"),
                )
                for marker in case["report_markers"]:
                    self.assertIn(marker, rendered)
                tracked_report = case["report"].read_text(encoding="utf-8")
                self.assertEqual(rendered, tracked_report)
                errors, _ = validate_report.validate(case["report"], REPO_ROOT)
                self.assertEqual([], errors)

    def test_openai_interface_metadata(self) -> None:
        lines = (
            (SKILL_DIR / "agents/openai.yaml")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        self.assertEqual("interface:", lines[0])
        interface: dict[str, str] = {}
        for line in lines[1:]:
            self.assertTrue(line.startswith("  "))
            key, value = line.strip().split(":", 1)
            interface[key] = json.loads(value.strip())
        self.assertEqual(
            {
                "display_name": "Technical Mechanism Analysis",
                "short_description": (
                    "Trace a mechanism with three validated diagrams"
                ),
                "default_prompt": (
                    "Use $tech-mechanism-analysis in lite or full mode. Before the "
                    "detailed analysis, produce and validate a business-flow diagram, "
                    "a sequence diagram, and an architecture-role diagram that states "
                    "which class, module, or service owns each responsibility; then "
                    "trace the mechanism with code evidence, boundary behavior cases, "
                    "acceptance cases, and conflict checks."
                ),
            },
            interface,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
