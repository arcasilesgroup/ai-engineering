#!/usr/bin/env bash
# Copilot wrapper for instinct-observe.py.
# Usage: copilot-instinct-observe.sh pre|post
# Fail-open: exit 0 always -- never blocks IDE.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PHASE="${1:-post}"
INPUT=$(cat)
TRANSLATED=$(printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/copilot-adapter.py" 2>/dev/null) || TRANSLATED="{}"
if [ "$PHASE" = "pre" ]; then
  export CLAUDE_HOOK_EVENT_NAME="PreToolUse"
else
  export CLAUDE_HOOK_EVENT_NAME="PostToolUse"
fi
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PROJECT_DIR}"
export AIENG_HOOK_ENGINE="github_copilot"
printf '%s' "$TRANSLATED" | python3 "$SCRIPT_DIR/instinct-observe.py"
EXIT_CODE=$?
exit "$EXIT_CODE"
