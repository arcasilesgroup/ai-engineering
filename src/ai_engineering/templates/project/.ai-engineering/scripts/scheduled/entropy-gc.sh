#!/usr/bin/env bash
# Scheduled wrapper for /ai-entropy-gc (spec-121).
#
# Cadence: weekly. Recommended cron: `0 4 * * 1` (Monday 04:00 UTC).
# Hard rule (inherited from the skill): NEVER auto-merge. Always opens
# a draft PR for human review.
#
# This wrapper exists so the schedule layer (cron, /schedule skill,
# launchd, systemd timer) has a single deterministic entrypoint instead
# of invoking a slash command directly.
#
# Behaviour:
# - If `ai-eng` CLI is on PATH and supports `simplify --conservative`,
#   invoke it and capture exit code.
# - Else, log a `framework_operation` event with
#   `operation=entropy_gc_scheduled_run`, `outcome=skipped` and exit 0.
# - Never raises, never blocks the schedule.

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
    printf '{"component":"scheduled.entropy-gc","kind":"framework_operation","operation":"entropy_gc_scheduled_run","outcome":"%s","detail":%s,"timestamp":"%s","schemaVersion":"1.0","source":"scheduled","engine":"cron","project":"ai-engineering"}\n' \
      "$outcome" "$detail" "$TS" >> "$EVENTS_FILE" 2>/dev/null || true
  fi
}

if ! command -v ai-eng >/dev/null 2>&1; then
  emit_event "skipped" '{"reason":"ai-eng_not_on_path"}'
  exit 0
fi

# Conservative simplify; rely on the skill's PR-opening logic.
if ai-eng simplify --conservative --no-pr 2>/dev/null; then
  emit_event "success" '{"mode":"conservative","pr":"deferred_to_skill"}'
else
  emit_event "failure" '{"mode":"conservative"}'
fi
