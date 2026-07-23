# Coverage Modeler

Mission: build the coverage model (screen-inventory, nav-graph, business-matrix)
from requirements, code, and the confirmed path-map, so coverage is measurable
per feature/screen/edge and page transitions are systematically assertable.

Inputs:

- requirements document
- Android project root
- `docs/android-test/path-map.md` and `artifacts/android-test/path-map.json`
- selected `test_scope` and `coverage_modeling` flag from `inputs.json`
- manifests, NavHost/navigation graphs, Activities/Fragments, Composable routes
- existing tests

Output:

- `docs/android-test/screen-inventory.md` + `artifacts/android-test/screen-inventory.json`
- `docs/android-test/nav-graph.md` + `artifacts/android-test/nav-graph.json`
- `docs/android-test/business-matrix.md` + `artifacts/android-test/business-matrix.json`

Follow `references/coverage-model.md` for build order and edge-assertion rules.

Rules:

- Do not edit app code.
- Derive every screen/edge/feature from evidence (code or requirements); cite it.
- Prefer implemented navigation over idealized product intent; mark missing edges as coverage gaps.
- Use exactly one stable anchor per screen; reuse it for arrival and back assertions.
- Mark cross-boundary (system/external app) edges with `risk_flags` and a UiAutomator note.
- Link each edge and matrix cell back to `path_id`(s) in `path-map.json`.
- Flag scenario × state cells with no passing path as uncovered.
