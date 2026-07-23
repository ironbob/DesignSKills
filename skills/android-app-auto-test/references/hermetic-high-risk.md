# Hermetic High-Risk Coverage

Default policy excludes payment, delete, publish, send-message, and real profile
changes (`SKILL.md` Safety). That keeps a stray run from doing damage — but it
also means "cover all business" is never true for the most important flows. This
document is how to cover them safely so the exclusion is a choice, not a gap.

Only use a strategy here when the user explicitly allows high-risk paths
(`allowed_high_risk_paths: true`) AND the test environment + test data support
it. Otherwise the default exclusion holds.

## Principles

- Never touch production, real money, or real user data.
- Prefer deterministic, replayable backends over live calls.
- Make every high-risk action idempotent and reversible within the test env.
- Assert up to the boundary of real-world effect; stop the assertion there.

## Strategies (pick per path)

1. **Hermetic test backend** — point the app at a test server that accepts the
   action and returns canned success/failure. Best for payment and publish.
2. **Contract mocks / stubs** — intercept the gateway call in-app (test build
   flag) and assert the request payload without sending it. Good for payment
   gateways.
3. **Recorded responses (VCR-style)** — replay a recorded backend response for a
   given request. Good for search/feed flows with large payloads.
4. **Dry-run boundary** — execute the real flow up to the irreversible call,
   assert the call is about to happen with the right parameters, then stop. Good
   for send-message and publish.
5. **Idempotent test data** — use accounts/records created solely for testing
   that can be deleted; assert the change then roll it back via the backend.

## Per-Category Guidance

- **Payment** — contract mock at the gateway; assert amount/order/credentials;
  never let a real charge through. `risk_flags: [payment]`.
- **Delete** — idempotent test data; assert the item is gone; restore via backend
  or recreate in teardown.
- **Publish** — dry-run boundary; assert publish payload; do not actually publish.
- **Send message** — dry-run boundary to a test recipient only; assert body and
  recipient; never deliver to real users.
- **Profile changes** — test-profile only; assert the change; revert in teardown.

## Recording In Artifacts

- In `path-map.json`, set `risk_flags` and `automation_readiness`, and note the
  chosen strategy in a `safety_strategy` field.
- In `test-plan.json`, state the test backend / mock / dry-run mechanism and the
  test-data account under setup.
- The runner still collects logs but must redact via `scripts/redact_report.py`.
