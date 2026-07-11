---
name: android-app-auto-test
description: Analyze a native Android app and user-specified requirements, derive real user operation paths, audit and improve testability, generate and run scoped real-device automation tests, collect logs, repair failures, rerun affected tests, and produce human-readable plus machine-readable reports. Use when Codex is asked to automate testing for a native Android app, validate Android user flows on a physical device, run only a specified test scope or existing test plan, add ids/testTags/contentDescription/logging for testability, choose among Espresso/Compose Test/UiAutomator based on project code, or run a repair loop after failed Android tests.
---

# Android App Auto Test

## Overview

Automate native Android app acceptance testing from requirements to real-device execution and repair. Treat the repository and the user-specified requirements document as evidence, produce durable artifacts under fixed `android-test` directories, ask for startup decisions once, then run the confirmed scope, fix failures, and report what changed. Support both full analysis runs and direct execution from an existing path map, test plan, test file, or explicit Gradle command.

## Startup Handshake

Before analysis or test execution, collect these inputs and decisions in one concise confirmation:

- Native Android project root and module if not obvious.
- User-specified requirements document path, unless the run starts from existing tests only.
- Requested test scope: all confirmed P0, selected priorities, selected `path_id`s, feature/module area, test class/file, package, or explicit Gradle command.
- Entry stage: `full`, `path-map`, `test-plan`, or `execute`. Default to `full` unless the user asks to start from existing artifacts or existing tests.
- Whether to re-analyze requirements/code; default to yes for `full`, no for `test-plan` or `execute`.
- Whether to regenerate or refresh `path-map.md`; default to yes for `full`, no for `test-plan` or `execute`.
- Whether to rerun the testability/log audit and apply low-risk ids/testTags/log additions; default to yes for newly generated paths, no for direct execution unless tests are blocked by locator/log gaps.
- Whether to generate/update tests or run existing tests only; default to generate/update for `full` and `test-plan`, existing-only for `execute`.
- Physical device `adb serial`; if multiple devices are connected, require an explicit serial.
- Whether app data may be cleared before tests. This decision applies to the run and should not be asked again.
- Whether low-risk testability changes may be made after the audit lists the exact files and change types. The expected default is yes.
- Maximum automatic repair attempts per failing path. Default to `3`.
- Whether any high-risk paths are allowed. Default to excluding payment, destructive deletion, publishing, sending messages, or real profile changes.
- Whether to run non-interactive. When `non_interactive` is true, the startup decisions above pre-authorize Gates 0–2 from `inputs.json` and the skill must not prompt mid-run. Required for CI or cron.
- Whether to run as a resumable batch. When `batch_mode` is true, drive the confirmed scope one path at a time through `artifacts/android-test/run-state.json` so the run survives interruption and resumes. Required for long runs or full-coverage runs.
- Whether to build the coverage model. When `coverage_modeling` is true, also produce `screen-inventory`, `nav-graph`, `business-matrix`, and `dependency-map` so coverage is measurable per feature/screen/edge and regression-safe repair works.
- Whether regression is re-run after an app-code fix. Default `regression_on_fix: true` in batch mode: after an `APP_FUNCTIONAL_BUG` fix, rerun the regression subset from `dependency-map.json`, not only the fixed path.
- Per-path state isolation: `clear_data`, `setup_contract`, or `none`. `none` is only safe when paths are provably independent.
- Environment retry budget for `ENVIRONMENT_ERROR` (`env_retry`: max retries + backoff) and flake policy (`flake_policy`: retries, quarantine threshold, minimum sample).

Assume the target backend is a test environment. Do not introduce special test account handling unless the project already has it.

## Fixed Output Locations

Create and maintain these directories in the target Android project:

```text
docs/android-test/
artifacts/android-test/
```

Use Markdown files in `docs/android-test/` for human review and JSON files in `artifacts/android-test/` for continuation by later agents.

## Required Workflow

Follow this workflow in order, skipping analysis/planning steps only when startup decisions explicitly choose a later entry stage and the required artifacts or commands already exist:

1. Read `references/workflow.md` and `references/artifact-schema.md`. When `coverage_modeling` is enabled, also read `references/coverage-model.md`; for unattended or repeated runs, also read `references/continuous-running.md`; when high-risk paths are allowed, also read `references/hermetic-high-risk.md`.
2. Capture startup inputs in `artifacts/android-test/inputs.json`.
3. Inspect the Android project and physical device. Use `scripts/collect_device_profile.sh` when useful.
4. Read `references/test-stack-selection.md`; produce or reuse `docs/android-test/test-stack-audit.md` and `artifacts/android-test/test-stack-audit.json`.
5. If startup decisions require analysis or `path-map.json` is missing, analyze the selected requirements/code scope to derive real operation paths. Produce `docs/android-test/path-map.md` and `artifacts/android-test/path-map.json`. When `coverage_modeling` is enabled, the coverage model (screen-inventory, nav-graph, business-matrix, dependency-map) is built after testability anchors are in place (step 8).
6. Ask the user to confirm generated or changed paths and priorities. If reusing an existing path map, confirm only the requested execution scope.
7. If startup decisions require testability/log review or the selected scope is not automatable, read `references/android-testability-rules.md`; audit ids, Compose testTags, content descriptions, and logs for the selected scope. Produce or update `docs/android-test/testability-audit.md`.
8. Apply approved low-risk testability changes once startup permission allows it and the audit lists the exact files and change types. Prefer stable ids/testTags over accessibility text. Add logs only where they help path verification or failure triage. Reconfirm before Gradle/config changes, behavior changes, broad logging, or changes outside the confirmed scope. When `coverage_modeling` is enabled, invoke the coverage-modeler role to produce `screen-inventory`, `nav-graph`, and `business-matrix`, and the regression-protector role to build `dependency-map`.
9. If startup decisions require planning or `test-plan.json` is missing, produce or update `docs/android-test/test-plan.md` and `artifacts/android-test/test-plan.json` for the confirmed scope.
10. Generate or update Android tests using the selected stack unless startup decisions say to run existing tests only.
11. Execute the confirmed scope on the selected physical device. In batch mode, drive this as a loop: initialize `artifacts/android-test/run-state.json` with `scripts/run_state.py init`, then repeatedly claim the next pending path with `run_state.py next-pending`, run `scripts/device_health_check.sh` first, run the smallest relevant test command, collect instrumentation output, screenshots or recordings when practical, and logcat evidence via `scripts/collect_logcat.sh`, then mark the path's status with `run_state.py mark`. Continue until no path is pending.
12. Classify each failure, fix one root cause at a time, record the fix, and rerun the affected path. Retry `ENVIRONMENT_ERROR` within `inputs.env_retry` before blocking. For `APP_FUNCTIONAL_BUG` fixes that touch app source, invoke the regression-protector to get the regression subset and rerun it (recorded in `regression-runs.json`), not just the fixed path. Stop after the configured `max_fix_attempts` for that path; in batch mode, mark it `failed` or `blocked` and continue with the next pending path instead of aborting.
13. Produce `docs/android-test/fix-report.md`, `docs/android-test/final-report.md`, and JSON artifacts for run logs, failures, fixes, and coverage. When the coverage model is enabled, also produce per-feature/screen/edge coverage dimensions; after regression reruns produce `docs/android-test/regression-report.md`; for flaky paths produce `docs/android-test/flake-report.md`. For continuous runs, append a `trend.json` entry with `scripts/build_trend.py` and render `docs/android-test/trend-report.md`. Run `scripts/redact_report.py` before finalizing reports that may contain secrets or personal data.

## Gates

Use these gates:

- Gate 0: Confirm startup scope, entry stage, whether to re-analyze code, whether to regenerate paths, whether to rerun testability/log audit, and whether to generate/update tests or run existing tests only.
- Gate 1: Confirm generated or changed operation paths and priority after `path-map.md`; when starting from existing artifacts, confirm only the selected execution scope.
- Gate 2: Confirm testability modifications only if startup permission was not already granted or if a high-risk code/config change is needed.
- Gate 3: Confirm real-device execution settings at startup only; do not repeatedly interrupt after confirmation.
- Non-interactive mode: when `non_interactive` is true in `inputs.json`, Gates 0–2 are pre-authorized by those same inputs and must not prompt. The dispatcher reuses Gate 3 settings for the whole batch and never blocks on a human.

## Failure Policy

Use these failure classes exactly:

- `TEST_CODE_ERROR`: test code is wrong, locator is unstable, or wait/synchronization is insufficient.
- `APP_TESTABILITY_GAP`: the app lacks stable ids, testTags, semantic descriptions, or logs needed for reliable testing.
- `APP_FUNCTIONAL_BUG`: app behavior contradicts the confirmed path expectation.
- `ENVIRONMENT_ERROR`: device, adb, network, backend, permission, or build environment issue.
- `REQUIREMENT_AMBIGUITY`: requirements, code, and confirmed path disagree.
- `FLAKY`: intermittent failure after rerun evidence.

Only change app behavior for `APP_FUNCTIONAL_BUG`. Fix tests for `TEST_CODE_ERROR`; add ids/testTags/logs for `APP_TESTABILITY_GAP`; report blockers for unresolved `ENVIRONMENT_ERROR` or `REQUIREMENT_AMBIGUITY`.

Repair And Reliability Addendum:

- Treat `ENVIRONMENT_ERROR` as retryable first: run `scripts/device_health_check.sh` before each path, and on failure retry within `inputs.env_retry` before recording a blocker.
- In batch mode, persist every path's status in `run-state.json` and never abort the whole batch on one path's failure; mark it and continue.
- Regressions: after any `APP_FUNCTIONAL_BUG` fix that touches app source, rerun the regression subset (Phase 2, `dependency-map.json`), not just the fixed path.
- Flakiness: retry within `flake_policy.retries`; intermittent failures are recorded for quarantine (Phase 3, `flake-tracker.json`) and stop blocking once they exceed threshold.

## Dedicated Agents

Use dedicated subagents when available. Read `references/subagent-protocol.md`, then launch agents with only the relevant artifacts and the role prompt from `agents/`. Do not pass private conclusions or long conversational summaries.

Recommended roles:

- `agents/path-analyst.md`
- `agents/testability-auditor.md`
- `agents/coverage-modeler.md` (when `coverage_modeling` is enabled)
- `agents/test-planner.md`
- `agents/dispatcher.md` (batch loop driver, when `batch_mode` is enabled)
- `agents/test-runner.md`
- `agents/bug-fixer.md`
- `agents/regression-protector.md` (regression subset + failure clustering)
- `agents/report-writer.md`

The main agent remains responsible for gate decisions, applying edits, running commands, and reconciling artifacts.

## Safety

Default to test environment execution. Do not store real credentials in the repository. Do not run high-risk paths unless explicitly allowed in startup inputs. Redact tokens, emails, phone numbers, cookies, authorization headers, and obvious session identifiers from final reports.

## Continuous And Full-Coverage Running

For unattended, repeated, all-business regression, set `non_interactive: true` and `batch_mode: true` and build the coverage model once (`coverage_modeling: true`). The dispatcher drives the batch from `run-state.json`; nightly runs the full map, per-commit runs only the `scripts/incremental_select.py` subset. See `references/continuous-running.md`. To cover payment/delete/publish safely instead of excluding them, see `references/hermetic-high-risk.md` (requires `allowed_high_risk_paths: true` and a supporting test environment).
