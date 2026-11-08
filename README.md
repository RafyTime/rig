# Rig

Personal configuration shared across Fedora and native Windows using
[chezmoi](https://www.chezmoi.io/). Start here when working on this repo or
setting up another device.

## Current setup

- `.chezmoiroot` selects `home/` as the managed source. Other repo files are not
  deployed directly.
- `agents/AGENTS.md` is the canonical personal instructions file. Templates
  render followers at `~/.agents/AGENTS.md`, `~/.codex/AGENTS.md`, and
  `~/.cursor/rules/personal.mdc` (always applied), and `~/.claude/CLAUDE.md`.
- Codex and Cursor share global skills in `~/.agents/skills/`.
- `zed/` contains reference settings, not yet managed by chezmoi.

The current Fedora machine's local chezmoi config sets
`sourceDir = "/home/lplata/Code/rig"`. Device-specific paths belong in local
configuration. The Codex template currently assumes default `~/.codex`;
custom `CODEX_HOME` support is not implemented.

## Daily workflow

Edit `agents/AGENTS.md`, then run from any directory:

```sh
chezmoi diff       # Preview installed changes
chezmoi apply      # Apply locally
chezmoi push       # Stage, commit, and push repo changes intentionally
```

On another device, `chezmoi update` pulls and applies. To preview first, use
`chezmoi update --apply=false`, then `chezmoi diff` and `chezmoi apply`.
Automatic commits, pushes, and background sync are disabled. Agents must not
commit or push unless explicitly requested.

## Another device

Install chezmoi, Git, uv, and Bun; authenticate with the Git host, then:

```sh
chezmoi init <rig-clone-url>
chezmoi diff
chezmoi apply
```

`chezmoi source-path` shows the effective `home/` source directory. Clone
locations may differ between devices. Verify Cursor's personal rule in a fresh
chat after applying. If selected skills already exist on that device, first use the adoption command below.

## Skills

Chezmoi runs `agents/skills.py sync` after applying configuration, on every
apply. The Python wrapper runs through **uv** and downloads through **Bun**.
Fedora execution is tested; the Windows PowerShell hook still needs testing on
an actual Windows device. Downloads use `skills@latest`; ordinary sync still
leaves installed downloaded versions unchanged.

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

Sources beginning with `./` are local skill containers relative to rig. Each
selected name maps to `<source>/<name>/SKILL.md`. Other sources are downloaded
through the CLI. Local sources refresh on apply; remote updates remain explicit.
From the repo root:

```sh
uv run --script agents/skills.py sync --dry-run  # Plan without writes/downloads
uv run update-skills.py                       # Explicitly refresh selected skills
uv run update-skills.py --dry-run             # Plan an update without downloading
```

On an existing device, adopt matching CLI-managed installations once:

```sh
uv run --script agents/skills.py sync --adopt-existing --dry-run
uv run --script agents/skills.py sync --adopt-existing
```

Adoption trusts current installed contents as the baseline when the existing
CLI lock identifies the selected source; it cannot establish whether those
contents were modified before adoption. Unknown-origin collisions are preserved.
After adoption, use the wrapper's update command rather than the global CLI
updater, which does not share the wrapper's ownership state. Downloads use the
CLI's project scope in a temporary directory before publishing global files;
the CLI's global lock file is no longer the shared inventory.

Downloads are batched by source, with one CLI call per downloaded source during
an update. Each requested skill is verified independently, and
unchanged contents are reported as `UNCHANGED` without replacing installed
files. Missing selections are reported individually; a failed CLI call preserves
all installations from that source while other sources continue.
Normal CLI output is hidden behind one progress line per source. Per-skill
results appear together at the end, with captured CLI diagnostics for failures.

- One manifest selects sources and names for downloaded and custom skills.
  Add shared skills there; direct CLI installs remain local until selected.
- Downloaded contents stay upstream, outside rig. Custom skill sources live in
  rig and use the same selection and installation workflow.
- Reconcile on every apply: install missing selections and refresh custom
  skills from rig. Leave existing downloaded versions unchanged.
- A separate explicit command updates only selected downloaded skills.
  `chezmoi update` means pull rig and apply, not refresh upstream skills.
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
3. Run `uv run --script agents/skills.py sync --adopt-existing --dry-run`, then
   run it without `--dry-run`. This explicitly transfers ownership only when the
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

### Preservation and reporting

- Preserve conflicting local edits and source/name collisions; report them.
  Intentional changes to downloaded content become separately owned custom skills.
- Preserve installed skills removed upstream and warn when detected. Offline
  reconciliation cannot discover upstream removals.
- Removing a selection proposes deletion only of its previously managed copy,
  with preview and confirmation. Unattended runs preserve pending removals and
  report incomplete results. Modified copies remain conflicts.
- Report unlisted local skills informationally and leave them untouched.
- Continue independent installations after failures; summarize failures and
  return an unsuccessful result. Apply other configuration before skill sync.
- Already-installed selections should reconcile offline. Missing skills offline
  are visible failures. First-time runtime/CLI bootstrap may need network access.

### State, recovery, and checks

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

Run checks from the repo root:

```sh
uv run python -m unittest discover -s tests -v
uvx ruff check agents/skills.py update-skills.py tests
uvx ruff format --check agents/skills.py update-skills.py tests
git diff --check
```

Tests use temporary homes and mocked downloads, plus an actual chezmoi apply
integration when chezmoi and uv are installed. Network installs and native Windows
execution are separate integration checks.
