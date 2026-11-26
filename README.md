# Rig

Rig keeps my personal configuration, agent setup, and skills in sync across
my machines with [chezmoi](https://www.chezmoi.io/). The current setup
supports Fedora and native Windows.

[Set up another device](#another-device) · [Daily workflow](#daily-workflow) ·
[Upgrade the CLI](#upgrade-the-cli) · [Repository layout](#repository-layout) ·
[Manage skills](#skills)

## Another device

Install Git, uv, and Bun, then authenticate with GitHub. Install the `rig`
CLI from a release tag and set up the checkout:

```sh
uv tool install git+https://github.com/RafyTime/rig@v0.2.0
rig init                 # Or: rig init OWNER/NAME for your own fork
```

`rig init` reuses chezmoi from PATH. Without it, Rig downloads the official
chezmoi release for x86-64 Fedora or Windows, checks it against the release's
published SHA-256 checksum, and installs it to `~/.local/bin`, where later `rig`
commands find it even if that directory is not on PATH. Init clones the
checkout but applies nothing; your dotfiles and skills change only on
`rig apply`. Running it again for the same repository is safe, and it stops if
chezmoi already manages a different one.

If this device already has selected skills installed, follow
[Adopt existing skills](#adopt-existing-skills) before the first apply.
On Windows, see [PowerShell execution policy](#powershell-execution-policy)
if the skill sync hook is blocked.

```sh
rig diff
rig apply
```

Run `chezmoi source-path` and check that it points to the `home/` directory
inside the Rig checkout. If you use Cursor, open a fresh chat and verify that
it loads the personal rule.

## Daily workflow

Edit `agents/AGENTS.md`, then run from any directory:

```sh
rig diff           # Preview installed changes
rig apply          # Apply locally and sync skills once
chezmoi push       # Stage, commit, and push repo changes intentionally
```

`rig diff` and `rig apply` delegate to chezmoi's active setup. Extra arguments
pass through, for example `rig diff --exclude scripts`; a `--` separator is
dropped, so write a target that starts with a dash as `./-name`. Output, prompts, and
exit codes are chezmoi's. Plain `chezmoi diff` and `chezmoi apply` keep working
without the `rig` CLI. Run `rig --help` for all commands and `rig --version`
for the installed release.

On another device, `rig update` pulls Rig, applies it, and syncs skills once
without refreshing downloaded versions. To preview first, run
`rig update --no-apply`, which only pulls, then `rig diff` and `rig apply`.
`chezmoi update` and `chezmoi update --apply=false` do the same without the CLI.
Automatic commits, pushes, and background sync are disabled. Agents must not
commit or push unless explicitly requested.

## Upgrade the CLI

The `rig` CLI has its own release lifecycle, separate from your configuration:

```sh
rig self update    # Install the latest stable release if it is newer
rig --version      # Confirm the installed release
```

`rig self update` asks GitHub for the latest stable release of `RafyTime/rig`
(drafts and pre-releases are skipped) and, if it is newer than the installed
CLI, runs `uv tool install --force git+https://github.com/RafyTime/rig@<tag>`.
uv's output streams through. If the CLI is already current, it says so and
installs nothing. It never pulls or applies the checkout and leaves installed
skills alone; use `rig update` and `rig skills update` for those. On native
Windows, rig moves its running launcher files aside so uv can replace them.

If the release check or uv fails, rig prints the error with the next step,
usually the `uv tool install` command to run yourself, and exits with status 1.

## Repository layout

| Path | Role |
| --- | --- |
| [`home/`](home/) | Files managed by chezmoi, selected by `.chezmoiroot`. |
| [`agents/AGENTS.md`](agents/AGENTS.md) | Canonical personal instructions for agents. |
| [`agents/skills.json`](agents/skills.json) | Selects downloaded and custom skills. |
| [`agents/skills/`](agents/skills/) | Source for custom skills. |
| [`zed/`](zed/) | Reference settings for Zed. |
| [`src/rig/`](src/rig/) | The `rig` CLI package. |

Templates render the personal instructions at `~/.agents/AGENTS.md`,
`~/.codex/AGENTS.md`, `~/.cursor/rules/personal.mdc` (always applied), and
`~/.claude/CLAUDE.md`. The Codex template assumes the default `~/.codex`.
Keep checkout paths in local configuration. For example, the current Fedora
machine sets `sourceDir = "/home/lplata/Code/rig"`.

## Skills

On each apply, chezmoi runs `agents/skills.py sync` through uv. Sync refreshes
custom skills and uses Bun with `skills@latest` to fetch missing downloaded
skills. Use an explicit update to refresh installed downloaded skills.

`rig skills` runs the same engine from the active chezmoi checkout against its
destination, so it works from any directory without applying dotfiles. It needs
chezmoi, uv, and Bun.

### Select and update skills

`agents/skills.json` is the selection manifest. For example:

```json
{
  "version": 1,
  "sources": [
    {"source": "mattpocock/skills", "skills": ["code-review", "tdd"]},
    {"source": "./agents/skills", "skills": ["unslop"]}
  ]
}
```

Sources beginning with `./` are local skill containers relative to the Rig
checkout. Each selected name maps to `<source>/<name>/SKILL.md`. Add shared
skills to the manifest. Direct CLI installs stay local until selected.

```sh
rig skills sync            # Install missing selections, refresh custom skills
rig skills sync --dry-run  # Plan without writes/downloads
rig skills update          # Explicitly refresh selected downloaded skills
rig skills update --dry-run  # Plan an update without downloading
```

Sync keeps installed downloaded versions; only `rig skills update` refreshes
them. For automation, the script entry points remain available from the repo
root: `uv run --script agents/skills.py sync|update [--dry-run]` and
`uv run update-skills.py [--dry-run]`.

### Adopt existing skills

On an existing device, run these commands once to adopt matching CLI-managed
installations:

```sh
rig skills sync --adopt-existing --dry-run
rig skills sync --adopt-existing
```

Adoption trusts current installed contents as the baseline when the existing
CLI lock identifies the selected source; it cannot establish whether those
contents were modified before adoption. Unknown-origin collisions are preserved.
Use `rig skills update` for later updates. Rig tracks ownership separately
from the global skills CLI.

### Sync behavior

- `chezmoi update` pulls Rig and applies the configuration.
- Missing downloads fetch current upstream content. Exact version parity and
  revision pinning are deferred. New upstream skills require explicit selection.
- Maintain ordinary copies of selected skills in both `~/.agents/skills/` and
  `~/.claude/skills/`, downloading each source only once. Each destination has
  its own ownership baseline and local-edit protection. No symlink privileges
  or Windows Developer Mode are needed.
- Migrate selected Claude symlinks pointing to the expected shared skill into
  ordinary copies automatically. Preserve other links and unmanaged directories.
  Identical unmanaged Claude copies can be adopted with `--adopt-existing`.
  Removed managed copies require confirmation in each destination.

Rig downloads through a temporary CLI project and batches requests by source.
It verifies each selected skill independently and keeps unchanged copies in
place. Apply and explicit updates print a summary, errors, and pending
removals. Dry runs also list planned changes.

### Custom skills and forks

Custom skills live under `agents/skills/<name>/SKILL.md`. `skills.sh.json`
declares this discovery path for the Vercel skills CLI; the skills do not depend
on chezmoi or the rig wrapper to be installed.

Once the skill files and discovery config are committed and pushed, install from
this repo independently:

```sh
bunx skills@latest add RafyTime/rig --list
bunx skills@latest add RafyTime/rig --skill unslop -g -a codex
```

The Codex target uses the shared global `.agents/skills` location, also read by
Cursor. To test unpublished changes, replace `RafyTime/rig` with the local repo
path. Run installs from a different directory if testing project-scoped installs
so the source repo stays clean.

Claude Code reads personal instructions from `~/.claude/CLAUDE.md`. Recent
versions also read a project's `AGENTS.md` when no project `CLAUDE.md` takes
precedence; check `/memory` in Claude Code to see loaded instructions. Claude
uses `~/.claude/skills/` for personal skills. Rig maintains selected copies there;
unlisted Claude skills remain untouched.

`agents/skills/unslop/SKILL.md` is the first custom skill, forked from the
installed `cursor/plugins` version. Edit this source in rig, then run
`chezmoi diff` and `chezmoi apply`. The diff shows the sync script, not a diff
of custom skill contents; use Git to review source edits. Upstream skill updates
no longer replace this custom selection.

To fork another managed skill:

1. Copy its installed folder into `agents/skills/<name>/` before modifying it.
2. Move its name from the downloaded source to the `./agents/skills` source's
   `skills` list in `agents/skills.json`. Keep the skill's frontmatter name.
3. Run `rig skills sync --adopt-existing --dry-run`, then run it without
   `--dry-run`. This explicitly transfers ownership only when the
   custom source, installed copy, and previous baseline match.
4. Make your edits in rig and apply normally. On a fresh device, apply installs
   the custom source directly. Existing devices need the explicit adoption step
   before edits diverge; otherwise preserve the source conflict and resolve it
   deliberately, or use a distinct name for the custom skill.

The custom unslop skill allows automatic invocation. Its description instructs
agents to apply it whenever composing or editing text, including chat replies,
documentation, and code comments.

`pwa-audit` is a custom, manually invoked skill. Use `$pwa-audit` in Codex to inspect
a web app, clarify its PWA needs, and get a prioritized report with individual
criterion scores. It offers a handoff or implementation after diagnosis.
Its `agents/openai.yaml` disables implicit invocation in Codex; its frontmatter
does the same in Cursor, where it is invoked as `/pwa-audit`.

`repo-review` reviews a GitHub repository's presentation, navigation, and
onboarding. Invoke it with `$repo-review` in Codex or `/repo-review` in
Claude Code and Cursor to get a read-only report with prioritized fixes.

`whats-next` is a custom, manually invoked extension of the engineering skill
flow. Use `$whats-next` in Codex or `/whats-next` in Claude/Cursor to choose
tracked work, preview short prompts and settings, and approve separate agent
threads. Assessment also works without thread-launch tools. It routes to existing
skills without changing their workflows.

### Preservation and reporting

- Preserve conflicting local edits and source/name collisions; report them.
  Intentional changes to downloaded content become separately owned custom skills.
- Preserve installed skills removed upstream and warn when detected. Offline
  reconciliation cannot discover upstream removals.
- Removing a selection proposes deletion only of its previously managed copy,
  with preview and confirmation. Unattended runs preserve pending removals and
  report incomplete results. Modified copies remain conflicts.
- Leave unlisted local skills untouched and omit them from routine output.
- Continue independent installations after failures; summarize failures and
  return an unsuccessful result. Apply other configuration before skill sync.
- Already-installed selections should reconcile offline. Missing skills offline
  are visible failures. First-time runtime/CLI bootstrap may need network access.

### PowerShell execution policy

On Windows, PowerShell must allow locally generated scripts. If the default
policy blocks the skill sync hook, run
`Set-ExecutionPolicy -Scope Process RemoteSigned` in the PowerShell session
before running `chezmoi apply`. This setting expires when that session closes.

### State and recovery

Chezmoi diffs will always show the after-script because it runs on every apply.
Use `chezmoi diff --exclude scripts` or `chezmoi verify --exclude scripts` to
check only managed configuration files.

Local ownership and content hashes live at `~/.local/state/rig/skills.json`
(on Windows, below the user home as well). Keep this state device-local.
Reconciliation refuses concurrent writers. A crashed run may leave `skills.lock`
or a `.rig-*` directory under the installed skills root; inspect it before
removing the lock or recovering its `old/` backup. Do not blindly delete state:
it distinguishes managed installs from unrelated files.

Failures preserve existing content and return a nonzero exit code. Source
changes or local modifications require manual resolution. Normal sync does not
query upstream for deprecations; an explicit update reports a failed selection
and preserves the installed copy. Dry runs plan actions without fetching sources.

The manifest was seeded from 30 CLI-recorded selections. Skills without source
metadata remain installed and unlisted until classified. The earlier vendored
snapshots and brittle shell restore script have been removed; installed skills
are preserved. Project skills are not managed yet. Claude copy ownership is stored
separately in `~/.local/state/rig/claude-skills.json`. The earlier
`claude-links.json` is retained only to track old links awaiting migration or removal.

## Development checks

CI runs these checks on Linux and native Windows for pull requests and pushes
to `main`. Run the same checks from the repo root with uv and Python 3.12+:

```sh
uv sync
uv run ruff check
uv run ruff format --check
uv run ty check
uv run pytest
git diff --check
```

pytest runs the existing unittest tests and any new pytest tests. Tests use
temporary homes and mocked downloads, plus actual chezmoi and `rig`
integrations, a `uv tool install` from a temporary tagged Git repository, and a
real `rig self update` from one tagged build to the next. That test serves the
release response from a file through `RIG_RELEASES_URL` and installs tags from
the temporary repository through `RIG_RELEASE_SOURCE`; both are test hooks,
not user settings.
Locally, the integrations are skipped unless chezmoi, Git, and uv are
installed. In CI, they always run. On Windows, the integration test uses the same
PowerShell policy as `chezmoi apply`, and the ownership tests need permission
to create symlinks (Developer Mode or an elevated shell). Network installs are
a separate integration check.
