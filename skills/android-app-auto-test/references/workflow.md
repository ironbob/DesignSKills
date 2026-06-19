# Workflow

Use this workflow as the operational contract for native Android automated testing.

## 1. Inputs

Capture startup decisions in `artifacts/android-test/inputs.json`:

- `requirements_path`
- `project_root`
- `android_module`
- `entry_stage`: `full`, `path-map`, `test-plan`, or `execute`
- `test_scope`
- `reanalyze_code`
- `regenerate_path_map`
- `rerun_testability_audit`
- `generate_or_update_tests`
- `run_existing_tests_only`
- `adb_serial`
- `may_clear_app_data`
- `may_modify_testability`
- `max_fix_attempts`, default `3`
- `allowed_high_risk_paths`, default `false`
- `target_environment`, fixed to `test`

Validate that the project is a native Android project by checking Gradle files, Android manifests, source sets, and package structure. Validate that the requirements file exists unless `entry_stage` is `execute` and the run uses only existing tests or explicit commands.

## 1.1 Scope And Entry Stage

Treat scope as a hard boundary for planning, execution, repair, and reporting. Supported scope forms:

- all confirmed P0 paths
- selected priorities: P0, P1, P2
- selected `path_id`s from `path-map.json`
- feature/module area named by the user
- selected test class, test package, or test file
- explicit Gradle command

Use these entry stages:

- `full`: inspect requirements/code, generate path map, audit testability/logs, plan, generate/update tests, then execute the confirmed scope.
- `path-map`: start from an existing or user-provided path map, optionally refresh selected paths, then audit/plan/execute the confirmed scope.
- `test-plan`: start from an existing path map and test plan, optionally refresh testability/logs or tests, then execute the confirmed scope.
- `execute`: run existing tests or an explicit command for the confirmed scope. Do not re-analyze code, regenerate paths, add logs, or generate tests unless the startup decision explicitly says to do so or execution is blocked by missing artifacts.

Before executing, confirm whether to:

- re-analyze requirements/code
- regenerate or refresh `path-map.md`
- rerun testability/log audit
- add ids/testTags/content descriptions/logs
- generate or update tests
- run existing tests only

If scope references unknown `path_id`s or missing test files, stop and ask for correction or permission to refresh the needed artifact.

## 2. Device Profile

Use `adb -s <serial>` for every adb command. Use `ANDROID_SERIAL=<serial>` or the project's equivalent for Gradle instrumentation commands. If no serial is known and more than one device is connected, stop and ask the user to choose.

Record:

- serial
- manufacturer, model, Android version, API level
- screen size and density
- network state when available
- package name and build variant
- whether app data was cleared

If the app package name, build variant, or clear-data status cannot be inferred safely, record `null` or `false` explicitly instead of inventing values.

## 3. Code And Requirements Analysis

Analyze only the requested code/requirements scope unless startup decisions request a full refresh. Inspect requirements, navigation, UI code, ViewModels/presenters, repository calls, manifests, and existing tests. Derive real operation paths from evidence, not desired behavior alone.

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

After producing or changing `path-map.md`, ask the user to confirm the paths and priorities. If reusing an existing path map, confirm only the selected execution scope. Proceed with the confirmed scope first.

## 4. Testability Audit

Audit whether each selected step can be located and verified without fragile text-only matching. Prefer:

1. Compose `Modifier.testTag(...)`
2. XML/View `android:id`
3. stable resource names
4. semantic `contentDescription` only when appropriate for accessibility
5. fallback text match only for stable, user-visible text

Audit logs for path verification and failure triage. Add or extend logs through the project's existing logging mechanism. Avoid noisy logs. Before editing, list the exact files and change types that will be touched. Reconfirm broad production-code, Gradle/config, logging, or behavior changes even when low-risk testability changes were allowed at startup.

## 5. Test Plan

Create `test-plan.md` and `test-plan.json` with:

- confirmed scope first
- selected test framework
- generated or modified test files
- setup/teardown strategy
- clear-app-data decision
- commands to run
- expected logs and assertions
- excluded high-risk paths
- known blockers

## 6. Run And Repair Loop

For each path, test class, or command in the confirmed scope:

1. Run the smallest relevant test command.
2. Collect evidence: command output, instrumentation output, logcat, stack traces, screenshots on failure, and screenrecord when useful.
3. Classify the failure using the fixed classes from `SKILL.md`.
4. Fix one root cause only.
5. Record the fix in `fix-report.md` and `artifacts/android-test/fixes.json`.
6. Rerun the affected test.
7. Stop after `max_fix_attempts` for that path.

Do not broaden a fix beyond the confirmed scope unless the same root cause clearly affects shared test infrastructure and the user approves the broader fix.

## 7. Final Report

Produce:

- `docs/android-test/final-report.md`: concise human report with scope, device, stack, coverage, results, fixes, unresolved issues, and next steps.
- JSON artifacts for follow-up automation: `run-log.json`, `failures.json`, `fixes.json`, `coverage.json`.

Redact secrets and personal data before final delivery.
