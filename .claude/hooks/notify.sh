#!/usr/bin/env bash
# Notification hook: Send desktop notification when a long operation completes.
#
# Detects the platform (macOS / Linux) and uses the appropriate notification
# mechanism. Notification failure never blocks the workflow.
#
# macOS: osascript display notification
# Linux: notify-send (if available)
#
# Exit: Always 0

set -euo pipefail

# ---------------------------------------------------------------------------
# Parse stdin JSON
# ---------------------------------------------------------------------------
INPUT="$(cat)"

# Extract tool_name for a meaningful notification message
TOOL_NAME="$(echo "$INPUT" | grep -o '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

if [[ -z "$TOOL_NAME" ]]; then
    TOOL_NAME="Operation"
fi

MESSAGE="$TOOL_NAME completed"

# ---------------------------------------------------------------------------
# Send notification based on platform
# ---------------------------------------------------------------------------
case "$(uname -s)" in
    Darwin)
        osascript -e "display notification \"$MESSAGE\" with title \"Claude Code\"" 2>/dev/null || true
        ;;
    Linux)
        if command -v notify-send &>/dev/null; then
            notify-send "Claude Code" "$MESSAGE" 2>/dev/null || true
        fi
        ;;
esac

exit 0
