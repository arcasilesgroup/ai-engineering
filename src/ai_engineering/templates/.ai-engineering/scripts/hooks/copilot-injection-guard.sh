#!/usr/bin/env bash
# Copilot wrapper for prompt-injection-guard.py: scan tool inputs for injection.
# Called by GitHub Copilot hooks (preToolCall event).
# Translates Copilot JSON field names to Claude Code convention, then delegates.
# MUST preserve exit code 2 for blocking — non-fail-open.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read Copilot JSON from stdin
INPUT=$(cat)

# Translate Copilot field names to Claude Code convention:
#   Copilot: { "toolName": "...", "toolArgs": {...} }
#   Claude:  { "tool_name": "...", "tool_input": {...} }
TRANSLATED=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    out = {}
    for k, v in d.items():
        if k == 'toolName':
            out['tool_name'] = v
        elif k == 'toolArgs':
            out['tool_input'] = v if isinstance(v, dict) else json.loads(v) if isinstance(v, str) else v
        else:
            out[k] = v
    json.dump(out, sys.stdout, separators=(',', ':'))
except Exception:
    sys.stdout.write(json.dumps({}))
" 2>/dev/null) || TRANSLATED="{}"

# Map Copilot event to Claude Code event name
export CLAUDE_HOOK_EVENT_NAME="PreToolUse"

# Pipe translated input to Python script, preserve exit code (2 = block)
echo "$TRANSLATED" | python3 "$SCRIPT_DIR/prompt-injection-guard.py"
EXIT_CODE=$?

exit "$EXIT_CODE"
