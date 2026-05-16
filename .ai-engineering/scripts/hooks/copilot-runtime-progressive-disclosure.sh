#!/usr/bin/env bash
# Copilot wrapper for runtime-progressive-disclosure.py (userPromptSubmitted).
# Surfaces top-K relevant skills via additionalContext. Fail-open.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
. "$SCRIPT_DIR/_lib/copilot-runtime.sh"

INPUT=$(cat)
TRANSLATED=$(printf '%s' "$INPUT" | copilot_framework_python_script "$PROJECT_DIR" "$SCRIPT_DIR/copilot-adapter.py" 2>/dev/null) || TRANSLATED="{}"

export CLAUDE_HOOK_EVENT_NAME="UserPromptSubmit"
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PROJECT_DIR}"
export AIENG_HOOK_ENGINE="github_copilot"

printf '%s' "$TRANSLATED" | copilot_framework_python_script "$PROJECT_DIR" "$SCRIPT_DIR/runtime-progressive-disclosure.py" || true
exit 0
