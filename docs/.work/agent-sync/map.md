# Agent setup with chezmoi

## Notes

The standalone sync-tool proposal is scrapped. The interview approved a small
chezmoi wrapper around Vercel's skills CLI. The root
[README](../../../README.md) is the maintained reference for setup and decisions.

## Decisions-so-far

- Instructions already render from `agents/AGENTS.md` through chezmoi.
- Implemented [manifest-driven sync](tasks/01-manifest-sync.md): Python through
  uv, Bun, and a shared manifest targeting global `.agents/skills` initially.
- Adopted 29 installed selections and restored missing `ask-matt`; all 154
  previously installed files were verified unchanged.
- Apply restores missing skills and refreshes custom skills. Downloaded updates
  and Git publication remain explicit.
- Earlier standalone-tool and snapshot decisions are superseded by the README.

## Fog

- Classify installed skills without upstream metadata.
- Test the generated PowerShell hook on an actual native Windows device.
- Future Claude destination support remains deferred.
