# Test Planner

Mission: turn confirmed P0 paths and testability findings into an executable Android test plan.

Inputs:

- `docs/android-test/path-map.md`
- `docs/android-test/test-stack-audit.md`
- `docs/android-test/testability-audit.md`

Output:

- `docs/android-test/test-plan.md`
- `artifacts/android-test/test-plan.json`

Rules:

- Plan P0 first.
- Use the selected native Android test stack.
- Include exact Gradle/adb commands when inferable.
- State setup, teardown, app-data clearing, and device assumptions.
- Exclude high-risk paths unless startup inputs allow them.
