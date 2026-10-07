# Agent sync design

## Notes

This interview covers global agent instructions and skill installation, syncing, and updates. IDE configuration and scheduling are outside the first version.

## Decisions-so-far

- Use Python, uv, and Typer.
- Use file copies rather than symlinks.
- Prefer one repository for personal use. Keep the option to select a separate setup repo. The location and selection mechanism remain open.
- The recorded skill selection is authoritative: sync installs selected skills missing from a machine.
- An explicit upstream skill update changes the local installation and the setup repo.
- Support edits in both the setup repo and installed locations. Show a conflict when both sides changed differently.
- First setup previews adoption choices for differing files, adopts matching files, and leaves unrelated skills alone.
- Run commands manually in the first version.
- New upstream skills require explicit selection; updating a pack does not adopt new skills automatically.
- Downloaded skills are intended to remain upstream-owned; intentional customizations belong to custom skills. Preserve unexpected local edits and require an explicit choice before replacing them.
- Manage global setup only, initially for Codex and Cursor. Project instructions and skills are outside scope.
- Store shared skills under the user's global `.agents/skills` directory. Copy canonical instructions to global `.agents/AGENTS.md` and the configured Codex home. Cursor instruction discovery still needs an explicit decision.
- Following the user's delegation of version policy, prefer storing downloaded skill snapshots in the setup repo. Sync copies chosen contents; an explicit update refreshes snapshots and installed copies. CLI integration details remain open.
- Generate a global Cursor rule from the canonical instructions. Verify the supported file format and discovery behavior before implementation.
- Resolve global destinations from the current user's home and `CODEX_HOME`, with optional machine-local path overrides.
- Removing a skill from the shared selection proposes uninstalling its previously managed copy. A locally deleted selected skill is missing and is reinstalled by pull.
- Process skills independently. Preserve the previous copy on an item failure, report partial results, and advance baseline state only for completed items.
- Minimize routine steps and decisions. Updating skills includes publishing the managed results.
- Following the user's delegation, `push` captures local managed changes, commits, and publishes; `update` refreshes selected downloaded skills, installs completed results, commits, and publishes. Neither needs a separate publication step or routine confirmation.
- Publish successful independent items even if another item fails. Retain completed local results if Git publication fails and report that publication is pending.
- Confirm proposed managed deletions once per operation with a list. Preserve conflicting local edits and leave unrelated items alone.
- First initialization is interactive: default to shared content, back up differing local copies, and offer keeping local content. Routine later operations ask only for conflicts or proposed deletions.

## Fog

- How to use the skills CLI while keeping the selected inventory authoritative and producing stored snapshots.
- Verify Cursor global rule discovery and format.
- Repo selection and first import of existing custom/downloaded skills.
- Adding skills, selecting newly published skills, and resolving name collisions.
- Local baseline storage, operation recovery, and first-version completion criteria.

Implementation waits until the user confirms the interview reached a shared understanding.
