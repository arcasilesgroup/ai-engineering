#!/usr/bin/env bash
# Telemetry hook: emit session lifecycle events.
# Usage: telemetry-session.sh [end]
# Called by Claude Code (Stop) and GitHub Copilot (sessionEnd) hooks.
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

MODE="${1:-end}"

# Read JSON from stdin if available (hook event data)
INPUT=""
if [ ! -t 0 ]; then
    INPUT=$(cat)
fi

# Resolve project root
ROOT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Activate venv if present
if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.venv/bin/activate" 2>/dev/null
elif [ -f "$ROOT_DIR/.venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.venv/Scripts/activate" 2>/dev/null
fi

case "$MODE" in
    end)
        ai-eng signals emit session_end \
            --actor=ai-session \
            --source=hook \
            --detail='{"type":"session_end"}' \
            2>/dev/null || true
        ;;
    *)
        # Unknown mode — skip silently
        ;;
esac

exit 0
