#!/usr/bin/env bash
# Copilot wrapper for telemetry-skill.py: emit skill_invoked on userPromptSubmitted.
# Called by GitHub Copilot hooks (userPromptSubmitted event).
# Translates Copilot JSON field names to Claude Code convention, then delegates.
# Fail-open: exit 0 always — never blocks IDE.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read Copilot JSON from stdin
INPUT=$(cat)

# Translate Copilot field names to Claude Code convention:
#   Copilot: { "prompt": "..." }  ->  same (field name matches)
# No field translation needed for telemetry-skill; prompt field is identical.

# Map Copilot event to Claude Code event name
export CLAUDE_HOOK_EVENT_NAME="UserPromptSubmit"

# Pipe translated input to Python script, preserve exit code
echo "$INPUT" | python3 "$SCRIPT_DIR/telemetry-skill.py"
EXIT_CODE=$?

exit "$EXIT_CODE"
