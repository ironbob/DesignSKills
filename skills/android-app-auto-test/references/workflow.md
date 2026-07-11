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
- `non_interactive`, default `false`; when true, `inputs.json` pre-authorizes Gates 0–2 and the run must not prompt
- `batch_mode`, default `false`; when true, drive the confirmed scope through `run-state.json`
- `coverage_modeling`, default `false`; when true, also build screen-inventory/nav-graph/business-matrix/dependency-map
- `regression_on_fix`, default `true` in batch mode
- `per_path_isolation`: `clear_data` | `setup_contract` | `none`
- `env_retry`: `{max_retries, backoff_seconds}` for `ENVIRONMENT_ERROR`
- `flake_policy`: `{retries, quarantine_threshold, sample_min}`

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

## 1.2 Non-Interactive And Batch Mode

- Non-interactive: when `non_interactive` is true, treat the startup decisions in `inputs.json` as final for Gates 0–2 and do not prompt. If a required decision is missing or a high-risk action is needed without an explicit allow, stop and emit a blocker instead of asking.
- Batch: when `batch_mode` is true, the confirmed scope runs one path at a time through `artifacts/android-test/run-state.json` (see §6). Initialize run-state after the test plan is confirmed; on any restart the loop resumes from run-state, never re-running paths already terminal.
- Per-path isolation: when `per_path_isolation` is `clear_data`, clear app data and re-seed before each path; when `setup_contract`, run the path's setup steps (login as a known test user, seed backend data) from the test plan; when `none`, only acceptable if paths are proven independent.

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

### 6.1 Batch Dispatch

In batch mode, drive the loop from `artifacts/android-test/run-state.json`:

1. `scripts/run_state.py init run-state.json --from-path-map path-map.json --from-inputs inputs.json` after the test plan is confirmed.
2. Repeat until `run_state.py next-pending` prints empty:
   1. The claimed `path_id` is now `running`.
   2. Run `scripts/device_health_check.sh <serial> <package>`; on non-zero, treat as `ENVIRONMENT_ERROR` and retry within `inputs.env_retry` (§6.3) before giving up on the path.
   3. Apply per-path isolation (§1.2) so paths do not contaminate each other.
   4. Run the smallest relevant test command for the path (or its class/package/command).
   5. Collect evidence: command output, instrumentation output, logcat via `scripts/collect_logcat.sh`, stack traces, screenshots on failure, and screenrecord when useful.
   6. Mark the path: `run_state.py mark run-state.json <path_id> <passed|failed|blocked>`.

If `batch_mode` is false, run the confirmed scope linearly without run-state.

### 6.2 Failure Classification And Repair

1. Classify each failure using the fixed classes from `SKILL.md`.
2. Fix one root cause only; record it in `fix-report.md` and `artifacts/android-test/fixes.json`.
3. Rerun the affected test. For `APP_FUNCTIONAL_BUG` fixes that touch app source, also rerun the regression subset from `dependency-map.json` (Phase 2); record it in `regression-runs.json`.
4. Stop after `max_fix_attempts` for that path; in batch mode mark it and continue.

Do not broaden a fix beyond the confirmed scope unless the same root cause clearly affects shared test infrastructure and the user approves the broader fix.

### 6.3 Environment Retry

`ENVIRONMENT_ERROR` is retryable: on a failed `device_health_check.sh` or a device drop, reconnect and retry the path up to `inputs.env_retry.max_retries` times with `backoff_seconds` between attempts. Only after the budget is exhausted record it as a blocker. Never mark a path blocked for a transient device condition that a retry would clear.

## 7. Final Report

Produce:

- `docs/android-test/final-report.md`: concise human report with scope, device, stack, coverage (incl. per-feature/screen/edge when the coverage model is on), results, fixes, unresolved issues, and next steps.
- `docs/android-test/regression-report.md` when regression reruns happened.
- `docs/android-test/flake-report.md` when any path was flaky (from `flake-tracker.json`).
- `docs/android-test/trend-report.md` for continuous runs (from `trend.json`).
- JSON artifacts for follow-up automation: `run-log.json`, `failures.json`, `fixes.json`, `regression-runs.json`, `flake-tracker.json`, `coverage.json`, `trend.json`.

For continuous runs, append one `trend.json` entry with `scripts/build_trend.py`
after the batch finishes. Redact secrets and personal data before final delivery.

## 8. Continuous And Incremental Mode

See `references/continuous-running.md` for the full pattern. In short:

- Nightly/full: `test_scope.scope_type=all_confirmed_p0`, `batch_mode=true`.
- Incremental/per-commit: `scripts/incremental_select.py dependency-map.json --base origin/master` → write affected `path_ids` into `inputs.test_scope` → `batch_mode=true`.
- Both lanes share one engine and one run-state machine; the skill is the engine, CI/cron is the driver.
- Flaky paths are recorded via `scripts/flake_tracker.py` and quarantined above threshold; the batch never blocks on a human in non-interactive mode.
