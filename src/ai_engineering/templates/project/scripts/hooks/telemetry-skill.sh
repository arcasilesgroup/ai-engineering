#!/usr/bin/env bash
# Telemetry hook: emit skill_invoked event on PostToolUse(Skill).
# Called by Claude Code and GitHub Copilot hooks.
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

# Read JSON from stdin (PostToolUse event data)
INPUT=$(cat)

# Extract skill name using jq, fallback to python3
extract_skill() {
    if command -v jq >/dev/null 2>&1; then
        echo "$INPUT" | jq -r '.tool_input.skill // empty' 2>/dev/null
    elif command -v python3 >/dev/null 2>&1; then
        echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {})
    if isinstance(ti, str):
        import json as j
        ti = j.loads(ti)
    print(ti.get('skill', ''))
except Exception:
    pass
" 2>/dev/null
    fi
}

SKILL_NAME=$(extract_skill)

# Skip if no skill name extracted
[ -z "$SKILL_NAME" ] && exit 0

# Strip "ai-" prefix for canonical name (ai-plan → plan)
CANONICAL_NAME="${SKILL_NAME#ai-}"
# Also strip "ai:" prefix (ai:plan → plan)
CANONICAL_NAME="${CANONICAL_NAME#ai:}"

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

# Emit event — fail-open
ai-eng signals emit skill_invoked \
    --actor=ai \
    --source=hook \
    --detail="{\"skill\":\"${CANONICAL_NAME}\"}" \
    2>/dev/null || true

exit 0
