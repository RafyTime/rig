---
name: repo-review
description: Review a GitHub repository's presentation, navigation, and onboarding.
disable-model-invocation: true
---

## Scope the review

Use the supplied GitHub repository or the current checkout's GitHub remote. Review the default branch unless the user specifies another revision. Inspect GitHub's repository page and the files at the reviewed revision. Record visibility and infer the intended audience from the user's goal and the project's own language. Ask if the audience is unclear and the answer would change the checklist.

Keep the review read-only. Inspect the documented workflow without running setup or deployment commands.

## Follow the reader's path

- **GitHub About.** Check whether the description and topics help readers identify and discover the project. Check the website link when a demo or docs exist.
- **README.** Inspect the GitHub-rendered page when available. Check the opening, section order, headings, and placement of the next step. Assess visual hierarchy and readability as well as completeness. Suggest screenshots or focused badges and banners where they help explain the project or guide the reader. [ShieldCN](https://shieldcn.dev/) is an optional source for badges and banners.
- **Structure.** Follow links and root-level cues to the main code or config, docs, and other entry points readers need.
- **Setup.** Check that readers invited to try or work on the project can find prerequisites, ordered steps, and a way to recognize success.
- **Contribution.** Check whether readers can tell if contributions are welcome and where to start when they are.

For a public personal project, focus on presentation and the actions it invites. For an open-source project, also check visible licensing terms, install or release discovery, support, and bug and security reporting. Assess issue forms, PR templates, and a code of conduct where they serve the contribution workflow. Check effective GitHub defaults before reporting a community file missing. For a private team repository, focus on access, internal docs, ownership, and where teammates get help or submit changes. Check archive or maintenance status when it affects adoption.

## Report and hand off

In chat, name the repository, reviewed revision, and audience, then give a short verdict. Number findings in order of reader impact. For each, state the affected reader task, link to observed evidence, and propose a concrete improvement. For missing guidance, cite the entry points checked. Note what could not be verified separately. Report only gaps that affect the intended audience.

Offer to draft selected fixes. Discuss choices that need owner input and show proposed file or GitHub settings changes for approval before applying them.
