---
name: whats-next
description: Choose useful tracked work and prepare approved agent threads. Manually invoked.
disable-model-invocation: true
---

# What's next

Choose the next useful unit of progress, then prepare the right session for it.
This flow selects existing work; the selected skill owns what happens inside each session.

## 1. Assess

Read the repository's tracker configuration. Assess current tickets, relevant specs
and comments, blocking edges, assignments, active PRs, and known running agent work.
Use current tracker state over historical status text in imported bodies. Inspect
relevant code enough to judge likely implementation overlap. State gaps in access
or evidence rather than treating unknown work as free to take.

Keep assessment read-only. Recommend up to five useful groups by default, or the
user's requested maximum. This is a cap, not a quota. Group by coherent outcome
and reasonable PR scope; include decisions, prototypes, and human verification
when they are the next useful activity. Specification readiness does not clear
open blockers. A blocked implementation may still allow a clearly scoped discussion.

Arrange groups into numbered steps. Within each step use a compact table:

| Group | Outcome | Tickets | Suggested skill |
| --- | --- | --- | --- |

Link ticket references. Groups within a step can proceed together within stated
ownership boundaries. Name each later group's actual prerequisites; it need not
wait for unrelated earlier groups. Distinguish tracker dependencies from suggested
sequencing to avoid code overlap. When overlap is unknown, make concurrency
conditional on checking it rather than recommending an unconditional parallel run.
End with a brief first recommendation and wait
for selection.

## 2. Prepare

Use the installed `ask-matt` as the ecosystem map when choosing a flow. Read a
candidate skill's `SKILL.md` before recommending it. Resolve installed locations
in the current harness; skill summaries and literal slash commands are not a
substitute for loading instructions.

- `implement` fits a bounded ticket.
- `implement-spec` fits a spec or a selected batch on one integration branch.
  For a batch, explicitly limit the prompt to the selected tickets. Its
  orchestrator owns internal dependencies; check external blockers here. Keep
  batch ownership disjoint from other active threads, including whole-spec runs.
- `grill-with-docs` fits a decision that can be sharpened in conversation;
  `wayfinder` fits an effort too large and uncertain for one session; `prototype`
  fits a design question needing runnable evidence.
- `to-tickets` owns breaking an approved spec into implementation tickets;
  `triage` owns evaluating incoming requests. Selecting existing work does not
  rerun either procedure.

Use these as routing pointers, preserving each skill's own scope. Human
verification may need only a short prompt, with no skill.

Accept the user's groups, skill overrides, provider/model, effort, and prompt
edits. Explain blockers or overlap that affect the combination. Discover available
models and options before previewing exact settings. Resolve missing choices with
the user or propose available defaults for approval.

Preview a small table with group, exact provider/model/effort, skill, and workspace,
followed by each short initial prompt. Code work may need an isolated branch and
worktree; discussion and verification usually use an existing checkout. Opening a
thread alone does not justify a new branch. Honor repository workspace rules.

Prompts carry skill and issue/spec references plus meaningful exceptions, including
selected-ticket boundaries. Rely on those artifacts for acceptance criteria and
ordinary working rules. Keep model and workspace settings in launch parameters.
When programmatic skill expansion is unavailable, include the installed skill path
and an instruction to read and follow it.

For example, a bounded ticket needs only:

```text
Read and follow <installed skill root>/implement/SKILL.md.
Implement <ticket URL>.
```

Add only scope exceptions the artifacts do not carry. For an `implement-spec`
batch, name the selected tickets; if launch already creates its integration branch,
tell it to use the current branch as that integration branch. Keep verification
equally short: "Help me verify the remaining items in <ticket URL>." Routine checks,
commit rules, and extra reporting tasks belong to their existing instructions.

Wait for approval of the prompts and launch settings. Incorporate edits before launch.

## 3. Launch

Immediately recheck ticket state, blockers, and active work for the approved groups.
If something invalidates the approved scope, return that change to the user before
launching affected work.

Create separate top-level threads using the approved prompts, settings, and
workspaces. Launch only approved groups. For T3, read [T3.md](T3.md) at this point
and follow the current environment's orchestration instructions.

Report each successfully launched thread's returned link with its model and
workspace. State partial failures accurately. If tools or the requested model are
unavailable, explain the limitation and supply the approved prompt for manual use;
leave execution to the user rather than substituting a provider or subagent.
