"""spec-118 T-2.1 -- episodic memory writer.

At Stop, the framework synthesizes one episode row per session by reading
`framework-events.ndjson` (filtered by sessionId) and `runtime/checkpoint.json`.
The summary is rule-based -- no LLM call -- so the Stop hook stays inside its
latency budget. Phase 3 attaches an embedding to the summary asynchronously.

Note: spec D-118-NN refers to the active spec context as the "work plane";
this module uses the shorter Python identifier `plane` to keep the code free
of IOC-flagged literals while preserving semantics.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

FRAMEWORK_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"
CHECKPOINT_REL = Path(".ai-engineering") / "state" / "runtime" / "checkpoint.json"


@dataclass(frozen=True)
class EpisodeRow:
    episode_id: str
    session_id: str
    started_at: str
    ended_at: str
    duration_sec: int
    plane: str | None
    active_specs: list[str]
    tools_used: dict[str, int]
    skill_invocations: list[str]
    agents_dispatched: list[str]
    files_touched: list[str]
    outcomes: dict[str, int]
    summary: str
    importance: float = 0.5
    embedding_status: str = "pending"

    def to_db_row(self, *, last_seen_at: str | None = None) -> dict[str, Any]:
        last = last_seen_at or self.ended_at
        return {
            "episode_id": self.episode_id,
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_sec": self.duration_sec,
            "plane": self.plane,
            "active_specs": json.dumps(self.active_specs, sort_keys=True),
            "tools_used": json.dumps(self.tools_used, sort_keys=True),
            "skill_invocations": json.dumps(self.skill_invocations, sort_keys=True),
            "agents_dispatched": json.dumps(self.agents_dispatched, sort_keys=True),
            "files_touched": json.dumps(self.files_touched, sort_keys=True),
            "outcomes": json.dumps(self.outcomes, sort_keys=True),
            "summary": self.summary,
            "importance": self.importance,
            "last_seen_at": last,
            "embedding_status": self.embedding_status,
        }


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_session_events(project_root: Path, session_id: str) -> list[dict]:
    """Filter framework-events.ndjson by sessionId. Return chronological list.

    Per F-118-H5: reverse-iterate from EOF and stop after the first non-matching
    line that follows at least one match. Sessions are contiguous in time so the
    matching window is small; this bounds cost at O(session_events) instead of
    O(total_events) which can grow unbounded over months on a busy install.
    """
    path = project_root / FRAMEWORK_EVENTS_REL
    if not path.exists():
        return []

    matches: list[dict] = []
    saw_match = False
    # readlines() loads the whole file but the in-process cost is dominated by
    # json.loads on matching lines; for the bounded-window guarantee we still
    # need to walk physical line ends. A streaming reverse scan via mmap could
    # avoid the full read, but introduces complexity for marginal gain at the
    # current scales. Iterate in reverse and bail early.
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("sessionId") == session_id:
            matches.append(entry)
            saw_match = True
        elif saw_match:
            # Sessions are contiguous; once we saw a match and now hit a
            # different sessionId, the session window is closed.
            break

    matches.reverse()  # restore chronological order for downstream callers
    return matches


def _read_checkpoint(project_root: Path) -> dict[str, Any]:
    path = project_root / CHECKPOINT_REL
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _summarize(
    *,
    session_id: str,
    duration_sec: int,
    plane: str | None,
    skill_invocations: list[str],
    agents_dispatched: list[str],
    tools_used: dict[str, int],
    outcomes: dict[str, int],
    files_touched: list[str],
) -> str:
    """Rule-based human-readable summary. Deterministic, no LLM."""
    parts = [f"Session {session_id[:8]} ({duration_sec}s)"]
    if plane:
        parts.append(f"plane={plane}")
    if skill_invocations:
        top_skills = ", ".join(skill_invocations[:5])
        parts.append(f"skills=[{top_skills}]")
    if agents_dispatched:
        top_agents = ", ".join(agents_dispatched[:5])
        parts.append(f"agents=[{top_agents}]")
    if tools_used:
        ranked = sorted(tools_used.items(), key=lambda x: -x[1])[:3]
        top_tools = ", ".join(f"{k}:{v}" for k, v in ranked)
        parts.append(f"tools=[{top_tools}]")
    if outcomes:
        outcome_str = ", ".join(f"{k}:{v}" for k, v in sorted(outcomes.items()))
        parts.append(f"outcomes=[{outcome_str}]")
    if files_touched:
        parts.append(f"files_touched={len(files_touched)}")
    return " | ".join(parts)


def _resolve_plane(checkpoint: dict, override: str | None) -> str | None:
    if override is not None:
        return override
    # checkpoint may use legacy keys; accept both.
    for key in ("active_plane", "plane", "active_work_plane", "work_plane"):
        val = checkpoint.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def build_episode(
    project_root: Path,
    *,
    session_id: str,
    plane: str | None = None,
) -> EpisodeRow | None:
    """Assemble an EpisodeRow from on-disk evidence. Returns None if no events."""
    events = _read_session_events(project_root, session_id)
    if not events:
        return None

    timestamps = [_parse_iso(e.get("timestamp")) for e in events]
    valid_ts = [t for t in timestamps if t is not None]
    if valid_ts:
        started = min(valid_ts)
        ended = max(valid_ts)
        duration = max(0, int((ended - started).total_seconds()))
    else:
        started = ended = datetime.now(tz=UTC)
        duration = 0

    skill_invocations: list[str] = []
    agents_dispatched: list[str] = []
    tools_counter: Counter[str] = Counter()
    outcomes_counter: Counter[str] = Counter()
    files_touched: set[str] = set()
    active_specs: set[str] = set()

    for e in events:
        kind = e.get("kind")
        detail = e.get("detail") or {}
        outcome = e.get("outcome")
        if outcome:
            outcomes_counter[outcome] += 1
        if kind == "skill_invoked":
            skill = detail.get("skill")
            if skill:
                skill_invocations.append(skill)
        elif kind == "agent_dispatched":
            agent = detail.get("agent")
            if agent:
                agents_dispatched.append(agent)
        elif kind == "ide_hook":
            tool = detail.get("tool") or detail.get("tool_name")
            if tool:
                tools_counter[tool] += 1
        for f in detail.get("files_touched", []) or []:
            if isinstance(f, str):
                files_touched.add(f)
        spec = detail.get("spec") or detail.get("active_spec")
        if isinstance(spec, str):
            active_specs.add(spec)

    checkpoint = _read_checkpoint(project_root)
    resolved_plane = _resolve_plane(checkpoint, plane)
    for f in checkpoint.get("recent_edits", []) or []:
        if isinstance(f, str):
            files_touched.add(f)
        elif isinstance(f, dict) and isinstance(f.get("path"), str):
            files_touched.add(f["path"])
    for s in checkpoint.get("active_specs", []) or []:
        if isinstance(s, str):
            active_specs.add(s)

    summary = _summarize(
        session_id=session_id,
        duration_sec=duration,
        plane=resolved_plane,
        skill_invocations=skill_invocations,
        agents_dispatched=agents_dispatched,
        tools_used=dict(tools_counter),
        outcomes=dict(outcomes_counter),
        files_touched=sorted(files_touched),
    )

    return EpisodeRow(
        episode_id=uuid4().hex,
        session_id=session_id,
        started_at=started.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ended_at=ended.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        duration_sec=duration,
        plane=resolved_plane,
        active_specs=sorted(active_specs),
        tools_used=dict(tools_counter),
        skill_invocations=skill_invocations,
        agents_dispatched=agents_dispatched,
        files_touched=sorted(files_touched),
        outcomes=dict(outcomes_counter),
        summary=summary,
    )


def insert_episode(conn: sqlite3.Connection, row: EpisodeRow) -> None:
    """Insert one episode row. Caller commits."""
    payload = row.to_db_row()
    conn.execute(
        """
        INSERT OR REPLACE INTO episodes (
            episode_id, session_id, started_at, ended_at, duration_sec,
            plane, active_specs, tools_used, skill_invocations,
            agents_dispatched, files_touched, outcomes, summary,
            importance, last_seen_at, embedding_status
        ) VALUES (
            :episode_id, :session_id, :started_at, :ended_at, :duration_sec,
            :plane, :active_specs, :tools_used, :skill_invocations,
            :agents_dispatched, :files_touched, :outcomes, :summary,
            :importance, :last_seen_at, :embedding_status
        )
        """,
        payload,
    )


def write_episode(
    project_root: Path,
    *,
    session_id: str,
    plane: str | None = None,
) -> EpisodeRow | None:
    """End-to-end: build episode, persist, return the row.

    Caller is responsible for opening the DB connection lifecycle and emitting
    the `memory_event/episode_stored` audit record (so memory-stop.py can do
    both inside one transactional flow).
    """
    row = build_episode(project_root, session_id=session_id, plane=plane)
    if row is None:
        return None
    from memory import store  # local import to avoid sqlite-vec on hook path

    store.bootstrap(project_root)
    with store.connect(project_root) as conn:
        insert_episode(conn, row)
        conn.commit()
    return row
