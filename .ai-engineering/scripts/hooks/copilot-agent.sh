#!/usr/bin/env bash
# Copilot telemetry hook: emit agent_dispatched on postToolUse matching agent tools.
# Called by GitHub Copilot hooks (postToolUse event).
# Fail-open: exit 0 always — never blocks IDE.
set -uo pipefail

main() {
    # Read JSON from stdin (postToolUse event data)
    INPUT=$(cat)

    # Resolve project root from script location
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    AUDIT_LOG="$PROJECT_DIR/.ai-engineering/state/audit-log.ndjson"

    # Extract toolName from stdin JSON
    TOOL_NAME=""
    if command -v jq >/dev/null 2>&1; then
        TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // empty' 2>/dev/null)
    elif command -v python3 >/dev/null 2>&1; then
        TOOL_NAME=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('toolName', ''))
except Exception:
    pass
" 2>/dev/null)
    fi

    # Detect agent dispatch: match registered agent names OR generic "task"/"agent" patterns.
    # Copilot sends the agent's registered `name` as toolName (e.g., "Build", "Explorer").
    # Claude sends "task" or tools containing "agent" in the name.
    TOOL_LOWER=$(echo "$TOOL_NAME" | tr '[:upper:]' '[:lower:]')

    # Registered agent names from .github/agents/*.agent.md
    case "$TOOL_LOWER" in
        build|explorer|plan|review|verify|guard|guide|simplifier) ;;
        task) ;;
        *agent*) ;;
        *) return 0 ;;
    esac

    # Extract agent type: try toolArgs.agent_type first (Claude pattern),
    # then fall back to toolName itself (Copilot pattern).
    AGENT_TYPE=""
    if command -v jq >/dev/null 2>&1; then
        AGENT_TYPE=$(echo "$INPUT" | jq -r '.toolArgs | if type == "string" then fromjson else . end | .agent_type // empty' 2>/dev/null)
    elif command -v python3 >/dev/null 2>&1; then
        AGENT_TYPE=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    args = d.get('toolArgs', {})
    if isinstance(args, str):
        args = json.loads(args)
    print(args.get('agent_type', ''))
except Exception:
    pass
" 2>/dev/null)
    fi

    # Fallback: use toolName as agent type (Copilot sends agent name directly)
    if [ -z "$AGENT_TYPE" ]; then
        AGENT_TYPE="$TOOL_NAME"
    fi


    # Skip if no agent type extracted
    [ -z "$AGENT_TYPE" ] && return 0

    # Normalize: lowercase, strip existing ai-/ai: prefix, re-add ai- prefix
    AGENT_TYPE=$(echo "$AGENT_TYPE" | tr '[:upper:]' '[:lower:]')
    AGENT_TYPE="${AGENT_TYPE#ai-}"
    AGENT_TYPE="${AGENT_TYPE#ai:}"
    AGENT_TYPE="ai-${AGENT_TYPE}"

    # Git metadata (fail gracefully if not in a repo)
    BRANCH=$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    COMMIT=$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")

    # Timestamp: use stdin JSON timestamp if available, otherwise generate ISO-8601
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Emit NDJSON event to audit log
    if command -v jq >/dev/null 2>&1; then
        jq -n -c \
            --arg agent "$AGENT_TYPE" \
            --arg branch "$BRANCH" \
            --arg commit "$COMMIT" \
            --arg ts "$TIMESTAMP" \
            '{actor:"ai",agent:$agent,branch:$branch,commit_sha:$commit,detail:{agent:$agent},event:"agent_dispatched",source:"hook",timestamp:$ts}' \
            >> "$AUDIT_LOG" 2>/dev/null
    else
        printf '{"actor":"ai","agent":"%s","branch":"%s","commit_sha":"%s","detail":{"agent":"%s"},"event":"agent_dispatched","source":"hook","timestamp":"%s"}\n' \
            "$AGENT_TYPE" "$BRANCH" "$COMMIT" "$AGENT_TYPE" "$TIMESTAMP" >> "$AUDIT_LOG" 2>/dev/null
    fi
}

main || exit 0
exit 0
