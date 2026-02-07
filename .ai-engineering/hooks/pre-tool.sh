#!/usr/bin/env bash
# ai-engineering pre-tool hook
# Validates tool usage before execution to enforce safety rules.
# Reads JSON from stdin (Claude Code hook protocol).

set -euo pipefail

# --- Read JSON from stdin ---
INPUT="$(cat)"

TOOL_NAME="$(echo "$INPUT" | grep -o '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"
COMMAND="$(echo "$INPUT" | grep -o '"command"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"
FILE_PATH="$(echo "$INPUT" | grep -o '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

# --- Load blocklist if exists ---
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
CONFIG_DIR="${PROJECT_ROOT}/.ai-engineering"
BLOCKLIST_FILE="${CONFIG_DIR}/hooks/blocklist.sh"

if [[ -f "$BLOCKLIST_FILE" ]]; then
  source "$BLOCKLIST_FILE"
fi

# ============================================================
# Bash tool checks
# ============================================================
if [[ "$TOOL_NAME" == "Bash" && -n "$COMMAND" ]]; then

  # Block force push
  if echo "$COMMAND" | grep -qE 'git\s+push\s+(-f|--force)'; then
    echo "BLOCKED: git push --force is not allowed. Use safe push strategies."
    exit 2
  fi

  # Block --no-verify
  if echo "$COMMAND" | grep -qE '\-\-no-verify'; then
    echo "BLOCKED: --no-verify bypasses safety checks and is not allowed."
    exit 2
  fi

  # Block direct push to protected branches
  PROTECTED_BRANCHES="${AI_ENG_PROTECTED_BRANCHES:-main master develop}"
  CURRENT_BRANCH="$(git branch --show-current 2>/dev/null || echo "")"

  if echo "$COMMAND" | grep -qE 'git\s+push'; then
    for branch in $PROTECTED_BRANCHES; do
      if [[ "$CURRENT_BRANCH" == "$branch" ]]; then
        echo "BLOCKED: Direct push to protected branch '$branch' is not allowed. Create a PR instead."
        exit 2
      fi
    done
  fi

  # Block destructive rm -rf on critical paths
  if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+(/|\.|\.git|node_modules|src|dist)'; then
    echo "BLOCKED: Destructive rm -rf on critical paths requires explicit user confirmation."
    exit 2
  fi

  # Block git branch -D / --delete --force (force delete branch)
  if echo "$COMMAND" | grep -qE 'git\s+branch\s+(-D|--delete\s+--force)'; then
    echo "BLOCKED: Force branch delete requires explicit user confirmation."
    exit 2
  fi

  # Block git checkout . / git restore . (discard all changes)
  if echo "$COMMAND" | grep -qE 'git\s+(checkout|restore)\s+(\.|--\s+\.)'; then
    echo "BLOCKED: Discarding all changes requires explicit user confirmation."
    exit 2
  fi

  # Block DROP TABLE / DROP DATABASE
  if echo "$COMMAND" | grep -qiE 'DROP\s+(TABLE|DATABASE)'; then
    echo "BLOCKED: DROP TABLE/DATABASE is not allowed via AI tools."
    exit 2
  fi

fi

# ============================================================
# Edit / Write tool checks (file sensitivity)
# ============================================================
if [[ "$TOOL_NAME" == "Edit" || "$TOOL_NAME" == "Write" ]]; then

  SENSITIVE_PATTERNS='\.env$|\.env\.|\.pem$|\.key$|credentials|\.secret'
  if [[ -n "$FILE_PATH" ]] && echo "$FILE_PATH" | grep -qE "$SENSITIVE_PATTERNS"; then
    echo "BLOCKED: Editing sensitive files (.env, .pem, .key, credentials) is not allowed via AI tools."
    exit 2
  fi

fi

# ============================================================
# Universal checks (all tools)
# ============================================================

# Warn on lint-disable patterns (advisory only, never blocks)
INPUT_TEXT="${COMMAND}${FILE_PATH}"
if echo "$INPUT_TEXT" | grep -qE '(eslint-disable|@ts-ignore|@ts-expect-error|# noqa|# type:\s*ignore)' 2>/dev/null; then
  echo "WARNING: Disabling safety checks detected. Ensure this is intentional and documented."
fi

# All checks passed
exit 0
