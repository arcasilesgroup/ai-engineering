#!/usr/bin/env bash
# PostToolUse hook: Auto-format files after Edit/Write operations.
#
# Reads the tool result from stdin JSON and runs the appropriate formatter
# based on the file extension. Formatting failures never block the workflow.
#
# Supported formatters:
#   .cs        -> dotnet format
#   .ts/.tsx   -> prettier
#   .js/.jsx   -> prettier
#   .py        -> ruff format
#   .tf        -> terraform fmt
#
# Exit: Always 0 (formatting failure must not block)

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse stdin JSON
# ---------------------------------------------------------------------------
# The hook receives JSON on stdin with fields like tool_name, file_path, etc.
# We extract fields without requiring jq.
INPUT="$(cat)"

# Extract tool_name -- only act on Edit and Write tools
TOOL_NAME="$(echo "$INPUT" | grep -o '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

if [[ "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "Write" ]]; then
    exit 0
fi

# Extract file_path from the JSON
FILE_PATH="$(echo "$INPUT" | grep -o '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
    exit 0
fi

# ---------------------------------------------------------------------------
# Detect extension and run formatter
# ---------------------------------------------------------------------------
EXT="${FILE_PATH##*.}"

case "$EXT" in
    cs)
        # Find the nearest .csproj or .sln going up from the file
        DIR="$(dirname "$FILE_PATH")"
        PROJECT=""
        while [[ "$DIR" != "/" ]]; do
            # Prefer .csproj first, then .sln
            CSPROJ="$(find "$DIR" -maxdepth 1 -name '*.csproj' -print -quit 2>/dev/null || true)"
            if [[ -n "$CSPROJ" ]]; then
                PROJECT="$CSPROJ"
                break
            fi
            SLN="$(find "$DIR" -maxdepth 1 -name '*.sln' -print -quit 2>/dev/null || true)"
            if [[ -n "$SLN" ]]; then
                PROJECT="$SLN"
                break
            fi
            DIR="$(dirname "$DIR")"
        done
        if [[ -n "$PROJECT" ]]; then
            dotnet format "$PROJECT" --include "$FILE_PATH" 2>/dev/null || true
        fi
        ;;

    ts|tsx|js|jsx)
        npx prettier --write "$FILE_PATH" 2>/dev/null || true
        ;;

    py)
        ruff format "$FILE_PATH" 2>/dev/null || true
        ;;

    tf)
        terraform fmt "$FILE_PATH" 2>/dev/null || true
        ;;
esac

exit 0
