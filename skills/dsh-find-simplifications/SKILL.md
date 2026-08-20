---
name: dsh-find-simplifications
description: 'Find and document evidence-backed simplifications in the deepseek-harness repository. Use for broad or targeted simplification audits, dead or duplicated surface removal, speculative or over-built behavior, unused public APIs and seams, hand-rolled infrastructure that may be replaced by a builtin or dependency, proposed Agent Notes, small inline TODO/FIXME/XXX notes, superseded Agent Note consolidation, or worthwhile simplification ideas from another PR.'
---

# Find DeepSeek Harness Simplifications

Find a few high-confidence ways to remove, fold, or demote existing harness surface area. Follow production consumers and recorded design intent; do not equate complexity, test coverage, or an unused-looking symbol with proof that removal is safe.

## Load Context Progressively

1. Read repository `AGENTS.md` and `.agents/notes/README.md`.
2. Read `docs/architecture.md` before judging code under `packages/`.
3. Search the Agent Note tree for the candidate's symbols, events, config keys, and concepts. Read only the matching notes; treat dual LLM adapters and dual persistence backends as intentional unless the user explicitly reopens that decision.
4. Load specialized guidance only when it applies:
   - Defensive code or async ownership: [references/trust-and-lifecycle.md](references/trust-and-lifecycle.md), plus `docs/defensive-patterns.md` and `docs/testing.md`.
   - Builtin or dependency replacement: [references/dependency-swaps.md](references/dependency-swaps.md).
   - Superseded Agent Notes: [references/note-lifecycle.md](references/note-lifecycle.md) and [`dsh-archive-agent-notes`](../dsh-archive-agent-notes/SKILL.md).
   - Another PR or branch: [references/pr-folding.md](references/pr-folding.md).

Resolve repository links from the installed location `.agents/skills/dsh-find-simplifications/`; this source copy is not expected to contain the deepseek-harness files.

## Survey The Requested Scope

Use parallel subagents only when the user asks for breadth or many candidates. Partition work by independent domains and require evidence:

- Agent loop/session log: turn and step boundaries, steering, cancellation, durable events, replay, load/resume.
- ACP and UI APIs: prompt settlement, teardown, transcript rendering, interaction state.
- LLM/tools/system prompt: stream/generate APIs, assemblers, registries, schemas, presentation hooks.
- Bash/tool execution: foreground/background split, job ownership, spill files, executor methods.
- Packages/examples/scripts/tests: package splits, inventories, snapshots, generated outputs, support packages.

For a targeted request, inspect only the named surface and its dependency/caller neighborhood. For a broad audit, begin with large or highly connected production surfaces; do not stop at the first unused symbol.

## Build A Candidate Ledger

Track every serious candidate before writing files; keep one compact row per candidate:

| Candidate | Production consumers | Non-production consumers | Net deletion | Behavior/API change | Recorded rationale | Risk | Confidence | Decision |
|---|---|---|---:|---|---|---|---|---|

Use `high`, `medium`, or `low` confidence. A durable Agent Note normally requires high confidence; a local cleanup may become an inline note. Record rejected candidates so the survey does not repeat work.

Strong candidates include:

- A method, event, config key, hook, helper, package, durable event, or test artifact with no production consumer.
- Tests or docs as the only consumers of behavior that is not load-bearing.
- Two representations or lifecycle mechanisms mirroring the same fact.
- A seam method every implementation supports but no consumer uses.
- A support/test/demo package whose separation adds publish or dependency overhead.
- Speculative product generality with no owner, such as unused multi-session, registry invalidation, job-roster, steering, or tool-owned presentation machinery.
- A rollback path, invariant, or expected-output corpus that protects only an unused API.
- Hand-rolled infrastructure whose replacement produces meaningful net deletion.

Reject or downgrade candidates that have a production caller, contradict an implemented Agent Note without stronger new evidence, cause unrelated churn without reducing surface area, or are merely small correctness/style cleanups.

## Prove Or Reject Each Candidate

1. Search exact symbols, event/wire strings, package names, config keys, and both `.method(` and `method(` forms with `rg`.
2. Classify consumers:
   - Production: `packages/*/src`, product-owned example/config paths, runtime scripts, loaders.
   - Non-production: tests, docs, notes, snapshots, generated expectations, comments.
   - Ambiguous: examples and scripts; inspect before classifying.
3. Read call sites and the relevant implementation. Use `knip` only as supporting evidence because dynamic events, public interfaces, and Cordis loader paths can evade it.
4. Search Agent Notes and documentation for the reason the surface exists.
5. Estimate net deletion: removed implementation, tests, docs, APIs, and dependencies minus replacement glue and migration work.
6. State the strongest reason to keep the current design and any capability or compatibility behavior the simplification gives up.
7. Assign the ledger decision: `agent-note`, `inline-note`, or `reject`.

Slight behavior changes are acceptable only when the resulting contract remains reasonable, simpler to explain, and explicit in the proposal.

## Stop And Report

For a targeted audit, stop when the named surface and its direct consumer/rationale graph are classified. For a non-exhaustive broad audit, stop when the requested high-confidence candidate count is reached after sampling at least three relevant domains, or when two consecutive domains produce no high-confidence candidate after that minimum sample. Survey every assigned domain only when the user asks for exhaustive coverage.

Report the ledger summary, areas surveyed, exclusions, and representative rejected candidates. Prefer a few proven candidates over filling a quota with weak ideas.

## Write The Result

Create one proposed Agent Note per durable design decision under `.agents/notes/proposed/<class>/yyyy-mm-dd-topic.md`, following `.agents/notes/README.md`. Consolidate with an existing owner instead of duplicating it. Use action-oriented titles, relative links, and one physical line per prose paragraph.

Include:

- `Problem`: current surface, file evidence, and production versus non-production consumers.
- `Proposal`: exact removals/folds, including tests, docs, schemas, snapshots, and generated artifacts.
- `Why not keep it?` or `What we give up`: strongest counterargument and lost capability.
- `Acceptance criteria`: observable end state and validation gates.
- `Risks`: API, behavior, compatibility, or future-product tradeoffs.

Use an inline `TODO(tag)`, `FIXME(tag)`, or `XXX(tag)` only for a small local cleanup that does not need a durable decision. Make it actionable and follow the urgency semantics in `docs/development.md`.

Do not modify code, notes, PRs, or branches when the user asked only for an audit or explanation. Match the artifact to the authorized scope.

## Validate Changes

For docs-only Agent Note changes, run at least:

```bash
pnpm run doc-sync
pnpm run lint
git diff --check
```

For code comments or skill changes, also run the relevant validator when one exists. Select further checks from the outgoing diff; the pre-push hook contributes typecheck only.

When a PR is authorized, summarize counts of added, consolidated, retained, downgraded, rejected, and deleted candidates; surveyed areas; intentional exclusions; and checks run. Keep it draft while the candidate set or review is unsettled.
