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
  "adb_serial": "DEVICE_SERIAL",
  "may_clear_app_data": false,
  "may_modify_testability": true,
  "max_fix_attempts": 3,
  "allowed_high_risk_paths": false,
  "target_environment": "test"
}
```

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
  "commands": ["./gradlew :app:connectedDebugAndroidTest"],
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
      "command": "./gradlew :app:connectedDebugAndroidTest",
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
      "verification_command": "./gradlew :app:connectedDebugAndroidTest",
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
