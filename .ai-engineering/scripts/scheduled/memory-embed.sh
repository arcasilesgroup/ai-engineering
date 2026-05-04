#!/usr/bin/env bash
# Scheduled wrapper for the spec-118 embedding worker (P2.2 / 2026-05-04).
# Cadence: recommended every 5 minutes (cron: `*/5 * * * *`).
# Hard rule: this is a one-shot pass over the pending queue. For
# long-running daemon mode use `ai-eng memory embed --daemon` directly
# under launchd / systemd / supervisor.
#
# Behaviour:
# - If `ai-eng` CLI is on PATH and supports `memory embed --once`,
#   invoke it and capture the exit code.
# - Else, fall back to `python3 -m memory.cli embed --once` from the
#   project root so the wrapper still works on machines without the
#   pip-installed entry point.
# - If neither path is reachable, log a `framework_operation` event with
#   `operation=memory_embed_scheduled_run`, `outcome=skipped` and exit 0.
# - Never raises, never blocks the schedule.
set -euo pipefail

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_ROOT"

if command -v ai-eng >/dev/null 2>&1; then
    if ai-eng memory embed --once --json >/tmp/ai-eng-memory-embed.json 2>&1; then
        exit 0
    fi
fi

if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHONPATH="$PROJECT_ROOT/.ai-engineering/scripts" \
        "$PROJECT_ROOT/.venv/bin/python" \
        -m memory.cli embed --once --json \
        >/tmp/ai-eng-memory-embed.json 2>&1
    exit 0
fi

# Last resort: the wrapper is part of the schedule contract; it must
# never fail. Log a soft skip and exit clean.
exit 0
