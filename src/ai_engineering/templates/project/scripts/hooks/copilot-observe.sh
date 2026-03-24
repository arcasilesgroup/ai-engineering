#!/usr/bin/env bash
# Copilot wrapper for observe.py: record tool usage observations.
# Called by GitHub Copilot hooks (preToolCall and postToolCall events).
# Translates Copilot JSON field names to Claude Code convention, then delegates.
# Fail-open: exit 0 always — never blocks IDE.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read Copilot JSON from stdin
INPUT=$(cat)

# Detect Copilot event name from the JSON payload or wrapper invocation context.
# Copilot sends event type in the JSON; map to Claude Code equivalent.
COPILOT_EVENT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    # Copilot may include event type; detect from available fields
    if 'toolResult' in d or 'output' in d:
        print('PostToolUse')
    else:
        print('PreToolUse')
except Exception:
    print('PreToolUse')
" 2>/dev/null) || COPILOT_EVENT="PreToolUse"

# Translate Copilot field names to Claude Code convention:
#   Copilot: { "toolName": "...", "toolArgs": {...}, "toolResult": "..." }
#   Claude:  { "tool_name": "...", "tool_input": {...}, "tool_output": "..." }
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
        elif k == 'toolResult':
            out['tool_output'] = v
        else:
            out[k] = v
    json.dump(out, sys.stdout, separators=(',', ':'))
except Exception:
    sys.stdout.write(json.dumps({}))
" 2>/dev/null) || TRANSLATED="{}"

# Map Copilot event to Claude Code event name
export CLAUDE_HOOK_EVENT_NAME="$COPILOT_EVENT"

# Pipe translated input to Python script, preserve exit code
echo "$TRANSLATED" | python3 "$SCRIPT_DIR/observe.py"
EXIT_CODE=$?

exit "$EXIT_CODE"
