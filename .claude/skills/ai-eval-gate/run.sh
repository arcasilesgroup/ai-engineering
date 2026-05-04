#!/usr/bin/env bash
# spec-119 /ai-eval-gate runtime shim. Dispatches to the Python entry
# script (_entry.py) which in turn invokes the engine under
# src/ai_engineering/eval/. The skill is self-contained: SKILL.md +
# _entry.py + run.sh.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENTRY="${SKILL_DIR}/_entry.py"

if [[ ! -f "$ENTRY" ]]; then
    echo "missing entry script: $ENTRY" >&2
    exit 2
fi

uv run python "$ENTRY" "$@"
