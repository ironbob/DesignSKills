# Dependency Or Builtin Swaps

Load this reference only when hand-rolled infrastructure may be replaced by a Node builtin or external package. The repository dependency-policy Agent Note owns the acceptance bar.

Consider protocol parsers, framers, retry/backoff loops, glob matchers, diff engines, and similar generic infrastructure.

For each candidate:

1. Define the exact hand-rolled surface and semantics.
2. Check the repository engine floor for a suitable builtin first.
3. For a package, verify maintenance, adoption, release health, license, transitive footprint, and security posture with current primary sources.
4. Map uncovered residual semantics; they remain as glue and count against the simplification.
5. Search Agent Notes for settled seams such as schemastery, vendored Cordis, twin adapters, or other recorded choices. New evidence must beat the recorded rationale.
6. Calculate net deletion: implementation, dedicated tests, and docs removed minus wrapper, migration, compatibility, and dependency-management code added.

Reject a swap that relocates comparable complexity into a wrapper, weakens a required contract, or depends on an unhealthy package. Record behavior differences and the strongest reason to keep the existing implementation.
