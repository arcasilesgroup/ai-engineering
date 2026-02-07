#!/usr/bin/env bash
# ai-engineering branch origin warning hook
# Advisory hook — warns when creating a branch from a non-compliance branch.
# Always exits 0 (never blocks).

set -euo pipefail

# --- Read JSON from stdin ---
INPUT="$(cat)"

TOOL_NAME="$(echo "$INPUT" | grep -o '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"
COMMAND="$(echo "$INPUT" | grep -o '"command"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

# Only check Bash commands that create branches
if [[ "$TOOL_NAME" != "Bash" ]]; then
  exit 0
fi

if ! echo "$COMMAND" | grep -qE 'git\s+(checkout\s+-b|switch\s+-c|branch\s+[^-])'; then
  exit 0
fi

# --- Detect default branch (3-tier fallback) ---
DEFAULT_BRANCH=""

# Tier 1: symbolic-ref
DEFAULT_BRANCH="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || true)"

# Tier 2: show-ref for common names
if [[ -z "$DEFAULT_BRANCH" ]]; then
  if git show-ref --verify --quiet refs/remotes/origin/main 2>/dev/null; then
    DEFAULT_BRANCH="main"
  elif git show-ref --verify --quiet refs/remotes/origin/master 2>/dev/null; then
    DEFAULT_BRANCH="master"
  fi
fi

# Tier 3: gh/az CLI
if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="$(gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name' 2>/dev/null || true)"
fi

if [[ -z "$DEFAULT_BRANCH" ]]; then
  DEFAULT_BRANCH="main"
fi

# --- Check current branch ---
CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || echo "")"

# Compliance branches: default, develop, release/*, hotfix/*
is_compliance_branch() {
  local branch="$1"
  case "$branch" in
    "$DEFAULT_BRANCH"|develop|development|staging)
      return 0 ;;
    release/*|hotfix/*)
      return 0 ;;
    *)
      return 1 ;;
  esac
}

if [[ -n "$CURRENT_BRANCH" ]] && ! is_compliance_branch "$CURRENT_BRANCH"; then
  echo "WARNING: Creating a branch from '$CURRENT_BRANCH' (non-compliance branch)."
  echo "  Consider branching from '$DEFAULT_BRANCH' instead to avoid merge complications."
fi

# Advisory only — never block
exit 0
