# [AGENTS.md](http://AGENTS.md)

Hey there, I'm Leo (Rafy). You're my agent. We will be working together a lot, so I thought it would be worth indroducing myself.

I'm a Computer Science student at IU Bad Honnef. I've also co-founded a travel-tech startup, AQI Travel.

I love to build. I focus on building complex things as simple as possible. I love to find ways to reduce complexity when solving problems.

I wanted to share some of my preferences here so we can be more aligned as we work together.

## General

- Commit completed units of work when it helps advance the task.
- Use Gitmoji commit messages. Keep them short and descriptive.
- Ask for approval before pushing or opening a pull request. Push only when the task is complete to avoid unnecessary CI runs or deployments.
- Name branches after their purpose, using prefixes (feat/, fix/, refactor/, docs/, chore/...) followed by a short kebab-case description. Do not use agent names as prefixes (no "codex/feature-slug...").
- Never force-push, rewrite shared history, or push directly to the default branch without explicit approval.
- Run checks proportionate to the change. For prose-only edits, review the diff & format; for behavior changes, run relevant checks before committing.

## Coding Preferences

- Keep things simple. Channel "yagni" energy unless told otherwise.
- Typesafety is useful, take advantage of it.
- Don't be scared to propose bold ideas if they can meaningfully benefit our work.
- Be careful with destructive actions that are not explicitly requested by the user.
- Tests are good! Endless smoke tests, "regression tests" for feature deletion, etc, much less good. Tests should be focused, not slop.
- Use concise comments to explain intent or non-obvious behavior, and keep them current & in sync with relevant ADRs (if any).
- Make failure modes explicit. Handle errors where recovery is possible; otherwise propagate them with useful context. Avoid silent failures.

### Tooling

- Use `uv` for Python dependency management, environments, and running scripts and tools.
- For JavaScript and TypeScript, prefer Vite+ (`vp`) where supported; otherwise use Bun for dependency management and running scripts and tools.
- If these tools cannot support a required workflow, explain the limitation before using an alternative. Keep existing lockfiles and package-manager configuration unless a migration is requested.

### TypeScript

- Write TypeScript that Matt Pocock and Theo Browne would be proud of.
- Avoid `any`. Prefer inferred and derived types so changes propagate through the type system.
- Avoid functions that only wrap a type assertion.

## Questions are read-only

- For questions and exploratory discussion, answer without editing files. Offer changes and wait for approval.

## Subagents

- Unless specified by a skill or the user, do not spawn subagents or multi-agent panel for work a single agent can finish in one pass. Delegation is for breadth or adversarial review, not for ordinary tasks.
- When more than one agent work in parallel, state file ownership up front so they do not collide.

## Blast Radius

- Never touch production, live databases, or daily-driver build/preview channels unless explicitly told to. When a task is adjacent to any of them, name what you are about to touch before touching it.
