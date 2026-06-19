# Subagent Protocol

Use dedicated subagents to prevent context drift. The main agent coordinates state, gates, edits, and command execution.

## Principles

- Pass raw artifacts and file paths, not conversational summaries.
- Give each subagent one bounded role and one output artifact.
- Do not leak expected answers, suspected fixes, or hidden conclusions.
- Prefer JSON/Markdown artifacts over prose handoff.
- Rebuild each subagent's context from source files.
- Main agent must verify outputs before acting.

## Roles

Prompt files live in `agents/`:

- `path-analyst.md`
- `testability-auditor.md`
- `test-planner.md`
- `test-runner.md`
- `bug-fixer.md`
- `report-writer.md`

## Handoff Pattern

Use prompts like:

```text
Use the android-app-auto-test role prompt at <skill>/agents/path-analyst.md.
Inputs:
- requirements: <path>
- project root: <path>
- scope and entry decisions: artifacts/android-test/inputs.json
- output: docs/android-test/path-map.md and artifacts/android-test/path-map.json
Do not edit code.
```

For direct execution:

```text
Use the android-app-auto-test role prompt at <skill>/agents/test-runner.md.
Inputs:
- artifacts/android-test/inputs.json with entry_stage=execute
- artifacts/android-test/test-plan.json or an explicit Gradle command from inputs.json
- selected existing test files when applicable
Output:
- append run evidence only for the confirmed scope
Do not re-analyze code, regenerate paths, add logs, or edit tests unless the main agent explicitly changes the startup decision.
```

For bug fixing:

```text
Use the android-app-auto-test role prompt at <skill>/agents/bug-fixer.md.
Inputs:
- one failure object from artifacts/android-test/failures.json
- relevant logs and test file paths
- max scope: files directly related to this failure
Output:
- minimal code change
- fixes.json entry
- fix-report.md entry
```

## Anti-Corruption Rules

- A runner must not infer root cause without evidence.
- A runner must not expand a scoped execution request into all instrumentation tests.
- A fixer must not rewrite unrelated architecture.
- A reporter must summarize artifacts only; it must not invent unexecuted coverage.
- If a subagent output contradicts artifacts, update the artifact or reject the output before proceeding.
