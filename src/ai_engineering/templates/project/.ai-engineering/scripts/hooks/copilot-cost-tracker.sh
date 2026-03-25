#!/usr/bin/env bash
# Copilot wrapper for cost-tracker.py: track token usage and estimate costs.
# Called by GitHub Copilot hooks (agentTurnEnd event).
# Translates Copilot JSON field names to Claude Code convention, then delegates.
# Fail-open: exit 0 always — never blocks IDE.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read Copilot JSON from stdin
INPUT=$(cat)

# Translate Copilot field names to Claude Code convention:
#   Copilot agentTurnEnd provides usage/token data; map to Claude Stop event shape.
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
export CLAUDE_HOOK_EVENT_NAME="Stop"

# Pipe translated input to Python script, preserve exit code
echo "$TRANSLATED" | python3 "$SCRIPT_DIR/cost-tracker.py"
EXIT_CODE=$?

exit "$EXIT_CODE"
