# Superseded Agent Notes

Load this reference only when the user asks to audit/coalesce Agent Notes or when an authorized simplification makes an owning note obsolete. Also use `dsh-archive-agent-notes` for retention and archive mechanics.

Do not turn every code audit into a repository-wide note audit. Proposed notes are never archived. Do not edit archived notes while simplifying current code or prose.

## Classify Supersession

1. Identify the current owner from shipped code, configuration, generated catalogs, package docs, newer Agent Notes, and inbound links. Dates and titles are discovery hints, not proof.
2. Classify the old note as fully or partially superseded.
3. Treat surviving behavior, a current contract, durable/wire format, migration or compatibility obligation, or an independently current rejected alternative as partial supersession.
4. Rationale that can be transferred to the current owner does not by itself make supersession partial.

## Fully Superseded Notes

Move every unique rationale, alternative, consequence, shipped verification fact, named coverage gap, reintroduction condition, and capability given up into the current owner. An inventory of deleted mechanics is not a durable decision fact.

Repair inbound links, then delete the English note, Chinese counterpart, and consistency record together. Search exact filenames, symbols, config keys, event names, and wire strings after editing.

## Added Then Removed Features

Let the removal note own the history only when the feature is absent from production code, configuration, schemas, durable/wire formats, migrations, and compatibility behavior; current documentation does not present it as available; and no test exercises it as supported behavior. Tests that enforce absence may remain.

Preserve why the feature existed, why that motivation no longer wins, alternatives to full removal, lost capability, conditions for reintroduction, and evidence that removal is complete.

Reject consolidation when only one transport, default, implementation, or presentation was removed; persisted data or compatibility handling survives; or the new owner lacks enough rationale to prevent accidental reintroduction. Keep partial supersessions cross-linked and current.
