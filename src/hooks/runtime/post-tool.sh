#!/usr/bin/env bash
# ai-engineering post-tool hook
# Runs after tool execution for automated quality actions.

set -euo pipefail

TOOL_NAME="${1:-}"
TOOL_INPUT="${2:-}"
TOOL_OUTPUT="${3:-}"

# === POST-EDIT ACTIONS ===

# After file edits, check for common issues
if [[ "$TOOL_NAME" == "Edit" || "$TOOL_NAME" == "Write" ]]; then
  FILE_PATH=$(echo "$TOOL_INPUT" | grep -oE '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*"file_path"\s*:\s*"//;s/"//')

  if [[ -n "$FILE_PATH" && -f "$FILE_PATH" ]]; then
    # Check for hardcoded secrets patterns
    if grep -qE '(password|secret|token|api[_-]?key)\s*[:=]\s*["\x27][^"\x27]{8,}' "$FILE_PATH" 2>/dev/null; then
      echo "WARNING: Possible hardcoded secret detected in $FILE_PATH. Please review."
    fi
  fi
fi

# All post-actions complete
exit 0
