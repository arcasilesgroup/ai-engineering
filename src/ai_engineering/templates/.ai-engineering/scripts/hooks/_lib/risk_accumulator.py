"""PRISM-style session-scoped risk score accumulator (spec-120 follow-up).

Layers over the existing per-IOC severity scoring in
``prompt-injection-guard.py`` with a running, time-decaying score
per session. Goals:

1. **Session-scoped accumulation** -- each finding contributes weight
   to a per-session running score rather than being evaluated in
   isolation.
2. **TTL decay** -- old events lose weight at a fixed exponential
   rate so a long-quiet session is forgiven.
3. **Threshold ladder** -- four-tier escalation (silent / warn /
   block / force_stop) so the host can graduate from a passive
   warning to a hard refusal.
4. **Repeat-signal weighting** -- the same signal repeated within a
   short window earns extra weight, integrating naturally with the
   ``runtime-guard.py`` loop-detection logic.

Design contract (mirrors the rest of ``_lib``):

* Stdlib only -- no ``ai_engineering.*`` imports.
* Tolerant of corruption -- a missing or malformed state file
  returns a fresh ``score=0`` snapshot AND emits
  ``framework_error error_code=risk_state_corrupted`` so the
  forensic trail records the rebuild.
* Atomic writes -- ``.tmp`` + ``os.replace`` so a crash mid-write
  never leaves the state file half-rewritten.
* State is local-only -- ``RUNTIME_DIR(project_root)`` (canonical
  ``.ai-engineering/runtime/``) is gitignored; this captures session
  telemetry, not source of truth.

Severity mapping:

* ``LOW``      = 1
* ``MEDIUM``   = 5
* ``HIGH``     = 20
* ``CRITICAL`` = 50  (alone hits ``warn`` threshold)

Threshold ladder:

* score < 10           -> ``silent``
* 10 <= score < 30     -> ``warn``
* 30 <= score < 60     -> ``block``
* score >= 60          -> ``force_stop``

TTL decay: ``decay_per_minute = 0.95`` (score halves in ~13.5 min).
Applied each time state is read; below the 0.1 noise floor the
score clamps to 0.

Repeat-signal weighting (same ``ioc_id`` in the last 60 minutes):

* 1 prior fire   -> 1.5x multiplier on the new addition
* >= 2 prior fires (i.e. this is the third+) -> 2.5x multiplier
"""

from __future__ import annotations

import contextlib
import json
import math
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from _lib.hook_context import RUNTIME_DIR

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"
# Spec-125 Wave 2: legacy ``state/runtime`` constants retained for
# backwards-compatible re-export only. Active path resolution flows through
# the ``RUNTIME_DIR(project_root)`` factory in ``_lib/hook_context.py``
# (canonical ``.ai-engineering/runtime/``); see ``_state_path`` below.
RUNTIME_DIR_REL = Path(".ai-engineering") / "state" / "runtime"
RISK_STATE_REL = RUNTIME_DIR_REL / "risk-score.json"
_RISK_STATE_FILENAME = "risk-score.json"

SEVERITY_SCORES: dict[str, float] = {
    "LOW": 1.0,
    "MEDIUM": 5.0,
    "HIGH": 20.0,
    "CRITICAL": 50.0,
}

# Decay per minute. score(t) = score(0) * DECAY_PER_MINUTE ** elapsed_minutes
# 0.95^minute -> half-life ≈ 13.5 minutes.
DECAY_PER_MINUTE = 0.95

# Below this floor, decay clamps to zero so we don't carry vanishingly small
# rounding noise forward forever.
NOISE_FLOOR = 0.1

# Repeat-signal weighting window (seconds) -- 60 minutes.
REPEAT_WINDOW_SECONDS = 60 * 60

# Repeat-signal multipliers keyed on prior-fire count in the window.
REPEAT_MULT_ONE_PRIOR = 1.5
REPEAT_MULT_TWO_OR_MORE_PRIORS = 2.5

# Ring buffer cap. Keeps the file small (~50 events ≈ 4 KiB).
RING_BUFFER_CAP = 50

# Threshold ladder. Tuple ordering matters -- evaluated low-to-high.
_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (60.0, "force_stop"),
    (30.0, "block"),
    (10.0, "warn"),
)


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskState:
    """Snapshot of the session-scoped risk accumulator.

    Frozen so callers can pass it around without worrying about a
    downstream consumer mutating the cached value. ``events`` is
    intentionally a plain list of dicts (not a dataclass) because
    consumers iterate it as observability payload, not as a typed
    domain object.
    """

    session_id: str
    score: float
    last_update_ts: str  # ISO 8601 UTC, e.g. "2026-05-04T10:30:00Z"
    events: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Path / time helpers
# ---------------------------------------------------------------------------


def _state_path(project_root: Path) -> Path:
    return RUNTIME_DIR(project_root) / _RISK_STATE_FILENAME


def _utcnow() -> datetime:
    """Wall-clock UTC. Wrapped so tests can monkeypatch the call site."""
    return datetime.now(UTC)


def _iso(ts: datetime) -> str:
    """Format a datetime as the canonical ISO-8601 UTC string."""
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        # Tolerate both "...Z" and explicit "+00:00" forms.
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Decay + read
# ---------------------------------------------------------------------------


def _apply_decay(score: float, last_update_ts: str | None, *, now: datetime) -> float:
    """Apply exponential decay since ``last_update_ts``.

    A missing or unparseable timestamp is treated as "no decay" so we
    never amplify noise from a corrupt file -- the corruption path
    has its own zero-out.
    """
    if score <= 0:
        return 0.0
    parsed = _parse_iso(last_update_ts)
    if parsed is None:
        return score
    elapsed = (now - parsed).total_seconds()
    if elapsed <= 0:
        return score
    elapsed_minutes = elapsed / 60.0
    decayed = score * (DECAY_PER_MINUTE**elapsed_minutes)
    if decayed < NOISE_FLOOR:
        return 0.0
    return decayed


def _emit_corruption_event(project_root: Path, *, summary: str) -> None:
    """Best-effort framework_error emission for a malformed state file.

    Wrapped in ``contextlib.suppress`` so any failure inside the
    observability shim never crashes the host caller -- the whole
    point of the corruption path is to keep the hook running.
    """
    with contextlib.suppress(Exception):
        # Lazy import keeps this module importable in test contexts that
        # never write framework events.
        import sys

        hooks_dir = Path(__file__).resolve().parent.parent
        if str(hooks_dir) not in sys.path:
            sys.path.insert(0, str(hooks_dir))
        from _lib.observability import emit_framework_error

        emit_framework_error(
            project_root,
            engine="ai_engineering",
            component="hook.risk-accumulator",
            error_code="risk_state_corrupted",
            summary=summary,
            source="hook",
        )


def _read_raw(project_root: Path) -> dict[str, Any] | None:
    """Read the persisted state. Returns ``None`` for missing or malformed.

    Caller is responsible for emitting the corruption event when this
    returns ``None`` for a *present-but-malformed* file. Differentiates
    "missing" (fresh session, not an error) from "malformed" (audit-
    worthy) by the OSError vs ValueError split.
    """
    path = _state_path(project_root)
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        # Malformed JSON -- caller should emit corruption event.
        _emit_corruption_event(project_root, summary="risk-score.json malformed JSON")
        return None
    if not isinstance(payload, dict):
        _emit_corruption_event(
            project_root, summary=f"risk-score.json wrong type: {type(payload).__name__}"
        )
        return None
    return payload


def _coerce_events(raw: Any) -> list[dict]:
    """Coerce a deserialized ``events`` field into a list of dicts.

    Drops non-dict entries silently -- the ring buffer is observability
    metadata, not source of truth, so a partially-corrupt buffer is
    survivable.
    """
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for entry in raw:
        if isinstance(entry, dict):
            out.append(entry)
    return out


def _make_fresh(session_id: str, *, now: datetime) -> RiskState:
    return RiskState(
        session_id=session_id,
        score=0.0,
        last_update_ts=_iso(now),
        events=[],
    )


# ---------------------------------------------------------------------------
# Public API: get / add / threshold_action / reset
# ---------------------------------------------------------------------------


def get(project_root: Path, *, session_id: str, now: datetime | None = None) -> RiskState:
    """Read the current state for ``session_id`` with decay applied.

    Behavior:

    * No file or empty file -> fresh ``score=0`` snapshot.
    * Malformed file -> fresh ``score=0`` AND ``framework_error
      error_code=risk_state_corrupted`` emitted.
    * Different ``session_id`` than what's persisted -> fresh
      snapshot for the new session (the old session's state is
      effectively retired). We don't carry state across sessions
      because session boundaries are the natural reset point for
      "graduated escalation"; a fresh session deserves fresh
      benefit-of-the-doubt.
    * Matching session -> persisted score with decay applied since
      ``last_update_ts``.
    """
    reference = now or _utcnow()
    payload = _read_raw(project_root)
    if payload is None:
        return _make_fresh(session_id, now=reference)
    persisted_session = payload.get("session_id") or payload.get("sessionId") or ""
    if persisted_session != session_id:
        # Different session -- fresh state. Persisted file belongs to
        # a prior session and is left in place; the next add() will
        # overwrite it with the new session's state.
        return _make_fresh(session_id, now=reference)

    score_raw = payload.get("score", 0.0)
    try:
        score = float(score_raw)
    except (TypeError, ValueError):
        _emit_corruption_event(project_root, summary="risk-score.json non-numeric score")
        return _make_fresh(session_id, now=reference)

    last_update = payload.get("last_update_ts") or payload.get("lastUpdateTs") or _iso(reference)
    decayed = _apply_decay(score, last_update, now=reference)
    events = _coerce_events(payload.get("events"))

    return RiskState(
        session_id=session_id,
        score=decayed,
        last_update_ts=last_update,
        events=events,
    )


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    """Write ``payload`` to ``path`` atomically via ``.tmp`` + ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        os.replace(tmp, path)
    finally:
        # Defensive: if .tmp lingered (e.g. write failed), clean it up so
        # the test_atomic_write contract holds.
        if tmp.exists():
            with contextlib.suppress(OSError):
                tmp.unlink()


def _count_recent_repeats(
    events: list[dict],
    *,
    ioc_id: str,
    now: datetime,
) -> int:
    """Count prior fires of ``ioc_id`` within ``REPEAT_WINDOW_SECONDS``."""
    if not events:
        return 0
    cutoff = now - timedelta(seconds=REPEAT_WINDOW_SECONDS)
    count = 0
    for entry in events:
        if entry.get("ioc_id") != ioc_id:
            continue
        ts = _parse_iso(entry.get("ts"))
        if ts is None:
            continue
        if ts >= cutoff:
            count += 1
    return count


def _repeat_multiplier(prior_count: int) -> float:
    """Return the score-addition multiplier for ``prior_count`` repeats."""
    if prior_count <= 0:
        return 1.0
    if prior_count == 1:
        return REPEAT_MULT_ONE_PRIOR
    return REPEAT_MULT_TWO_OR_MORE_PRIORS


def add(
    project_root: Path,
    *,
    session_id: str,
    severity: str,
    ioc_id: str,
    source: str = "prompt-injection-guard",
    now: datetime | None = None,
) -> RiskState:
    """Add a finding to the session's running score.

    Pipeline:

    1. Read current state (with decay applied).
    2. Look up severity weight; unknown severities cost 0 (defensive
       fail-open -- we'd rather under-count than crash).
    3. Apply repeat-signal multiplier based on prior fires of the
       same ``ioc_id`` in the last hour.
    4. Append the event to the ring buffer (cap RING_BUFFER_CAP).
    5. Atomic-write the new state. Returns the post-write snapshot.

    The state file always reflects the "current session" -- if the
    previous file's ``session_id`` differs we overwrite it. This
    matches ``get()``'s session-isolation semantics.
    """
    reference = now or _utcnow()
    severity_key = (severity or "").strip().upper()
    base_score = SEVERITY_SCORES.get(severity_key, 0.0)

    current = get(project_root, session_id=session_id, now=reference)
    prior_repeats = _count_recent_repeats(current.events, ioc_id=ioc_id, now=reference)
    multiplier = _repeat_multiplier(prior_repeats)
    score_added = base_score * multiplier
    new_score = current.score + score_added

    new_event = {
        "ts": _iso(reference),
        "ioc_id": ioc_id,
        "severity": severity_key,
        "score_added": round(score_added, 4),
        "source": source,
    }
    new_events = [*current.events, new_event]
    if len(new_events) > RING_BUFFER_CAP:
        # Keep the most-recent RING_BUFFER_CAP entries.
        new_events = new_events[-RING_BUFFER_CAP:]

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "session_id": session_id,
        "score": round(new_score, 4),
        "last_update_ts": _iso(reference),
        "events": new_events,
    }
    _atomic_write(_state_path(project_root), payload)
    return RiskState(
        session_id=session_id,
        score=new_score,
        last_update_ts=_iso(reference),
        events=new_events,
    )


def threshold_action(score: float) -> str:
    """Return ``'silent' | 'warn' | 'block' | 'force_stop'`` for ``score``.

    Evaluated highest-to-lowest so a score that crosses multiple
    thresholds returns the most severe label.
    """
    if math.isnan(score) or score < 0:
        return "silent"
    for floor, label in _THRESHOLDS:
        if score >= floor:
            return label
    return "silent"


def reset(project_root: Path, *, session_id: str | None = None) -> None:
    """Remove the persisted state file.

    ``session_id`` is accepted for API symmetry but ignored -- the
    state file is single-session by construction, so a reset always
    wipes whichever session is currently persisted.
    """
    del session_id  # API symmetry only.
    path = _state_path(project_root)
    with contextlib.suppress(FileNotFoundError):
        path.unlink()
    # Also clean up any orphan .tmp from an interrupted write.
    tmp = path.with_suffix(path.suffix + ".tmp")
    with contextlib.suppress(FileNotFoundError):
        tmp.unlink()


__all__ = [
    "DECAY_PER_MINUTE",
    "NOISE_FLOOR",
    "REPEAT_MULT_ONE_PRIOR",
    "REPEAT_MULT_TWO_OR_MORE_PRIORS",
    "REPEAT_WINDOW_SECONDS",
    "RING_BUFFER_CAP",
    "RISK_STATE_REL",
    "RUNTIME_DIR_REL",
    "SCHEMA_VERSION",
    "SEVERITY_SCORES",
    "RiskState",
    "add",
    "get",
    "reset",
    "threshold_action",
]
