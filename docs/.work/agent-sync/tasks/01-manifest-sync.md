# Manifest-driven global skills

Status: resolved
Type: task

Implement the approved behavior in the root README using Python through uv,
Vercel's skills CLI, and chezmoi after-scripts. Initial destination is global
`.agents/skills`. Keep unclassified local skills unlisted. Verify in isolated
homes before enabling live reconciliation. Do not commit or push.

## Answer

Implemented `agents/skills.py`, `agents/skills.json`, and chezmoi after-scripts.
Removed vendored snapshots and legacy restore inputs without deleting installed
skills. The real CLI staging check, isolated chezmoi integration, and live sync
passed. Restored `ask-matt`; adopted other selected installations unchanged.
Native Windows execution remains a documented device check.
