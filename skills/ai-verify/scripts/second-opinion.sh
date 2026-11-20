#!/usr/bin/env bash
# Spawn an independent, read-only reviewer (a fresh agent session) to review a change.
#
# Usage: second-opinion.sh <packet-path> [--model <model>]
#
# Prints the reviewer's report to stdout and also writes it next to the packet
# as <packet-basename>.review.md so it survives for later reference.
#
# The reviewer gets Read/Grep/Glob only. It cannot edit, run commands, or reach
# MCP servers, so bypassing its permission prompts is safe -- there is nothing
# destructive in its toolset. This matters: a review that stops halfway to ask
# for permission just hangs the parent session.

set -uo pipefail

PACKET="${1:-}"
shift || true

if [[ -z "$PACKET" ]]; then
  echo "error: no packet path given. Usage: second-opinion.sh <packet-path> [--model <model>]" >&2
  exit 2
fi

if [[ ! -f "$PACKET" ]]; then
  echo "error: packet not found: $PACKET" >&2
  exit 2
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "error: 'claude' is not on PATH; cannot spawn a reviewer." >&2
  exit 127
fi

# Resolve to an absolute path so the reviewer reads exactly this file rather
# than globbing for something with a similar name.
PACKET="$(cd "$(dirname "$PACKET")" && pwd)/$(basename "$PACKET")"
OUT="${PACKET%.md}.review.md"

MODEL_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model) MODEL_ARGS+=(--model "$2"); shift 2 ;;
    *) echo "error: unknown argument: $1" >&2; exit 2 ;;
  esac
done

claude -p "Read $PACKET and follow its instructions exactly." \
  --tools "Read,Grep,Glob" \
  --permission-mode bypassPermissions \
  --strict-mcp-config \
  --no-session-persistence \
  "${MODEL_ARGS[@]}" \
  < /dev/null > "$OUT" 2>&1
STATUS=$?

if [[ $STATUS -ne 0 ]]; then
  echo "error: reviewer exited with status $STATUS. Output follows:" >&2
  cat "$OUT" >&2
  exit $STATUS
fi

# An empty report means the reviewer failed silently rather than finding
# nothing -- a real "no bugs" verdict still produces prose. Surface the
# difference instead of letting it read as a clean bill of health.
if [[ ! -s "$OUT" ]]; then
  echo "error: reviewer produced no output. Treat this as a failed review, not a clean one." >&2
  exit 1
fi

cat "$OUT"
