# Issue tracker

Specs and tickets live in GitHub Issues for `RafyTime/rig`. Use `gh`
from the repository checkout. `docs/.work/` contains historical records.

- Create issues with `gh issue create`. Pass multiline bodies with `--body-file`.
- Read issues with `gh issue view <number> --comments`.
- Find work with `gh issue list --state open` and the relevant label filters.
- Comment, apply labels, and close with `gh issue comment`, `gh issue edit`,
  and `gh issue close`.

**PRs as a request surface: no.**

## Wayfinding

- Create the map as an issue labelled `wayfinder:map`. Keep its Notes,
  Decisions-so-far, and Fog in the issue body. Create the label when first needed.
- Create tickets with `gh issue create --parent <map>` or attach existing
  tickets with `gh issue edit <map> --add-sub-issue <ticket>`. Use the
  `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling`, or
  `wayfinder:task` label. Create these labels when first needed.
- Record blockers as native GitHub issue dependencies. If unavailable,
  add `Blocked by: #<number>` to the ticket.
- Select the first open, unassigned child in map order whose blockers
  are closed. Claim it with `gh issue edit <ticket> --add-assignee @me`.
- Resolve by posting the answer, closing the ticket, and linking the
  decision from the parent map.
