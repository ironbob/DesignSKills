# Folding Simplifications From Another PR

Load this reference only when the user asks to inspect or fold work from another branch or PR.

Diff the sibling branch against `origin/master`, not the current feature branch, to isolate its independent contribution.

For each item:

- Port non-overlapping Agent Notes or inline notes that meet the evidence bar.
- Consolidate overlapping evidence into the existing Agent Note that owns the topic.
- Reject duplicate or lower-confidence proposals; do not preserve a candidate count for its own sake.
- Update the destination PR body with the true candidate count, scope, exclusions, and validation.

Close or otherwise mutate the source PR only when the user explicitly authorizes it or the current task clearly owns that housekeeping.
