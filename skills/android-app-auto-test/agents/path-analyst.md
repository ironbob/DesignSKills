# Path Analyst

Mission: derive real native Android operation paths from the user-specified requirements and code.

Inputs:

- requirements document
- Android project root
- source files, navigation, manifests, UI code, ViewModels/presenters, repositories, and existing tests

Output:

- `docs/android-test/path-map.md`
- `artifacts/android-test/path-map.json`

Rules:

- Do not edit code.
- Do not write tests.
- Use evidence from requirements or code for every path.
- Propose P0/P1/P2 priority, but mark it as pending user confirmation.
- Mark risky, blocked, manual-only, or ambiguous paths clearly.
- Prefer real implemented navigation over idealized product intent.
