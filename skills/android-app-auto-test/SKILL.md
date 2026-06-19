---
name: android-app-auto-test
description: Analyze a native Android app and user-specified requirements, derive real user operation paths, audit and improve testability, generate and run P0-first real-device automation tests, collect logs, repair failures, rerun affected tests, and produce human-readable plus machine-readable reports. Use when Codex is asked to automate testing for a native Android app, validate Android user flows on a physical device, add ids/testTags/contentDescription/logging for testability, choose among Espresso/Compose Test/UiAutomator based on project code, or run a repair loop after failed Android tests.
---

# Android App Auto Test

## Overview

Automate native Android app acceptance testing from requirements to real-device execution and repair. Treat the repository and the user-specified requirements document as evidence, produce durable artifacts under fixed `android-test` directories, ask for startup decisions once, then run P0 paths, fix failures, and report what changed.

## Startup Handshake

Before analysis or test execution, collect these inputs and decisions in one concise confirmation:

- Native Android project root and module if not obvious.
- User-specified requirements document path.
- Physical device `adb serial`; if multiple devices are connected, require an explicit serial.
- Whether app data may be cleared before tests. This decision applies to the run and should not be asked again.
- Whether testability changes may be made. The expected default is yes.
- Maximum automatic repair attempts per failing path. Default to `3`.
- Whether any high-risk paths are allowed. Default to excluding payment, destructive deletion, publishing, sending messages, or real profile changes.

Assume the target backend is a test environment. Do not introduce special test account handling unless the project already has it.

## Fixed Output Locations

Create and maintain these directories in the target Android project:

```text
docs/android-test/
artifacts/android-test/
```

Use Markdown files in `docs/android-test/` for human review and JSON files in `artifacts/android-test/` for continuation by later agents.

## Required Workflow

Follow this workflow in order:

1. Read `references/workflow.md` and `references/artifact-schema.md`.
2. Capture startup inputs in `artifacts/android-test/inputs.json`.
3. Inspect the Android project and physical device. Use `scripts/collect_device_profile.sh` when useful.
4. Read `references/test-stack-selection.md`; produce `docs/android-test/test-stack-audit.md` and `artifacts/android-test/test-stack-audit.json`.
5. Analyze the user-specified requirements and code to derive real operation paths. Produce `docs/android-test/path-map.md` and `artifacts/android-test/path-map.json`.
6. Ask the user to confirm `path-map.md`, including P0/P1/P2 priorities. The skill may propose priorities first; P0 must be confirmed before execution.
7. Read `references/android-testability-rules.md`; audit ids, Compose testTags, content descriptions, and logs. Produce `docs/android-test/testability-audit.md`.
8. Apply approved testability changes once startup permission allows it. Prefer stable ids/testTags over accessibility text. Add logs only where they help path verification or failure triage.
9. Produce `docs/android-test/test-plan.md` and `artifacts/android-test/test-plan.json`, starting with P0 coverage.
10. Generate or update Android tests using the selected stack.
11. Run P0 tests on the selected physical device. Collect command output, instrumentation output, screenshots or recordings when practical, and logcat evidence. Use `scripts/collect_logcat.sh` when useful.
12. Classify each failure, fix one root cause at a time, record the fix, and rerun the affected path. Stop after the configured maximum attempts.
13. Produce `docs/android-test/fix-report.md`, `docs/android-test/final-report.md`, and JSON artifacts for run logs, failures, fixes, and coverage. Run `scripts/redact_report.py` before finalizing reports that may contain secrets or personal data.

## Gates

Use these gates:

- Gate 1: Confirm operation paths and P0 priority after `path-map.md`.
- Gate 2: Confirm testability modifications only if startup permission was not already granted or if a high-risk code/config change is needed.
- Gate 3: Confirm real-device execution settings at startup only; do not repeatedly interrupt after confirmation.

## Failure Policy

Use these failure classes exactly:

- `TEST_CODE_ERROR`: test code is wrong, locator is unstable, or wait/synchronization is insufficient.
- `APP_TESTABILITY_GAP`: the app lacks stable ids, testTags, semantic descriptions, or logs needed for reliable testing.
- `APP_FUNCTIONAL_BUG`: app behavior contradicts the confirmed path expectation.
- `ENVIRONMENT_ERROR`: device, adb, network, backend, permission, or build environment issue.
- `REQUIREMENT_AMBIGUITY`: requirements, code, and confirmed path disagree.
- `FLAKY`: intermittent failure after rerun evidence.

Only change app behavior for `APP_FUNCTIONAL_BUG`. Fix tests for `TEST_CODE_ERROR`; add ids/testTags/logs for `APP_TESTABILITY_GAP`; report blockers for unresolved `ENVIRONMENT_ERROR` or `REQUIREMENT_AMBIGUITY`.

## Dedicated Agents

Use dedicated subagents when available. Read `references/subagent-protocol.md`, then launch agents with only the relevant artifacts and the role prompt from `agents/`. Do not pass private conclusions or long conversational summaries.

Recommended roles:

- `agents/path-analyst.md`
- `agents/testability-auditor.md`
- `agents/test-planner.md`
- `agents/test-runner.md`
- `agents/bug-fixer.md`
- `agents/report-writer.md`

The main agent remains responsible for gate decisions, applying edits, running commands, and reconciling artifacts.

## Safety

Default to test environment execution. Do not store real credentials in the repository. Do not run high-risk paths unless explicitly allowed in startup inputs. Redact tokens, emails, phone numbers, cookies, authorization headers, and obvious session identifiers from final reports.
