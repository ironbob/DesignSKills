# Coverage Model

When `coverage_modeling` is enabled, turn the flat path list into a measurable
coverage model so "page transitions correct" and "all business covered" become
answerable instead of merely asserted. Read together with `artifact-schema.md`
(Phase 2 artifacts) and `references/android-testability-rules.md`.

## Build Order

1. `screen-inventory.json` — enumerate every locatable screen.
2. `nav-graph.json` — assert each transition edge.
3. `business-matrix.json` — map feature × scenario × state to paths.
4. `dependency-map.json` — map path ↔ production source, for regression + incremental selection.

## 1. Screen Inventory

A screen is the smallest unit the user perceives as a "page": an Activity, a
Fragment, or a Composable navigation route. For each screen record:

- stable `screen_id` — lowercase, domain-meaningful: `login`, `home`, `order_detail`
- `type` and `route_or_class` — from the manifest, NavHost, or Composable graph
- `anchor` — the testTag or id that proves the screen is shown. This is the page-transition assertion target.
- `evidence` — the file that defines the screen

Use exactly one anchor per screen and prefer a screen-level testTag
(`login.screen`) so the same locator asserts both arrival and back navigation.

## 2. Navigation Graph

An edge is the unit of "page transition correctness". For each implemented
transition record `from`, `to`, `trigger`, `expected_dest_anchor`, `back_dest`,
`args`, `path_id`, `automation_readiness`, and `risk_flags`.

What "transition correct" means — assert all that apply:

1. **Destination reached**: `expected_dest_anchor` is visible.
2. **Back stack correct**: pressing back lands on `back_dest`, not an unrelated screen.
3. **Arguments intact**: `args` render correctly on the destination.
4. **No duplicates**: repeated triggers do not stack duplicate screens (`singleTop`/`popUpTo` honored).
5. **State survives**: rotation or process-death restore keeps the user on the same screen with state preserved.

Edges the path-map already exercises are verified through their path. Edges with
no path are coverage gaps: either give them a path or mark them `manual_only`.
Cross-boundary edges (system permission, external app, settings) use UiAutomator
steps (see `test-stack-selection.md`) and are flagged in `risk_flags`.

## 3. Business Matrix

Group paths by feature so coverage reports per business module, not just per
path. A feature is covered when every scenario in every relevant state has at
least one `passed` path.

- `feature_id` + `name`: a business module a product owner recognizes (auth, home, search, order, payment)
- `scenarios`: each meaningful user goal in the feature
- `states`: preconditions that change behavior (`logged_out`/`logged_in`, `empty`/`has_data`, `online`/`offline`)
- `path_ids`: paths covering this scenario × state
- `covered`: recomputed from the latest run-state/coverage

Any scenario × state with no passing path is an "all business" backlog item.

## 4. Dependency Map

Bidirectional path ↔ source mapping, used by regression-safe repair and
incremental selection. Build from:

- testability-audit evidence (files whose ids/testTags/logs a path relies on)
- static reachability from the screen / ViewModel / Repository the path touches
- existing tests' imports

Keep it conservative: over-mapping widens regression reruns (slow), under-mapping
hides regressions (unsafe). Prefer sources a path actually exercises.

## Coverage Dimensions

`coverage.json` rolls up three dimensions from this model:

- `by_feature` — from `business-matrix`
- `by_screen` — from `screen-inventory` (a screen is covered when an edge into it passed)
- `by_edge` — from `nav-graph` (`verified` true when the linked path passed)

These are the numbers that answer "did we cover all business and all transitions".
