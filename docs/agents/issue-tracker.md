# Issue tracker

Issues and specs live as Markdown files under `docs/.work/`.

- One directory per feature: `docs/.work/<feature>/`.
- Specs: `docs/.work/<feature>/spec.md`.
- Individual tickets: `docs/.work/<feature>/tasks/NN-<slug>.md`,
  numbered from 01.
- Record triage state in a `Status:` line near the top.
  Use the roles in `triage-labels.md`.
- Append discussion under a `## Comments` heading.

When publishing a ticket, create its individual file.
When fetching a ticket, read the referenced file.

## Wayfinding

- Map: `docs/.work/<feature>/map.md`, with Notes,
  Decisions-so-far, and Fog sections.
- Child tickets use the same `tasks/NN-<slug>.md` convention.
- Record ticket type in `Type:`: research, prototype,
  grilling, or task.
- Record dependencies in `Blocked by: NN, NN`.
- Choose the lowest-numbered open, unblocked, unclaimed ticket.
- Set `Status: claimed` before starting work.
- To resolve, append an `## Answer`, set `Status: resolved`,
  and add a summary and link to the map's Decisions-so-far.
