#!/usr/bin/env python3
"""PreToolUse hook: suggest /compact at strategic intervals.

Tracks per-session tool call count and prints an advisory message to stderr
when the count crosses the configured threshold. Advisory only -- never blocks.

Phase transition guide (for human decision-making):
  Research -> Planning:      Compact (research context is bulky; plan is distilled)
  Planning -> Implementation: Compact (plan is in file; free context for code)
  Implementation -> Testing:  Maybe (keep if tests reference recent code)
  Debugging -> Next feature:  Compact (debug traces pollute unrelated work)
  Mid-implementation:         No (losing file paths and partial state is costly)
  After failed approach:      Compact (clear dead-end reasoning)

Fail-open: exit 0 always -- never blocks IDE.
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import (
    get_project_root,
    passthrough_stdin,
    read_stdin,
)

_COMPACT_THRESHOLD = max(1, int(os.environ.get("COMPACT_THRESHOLD", "50")))
_COMPACT_REMINDER_INTERVAL = max(1, int(os.environ.get("COMPACT_REMINDER_INTERVAL", "25")))
_STATE_DIR: Path | None = None
_COUNTER_FILE: Path | None = None


def _load_counters() -> dict:
    """Load the counter state file."""
    counter_file = _counter_file()
    try:
        if counter_file.exists():
            with open(counter_file, encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_counters(counters: dict, current_key: str) -> None:
    """Persist counter state to disk, keeping only the current session."""
    counter_file = _counter_file()
    try:
        counter_file.parent.mkdir(parents=True, exist_ok=True)
        pruned = {current_key: counters[current_key]}
        with open(counter_file, "w", encoding="utf-8") as f:
            json.dump(pruned, f, separators=(",", ":"))
    except OSError:
        pass


def _counter_file() -> Path:
    if _COUNTER_FILE is not None:
        return _COUNTER_FILE
    if _STATE_DIR is not None:
        return _STATE_DIR / "strategic-compact.json"
    project_root = get_project_root()
    return project_root / ".ai-engineering" / "state" / "strategic-compact.json"


def _get_session_key() -> str:
    """Build a session key from CLAUDE_SESSION_ID or timestamp-based fallback."""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "") or os.environ.get(
        "GITHUB_COPILOT_SESSION_ID",
        "",
    )
    if session_id:
        return session_id
    # Fallback: date-hour bucket so sessions within the same hour share a counter
    return datetime.now(UTC).strftime("%Y%m%d-%H")


def _should_advise(count: int) -> bool:
    """Return True if count has crossed a threshold boundary."""
    if count < _COMPACT_THRESHOLD:
        return False
    if count == _COMPACT_THRESHOLD:
        return True
    # After threshold, advise every REMINDER_INTERVAL calls
    past_threshold = count - _COMPACT_THRESHOLD
    return past_threshold % _COMPACT_REMINDER_INTERVAL == 0


def _print_advisory(count: int) -> None:
    """Print advisory message to stderr (visible to the agent, not blocking)."""
    msg = (
        f"\n[strategic-compact] {count} tool calls this session. "
        f"Consider running /compact if you are between phases "
        f"(e.g., research->planning, debugging->next feature).\n"
    )
    sys.stderr.write(msg)
    sys.stderr.flush()


def main() -> None:
    hook_event = os.environ.get("CLAUDE_HOOK_EVENT_NAME", "")
    if hook_event != "PreToolUse":
        passthrough_stdin(read_stdin())
        return

    data = read_stdin()

    tool_name = data.get("tool_name", "")
    if not tool_name:
        passthrough_stdin(data)
        return

    session_key = _get_session_key()
    counters = _load_counters()

    current = counters.get(session_key, 0) + 1
    counters[session_key] = current
    _save_counters(counters, session_key)

    if _should_advise(current):
        _print_advisory(current)

    passthrough_stdin(data)


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
