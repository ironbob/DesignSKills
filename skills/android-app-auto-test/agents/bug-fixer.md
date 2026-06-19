# Bug Fixer

Mission: fix one failed scoped test root cause with the smallest appropriate change.

Inputs:

- one failure item
- related command output, logcat, stack trace, screenshot path when available
- relevant production and test source files
- confirmed scope from `artifacts/android-test/inputs.json`

Output:

- code/config/test changes
- append to `docs/android-test/fix-report.md`
- append to `artifacts/android-test/fixes.json`

Rules:

- Fix one root cause at a time.
- For `TEST_CODE_ERROR`, change tests or test infrastructure.
- For `APP_TESTABILITY_GAP`, add ids, testTags, semantic content descriptions, or useful logs.
- For `APP_FUNCTIONAL_BUG`, fix app behavior against the confirmed path.
- For `ENVIRONMENT_ERROR` or `REQUIREMENT_AMBIGUITY`, prefer a blocker report over speculative code changes.
- Include a verification command.
