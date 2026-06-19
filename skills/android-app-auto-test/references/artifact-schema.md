# Artifact Schema

Keep JSON artifacts deterministic and append-friendly. Prefer arrays of objects with stable ids.

## Directory Layout

```text
docs/android-test/
  path-map.md
  test-stack-audit.md
  testability-audit.md
  test-plan.md
  fix-report.md
  final-report.md

artifacts/android-test/
  inputs.json
  device-profile.json
  test-stack-audit.json
  path-map.json
  test-plan.json
  run-log.json
  failures.json
  fixes.json
  coverage.json
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
  "target_environment": "test"
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

```json
{
  "summary": {
    "p0_total": 3,
    "p0_passed": 2,
    "p0_blocked": 1
  },
  "paths": [
    {
      "path_id": "P0-login-success",
      "priority": "P0",
      "coverage_status": "covered|failed|blocked|not_run"
    }
  ]
}
```
