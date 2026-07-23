# Continuous Running

How to run the skill unattended, repeatedly, and across all business — the layer
that turns the single-run engine into a regression system. Read together with
`workflow.md` §1.2 and §6.

## Preconditions

- `non_interactive: true` and `batch_mode: true` in `inputs.json`.
- A physical device (or a stable device-farm slot) reachable via `adb_serial`.
- `per_path_isolation` set to `clear_data` or `setup_contract`, not `none`.
- Coverage model built once (`coverage_modeling: true` on the first/full run) so
  `dependency-map.json` exists for incremental selection.

## Two Lanes

- **Nightly / full** — run every path in the map (or all confirmed P0). Trigger:
  scheduled (cron). Set `test_scope.scope_type=all_confirmed_p0`,
  `batch_mode=true`. Appends one `trend.json` entry. This is the "cover all
  business" run.
- **Incremental / per-commit** — run only paths affected by the diff. Trigger:
  CI on a pull request. Use `scripts/incremental_select.py` to compute the
  subset from `dependency-map.json` + `git diff`, write the affected `path_ids`
  into `inputs.test_scope`, then run with `batch_mode=true`.

Both lanes share one engine and one run-state machine; only the scope differs.

## Resume And Durability

- `run-state.json` is the resume point. If a run dies mid-batch, restart with the
  same file; `run_state.py next-pending` skips everything already terminal.
- Never abort the batch on one path. Mark `failed`/`blocked` and continue.
- After a full pass with failures, optionally `run_state.py reset` and rerun just
  the failed/blocked/flaky set.

## Device Reliability

- `scripts/device_health_check.sh` runs before every path. On non-zero, retry the
  path within `inputs.env_retry` (reconnect + backoff) before blocking.
- For device rotation, record `device-profile.json` per run; a device swap keeps
  the same batch as long as `run-state.json` is unchanged.
- Quarantine a device (not a path) if its `ENVIRONMENT_ERROR` rate is high.

## Flakiness

- On a path that fails then passes on retry, `flake_tracker.py record` it and mark
  the path `flaky` in run-state.
- Before each batch, `flake_tracker.py recompute`. Paths above the threshold move
  to the monitor lane: they keep running but a flaky failure no longer blocks.
- The nightly lane still surfaces monitor-lane failures for visibility.

## Trend And Reporting

- After each batch, `build_trend.py` appends a `trend.json` entry; the
  report-writer renders `docs/android-test/trend-report.md` (pass/fail/flake over
  time, feature-coverage heatmap, flake leaderboard).
- `final-report.md` describes the latest batch only; `trend-report.md` spans
  history.

## Scheduling Examples

CI incremental on a pull request:

```bash
git diff --name-only origin/master \
  | scripts/incremental_select.py artifacts/android-test/dependency-map.json --from-stdin \
  > affected.txt
# write affected.txt into inputs.json test_scope.path_ids, then run the skill
# with non_interactive=true, batch_mode=true.
```

Cron nightly full: same skill call with `test_scope.scope_type=all_confirmed_p0`.

The skill is the engine; CI/cron is the driver. Keep scheduling external and
stateless — do not embed it inside the skill.
