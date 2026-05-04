#!/usr/bin/env bash
# Copilot wrapper for memory-stop.py (sessionEnd).
# Persists the current session as an episode in memory.db. Fail-open.
# Mirrors the canonical memory-stop.py contract; kept as a thin shell
# wrapper so .github/hooks/hooks.json can wire the Bash + PowerShell
# halves uniformly.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
. "$SCRIPT_DIR/_lib/copilot-runtime.sh"

INPUT=$(cat)
TRANSLATED=$(printf '%s' "$INPUT" | copilot_framework_python_script "$PROJECT_DIR" "$SCRIPT_DIR/copilot-adapter.py" 2>/dev/null) || TRANSLATED="{}"

export CLAUDE_HOOK_EVENT_NAME="Stop"
export CLAUDE_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PROJECT_DIR}"
export AIENG_HOOK_ENGINE="github_copilot"

printf '%s' "$TRANSLATED" | copilot_framework_python_script "$PROJECT_DIR" "$SCRIPT_DIR/memory-stop.py" || true
exit 0
