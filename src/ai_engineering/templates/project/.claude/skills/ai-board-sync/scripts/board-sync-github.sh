#!/usr/bin/env bash
# board-sync-github.sh -- Query GitHub Projects v2 for current sprint work item states.
#
# Usage:
#   bash board-sync-github.sh <project-number> --owner <org>
#
# The --owner value comes from github_project.owner in .ai-engineering/manifest.yml.
# Requires: gh CLI authenticated with project read scope.
# Cross-platform: bash 4+, macOS/Linux/WSL.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash board-sync-github.sh <project-number> --owner <org>" >&2
  exit 1
fi

PROJECT_NUMBER="$1"
OWNER=""

# Parse optional --owner flag
shift
while [[ $# -gt 0 ]]; do
  case "$1" in
    --owner) OWNER="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# Build the gh command
GH_ARGS=("project" "item-list" "$PROJECT_NUMBER" "--format" "json")
if [[ -n "$OWNER" ]]; then
  GH_ARGS+=("--owner" "$OWNER")
fi

# Fetch project items and summarize states
echo "Fetching items from project #${PROJECT_NUMBER}..."
ITEMS=$(gh "${GH_ARGS[@]}" 2>&1) || {
  echo "Error: Failed to query project. Check gh auth and project access." >&2
  echo "  Hint: gh auth login --scopes project" >&2
  exit 1
}

# Output a summary table of work item states
# TODO: Expand to filter by sprint iteration field if configured in manifest
echo "$ITEMS" | python3 -c "
import json, sys
from collections import Counter

data = json.load(sys.stdin)
items = data.get('items', [])
if not items:
    print('No items found in project.')
    sys.exit(0)

print(f'Total items: {len(items)}')
print()
statuses = Counter(
    item.get('status', '(none)') for item in items
)
print('Status breakdown:')
for status, count in sorted(statuses.items()):
    print(f'  {status}: {count}')
"
