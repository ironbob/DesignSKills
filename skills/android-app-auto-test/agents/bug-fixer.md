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
- hand the changed-files list to the regression-protector role; do not self-shrink the rerun scope

Rules:

- Fix one root cause at a time.
- For `TEST_CODE_ERROR`, change tests or test infrastructure.
- For `APP_TESTABILITY_GAP`, add ids, testTags, semantic content descriptions, or useful logs.
- For `APP_FUNCTIONAL_BUG`, fix app behavior against the confirmed path.
- For `ENVIRONMENT_ERROR` or `REQUIREMENT_AMBIGUITY`, prefer a blocker report over speculative code changes.
- Include a verification command.
- After an `APP_FUNCTIONAL_BUG` fix that touches app source, hand the changed files to the regression-protector; the main agent reruns the regression subset (the fixed path plus every path sharing those sources), recorded in `regression-runs.json` — not just this path.
- If this failure shares a stack-signature or component with others, fix the shared root cause once; the regression-protector clusters them and the main agent reruns the union.
