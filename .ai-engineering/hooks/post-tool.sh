#!/usr/bin/env bash
# ai-engineering post-tool hook
# Runs after tool execution for automated quality actions.
# Reads JSON from stdin (Claude Code hook protocol).

set -euo pipefail

# --- Read JSON from stdin ---
INPUT="$(cat)"

TOOL_NAME="$(echo "$INPUT" | grep -o '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"
FILE_PATH="$(echo "$INPUT" | grep -o '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

# ============================================================
# Post Edit/Write actions only
# ============================================================
if [[ "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "Write" ]]; then
  exit 0
fi

if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# --- Check for hardcoded secrets ---
if grep -qE '(password|secret|token|api[_-]?key)\s*[:=]\s*["\x27][^\x27"]{8,}' "$FILE_PATH" 2>/dev/null; then
  echo "WARNING: Possible hardcoded secret detected in $FILE_PATH. Please review."
fi

# --- Auto-format by extension (silent, never blocks) ---
EXT="${FILE_PATH##*.}"
case "$EXT" in
  ts|tsx|js|jsx)
    npx prettier --write "$FILE_PATH" 2>/dev/null || true
    ;;
  py)
    ruff format "$FILE_PATH" 2>/dev/null || true
    ;;
  cs)
    DIR="$(dirname "$FILE_PATH")"
    while [[ "$DIR" != "/" ]]; do
      PROJECT=$(find "$DIR" -maxdepth 1 \( -name "*.csproj" -o -name "*.sln" \) 2>/dev/null | head -1)
      if [[ -n "$PROJECT" ]]; then
        dotnet format "$PROJECT" --include "$FILE_PATH" 2>/dev/null || true
        break
      fi
      DIR="$(dirname "$DIR")"
    done
    ;;
  tf)
    terraform fmt "$FILE_PATH" 2>/dev/null || true
    ;;
esac

# All post-actions complete
exit 0
