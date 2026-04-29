#!/usr/bin/env bash
# Copilot wrapper for instinct-observe.py.
# Usage: copilot-instinct-observe.sh pre|post
# Fail-open: exit 0 always -- never blocks IDE.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PHASE="${1:-post}"
. "$SCRIPT_DIR/_lib/copilot-runtime.sh"
INPUT=$(cat)
TRANSLATED=$(printf '%s' "$INPUT" | copilot_framework_python_script "$PROJECT_DIR" "$SCRIPT_DIR/copilot-adapter.py" 2>/dev/null) || TRANSLATED="{}"
[ "$PHASE" = "pre" ] && export CLAUDE_HOOK_EVENT_NAME="PreToolUse" || export CLAUDE_HOOK_EVENT_NAME="PostToolUse"
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PROJECT_DIR}"
export AIENG_HOOK_ENGINE="github_copilot"
printf '%s' "$TRANSLATED" | copilot_framework_python_script "$PROJECT_DIR" "$SCRIPT_DIR/instinct-observe.py" || true
exit 0
