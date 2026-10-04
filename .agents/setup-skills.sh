#!/usr/bin/env bash
# Restore global agent skills recorded by the Vercel `skills` CLI.
#
# Usage:
#   ./setup-skills.sh [path/to/.skill-lock.json]
#   ./setup-skills.sh --dry-run [path/to/.skill-lock.json]

set -euo pipefail

dry_run=false
if [[ "${1:-}" == "--dry-run" ]]; then
  dry_run=true
  shift
fi

lock_file="${1:-$HOME/.agents/.skill-lock.json}"

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required. Install it with your distribution's package manager." >&2
  exit 1
fi

if ! command -v bunx >/dev/null 2>&1; then
  echo "Error: bunx is required. Install Bun first: https://bun.sh" >&2
  exit 1
fi

if [[ ! -f "$lock_file" ]]; then
  echo "Error: lock file not found: $lock_file" >&2
  exit 1
fi

if ! jq -e '.version == 3 and (.skills | type == "object")' "$lock_file" >/dev/null; then
  echo "Error: expected a version-3 global .skill-lock.json: $lock_file" >&2
  exit 1
fi

mapfile -t agents < <(jq -r '.lastSelectedAgents[]? // empty' "$lock_file")
mapfile -t installs < <(
  jq -r '
    .skills
    | to_entries[]
    | select((.value.sourceUrl // .value.source // "") != "")
    | [.key, (.value.sourceUrl // .value.source)]
    | @tsv
  ' "$lock_file"
)

if (( ${#installs[@]} == 0 )); then
  echo "No skills found in $lock_file"
  exit 0
fi

echo "Restoring ${#installs[@]} global skill(s) from $lock_file"
if (( ${#agents[@]} > 0 )); then
  echo "Target agents: ${agents[*]}"
fi

for install in "${installs[@]}"; do
  IFS=$'\t' read -r skill source <<< "$install"
  command=(bunx skills@latest add "$source" --skill "$skill" --global --yes)
  if (( ${#agents[@]} > 0 )); then
    command+=(--agent "${agents[@]}")
  fi

  if [[ "$dry_run" == true ]]; then
    printf 'Would install: '
    printf '%q ' "${command[@]}"
    printf '\n'
  else
    printf '\nInstalling %s from %s\n' "$skill" "$source"
    "${command[@]}"
  fi
done

if [[ "$dry_run" == true ]]; then
  printf '\nDry run complete; no skills were installed.\n'
else
  printf '\nRestore complete. Check the result with: bunx skills@latest list --global\n'
fi
