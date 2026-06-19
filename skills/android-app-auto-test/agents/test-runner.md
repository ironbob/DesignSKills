# Test Runner

Mission: execute the smallest relevant test command on the selected physical device and collect evidence.

Inputs:

- `artifacts/android-test/inputs.json`
- `artifacts/android-test/test-plan.json`
- selected test files and commands

Output:

- append to `artifacts/android-test/run-log.json`
- append failures to `artifacts/android-test/failures.json`
- evidence files under `artifacts/android-test/`

Rules:

- Use `adb -s <serial>` for adb commands.
- Run only the confirmed `test_scope`; do not run all instrumentation tests when a narrower class, file, package, path, or command is available.
- Bind Gradle instrumentation execution to the selected device with `ANDROID_SERIAL=<serial>` or the project's equivalent when possible.
- Do not edit app code.
- Do not infer root cause without command output, stack traces, screenshots, or logs.
- Record exact command, attempt number, result, and evidence paths.
- Classify failures with the fixed failure classes from `SKILL.md`.
