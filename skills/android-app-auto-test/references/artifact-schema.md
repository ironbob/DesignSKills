# Artifact Schema

Keep JSON artifacts deterministic and append-friendly. Prefer arrays of objects with stable ids.

## Directory Layout

```text
docs/android-test/
  path-map.md
  screen-inventory.md
  nav-graph.md
  business-matrix.md
  test-stack-audit.md
  testability-audit.md
  test-plan.md
  fix-report.md
  regression-report.md
  flake-report.md
  final-report.md
  trend-report.md

artifacts/android-test/
  inputs.json
  device-profile.json
  test-stack-audit.json
  path-map.json
  screen-inventory.json
  nav-graph.json
  business-matrix.json
  dependency-map.json
  test-plan.json
  run-state.json
  run-log.json
  failures.json
  fixes.json
  regression-runs.json
  flake-tracker.json
  coverage.json
  trend.json
```

## inputs.json

```json
{
  "requirements_path": "docs/prd.md",
  "project_root": ".",
  "android_module": "app",
  "entry_stage": "full",
  "test_scope": {
    "scope_type": "priorities|path_ids|feature|module|test_file|test_class|test_package|gradle_command|all_confirmed_p0",
    "priorities": ["P0"],
    "path_ids": [],
    "feature": null,
    "module": "app",
    "test_files": [],
    "test_classes": [],
    "test_package": null,
    "gradle_command": null
  },
  "reanalyze_code": true,
  "regenerate_path_map": true,
  "rerun_testability_audit": true,
  "generate_or_update_tests": true,
  "run_existing_tests_only": false,
  "adb_serial": "DEVICE_SERIAL",
  "may_clear_app_data": false,
  "may_modify_testability": true,
  "max_fix_attempts": 3,
  "allowed_high_risk_paths": false,
  "target_environment": "test",
  "non_interactive": false,
  "batch_mode": false,
  "coverage_modeling": false,
  "regression_on_fix": true,
  "per_path_isolation": "clear_data|setup_contract|none",
  "env_retry": { "max_retries": 2, "backoff_seconds": 30 },
  "flake_policy": { "retries": 1, "quarantine_threshold": 0.3, "sample_min": 5 }
}
```

Use `entry_stage: "execute"` with `run_existing_tests_only: true` when the user wants to directly run an existing test class/file/package or explicit Gradle command. In that mode, keep `reanalyze_code`, `regenerate_path_map`, `rerun_testability_audit`, and `generate_or_update_tests` false unless the user confirms otherwise.

## device-profile.json

```json
{
  "adb_serial": "DEVICE_SERIAL",
  "manufacturer": "Google",
  "model": "Pixel 8",
  "android_version": "15",
  "api_level": "35",
  "screen_size": "Physical size: 1080x2400",
  "screen_density": "Physical density: 420",
  "network_summary": "Active default network: ...",
  "package_name": null,
  "build_variant": null,
  "app_data_cleared": false
}
```

Use `null` for unknown package/build fields. Use `false` for `app_data_cleared` unless the run actually cleared data.

## test-stack-audit.json

```json
{
  "selected_stack": "compose-test|espresso|uiautomator|hybrid",
  "ui_architecture": "compose|xml-view|hybrid|unknown",
  "existing_test_dependencies": ["androidx.test.ext:junit", "androidx.compose.ui:ui-test-junit4"],
  "dependencies_to_add": [],
  "device_selection": {
    "adb_serial": "DEVICE_SERIAL",
    "gradle_device_binding": "ANDROID_SERIAL=DEVICE_SERIAL",
    "multi_device_risk": false
  },
  "commands": ["ANDROID_SERIAL=DEVICE_SERIAL ./gradlew :app:connectedDebugAndroidTest"],
  "evidence": ["app/build.gradle.kts", "app/src/androidTest/..."],
  "blockers": []
}
```

Set `multi_device_risk` to `true` and add an `ENVIRONMENT_ERROR` blocker when Gradle execution cannot be bound to the selected device.

## path-map.json

```json
{
  "paths": [
    {
      "path_id": "P0-login-success",
      "priority": "P0",
      "goal": "User signs in with valid credentials",
      "preconditions": ["Test environment account exists"],
      "steps": [
        {
          "step_id": "open-login",
          "action": "Open login screen",
          "locator_hint": "Login route or Activity",
          "expected": "Login form is visible"
        }
      ],
      "expected_logs": ["path_start", "result_success"],
      "automation_readiness": "ready",
      "risk_flags": [],
      "evidence": ["app/src/main/..."]
    }
  ]
}
```

## test-plan.json

```json
{
  "selected_stack": "compose-test|espresso|uiautomator|hybrid",
  "commands": ["ANDROID_SERIAL=DEVICE_SERIAL ./gradlew :app:connectedDebugAndroidTest"],
  "scope": {
    "scope_type": "path_ids",
    "path_ids": ["P0-login-success"]
  },
  "paths": [
    {
      "path_id": "P0-login-success",
      "test_file": "app/src/androidTest/...",
      "status": "planned",
      "assertions": ["Login success screen is visible"]
    }
  ]
}
```

## run-log.json

```json
{
  "runs": [
    {
      "run_id": "2026-06-19T12-00-00Z-P0-login-success-1",
      "path_id": "P0-login-success",
      "attempt": 1,
      "scope": {
        "scope_type": "path_ids",
        "path_ids": ["P0-login-success"]
      },
      "command": "ANDROID_SERIAL=DEVICE_SERIAL ./gradlew :app:connectedDebugAndroidTest",
      "device_serial": "DEVICE_SERIAL",
      "started_at": "ISO-8601",
      "finished_at": "ISO-8601",
      "result": "pass|fail|blocked",
      "evidence_files": ["artifacts/android-test/logcat-...txt"]
    }
  ]
}
```

## failures.json

```json
{
  "failures": [
    {
      "failure_id": "F-001",
      "path_id": "P0-login-success",
      "class": "TEST_CODE_ERROR",
      "symptom": "Test timed out waiting for Home screen",
      "evidence": ["stack trace excerpt", "logcat file path"],
      "root_cause": "Insufficient idle/wait handling",
      "status": "fixed|blocked|open"
    }
  ]
}
```

## fixes.json

```json
{
  "fixes": [
    {
      "fix_id": "FX-001",
      "failure_id": "F-001",
      "path_id": "P0-login-success",
      "summary": "Wait for navigation destination before assertion",
      "files_changed": ["app/src/androidTest/..."],
      "verification_command": "ANDROID_SERIAL=DEVICE_SERIAL ./gradlew :app:connectedDebugAndroidTest",
      "verification_result": "pass"
    }
  ]
}
```

## coverage.json

`summary` and `paths` remain as v1. The dimensions below are added when
`coverage_modeling` is enabled, so per-feature / per-screen / per-edge coverage
becomes answerable, not just per-path.

```json
{
  "summary": {
    "p0_total": 3,
    "p0_passed": 2,
    "p0_blocked": 1
  },
  "by_feature": [
    { "feature_id": "auth", "total": 5, "passed": 4, "failed": 0, "blocked": 1, "coverage_ratio": 0.8 }
  ],
  "by_screen": [
    { "screen_id": "login", "total": 3, "passed": 3, "coverage_ratio": 1.0 }
  ],
  "by_edge": [
    { "edge_id": "login->home.submit", "verified": true, "path_id": "P0-login-success" }
  ],
  "paths": [
    {
      "path_id": "P0-login-success",
      "priority": "P0",
      "coverage_status": "covered|failed|blocked|not_run"
    }
  ]
}
```

## Phase 1 Artifacts — Resumable Batch

### run-state.json

Single source of truth for a resumable batch. One path at a time transitions
`pending -> running -> {passed|failed|blocked|flaky|skipped}`. Because state is
on disk, any session resumes by reloading this file. Managed by
`scripts/run_state.py`.

```json
{
  "batch_id": "2026-07-11T10-00-00Z",
  "created_at": "ISO-8601",
  "scope": { "scope_type": "all_confirmed_p0", "path_ids": [] },
  "non_interactive": true,
  "max_fix_attempts": 3,
  "regression_on_fix": true,
  "flake_policy": { "retries": 1, "quarantine_threshold": 0.3, "sample_min": 5 },
  "paths": [
    {
      "path_id": "P0-login-success",
      "priority": "P0",
      "status": "pending",
      "attempts": 0,
      "fix_attempts": 0,
      "last_run_id": null,
      "last_failure_id": null,
      "updated_at": null,
      "blocked_reason": null
    }
  ],
  "progress": {
    "pending": 1, "running": 0, "passed": 0,
    "failed": 0, "blocked": 0, "flaky": 0, "skipped": 0
  }
}
```

## Phase 2 Artifacts — Coverage Model

### screen-inventory.json

Every locatable screen (Activity, Fragment, or Composable route) with its
stable anchor. Drives the per-screen coverage dimension and the navigation graph.

```json
{
  "screens": [
    {
      "screen_id": "login",
      "type": "activity|fragment|composable-route",
      "route_or_class": "com.example.LoginActivity",
      "anchor": { "locator_type": "testTag|id", "value": "login.screen" },
      "module": "app",
      "evidence": ["app/src/main/.../LoginActivity.kt"]
    }
  ]
}
```

### nav-graph.json

Nodes are `screen_id`s from `screen-inventory.json`; edges are the transitions to
assert. An edge is the unit of "page transition correctness": trigger the action,
assert the destination anchor, press back, assert `back_dest`. `manual_only` or
`risk_flags` mark edges the runner must skip or gate.

```json
{
  "edges": [
    {
      "edge_id": "login->home.submit",
      "from": "login",
      "to": "home",
      "trigger": { "action": "click submit", "locator_hint": "login.submit_button" },
      "expected_dest_anchor": "home.screen",
      "back_dest": "login",
      "args": [],
      "assertions": ["dest anchor visible", "back returns to back_dest"],
      "path_id": "P0-login-success",
      "risk_flags": [],
      "automation_readiness": "ready|needs_testability|manual_only|blocked"
    }
  ]
}
```

### business-matrix.json

Feature × scenario × state mapped to `path_id`s. This is what makes "cover all
business" measurable: a feature is covered when every scenario in every relevant
state has at least one `passed` path.

```json
{
  "features": [
    {
      "feature_id": "auth",
      "name": "登录注册",
      "module": "app",
      "scenarios": [
        {
          "scenario": "valid login",
          "states": ["logged_out"],
          "path_ids": ["P0-login-success"],
          "covered": true
        }
      ]
    }
  ]
}
```

### dependency-map.json

Bidirectional mapping between path and production source files, used for
regression-safe repair and incremental selection. Built by
`agents/regression-protector.md` from testability-audit evidence + imports.

```json
{
  "path_to_sources": {
    "P0-login-success": [
      "app/src/main/.../LoginActivity.kt",
      "app/src/main/.../LoginViewModel.kt"
    ]
  },
  "source_to_paths": {
    "app/src/main/.../LoginViewModel.kt": ["P0-login-success", "P1-logout"]
  }
}
```

### regression-runs.json

Append-only log of regression subsets triggered after app-code fixes, so the
safety net is auditable.

```json
{
  "runs": [
    {
      "fix_id": "FX-007",
      "triggered_by_path_id": "P0-login-success",
      "changed_files": ["app/src/main/.../LoginViewModel.kt"],
      "rerun_path_ids": ["P0-login-success", "P1-logout"],
      "result": { "P0-login-success": "passed", "P1-logout": "passed" },
      "regression_introduced": false
    }
  ]
}
```

## Phase 3 Artifacts — Continuous Running

### flake-tracker.json

Per-path flake history and derived lane assignment. Paths above
`quarantine_threshold` (default 0.3) with at least `sample_min` samples move to
the `monitor` lane: still run, but no longer block the batch.

```json
{
  "records": [
    {
      "path_id": "P1-search-filter",
      "run_id": "2026-07-11T10-00-00Z-P1-search-filter-1",
      "first_attempt_failed": true,
      "passed_on_retry": true,
      "recorded_at": "ISO-8601"
    }
  ],
  "rates": [
    {
      "path_id": "P1-search-filter",
      "sample_size": 10,
      "flake_count": 4,
      "flake_rate": 0.4,
      "lane": "blocking|monitor",
      "quarantined": true
    }
  ]
}
```

### trend.json

Append-only cross-batch history. Each finished batch adds one entry; the
report-writer renders `docs/android-test/trend-report.md` from it.

```json
{
  "history": [
    {
      "batch_id": "2026-07-11T10-00-00Z",
      "finished_at": "ISO-8601",
      "trigger": "nightly|incremental|manual",
      "total": 33,
      "passed": 30,
      "failed": 2,
      "blocked": 1,
      "flaky": 0,
      "duration_seconds": 1200,
      "feature_coverage": { "auth": 0.8, "home": 1.0 }
    }
  ]
}
```
