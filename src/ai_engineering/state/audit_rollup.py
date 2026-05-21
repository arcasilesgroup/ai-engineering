"""spec-148 P1: token rollups computed directly from framework-events.ndjson.

Pure, dependency-free replacement for the retired SQLite
``skill/agent/session_token_rollup`` views (formerly in ``audit_index``).
The NDJSON event log (`framework-events.ndjson`) is the single source of
truth; these helpers scan it and reproduce the exact view semantics:

* :func:`skill_token_rollup`  — ``kind == 'skill_invoked'``, group by
  ``detail.skill``; ``invocations`` = COUNT.
* :func:`agent_token_rollup`  — ``kind == 'agent_dispatched'``, group by
  ``detail.agent``; ``dispatches`` = COUNT.
* :func:`session_token_rollup` — group by ``sessionId`` (non-null);
  ``started_at``/``ended_at`` = MIN/MAX ``timestamp``; ``events`` = COUNT.

Token fields live at ``detail.genai.usage.{input,output,total}_tokens``
and ``detail.genai.usage.cost_usd`` (nullable; treated as 0 for sums,
matching ``SUM`` over a column where NULLs do not contribute). A missing
file yields an empty list; a malformed line is skipped, never fatal.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

# Canonical location of the append-only framework event stream (the single
# source of truth for the audit surface, spec-148 files-only).
NDJSON_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


def _iter_events(ndjson_path: Path):
    """Yield parsed event dicts from an NDJSON file; skip malformed lines."""
    try:
        text = ndjson_path.read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(event, dict):
            yield event


def _usage(event: dict[str, Any]) -> dict[str, Any]:
    detail = event.get("detail")
    if not isinstance(detail, dict):
        return {}
    genai = detail.get("genai")
    if not isinstance(genai, dict):
        return {}
    usage = genai.get("usage")
    return usage if isinstance(usage, dict) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _float(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _accumulate(event: dict[str, Any], acc: dict[str, Any]) -> None:
    usage = _usage(event)
    acc["input_tokens"] += _int(usage.get("input_tokens"))
    acc["output_tokens"] += _int(usage.get("output_tokens"))
    acc["total_tokens"] += _int(usage.get("total_tokens"))
    acc["cost_usd"] += _float(usage.get("cost_usd"))


def _new_acc() -> dict[str, Any]:
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}


def skill_token_rollup(ndjson_path: Path) -> list[dict[str, Any]]:
    """Per-skill token rollup over ``skill_invoked`` events."""
    groups: dict[str | None, dict[str, Any]] = defaultdict(lambda: {**_new_acc(), "invocations": 0})
    for event in _iter_events(ndjson_path):
        if event.get("kind") != "skill_invoked":
            continue
        detail = event.get("detail")
        skill = detail.get("skill") if isinstance(detail, dict) else None
        if not isinstance(skill, str):
            skill = None
        acc = groups[skill]
        acc["invocations"] += 1
        _accumulate(event, acc)
    return [
        {"skill": skill, **acc}
        for skill, acc in sorted(groups.items(), key=lambda kv: (kv[0] is None, kv[0] or ""))
    ]


def agent_token_rollup(ndjson_path: Path) -> list[dict[str, Any]]:
    """Per-agent token rollup over ``agent_dispatched`` events."""
    groups: dict[str | None, dict[str, Any]] = defaultdict(lambda: {**_new_acc(), "dispatches": 0})
    for event in _iter_events(ndjson_path):
        if event.get("kind") != "agent_dispatched":
            continue
        detail = event.get("detail")
        agent = detail.get("agent") if isinstance(detail, dict) else None
        if not isinstance(agent, str):
            agent = None
        acc = groups[agent]
        acc["dispatches"] += 1
        _accumulate(event, acc)
    return [
        {"agent": agent, **acc}
        for agent, acc in sorted(groups.items(), key=lambda kv: (kv[0] is None, kv[0] or ""))
    ]


def session_token_rollup(ndjson_path: Path) -> list[dict[str, Any]]:
    """Per-session token rollup; ``started_at``/``ended_at`` = MIN/MAX timestamp."""
    groups: dict[str, dict[str, Any]] = {}
    for event in _iter_events(ndjson_path):
        session_id = event.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            continue
        ts = event.get("timestamp")
        ts = ts if isinstance(ts, str) else ""
        acc: dict[str, Any] | None = groups.get(session_id)
        if acc is None:
            acc = {**_new_acc(), "events": 0, "started_at": ts, "ended_at": ts}
            groups[session_id] = acc
        acc["events"] += 1
        if ts and (not acc["started_at"] or ts < acc["started_at"]):
            acc["started_at"] = ts
        if ts and ts > acc["ended_at"]:
            acc["ended_at"] = ts
        _accumulate(event, acc)
    return [{"session_id": sid, **acc} for sid, acc in sorted(groups.items())]


__all__ = [
    "NDJSON_REL",
    "agent_token_rollup",
    "session_token_rollup",
    "skill_token_rollup",
]
