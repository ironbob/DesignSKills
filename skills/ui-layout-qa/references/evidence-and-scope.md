# Evidence, Scope, and Severity

Use this reference only when evidence is incomplete or conflicting, a likely fix crosses component boundaries, or a full audit needs grouping.

## Evidence classes

| Class | Meaning | Permitted conclusion |
| --- | --- | --- |
| Code | A source constraint or behavior relevant to the target | Intended behavior or a plausible structural cause; not visual verification by itself |
| Screenshot | A visible rendered fact in the supplied image | Observable symptom only; no implementation cause by itself |
| Rendered verification | A current preview, emulator, screenshot test, or equivalent actual result | Visible result for the exercised state and environment |
| Existing check | A relevant automated test or lint/check result | Only the behavior that check actually covers |
| Missing | Required evidence cannot be obtained | `unverified`; explain the missing condition |

## Combine evidence

1. Start from code to determine the intended behavior when code exists.
2. Use screenshots or running output to determine what was actually rendered.
3. When they conflict, state both facts and the scope of the discrepancy. Do not let the screenshot redefine intended behavior.
4. When code is absent, limit the result to screenshot observations. When screenshots or runtime output are absent, do not describe a static-code conclusion as a visually verified result.

Use precise language:

- `verified`: current evidence confirms the required result for the named state.
- `unverified`: the result may be correct, but evidence is insufficient.
- `not applicable`: the state or check does not exist for this target; state why.
- `pending approval`: a full-audit group has not been authorized for modification.

## Scope ladder

Start at the smallest rung that can explain the issue. Expand only when the current rung cannot provide a reliable diagnosis.

1. Target component/view and local layout rules.
2. Direct parent, direct children, sibling actions, and local state variants.
3. Shared component, token, container, or responsive rule directly governing the target.
4. Adjacent screen/region only when the target's root cause or regression path reaches it.

Reading a wider scope does not automatically authorize editing it. In incremental mode, explain and obtain direction before editing beyond directly coupled regions. In full mode, put the wider region into a separately approved group.

## Severity for full-audit grouping

| Severity | User impact | Typical grouping action |
| --- | --- | --- |
| Critical | A required action or essential content is unreachable, obscured, or unusable | Isolate as a high-priority group |
| High | Frequent comprehension or operation failure, such as overflow hiding key content or a narrow layout blocking primary actions | Group by the affected region; recommend repair first |
| Medium | Noticeable hierarchy, alignment, density, or state-layout degradation with a usable workaround | Group with related region issues |
| Low | Local inconsistency with a concrete but limited impact | Keep compact; do not inflate the audit |

Do not assign severity for personal style preference. State the concrete comprehension, navigation, or operation impact.
