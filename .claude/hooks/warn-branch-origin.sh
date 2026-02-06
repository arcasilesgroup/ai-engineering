#!/usr/bin/env bash
# PreToolUse hook: Warn when creating a branch not based on the default or compliance branch.
#
# Reads stdin JSON to extract the command being run and checks if branch creation
# is based on a compliance branch (main, master, develop, dev/*, release/*, hotfix/*).
#
# This hook is ADVISORY ONLY — it warns but never blocks.
#
# Exit codes:
#   0 = allow the command (always)

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse stdin JSON
# ---------------------------------------------------------------------------
INPUT="$(cat)"

# Extract tool_name — only act on Bash tool
TOOL_NAME="$(echo "$INPUT" | grep -o '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

if [[ "$TOOL_NAME" != "Bash" ]]; then
    exit 0
fi

# Extract the command field from JSON
COMMAND="$(echo "$INPUT" | grep -o '"command"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Normalize: collapse whitespace
CMD_NORMALIZED="$(echo "$COMMAND" | tr '\n' ' ' | sed 's/  */ /g')"

# ---------------------------------------------------------------------------
# Check if this is a branch creation command
# ---------------------------------------------------------------------------

# Match: git checkout -b <name> [<base>] or git switch -c <name> [<base>]
if ! echo "$CMD_NORMALIZED" | grep -qE 'git\s+(checkout\s+-b|switch\s+-c)\s+'; then
    exit 0
fi

# ---------------------------------------------------------------------------
# Detect default branch
# ---------------------------------------------------------------------------
DEFAULT_BRANCH="$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || true)"
if [[ -z "$DEFAULT_BRANCH" ]]; then
    if git show-ref --verify --quiet refs/remotes/origin/main 2>/dev/null; then
        DEFAULT_BRANCH="main"
    elif git show-ref --verify --quiet refs/remotes/origin/master 2>/dev/null; then
        DEFAULT_BRANCH="master"
    else
        # Cannot detect default branch — skip check
        exit 0
    fi
fi

# ---------------------------------------------------------------------------
# Compliance branch check function
# ---------------------------------------------------------------------------
is_compliance_branch() {
    local BRANCH="$1"
    if echo "$BRANCH" | grep -qE "^(main|master|develop)$|^dev/|^release/|^hotfix/"; then
        return 0
    fi
    return 1
}

# ---------------------------------------------------------------------------
# Extract the base ref from the command
# ---------------------------------------------------------------------------

# git checkout -b <new-branch> [<base>]
# git switch -c <new-branch> [<base>]
# The base ref is the optional argument after the new branch name
BASE_REF=""

if echo "$CMD_NORMALIZED" | grep -qE 'git\s+checkout\s+-b\s+'; then
    # Extract: git checkout -b <name> <base>
    BASE_REF="$(echo "$CMD_NORMALIZED" | sed -E 's/.*git\s+checkout\s+-b\s+[^ ]+\s*//' | awk '{print $1}' || true)"
elif echo "$CMD_NORMALIZED" | grep -qE 'git\s+switch\s+-c\s+'; then
    # Extract: git switch -c <name> <base>
    BASE_REF="$(echo "$CMD_NORMALIZED" | sed -E 's/.*git\s+switch\s+-c\s+[^ ]+\s*//' | awk '{print $1}' || true)"
fi

# ---------------------------------------------------------------------------
# Evaluate and warn if needed
# ---------------------------------------------------------------------------

if [[ -n "$BASE_REF" ]]; then
    # Explicit base ref provided — check if it's a compliance branch
    if is_compliance_branch "$BASE_REF"; then
        exit 0  # Branching from a compliance branch is fine
    fi
    # Also check if the base ref matches the default branch
    if [[ "$BASE_REF" == "$DEFAULT_BRANCH" || "$BASE_REF" == "origin/$DEFAULT_BRANCH" ]]; then
        exit 0
    fi
    echo "WARNING: New branch is based on '$BASE_REF', not the default branch ($DEFAULT_BRANCH). Consider using /git branch for consistency." >&2
else
    # No explicit base — branch will be created from HEAD
    CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [[ -z "$CURRENT_BRANCH" ]]; then
        exit 0  # Detached HEAD or unknown state — skip
    fi
    if [[ "$CURRENT_BRANCH" == "$DEFAULT_BRANCH" ]]; then
        exit 0  # Creating from default branch — perfect
    fi
    if is_compliance_branch "$CURRENT_BRANCH"; then
        exit 0  # Creating from a compliance branch — acceptable
    fi
    echo "WARNING: New branch will be based on '$CURRENT_BRANCH', not the default branch ($DEFAULT_BRANCH). Consider using /git branch for consistency." >&2
fi

# Always allow — this hook is advisory only
exit 0
