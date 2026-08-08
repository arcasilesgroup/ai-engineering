"""Opens and closes the trace, and moves the in-flight buffer into the durable chain.

Telemetry: it blocks nothing. It is also what makes the record readable, because it is
where the session's events stop being a buffer inside a clone and become links in a
chain that lives outside every clone.

On close it flushes rather than discards — the buffer is appended to the durable file
and then emptied, so nothing is lost — and it says one line out loud when the weekly
digest has gone unread, because the reader of that record is a person and the reminder
belongs to the person.
"""

from __future__ import annotations

import json
import shutil
import sys
import time

from _emit import config, emit, flush, home, repo_root, session_id
from _wrap import telemetry

STALE_DAYS = 7


def note(text: str) -> None:
    sys.stderr.write(f"[ai-eng] {text}\n")


def digest_age_days() -> float | None:
    stamp = home() / "cache" / "digest.json"
    try:
        read_at = json.loads(stamp.read_text())["read"]
    except (OSError, ValueError, KeyError):
        return None
    return (time.time() - float(read_at)) / 86400


@telemetry("session")
def run(payload: dict) -> None:
    event = payload.get("_event") or payload.get("hook_event_name", "")
    root = repo_root()

    if event == "SessionStart":
        emit("session", "session", phase="start", id=session_id())
        if shutil.which("ai-eng") is None:
            note("ai-eng is not on PATH: the CLI half of the framework is unreachable here.")
        if root is not None and not (root / ".ai" / "config.toml").exists():
            note("this repository is not set up — no pin, no git hooks. Run `ai-eng init`.")
        age = digest_age_days()
        if age is None or age > STALE_DAYS:
            note("the weekly record has not been read. `ai-eng digest` is one paragraph.")
        return

    emit("session", "session", phase="end", id=session_id())
    moved = flush(root)
    if moved and config().get("observability", {}).get("endpoint"):
        import _otlp

        _otlp.send_tail(moved)  # off the hot path on purpose: never during a tool call
