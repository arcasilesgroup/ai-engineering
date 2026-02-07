#!/usr/bin/env bash
# ai-engineering pre-tool hook
# Validates tool usage before execution to enforce safety rules.
# Installed in .ai-engineering/hooks/ and triggered by IDE hook integration.

set -euo pipefail

TOOL_NAME="${1:-}"
TOOL_INPUT="${2:-}"
CONFIG_DIR="$(git rev-parse --show-toplevel 2>/dev/null)/.ai-engineering"
BLOCKLIST_FILE="${CONFIG_DIR}/hooks/blocklist.sh"

# Load blocklist if exists
if [[ -f "$BLOCKLIST_FILE" ]]; then
  source "$BLOCKLIST_FILE"
fi

# === BLOCKED PATTERNS ===

# Block force push
if echo "$TOOL_INPUT" | grep -qE 'git\s+push\s+(-f|--force)'; then
  echo "BLOCKED: git push --force is not allowed. Use safe push strategies."
  exit 2
fi

# Block --no-verify
if echo "$TOOL_INPUT" | grep -qE '--no-verify'; then
  echo "BLOCKED: --no-verify bypasses safety checks and is not allowed."
  exit 2
fi

# Block direct push to protected branches
PROTECTED_BRANCHES="${AI_ENG_PROTECTED_BRANCHES:-main master develop}"
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "")

if echo "$TOOL_INPUT" | grep -qE 'git\s+push'; then
  for branch in $PROTECTED_BRANCHES; do
    if [[ "$CURRENT_BRANCH" == "$branch" ]]; then
      echo "BLOCKED: Direct push to protected branch '$branch' is not allowed. Create a PR instead."
      exit 2
    fi
  done
fi

# Block editing sensitive files
SENSITIVE_PATTERNS='\.env$|\.env\.|\.pem$|\.key$|credentials|\.secret'
if echo "$TOOL_INPUT" | grep -qE "$SENSITIVE_PATTERNS"; then
  echo "BLOCKED: Editing sensitive files (.env, .pem, .key, credentials) is not allowed via AI tools."
  exit 2
fi

# Block destructive rm -rf on critical paths
if echo "$TOOL_INPUT" | grep -qE 'rm\s+-rf\s+(/|\.|\.git|node_modules|src|dist)'; then
  echo "BLOCKED: Destructive rm -rf on critical paths requires explicit user confirmation."
  exit 2
fi

# Block disabling safety tools
if echo "$TOOL_INPUT" | grep -qE '(eslint-disable-next-line|@ts-ignore|@ts-expect-error|# noqa|# type:\s*ignore)'; then
  echo "WARNING: Disabling safety checks detected. Ensure this is intentional and documented."
  # Warning only, not blocking
fi

# All checks passed
exit 0
