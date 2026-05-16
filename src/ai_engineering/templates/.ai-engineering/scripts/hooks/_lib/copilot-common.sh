#!/usr/bin/env bash
# spec-114 D-114-01: shared Bash lib for Copilot hook adapters.
#
# Sealed contract: imports nothing beyond Bash builtins + `jq`. The shell
# adapters source this file via a one-line preamble and use the four
# functions below to remove the boilerplate that previously lived inline
# in every copilot-*.sh.
#
# Functions:
#   read_stdin_payload [field]   -- read JSON from stdin into $PAYLOAD;
#                                   echo `field` (jq path) if provided.
#   emit_event KIND COMPONENT OUTCOME [DETAIL_JSON]
#                                -- append a canonical NDJSON entry to
#                                   .ai-engineering/state/framework-events.ndjson
#                                   with prev_event_hash chain pointer.
#   should_fail_open             -- install ERR trap so any unhandled error
#                                   returns exit 0 (D-105-09 fail-open).
#   log_to_stderr LEVEL MESSAGE  -- structured `[LEVEL] component: msg`
#                                   stderr line; never raises.
#
# Convention: callers set $COPILOT_COMPONENT (e.g. "hook.copilot-skill")
# before invoking emit_event/log_to_stderr so the component label is
# threaded through automatically. If unset, "hook.copilot-unknown" is used.

# --- helpers ---------------------------------------------------------------

# Resolve the project root from the script that sources us. Walks up from
# the sourcing script's directory looking for the .ai-engineering marker.
_copilot_common_project_root() {
    local script_dir="${1:-}"
    if [ -z "$script_dir" ]; then
        # Sourcing script's location: walk up from $BASH_SOURCE[1] when set.
        local caller="${BASH_SOURCE[1]:-}"
        if [ -n "$caller" ]; then
            script_dir="$(cd "$(dirname "$caller")" && pwd)"
        else
            script_dir="$(pwd)"
        fi
    fi
    # Hooks live at .ai-engineering/scripts/hooks/<name>.sh; the project root
    # is three levels up. We still walk to be defensive against being called
    # from a different layout.
    local current="$script_dir"
    for _ in 1 2 3 4 5 6; do
        if [ -d "$current/.ai-engineering" ]; then
            printf '%s\n' "$current"
            return 0
        fi
        local parent
        parent="$(dirname "$current")"
        [ "$parent" = "$current" ] && break
        current="$parent"
    done
    printf '%s\n' "$script_dir"
}

# --- 1. read_stdin_payload -------------------------------------------------

# Read JSON from stdin into the global $PAYLOAD. If `$1` is provided it is
# treated as a `jq` filter (e.g. `.toolName`) and the extracted string is
# echoed on stdout (empty when missing or when jq is unavailable).
read_stdin_payload() {
    local field="${1:-}"
    if [ -z "${PAYLOAD:-}" ]; then
        PAYLOAD=$(cat 2>/dev/null) || PAYLOAD=""
    fi
    [ -z "$field" ] && return 0
    if command -v jq >/dev/null 2>&1 && [ -n "$PAYLOAD" ]; then
        printf '%s' "$PAYLOAD" | jq -r "${field} // empty" 2>/dev/null || true
    fi
}

# --- 2. emit_event ---------------------------------------------------------

# Append a unified-schema NDJSON entry to framework-events.ndjson. Honours
# the spec-110 prev_event_hash chain pointer at root; produces nothing
# (returns 0) on any unrecoverable error so hooks remain fail-open.
#
# Args:  KIND COMPONENT OUTCOME [DETAIL_JSON]
# Env:   COPILOT_SESSION_ID, COPILOT_TRACE_ID, GITHUB_COPILOT_SESSION_ID,
#        GITHUB_COPILOT_TRACE_ID -- propagated into the entry when set.
emit_event() {
    command -v jq >/dev/null 2>&1 || return 0
    local kind="${1:-}" component="${2:-}" outcome="${3:-success}" detail="${4:-{\}}"
    [ -z "$kind" ] && return 0
    [ -z "$component" ] && component="${COPILOT_COMPONENT:-hook.copilot-unknown}"

    local project_root
    project_root="$(_copilot_common_project_root)"
    local events_path="$project_root/.ai-engineering/state/framework-events.ndjson"
    local events_dir
    events_dir="$(dirname "$events_path")"
    [ -d "$events_dir" ] || mkdir -p "$events_dir" 2>/dev/null || return 0

    local timestamp
    timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)" || timestamp="1970-01-01T00:00:00Z"
    local correlation_id="${COPILOT_TRACE_ID:-${GITHUB_COPILOT_TRACE_ID:-}}"
    if [ -z "$correlation_id" ]; then
        if command -v uuidgen >/dev/null 2>&1; then
            correlation_id="$(uuidgen 2>/dev/null | tr -d - | tr 'A-F' 'a-f')"
        else
            correlation_id="$(printf '%s%s' "$$" "$timestamp" | shasum 2>/dev/null | head -c 32)"
        fi
    fi
    local session_id="${COPILOT_SESSION_ID:-${GITHUB_COPILOT_SESSION_ID:-}}"
    local project_name
    project_name="$(basename "$project_root")"

    local prev_hash="null"
    if [ -f "$events_path" ]; then
        local last_line
        last_line="$(tail -n 1 "$events_path" 2>/dev/null | tr -d '\r')"
        if [ -n "$last_line" ]; then
            local hash
            local raw
            raw="$(printf '%s' "$last_line" | jq -c 'del(.prev_event_hash, .prevEventHash)' 2>/dev/null \
                | shasum -a 256 2>/dev/null)"
            # `shasum` prints "<hex>  -" — strip everything from the first space.
            hash="${raw%% *}"
            [ -n "$hash" ] && prev_hash="\"$hash\""
        fi
    fi

    local detail_json="$detail"
    printf '%s' "$detail_json" | jq -e . >/dev/null 2>&1 || detail_json="{}"

    local entry
    entry="$(jq -nc \
        --arg kind "$kind" \
        --arg engine "copilot" \
        --arg timestamp "$timestamp" \
        --arg component "$component" \
        --arg outcome "$outcome" \
        --arg correlationId "$correlation_id" \
        --arg schemaVersion "1.0" \
        --arg project "$project_name" \
        --arg source "hook" \
        --arg sessionId "$session_id" \
        --argjson detail "$detail_json" \
        --argjson prev_event_hash "$prev_hash" \
        '{kind:$kind,engine:$engine,timestamp:$timestamp,component:$component,
          outcome:$outcome,correlationId:$correlationId,schemaVersion:$schemaVersion,
          project:$project,source:$source,detail:$detail,prev_event_hash:$prev_event_hash}
         | if $sessionId == "" then . else . + {sessionId:$sessionId} end' 2>/dev/null)"
    [ -z "$entry" ] && return 0
    printf '%s\n' "$entry" >>"$events_path" 2>/dev/null || return 0
}

# --- 3. should_fail_open ---------------------------------------------------

# Install an ERR trap that exits 0 on unhandled error. Use at the top of a
# hook to guarantee D-105-09 fail-open semantics without manual `|| exit 0`
# guards on every line.
should_fail_open() {
    trap 'exit 0' ERR
    set +e
}

# --- 4. log_to_stderr ------------------------------------------------------

# Structured stderr logger. Format: `[LEVEL] component: message`.
# Never raises — silently drops if stderr is closed.
log_to_stderr() {
    local level="${1:-info}"
    local message="${2:-}"
    local component="${COPILOT_COMPONENT:-hook.copilot-unknown}"
    printf '[%s] %s: %s\n' "$level" "$component" "$message" >&2 2>/dev/null || true
}
