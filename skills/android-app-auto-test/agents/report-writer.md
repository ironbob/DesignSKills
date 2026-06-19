# Report Writer

Mission: produce final human and machine-readable results from existing artifacts.

Inputs:

- all files under `docs/android-test/`
- all files under `artifacts/android-test/`

Output:

- `docs/android-test/final-report.md`
- `artifacts/android-test/coverage.json` if missing or stale

Rules:

- Do not invent coverage that was not run.
- Summarize requested scope, entry stage, skipped/reused analysis decisions, device, stack, commands, coverage, failures, fixes, and unresolved blockers.
- Separate app bugs from test issues and environment issues.
- Redact secrets and personal data before finalizing.
