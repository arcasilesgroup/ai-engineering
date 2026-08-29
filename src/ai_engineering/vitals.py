"""Where a cycle's wall minutes went, read from the framework's own event record.

Spec 047 / B-047-3. The input is the text of `.ai/events.jsonl` (or one session's slice
of it) and a session id; minutes are attributed between consecutive ISO `ts` stamps to
the earlier event's `cls`, and the verdict compares the wall time against
`contract.CYCLE_WALL_BUDGET_MINUTES`. The clock disqualifies and never approves: a PASS
here says the arithmetic fit, and nothing about the work. `stamp` is the chain seal, not
a time; this reader never uses it, and a line it cannot parse is skipped, not guessed —
a stream with no readable event for the session is NO_DATA, never an empty green.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from . import contract


def read(raw: str, session: str) -> dict[str, Any]:
    """Wall minutes and per-`cls` minutes for one session's events, in file order."""
    stamps: list[tuple[datetime, str]] = []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(event, dict) or event.get("session") != session:
            continue
        try:
            at = datetime.fromisoformat(str(event["ts"]))
        except (KeyError, ValueError, TypeError):
            continue
        cls = str(event.get("cls", "command"))
        stamps.append((at, cls))
    by_cls: dict[str, float] = {}
    wall = 0.0
    for (start, cls), (nxt, _) in zip(stamps, stamps[1:], strict=False):
        gap = (nxt - start).total_seconds() / 60.0
        by_cls[cls] = round(by_cls.get(cls, 0.0) + gap, 6)
        wall += gap
    return {
        "events": len(stamps),
        "wall_minutes": round(wall, 6),
        "by_cls": by_cls,
    }


def verdict(raw: str, session: str) -> dict[str, Any]:
    """PASS inside the budget, INCOMPLETE [OVER_BUDGET] naming the largest bucket,
    INCOMPLETE [NO_DATA] when the session has no readable pair of events."""
    seen = read(raw, session)
    events: int = seen["events"]
    wall: float = seen["wall_minutes"]
    by_cls: dict[str, float] = seen["by_cls"]
    if events < 2:
        return {"outcome": "INCOMPLETE", "code": "NO_DATA", "wall_minutes": wall}
    if wall > contract.CYCLE_WALL_BUDGET_MINUTES:
        largest = max(by_cls, key=lambda cls: by_cls[cls]) if by_cls else "none"
        return {
            "outcome": "INCOMPLETE",
            "code": "OVER_BUDGET",
            "wall_minutes": wall,
            "largest": largest,
            "by_cls": by_cls,
        }
    return {"outcome": "PASS", "wall_minutes": wall, "by_cls": by_cls}
