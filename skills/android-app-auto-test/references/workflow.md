# Workflow

Use this workflow as the operational contract for native Android automated testing.

## 1. Inputs

Capture startup decisions in `artifacts/android-test/inputs.json`:

- `requirements_path`
- `project_root`
- `android_module`
- `adb_serial`
- `may_clear_app_data`
- `may_modify_testability`
- `max_fix_attempts`, default `3`
- `allowed_high_risk_paths`, default `false`
- `target_environment`, fixed to `test`

Validate that the requirements file exists and the project is a native Android project by checking Gradle files, Android manifests, source sets, and package structure.

## 2. Device Profile

Use `adb -s <serial>` for every adb command. If no serial is known and more than one device is connected, stop and ask the user to choose.

Record:

- serial
- manufacturer, model, Android version, API level
- screen size and density
- network state when available
- package name and build variant
- whether app data was cleared

## 3. Code And Requirements Analysis

Analyze requirements, navigation, UI code, ViewModels/presenters, repository calls, manifests, and existing tests. Derive real operation paths from evidence, not desired behavior alone.

Each path must contain:

- stable `path_id`
- business goal
- priority proposed by the skill: P0, P1, or P2
- preconditions and test data assumptions
- entry point
- ordered user actions
- expected UI result
- expected state or backend-visible result when inferable
- logging evidence expected during execution
- automation readiness: `ready`, `needs_testability`, `manual_only`, or `blocked`
- risk flags: auth, payment, deletion, publish, external app, system permission, captcha, timing, network
- evidence references to requirement sections or code files

After producing `path-map.md`, ask the user to confirm the paths and priorities. Proceed with P0 first.

## 4. Testability Audit

Audit whether each P0 step can be located and verified without fragile text-only matching. Prefer:

1. Compose `Modifier.testTag(...)`
2. XML/View `android:id`
3. stable resource names
4. semantic `contentDescription` only when appropriate for accessibility
5. fallback text match only for stable, user-visible text

Audit logs for path verification and failure triage. Add or extend logs through the project's existing logging mechanism. Avoid noisy logs.

## 5. Test Plan

Create `test-plan.md` and `test-plan.json` with:

- P0 paths first
- selected test framework
- generated or modified test files
- setup/teardown strategy
- clear-app-data decision
- commands to run
- expected logs and assertions
- excluded high-risk paths
- known blockers

## 6. Run And Repair Loop

For each P0 path:

1. Run the smallest relevant test command.
2. Collect evidence: command output, instrumentation output, logcat, stack traces, screenshots on failure, and screenrecord when useful.
3. Classify the failure using the fixed classes from `SKILL.md`.
4. Fix one root cause only.
5. Record the fix in `fix-report.md` and `artifacts/android-test/fixes.json`.
6. Rerun the affected test.
7. Stop after `max_fix_attempts` for that path.

Do not broaden a fix beyond the failing path unless the same root cause clearly affects shared test infrastructure.

## 7. Final Report

Produce:

- `docs/android-test/final-report.md`: concise human report with scope, device, stack, coverage, results, fixes, unresolved issues, and next steps.
- JSON artifacts for follow-up automation: `run-log.json`, `failures.json`, `fixes.json`, `coverage.json`.

Redact secrets and personal data before final delivery.
