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

spec-201 (sub-003) adds two session-level semantics:

* **Summary de-duplication.** A ``session_token_rollup`` event restates the
  whole session, so adding it to the members it summarises would double-count.
  Its usage accumulates separately and each field is reported as
  ``max(member_sum, summary_max)`` — the same "never undercount" rule the
  emitter uses when merging its two sources. Members carry no usage today, so
  the summary supplies the number; the max rule stays correct once they do.
  The summary bucket itself reduces with MAX, not SUM: one summary is emitted
  per turn and each restates the *cumulative* session total, so N of them are
  a monotone series whose sum overstates by roughly the turn count
  (spec-201 B1).
* **``genai_system`` column.** Comma-joined sorted distinct
  ``detail.genai.system`` values seen in the session, ``""`` when none. A
  session can legitimately span several drivers (subagents on different
  models); a single last-write-wins value would hide one.

``skill_token_rollup`` / ``agent_token_rollup`` are unchanged: they group by
kind and never see the summary event.
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


def _absorb_summary(event: dict[str, Any], acc: dict[str, Any]) -> None:
    """Field-wise MAX of a session summary into ``acc``.

    Every turn emits a ``session_token_rollup`` restating the session's
    *cumulative* total, so N summaries form a monotone series. Summing them
    reports the series' sum instead of its last value — an overstatement that
    grows with turn count and multiplies any reported cost by the same factor
    (spec-201 B1). Max is the correct reduction and is idempotent under
    repeat emission.
    """
    usage = _usage(event)
    acc["input_tokens"] = max(acc["input_tokens"], _int(usage.get("input_tokens")))
    acc["output_tokens"] = max(acc["output_tokens"], _int(usage.get("output_tokens")))
    acc["total_tokens"] = max(acc["total_tokens"], _int(usage.get("total_tokens")))
    acc["cost_usd"] = max(acc["cost_usd"], _float(usage.get("cost_usd")))


def _is_session_summary(event: dict[str, Any]) -> bool:
    """True for the ``session_token_rollup`` event, which restates a session."""
    detail = event.get("detail")
    if not isinstance(detail, dict):
        return False
    return detail.get("operation") == "session_token_rollup"


def _genai_system(event: dict[str, Any]) -> str:
    """Return ``detail.genai.system``, or ``""`` when absent/malformed."""
    detail = event.get("detail")
    if not isinstance(detail, dict):
        return ""
    genai = detail.get("genai")
    if not isinstance(genai, dict):
        return ""
    system = genai.get("system")
    return system if isinstance(system, str) else ""


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
    """Per-session token rollup; ``started_at``/``ended_at`` = MIN/MAX timestamp.

    Member usage SUMS; ``session_token_rollup`` summary usage reduces with MAX
    (each summary restates the cumulative session total, so summing them
    inflates by the turn count); the two are reconciled as
    ``max(member_sum, summary_max)`` per field so a summary can never
    double-count the events it summarises.
    """
    meta: dict[str, dict[str, Any]] = {}
    members: dict[str, dict[str, Any]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    systems: dict[str, set[str]] = {}
    for event in _iter_events(ndjson_path):
        session_id = event.get("sessionId")
        if not isinstance(session_id, str) or not session_id:
            continue
        ts = event.get("timestamp")
        ts = ts if isinstance(ts, str) else ""
        row: dict[str, Any] | None = meta.get(session_id)
        if row is None:
            row = {"events": 0, "started_at": ts, "ended_at": ts}
            meta[session_id] = row
            members[session_id] = _new_acc()
            summaries[session_id] = _new_acc()
            systems[session_id] = set()
        row["events"] += 1
        if ts and (not row["started_at"] or ts < row["started_at"]):
            row["started_at"] = ts
        if ts and ts > row["ended_at"]:
            row["ended_at"] = ts
        system = _genai_system(event)
        if system:
            systems[session_id].add(system)
        if _is_session_summary(event):
            _absorb_summary(event, summaries[session_id])
        else:
            _accumulate(event, members[session_id])
    rows: list[dict[str, Any]] = []
    for sid, row in sorted(meta.items()):
        member = members[sid]
        summary = summaries[sid]
        merged = {key: max(member[key], summary[key]) for key in member}
        rows.append(
            {
                "session_id": sid,
                **merged,
                **row,
                "genai_system": ",".join(sorted(systems[sid])),
            }
        )
    return rows


__all__ = [
    "NDJSON_REL",
    "agent_token_rollup",
    "session_token_rollup",
    "skill_token_rollup",
]
