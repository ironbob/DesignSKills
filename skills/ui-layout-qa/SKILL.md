---
name: ui-layout-qa
description: "Audit and repair user-visible UI layout from source code and/or screenshots. Use when creating, modifying, reviewing, or debugging Web, desktop, or mobile UI and the request involves layout quality, long-text wrapping or overflow, alignment, spacing, sizing, responsive behavior, content density, or empty/loading/error states. Supports incremental repair for the affected change and full audits with grouped approval. Do not use for visual-style selection, branding, color/font restyling, or a dedicated accessibility audit."
---

# UI Layout QA

Keep user-visible UI usable and structurally coherent without turning a focused UI task into a style redesign or an uncontrolled refactor.

## Priority order

Apply this strict order whenever goals conflict:

1. Functional accuracy and usability
2. Context efficiency
3. Speed
4. Token efficiency

Start with the smallest relevant scope. Expand code, rendered states, or validation only when needed to make a reliable conclusion. Never save context, time, or tokens by guessing, skipping a necessary regression check, or declaring an unverified result passed.

## Select the mode and evidence boundary

| Situation | Mode / action |
| --- | --- |
| User asks to create or change a screen, component, or UI behavior | **Incremental** by default |
| User asks to audit an existing app, a page set, or all UI | **Full audit** |
| User explicitly names either mode | Honor it |
| Only screenshots are available | **Screenshot observation**; do not modify code or propose code changes |

- **Incremental:** Analyze the target and directly coupled layout regions. Repair confirmed issues in that scope, then verify them. Briefly note unrelated existing issues without changing them.
- **Full audit:** Analyze the requested range, group findings by affected region or severity, and stop for user approval before changing each group. After approval, repair and verify only approved groups.
- **Screenshot observation:** Report only directly observable findings. Do not infer implementation causes, generate sample fixes, or claim a problem is resolved.

When code and screenshots both exist, treat code as the intended behavior and screenshots as evidence of actual rendering. If they conflict, report the discrepancy; do not silently reinterpret the intended behavior to match the screenshot. If code is ambiguous, state that the intended behavior cannot be determined rather than treating the screenshot as the specification.

## Workflow

### 1. Establish the target

1. Identify platform, requested mode, target UI region, supplied evidence, and relevant states.
2. For code, start at the entry view/component and only the layout parents, children, styles, data states, and tests that can affect the target. Do not scan the entire repository by default.
3. For screenshots, inspect the actual image when tooling permits. Record only visible facts; missing states, cropped content, or illegible text are unknown rather than defects.
4. Load `references/evidence-and-scope.md` when code and screenshots conflict, the change may cross component boundaries, or a conclusion lacks evidence.

### 1.5 Scan-map confirmation gate

Before diagnosing findings, proposing code changes, or editing code, load
`references/scan-map-gate.md` and create a text-drawn structural map for every scan target.
For full audits, a target is every nonblocked page in the discovered inventory; blocked pages must
still appear in the overview with their blocker. For incremental work, it is the target and each
directly coupled region; for screenshot observation, it is each supplied screen.

Write the map artifacts and `scan-map-manifest.json` into the work artifact directory, then run:

```bash
python3 <skill-dir>/scripts/validate_scan_map.py <scan-map-manifest.json> \
  --phase draft --artifact-root <artifact-root>
```

Present the overview and the text maps to the user, explicitly marking unknowns rather than
inventing structure. Stop and wait for explicit confirmation. After the user confirms, record the
actual confirmation message as evidence for every approved target and run:

```bash
python3 <skill-dir>/scripts/validate_scan_map.py <scan-map-manifest.json> \
  --phase confirmed --artifact-root <artifact-root>
```

Do not continue to layout diagnosis, repairs, full-audit grouping, or screenshot findings until the
confirmed phase succeeds. If the user corrects a map, revise only that target, reset its
confirmation to `pending`, and repeat the gate for it. A confirmation applies to the recorded map
revision only.

For a **full audit**, begin with page discovery before inspecting findings. Load
`references/full-audit-coverage.md`, build the required page inventory, and validate it with:

```bash
python3 <skill-dir>/scripts/validate_audit_coverage.py <page-inventory.json>
```

Do not call a full audit complete until the inventory has no pending or blocked required checks:

```bash
python3 <skill-dir>/scripts/validate_audit_coverage.py <page-inventory.json> \
  --require-coverage-complete
```

The inventory is the source of truth for page coverage. The scan-map gate follows inventory
discovery and must contain one map per discovered page before detailed audit work starts. When
screenshots are the only input, ask for a page list or additional screenshots; record absent pages
as blocked rather than assuming they do not exist.

### 2. Inspect the relevant quality dimensions

Check only dimensions that apply to the target. Always consider the target's normal state; add long text, narrow viewport/window, and relevant empty/loading/error states before calling a code repair complete.

Load the matching section of `references/check-catalog.md`:

- text wrap, truncation, clipping, overflow, or action displacement;
- alignment, spacing, sizing, or parent/child geometry;
- responsive, window-resize, small-screen, or safe-area behavior;
- information hierarchy or content-density concerns;
- empty, loading, or error-state layout.

Trace visible symptoms to the highest responsible layout constraint before applying local offsets. Treat a preference as a finding only when it has a concrete usability or comprehension impact.

### 3. Repair within authorization

For **incremental** work:

1. Fix the target and directly coupled regions with the smallest change that preserves existing behavior and necessary information.
2. Do not refactor unrelated code, restyle the product, remove content merely to make it fit, or alter business relationships.
3. If the root cause requires modifying a region outside the direct scope, explain the required expansion and its impact before modifying that additional region.

For a **full audit**:

1. Use two passes: first discover pages, shared shells, shared components, and required states; then inspect each page's unique region. Reuse one documented shared-structure conclusion instead of repeatedly analyzing the same shell on every page.
2. Prioritize critical task pages, text-dense pages, narrow-layout risks, and recently changed pages, but retain every discovered page in the inventory.
3. Produce compact groups containing region/severity, concrete impact, evidence, proposed repair boundary, and affected inventory pages.
4. Wait for the user to approve one or more groups. Do not edit an unapproved group.
5. Repair approved groups separately. Re-verify every inventory page affected by a shared change; if a new issue or scope expansion appears, add it as a new or updated approval item.

### 4. Verify and report honestly

1. Run the narrowest existing app preview, test, screenshot check, or other verification that can validate the repair. Prefer actual rendering for high-risk layout changes when available.
2. Verify the repaired target, directly coupled area, long text or equivalent boundary content, narrow viewport/window, and relevant exception state. Mark an unavailable state as `not applicable` only with a reason; otherwise mark it `unverified`.
3. Do not confuse "code changed" with "layout verified." If execution or rendering is unavailable, state the limitation and downgrade the conclusion.
4. Use the appropriate compact output from `references/report-contract.md`. Include repaired findings, verification status, and remaining or unrelated issues; do not dump raw scans or long logs.

For a full audit, reuse a single running app/test session and standard viewport/window presets where possible. Parallelize independent read-only discovery or classification only when tooling permits; keep edits and their regressions serial. Speed must come from eliminating duplicate discovery and duplicate shared-component analysis, never from skipping inventory pages or required checks.

## Required guardrails

- Preserve functionality, navigation, data relationships, and required information while repairing layout.
- Prefer parent constraints and shared layout rules over scattered one-off offsets.
- Do not use screenshot-only evidence to invent code causes or fixes.
- Do not modify unrelated historical problems during incremental work; log them in one short section.
- Do not modify any full-audit group before the user approves that group.
- Do not claim full-audit coverage when the page inventory has pending or blocked required checks.
- Do not diagnose, repair, or claim that a target was scanned until its text scan map has passed the user-confirmed gate.
- Do not claim complete verification when only static evidence exists.
- Keep visual-style decisions out of scope. Route style selection or restyling to `ui-design-app` when needed.
- Keep complete accessibility audits out of scope. Mention a layout-adjacent risk only when it directly prevents use of the inspected UI.

## Self-check before handoff

1. Confirm the selected mode and that every edit is inside its authorization boundary.
2. Confirm findings are tied to visible evidence or relevant code, not taste.
3. Confirm long text, narrow layout, and relevant abnormal states have a `verified`, `unverified`, or reasoned `not applicable` result.
4. Confirm no existing behavior or necessary content was removed merely to improve alignment.
5. Confirm the report separates fixed, unverified, pending approval, and unrelated issues.
6. For a full audit, confirm the inventory lists every discovered page and every required check is terminal. Run the coverage validator with `--require-coverage-complete` before claiming coverage complete.
7. Confirm every scan target has a matching text map, source anchors, explicit unknowns, and user-confirmation evidence for its current revision. Re-run `validate_scan_map.py --phase confirmed`.

## Resource routing

- `references/evidence-and-scope.md`: evidence classification, code/screenshot conflicts, scope expansion, and severity. Read for ambiguous evidence or authorization decisions.
- `references/check-catalog.md`: selected Web, desktop, mobile, text, geometry, density, and state checks. Read only the relevant sections.
- `references/report-contract.md`: compact reporting contracts for screenshot observation, incremental work, and full audits. Read before reporting findings or requesting full-audit approval.
- `references/full-audit-coverage.md`: page discovery, inventory contract, coverage gate, shared-structure reuse, and speed rules. Read at the start of every full audit.
- `references/scan-map-gate.md`: text-drawn scan-map format, artifact contract, and user-confirmation gate. Read before every diagnosis or repair.
- `scripts/validate_audit_coverage.py`: deterministic validation of the full-audit inventory; use `--require-coverage-complete` before claiming page coverage and `--require-verified` only when every required check has direct verification.
- `scripts/validate_scan_map.py`: validates one-to-one text maps, evidence anchors, and draft/confirmed user-confirmation gates. Run before and after presenting scan maps.
