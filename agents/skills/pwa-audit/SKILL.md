---
name: pwa-audit
description: "Assess a project's PWA setup, clarify product needs, and produce a prioritized audit with individual criterion scores before handoff or implementation. Manually invoked."
disable-model-invocation: true
---

# PWA audit

Find the smallest PWA implementation that serves this product well. Start with the repository, give a provisional audit, interview the user about consequential decisions, then diagnose against the agreed target. Support missing, partial, and established implementations.

Honor an explicit report-only request: use supplied decisions, label unresolved assumptions, and finish the report without requiring an interview or an implementation choice.

## 1. Explore and give a preliminary audit

Read repository instructions, product docs, and relevant app entry points. Identify the web app, framework, existing manifest, service worker tooling, assets, tests, and local run commands. Follow generated configuration back to its source. In a monorepo, identify the intended app before expanding the audit. If there is no web app, explain that finding and ask whether a planned web app is the target; do not invent one.

Read [criteria.md](references/criteria.md) to guide inspection. Use available local checks and an isolated browser profile when possible. Running a development server does not prove that a generated production service worker works. Prefer an isolated local production build when the repository supports one. Keep builds and tests clear of production services and shared preview channels.

Keep application code unchanged during diagnosis. Use temporary locations for audit artifacts. If checks require missing credentials, tools, or devices, continue source inspection and label the affected behavior unverified. Installation of dependencies, deployments, and remote mutations are separate actions governed by existing user authorization.

Present a short preliminary audit before asking product questions:

- What is implemented, absent, or visibly broken, with file or runtime evidence.
- The essential fixes that do not depend on unresolved product decisions.
- The decisions and verification gaps that could change the recommendation.

This phase is complete when the user can distinguish confirmed defects from provisional recommendations. Missing PWA features alone do not establish a defect.

## 2. Grill for product fit

Investigate facts yourself. Ask the user for decisions and product knowledge the repository cannot establish. Use small rounds of independent questions, each with a recommended answer and its tradeoff. Wait for answers before asking questions that depend on them. Challenge a request when its complexity exceeds its user benefit.

Resolve only decisions that affect this audit:

- Who uses the app, their important journeys, and the target devices and browser versions.
- Why installation would help, and whether mobile, desktop, or both need an installed experience.
- What should happen with slow connections or no connection: clear failure handling, selected offline reading, or offline writes and later synchronization.
- Which data can remain on a device, how stale it may be, and what happens on logout, account changes, or shared devices.
- Whether updates may interrupt work, and whether push or other platform capabilities solve a specific need.

Carry forward answers already supplied in the conversation. Ask only questions whose answers could change scope, priorities, architecture, or acceptance checks. If those decisions are already settled, summarize them without repeating an interview. Stop once each material decision has an answer or an explicitly accepted assumption. Treat unresolved material choices as open, not silently agreed. Confirm the target in a short recap; use an existing explicit agreement rather than requesting the same approval again.

## 3. Diagnose against the agreed target

Select applicable outcomes from the checklist and adapt them into observable acceptance criteria for the agreed journeys and platform combinations. A feature the product deliberately does not need is N/A, not a missing point. Also examine existing capabilities that create risk even when the target no longer needs them, such as an old worker serving stale assets.

Read [platforms.md](references/platforms.md) for the selected platforms, installation, updates, and current-source pointers. Verify changing compatibility claims against current vendor documentation; record browser/OS versions and the audit date. If browsing is unavailable, disclose the uncertainty rather than treating remembered support as a verified fact.

Inspect source and exercise the relevant behavior with available tools. Check normal operation and the failure cases that could invalidate the product promise: fresh versus returning visits, installed launch, network failure and recovery, updates, and authentication as applicable. Test behavior, not keyword presence. A manifest declaration, plugin dependency, or matching function name is a lead, not proof of an end-to-end result.

### Individual rubric

Score each applicable criterion independently, splitting it by platform or journey when results differ:

- **0 / Unmet:** Evidence establishes that the agreed outcome fails or is absent.
- **1 / Partial:** Evidence establishes a working subset and specific unmet acceptance conditions.
- **2 / Met:** Evidence demonstrates all acceptance conditions for that criterion at its stated scope.
- **N/A:** The outcome does not apply, with the product or platform reason.
- **Not verified:** Evidence is insufficient. State what would verify it. This is not a numeric score or a failure.

Keep evidence type separate: source inspection, local automated check, browser observation, real-device test, or field measurement. Static criteria can be met through source inspection; installed behavior needs runtime evidence. Source-only plausibility cannot earn a partial runtime score. When splitting an outcome into static and runtime checks, retain the unverified remainder explicitly; a narrower pass cannot stand in for the full outcome. Where a known defect coexists with untested cases, report the known score and the remaining verification gap.

Set priority by consequence: **Essential** protects an agreed core journey, accessibility, privacy, or data integrity; **Improvement** has demonstrated benefit but does not block that target; **Optional** is a useful extension the user may choose. Scores describe fulfillment, not urgency. Do not calculate aggregate scores, percentages, category averages, or letter grades. The target is ready only when the agreed essentials are met and verified. The audit is complete when selected criteria have results, evidence or verification gaps, and actionable next steps, even if implementation remains.

## 4. Report and choose the next action

Keep the report short, using this order:

1. **Target:** App, user journeys, platforms, offline promise, and material decisions or exclusions.
2. **Verdict:** What is ready, what blocks the target, and what remains unverified.
3. **Scorecard:** One concise entry per selected criterion: ID/name, individual result, priority, evidence and scope. Group N/A decisions with their reasons. Avoid reproducing irrelevant checklist items.
4. **Next steps:** Essentials first. Each finding names the user impact, affected file/component, smallest appropriate fix, and observable acceptance check. Link to scorecard evidence rather than repeating it.
5. **Verification limits:** Tools/checks run, unavailable device or field evidence, and open decisions. Never describe the entire app as WCAG-conformant or fast from a single automated run.

Unless the user requested report-only, offer two choices after the report: **write an implementation handoff** or **implement here**. Wait for the user's choice unless they have already explicitly selected a path. An audit request alone does not authorize application changes.

For a handoff, write one self-contained Markdown file to the user's requested location, otherwise an OS temporary directory. Include the target and decisions, current implementation with file paths, criterion results and evidence, prioritized work, acceptance checks, commands, and remaining unknowns. Reference existing durable artifacts where useful, but include the decision summary a fresh agent needs. Exclude secrets and personal data. Link the file; creating it does not authorize messaging or starting another agent.

For implementation, follow repository conventions and the existing stack. Implement the agreed essentials first, add focused behavioral tests where useful, and run the available quality checks. Reassess affected criteria with the same acceptance checks and report remaining gaps. Stop when the agreed scope is satisfied; additional capabilities earn no extra credit.
