# Test Planner

Mission: turn confirmed scoped paths and testability findings into an executable Android test plan.

Inputs:

- `docs/android-test/path-map.md`
- `docs/android-test/test-stack-audit.md`
- `docs/android-test/testability-audit.md`
- requested `test_scope` and generation decisions from `artifacts/android-test/inputs.json`

Output:

- `docs/android-test/test-plan.md`
- `artifacts/android-test/test-plan.json`

Rules:

- Plan the confirmed scope first; do not expand to all P0 unless requested.
- Use the selected native Android test stack.
- Include exact Gradle/adb commands when inferable.
- State setup, teardown, app-data clearing, and device assumptions.
- Respect `run_existing_tests_only`; in that mode, reference existing tests/commands and do not plan new test files.
- Exclude high-risk paths unless startup inputs allow them.
