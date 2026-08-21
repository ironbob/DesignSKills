# Reporting Contract

Use a compact report. Include evidence and decision-relevant limitations; omit raw scans, unrelated code listings, and cosmetic commentary.

## Screenshot observation

```markdown
## Observable layout findings

| Severity | Region | Observable fact | Impact | Evidence |
| --- | --- | --- | --- | --- |
| High | … | … | … | Screenshot |

### Limits
- No source code was supplied; no implementation cause, repair, or verification conclusion is made.
```

## Incremental work

```markdown
## Scope
- Target: …
- Directly coupled regions: …

## Repaired and verified
| Finding | Change boundary | Verification | Status |
| --- | --- | --- | --- |
| … | … | long text / narrow layout / error state | verified / unverified / not applicable |

## Limitations or remaining work
- …

## Unrelated existing issues (not changed)
- …
```

List only findings actually encountered. Do not fabricate every state to fill the template.

## Full-audit approval request

```markdown
## Audit scope
- …

## Coverage snapshot
- Discovered pages: …
- Coverage-complete pages: …
- Pages with unverified checks: …
- Blocked pages: …
- Coverage status: complete / incomplete

## Proposed repair groups
| Group | Severity | Region | Affected pages | Findings and impact | Evidence | Repair boundary |
| --- | --- | --- | --- | --- | --- | --- |
| A | High | … | … | … | … | … |

Please approve the groups to repair, for example: `Approve A and C`.
```

Stop after this request. Do not modify code until the user approves a group.

## Full-audit group completion

```markdown
## Group A — completed
- Approved boundary: …
- Repaired findings: …
- Re-verified affected pages: …
- Verification: …
- Status: verified / partially verified / unverified

## Remaining groups
- B: pending approval
- C: not started
```

Use `partially verified` only when a clearly named subset has direct verification. State which states or environments remain unverified.

Do not call the full audit coverage-complete while any inventory page has a pending or blocked required check. A coverage-complete audit can still contain `audited_unverified` checks; call it fully verified only when every required check is verified or reasoned not applicable.
