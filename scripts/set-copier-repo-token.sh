#!/usr/bin/env bash

set -euo pipefail

readonly secret_name="PAT_WEEKLY_UPDATE"

command -v gh >/dev/null || {
  echo "error: gh is required" >&2
  exit 2
}

gh auth status >/dev/null
owner="${1:-$(gh api user --jq .login)}"

if [[ -n "${PAT_WEEKLY_UPDATE:-}" ]]; then
  token=$PAT_WEEKLY_UPDATE
else
  read -rsp "Token for ${secret_name}: " token
  echo
fi

if [[ -z "$token" ]]; then
  echo "error: token must not be empty" >&2
  exit 2
fi

mapfile -t repositories < <(
  gh repo list "$owner" \
    --visibility public \
    --limit 1000 \
    --json isArchived,isFork,nameWithOwner \
    --jq '.[] | select((.isArchived | not) and (.isFork | not)) | .nameWithOwner'
)

copier_repositories=0
failures=0

for repository in "${repositories[@]}"; do
  if ! gh api --silent "repos/${repository}/contents/.copier-answers.yml" \
    >/dev/null 2>&1; then
    continue
  fi

  copier_repositories=$((copier_repositories + 1))
  echo "Setting ${secret_name} for ${repository}"
  if ! printf '%s' "$token" | gh secret set "$secret_name" --repo "$repository"; then
    echo "error: failed to set ${secret_name} for ${repository}" >&2
    failures=$((failures + 1))
  fi
done

unset token

if ((failures > 0)); then
  echo "Failed to update ${failures} of ${copier_repositories} Copier repositories." >&2
  exit 1
fi

echo "Updated ${copier_repositories} public Copier repositories owned by ${owner}."
