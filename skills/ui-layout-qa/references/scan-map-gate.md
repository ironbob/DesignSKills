# Scan-Map Confirmation Gate

Use this gate before every UI-layout diagnosis or repair. It turns the agent's first-pass scan into
a reviewable artifact rather than an unsupported claim that pages were inspected.

## 1. Targets and artifact layout

Write artifacts outside the target product. Use a directory such as
`ui-layout-qa/YYYY-MM-DD-<topic>/` unless the user specifies another location:

```text
<artifact-root>/
├── scan-map-overview.txt
├── scan-map-manifest.json
└── scan-map/
    ├── <target-id>.txt
    └── ...
```

- **Incremental:** map the requested region and each directly coupled region that must be scanned.
- **Full audit:** map every page in `page-inventory.json`; include blocked pages in the overview
  with their blocker, but do not fabricate a page diagram that cannot be sourced.
- **Screenshot observation:** map every supplied screen from visible evidence only.

Each target has exactly one current map file and one manifest entry. Do not merge independently
confirmable screens into prose or hide pages in a generic app-shell sketch.

## 2. Text-map format

Each map is a compact monospace drawing of regions, hierarchy, visible content groups, actions,
and relevant state boundaries. It is not a visual-style mockup. Use only facts supported by source
or screenshot evidence; mark unknown or conditional structure as `[unknown: reason]`.

```text
Target: projects
Source: src/routes.ts:/projects; src/features/projects/ProjectsPage.tsx
Unknown: empty-state action label is not reachable in current evidence

+--------------------------------------------------------------+
| App shell                                                    |
|  Sidebar        | Projects                                   |
|  - All          | [Page title]                 [New project] |
|  - Favorites    | ------------------------------------------ |
|                 | [Filter row]                              |
|                 | [Project list / empty state]              |
+--------------------------------------------------------------+
```

Rules:

- Show the parent/child regions that may affect layout; do not list CSS properties or dump code.
- Include visible long-text-bearing areas and primary actions when known.
- Use a separate map for a visually or structurally independent state when it changes the layout.
- Keep a normal map short; put detailed source anchors in the manifest instead of inflating the
  drawing.
- For screenshot-derived maps, use screenshot labels in `Source:` and never fill hidden regions
  from assumptions.

## 3. Manifest contract

```json
{
  "mode": "full_audit",
  "scan_scope": "Customer app",
  "overview_file": "scan-map-overview.txt",
  "targets": [
    {
      "id": "projects",
      "label": "Projects",
      "map_file": "scan-map/projects.txt",
      "source_anchors": [
        "src/routes.ts:/projects",
        "src/features/projects/ProjectsPage.tsx"
      ],
      "evidence_types": ["code", "screenshot"],
      "unknowns": ["empty-state action label is not reachable"],
      "revision": 1,
      "confirmation": {"status": "pending"}
    }
  ]
}
```

Allowed modes are `incremental`, `full_audit`, and `screenshot_observation`. `overview_file` must
be a safe relative path to a non-empty text file under the artifact root. A target requires an
`id`, `label`, relative `map_file`, non-empty `source_anchors`, at least one `evidence_type`, a
positive `revision`, and `confirmation`.

Allowed confirmation statuses are:

| Status | Meaning |
| --- | --- |
| `pending` | Draft map awaits user review |
| `user_confirmed` | User explicitly approved this revision; include `confirmed_by: "user"` and message evidence |
| `needs_revision` | User corrected or rejected the map; revise, increment `revision`, then reset to pending |

## 4. Gate sequence

1. Discover the target set and generate all current maps plus the overview.
2. Run draft validation:

   ```bash
   python3 <skill-dir>/scripts/validate_scan_map.py <scan-map-manifest.json> \
     --phase draft --artifact-root <artifact-root>
   ```

3. Present the overview and every text map to the user. Keep the chat concise only when many maps
   exist: show the overview, give artifact paths for all maps, and explicitly ask the user to
   confirm or correct the named targets. Do not start diagnosis in the same turn.
4. On explicit confirmation, record the actual user message in every approved target's
   `confirmation.evidence`, set `status` to `user_confirmed`, and run confirmed validation.
5. Continue only after all current targets pass confirmed validation. In a full audit, partial
   confirmation blocks the audit; the user may instead request a newly scoped audit limited to the
   confirmed targets, but it cannot be called app-wide.
6. When a target changes or the user corrects it, increment `revision`, replace its map, reset its
   confirmation, and run the gate again. Never carry confirmation across revisions.

The user may approve several named targets or the complete overview in one explicit response. Do
not treat silence, a generic acknowledgement, or the agent's own confidence as confirmation.
