"""Agent-to-agent (A2A) artifact protocol — spec-122 / 2026-05-04 gap closure (P3.1).

The doctrine §72-78 calls for standardized artifact handoffs between
agents so traceability survives nested subagent dispatch. Today the
``Agent`` / ``Task`` tools emit raw strings and downstream consumers
have to re-parse them; this module gives every agent invocation a
schema-bound artifact persisted under
``.ai-engineering/state/agent-artifacts/<run-id>.json``.

Schema (frozen dataclass ``AgentArtifact``):

* ``run_id``         — uuid4 hex of the agent invocation.
* ``agent_type``     — slug of the agent (e.g. ``ai-explore``, ``ai-build``).
* ``inputs``         — dict of inputs the dispatcher passed.
* ``outputs``        — dict of structured outputs the agent returned.
* ``citations``      — list of ``startLine:endLine:filepath`` refs.
* ``confidence``     — optional 0.0..1.0 self-assessment.
* ``parent_run_id``  — None for root, parent's run_id for nested.
* ``started_at`` / ``ended_at`` — ISO8601 UTC.
* ``status``         — one of ``"success" | "failure" | "partial"``.

The persistence layer uses an atomic ``os.replace`` write so concurrent
writes for the same run_id resolve to a single winner instead of leaving
a half-written JSON on disk. Trace lookups (``trace_session``) walk
``runs/<session-id>/`` symlinks the dispatcher creates so the parent →
children relationship is recoverable without scanning every JSON.

Sealed contract: stdlib-only (no ``ai_engineering.*`` imports), matches
the rest of ``_lib``.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

ARTIFACTS_REL = Path(".ai-engineering") / "state" / "agent-artifacts"
ALLOWED_STATUS = frozenset({"success", "failure", "partial"})


@dataclass(frozen=True)
class AgentArtifact:
    """Single agent invocation, persisted as one JSON file."""

    run_id: str
    agent_type: str
    inputs: dict
    outputs: dict
    citations: list[str]
    started_at: str
    ended_at: str
    status: Literal["success", "failure", "partial"]
    parent_run_id: str | None = None
    confidence: float | None = None
    extras: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _iso_now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id() -> str:
    """Return a fresh uuid4 hex (32 chars) for a new agent invocation."""
    return uuid4().hex


def artifacts_dir(project_root: Path) -> Path:
    """Return the canonical artifacts directory; create on demand."""
    path = project_root / ARTIFACTS_REL
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifact_path(project_root: Path, run_id: str) -> Path:
    """Return the canonical path for a single artifact's JSON file."""
    return artifacts_dir(project_root) / f"{run_id}.json"


def write_artifact(project_root: Path, artifact: AgentArtifact) -> Path:
    """Atomically persist an artifact. Returns the resolved path.

    Uses tempfile + os.replace so concurrent writes for the same run_id
    resolve to a single winner (POSIX rename is atomic). The temp file
    lives in the same directory as the target so cross-device renames
    are not a concern.

    Validates ``status`` against the allowed set before writing so a
    bad enum value lands a ValueError instead of silently corrupting
    downstream replay.
    """
    if artifact.status not in ALLOWED_STATUS:
        msg = (
            f"AgentArtifact.status must be one of {sorted(ALLOWED_STATUS)}; got {artifact.status!r}"
        )
        raise ValueError(msg)
    target = artifact_path(project_root, artifact.run_id)
    payload = json.dumps(artifact.to_dict(), sort_keys=True, indent=2)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{artifact.run_id}-", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
        os.replace(tmp_path, target)
    except Exception:
        # Clean up the tmpfile if the rename failed; never leave detritus.
        import contextlib

        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    return target


def load_artifact(project_root: Path, run_id: str) -> AgentArtifact | None:
    """Read an artifact by run_id; return None when missing/malformed."""
    path = artifact_path(project_root, run_id)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        return AgentArtifact(
            run_id=str(data["run_id"]),
            agent_type=str(data.get("agent_type", "")),
            inputs=dict(data.get("inputs") or {}),
            outputs=dict(data.get("outputs") or {}),
            citations=list(data.get("citations") or []),
            started_at=str(data.get("started_at", "")),
            ended_at=str(data.get("ended_at", "")),
            status=str(data.get("status", "success")),  # type: ignore[arg-type]
            parent_run_id=data.get("parent_run_id"),
            confidence=data.get("confidence"),
            extras=dict(data.get("extras") or {}),
        )
    except (KeyError, TypeError, ValueError):
        return None


def trace_session(project_root: Path, session_id: str) -> list[AgentArtifact]:
    """Return all artifacts whose extras.session_id matches; oldest first.

    Iterates the artifacts directory and filters by session_id stamped
    in ``extras``. Bounded scan: artifacts are tiny (few KB each) so a
    full directory walk stays well under 100 ms even at ~10k entries.
    """
    out: list[AgentArtifact] = []
    base = artifacts_dir(project_root)
    if not base.is_dir():
        return out
    for child in base.iterdir():
        if child.suffix != ".json":
            continue
        artifact = load_artifact(project_root, child.stem)
        if artifact is None:
            continue
        if artifact.extras.get("session_id") == session_id:
            out.append(artifact)
    out.sort(key=lambda a: a.started_at)
    return out


__all__ = [
    "ALLOWED_STATUS",
    "ARTIFACTS_REL",
    "AgentArtifact",
    "artifact_path",
    "artifacts_dir",
    "load_artifact",
    "new_run_id",
    "trace_session",
    "write_artifact",
]
