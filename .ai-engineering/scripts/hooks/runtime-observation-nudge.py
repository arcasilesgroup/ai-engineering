#!/usr/bin/env python3
"""SessionStart hook: surface the session-watch review backlog (spec-165 D-165-03).

System B (``/ai-session-watch --review``) is manual and has no reliable
trigger, so operator-correction observations accumulate unconsolidated in
``observation-events.ndjson``. This hook emits a one-line
``hookSpecificOutput.additionalContext`` nudge at SessionStart when there
are observations newer than the last review, so the backlog stops being
invisible.

Hot-path discipline (spec-165 D-165-03): the staleness check is O(1) — it
compares the event-stream **mtime** (``stat``) against the ``lastReviewedAt``
checkpoint in ``meta.json``. It NEVER reads the (multi-MB) event stream.
Fail-open: any error -> silent passthrough, never blocks the IDE.
"""

from __future__ import annotations

import contextlib
import json
import sys
from datetime import datetime
from pathlib import Path

from _lib.audit import passthrough_stdin
from _lib.hook_common import run_hook_safe
from _lib.hook_context import get_hook_context

_META_REL = ".ai-engineering/observations/meta.json"
_NDJSON_REL = ".ai-engineering/state/observation-events.ndjson"

_HINT = (
    "[observation-nudge] Unconsolidated session-watch observations are pending "
    "review — run /ai-session-watch --review to consolidate corrections "
    "into the corpus."
)


def _parse_iso(value: object) -> float | None:
    """Best-effort ISO-8601 -> POSIX timestamp; None on any failure."""
    if not isinstance(value, str) or not value:
        return None
    with contextlib.suppress(Exception):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    return None


def _pending(project_root: Path) -> bool:
    """True when observations exist that post-date the last review. O(1).

    Uses only ``stat`` on the event stream (never reads its contents) and a
    small ``meta.json`` read. Fail-open: when the review state cannot be
    confirmed but events exist, returns True (a spurious nudge is harmless;
    a missed one defeats the purpose).
    """
    ndjson = project_root / _NDJSON_REL
    try:
        st = ndjson.stat()
    except OSError:
        return False  # no event stream -> nothing pending
    if st.st_size == 0:
        return False
    last_reviewed: float | None = None
    with contextlib.suppress(Exception):
        meta = json.loads((project_root / _META_REL).read_text(encoding="utf-8"))
        if isinstance(meta, dict):
            last_reviewed = _parse_iso(meta.get("lastReviewedAt"))
    if last_reviewed is None:
        return True  # never reviewed (or unparseable) but events exist
    return st.st_mtime > last_reviewed


def main() -> None:
    ctx = get_hook_context()
    if ctx.event_name != "SessionStart":
        passthrough_stdin(ctx.data)
        return
    if not _pending(ctx.project_root):
        passthrough_stdin(ctx.data)
        return
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": _HINT,
                }
            },
            separators=(",", ":"),
        )
    )
    sys.stdout.flush()


if __name__ == "__main__":
    run_hook_safe(
        main,
        component="hook.runtime-observation-nudge",
        hook_kind="session-start",
        script_path=Path(__file__),
    )
