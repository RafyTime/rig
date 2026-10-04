# [AGENTS.md](http://AGENTS.md)

Hey there, I'm Leo. You're my agent. We will be working together a lot, so I thought it would be worth indroducing myself.

I'm a Computer Science student at IU Bad Honnef. I've also co-founded a travel-tech startup, AQI Travel.

I love to build. I focus on building complex things as simple as possible. I love to find ways to reduce complexity when solving problems.

I wanted to share some of my preferences here so we can be more aligned as we work together.

## General

- Do not commit, push, or open pull requests unless explicitly requested by the user.
- Always run any available quality checks (lint, format, typecheck, tests...) after finishing some unit of work.

## Coding Preferences

- Keep things simple. Channel "yagni" energy unless told otherwise.
- Typesafety is useful, take advantage of it.
- Don't be scared to propose bold ideas if they can meaningfully benefit our work.
- Be careful with destructive actions that are not explicitly requested by the user.
- Tests are good! Endless smoke tests, "regression tests" for feature deletion, etc, much less good. Tests should be focused, not slop.
- Comments are a great way to clarify functionality and how code is used. Don't comment every line, but feel free to describe (concisely) how functions are used above function definitions, classes, etc.
- Keep comments up to date! When making changes, it is important to keep things in sync.

### Typescript

- `any` is the enemy. Inferred types are our friend. Our systems should adapt changes, instead of requiring changes everywhere.
- If your TS code looks like python, it is bad TS code.
- Avoid one-line functions that are just casting wrappers.
- Write TypeScripts in ways Matt Pocock and Theo (t3.gg) would be proud of.

## Questions are read-only

- A question is a request for an answer, not changes. If the message opens with "how hard would it be", "what are your thoughts", "why does", "should we", "is it possible", "can X do Y", or otherwise asks rather than instructs: answer it, and do not edit files.
- If the answer is obvious and the change is trivial, still answer first and offer the change. Ask before making it.

## Subagents

- Unless specified by a skill or the user, do not spawn subagents or multi-agent panel for work a single agent can finish in one pass. Delegation is for breadth or adversarial review, not for ordinary tasks.
- When more than one agent work in parallel, state file ownership up front so they do not collide.

## Blast Radius

- Never touch production, live databases, or daily-driver build/preview channels unless explicitly told to. When a task is adjacent to any of them, name what you are about to touch before touching it.
