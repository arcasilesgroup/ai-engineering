#!/usr/bin/env bash
# Scheduled wrapper for /ai-session-watch-sweep (spec-165).
#
# Cadence: weekly. Recommended cron: `0 4 * * 2` (Tuesday 04:00 UTC).
# Hard rules (inherited from the skill): NEVER auto-merge, NEVER auto-file
# work items. The consolidation always opens a draft PR for human review.
#
# This wrapper is the deterministic cron entrypoint. Unlike simplify-sweep,
# the session-watch --review consolidation is LLM-driven and has no
# deterministic `ai-eng` subcommand to run headless, so this wrapper only
# records the scheduled cycle (observability) — the actual review runs via
# the agent path (`/schedule weekly /ai-session-watch-sweep`, which invokes
# the skill through an agent). Never raises, never blocks the schedule.

set -euo pipefail

PROJECT_ROOT="${AIENG_PROJECT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$PROJECT_ROOT"

EVENTS_FILE="$PROJECT_ROOT/.ai-engineering/state/framework-events.ndjson"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

emit_event() {
  # Best-effort NDJSON append. Schema parity is not enforced here —
  # the spec-120 SQLite indexer handles malformed lines defensively.
  local outcome="$1"
  local detail="$2"
  if [ -w "$(dirname "$EVENTS_FILE")" ] || mkdir -p "$(dirname "$EVENTS_FILE")" 2>/dev/null; then
    printf '{"component":"scheduled.session-watch-sweep","kind":"framework_operation","operation":"session_watch_sweep_scheduled_run","outcome":"%s","detail":%s,"timestamp":"%s","schemaVersion":"1.0","source":"scheduled","engine":"cron","project":"ai-engineering"}\n' \
      "$outcome" "$detail" "$TS" >> "$EVENTS_FILE" 2>/dev/null || true
  fi
}

# The review is LLM-driven; the agent path (/schedule) performs it. This
# wrapper records the cycle so a missing agent run is observable.
emit_event "skipped" '{"reason":"requires_agent_review","via":"/schedule weekly /ai-session-watch-sweep"}'
exit 0
