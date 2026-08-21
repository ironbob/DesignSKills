# Full-Audit Coverage and Speed Contract

Read this reference at the start of every full audit. Its purpose is to make page coverage
auditable while avoiding duplicate analysis of shared UI.

## 1. Define the auditable surface

A page is a reachable user-facing screen, route, desktop window, or top-level mobile screen.
Record dialogs, sheets, inspectors, and persistent panels under their owning page unless they are
independently reachable. Record dynamic or permission-gated pages even when they cannot be opened.

Discover pages from the smallest reliable combination of:

- route/deep-link declarations and screen/window registrations;
- navigation configuration and visible navigation destinations;
- top-level page/view entry points and feature modules;
- user-provided page lists, screenshots, test plans, or product maps.

Do not assume one discovery source is exhaustive. If discovery is incomplete, record the gap as a
blocked inventory entry or scope limitation; do not call the audit app-wide.

## 2. Scan-map confirmation gate

After building the initial inventory, generate one text-drawn structural map per inventory page
before detailed diagnosis. Follow `references/scan-map-gate.md`. The map gate proves that every
inventory page received a first-pass scan and lets the user correct the agent's page understanding
before any finding, grouping, or repair is produced.

Do not fill detailed page checks or generate repair groups until every unblocked inventory page has
a confirmed scan-map entry. A blocked inventory page must appear in the map overview with its
blocker; it remains a coverage blocker, not an invisible omission.

## 3. Inventory contract

Write `page-inventory.json` in the work artifact directory. Do not add it to the target product.

```json
{
  "audit_scope": "Customer app full UI audit",
  "pages": [
    {
      "id": "projects",
      "name": "Projects",
      "platform": "web",
      "entry_evidence": ["src/routes.ts: /projects"],
      "reachability": "reachable",
      "shared_structures": ["app-shell", "data-table"],
      "required_states": ["empty", "error"],
      "checks": [
        {"name": "default", "result": "verified", "evidence": ["running app: /projects"]},
        {"name": "long_text", "result": "verified", "evidence": ["fixture: 120-character title"]},
        {"name": "narrow", "result": "audited_unverified", "reason": "responsive preview is unavailable"},
        {"name": "state:empty", "result": "not_applicable", "reason": "this page never has an empty result"},
        {"name": "state:error", "result": "verified", "evidence": ["existing error-state test"]}
      ]
    }
  ]
}
```

Required page fields are `id`, `name`, `platform`, `entry_evidence`, `reachability`, and `checks`.
Use platform values `web`, `desktop`, or `mobile`; reachability values `reachable`, `conditional`,
or `blocked`.

For every page that is not blocked, include one check each for `default`, `long_text`, and
`narrow`; include `state:<name>` for every item in `required_states`. A check result is one of:

| Result | Meaning |
| --- | --- |
| `verified` | Direct evidence confirms the named check |
| `audited_unverified` | The page/check was analyzed but lacks direct verification |
| `not_applicable` | The named check does not apply; provide a reason |
| `blocked` | The named check cannot be performed; provide a reason |
| `pending` | Not yet audited; this blocks coverage completion |

## 4. Coverage gates

Run the validator whenever the inventory changes:

```bash
python3 <skill-dir>/scripts/validate_audit_coverage.py <page-inventory.json>
```

Use these claims precisely:

| Claim | Required condition |
| --- | --- |
| Inventory valid | Validator succeeds without completion flags |
| Coverage complete | `--require-coverage-complete` succeeds: every nonblocked page has required checks and none is pending or blocked |
| Fully verified | `--require-verified` succeeds: coverage is complete and every required check is `verified` or `not_applicable` |

A blocked page makes app-wide coverage incomplete. `audited_unverified` permits a coverage-complete
claim but must remain visible in the report and prevents a fully verified claim.

## 5. Fast, complete audit sequence

1. **Discover once.** Build and validate the inventory, then complete the scan-map confirmation
   gate before page-level diagnosis. Report the discovered count and blocked pages early.
2. **Cluster once.** Identify shared shells, navigation, reusable panels, and common components.
   Inspect each shared structure once and record its conclusion and affected page IDs.
3. **Triage by risk.** Inspect primary task pages, dense-text pages, narrow-layout risks, and
   recently changed pages first. This changes order, never coverage obligation.
4. **Inspect unique surfaces.** For each page, inspect only its unique region plus inherited risks
   from its shared structures. Fill its required checks in the inventory.
5. **Reuse the environment.** Keep one running app/test session and standardized platform sizes
   when possible; avoid restarting the same environment per page.
6. **Batch approvals.** Group issues by shared root cause or page region, then obtain grouped
   approval before repairs.
7. **Targeted regression.** A shared fix re-verifies all linked pages; a local fix re-verifies the
   target and directly coupled pages only.

Independent read-only discovery and classification may run in parallel when the available tooling
supports it. Keep code edits and verification of dependent fixes serial.

## 6. Completion report

Report at minimum: discovered pages, coverage-complete pages, pages containing
`audited_unverified` checks, blocked pages, shared structures reused, approved repair groups, and
the exact strongest truthful claim: inventory valid, coverage complete, or fully verified.
