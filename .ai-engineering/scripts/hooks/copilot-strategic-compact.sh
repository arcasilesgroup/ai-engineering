#!/usr/bin/env bash
# Copilot wrapper for strategic-compact.py.
# Fail-open: exit 0 always -- never blocks IDE.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
INPUT=$(cat)
TRANSLATED=$(printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/copilot-adapter.py" 2>/dev/null) || TRANSLATED="{}"
export CLAUDE_HOOK_EVENT_NAME="PreToolUse"
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PROJECT_DIR}"
export AIENG_HOOK_ENGINE="github_copilot"
printf '%s' "$TRANSLATED" | python3 "$SCRIPT_DIR/strategic-compact.py"
EXIT_CODE=$?
exit "$EXIT_CODE"
