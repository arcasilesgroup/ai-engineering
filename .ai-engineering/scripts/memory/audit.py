"""spec-118 T-1.7 -- single emitter for `memory_event` audit records.

Routes through `_lib/observability.py::append_framework_event` so the hash
chain stays intact and the framework's existing audit consumers see memory
operations alongside skill_invoked, agent_dispatched, and friends.

Per CONCERN-1 from the pre-dispatch guard advisory: the runtime gate
(`_ALLOWED_KINDS`) discriminates on `kind`; the legacy audit-event JSON
schema discriminates on `event`. They govern different streams. This module
emits to `framework-events.ndjson` via `kind`; the `event` field stays absent
because the live framework writer never sets it. Schema validation against
the legacy `audit-log.ndjson` schema (which is retained only for historical
read of the legacy stream) is therefore not exercised on this path.

Per WARN-6: `source` is `"cli"` for CLI-invoked operations and `"hook"` for
hook-invoked operations. No new `source` enum value is introduced.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

# The hook _lib lives next to memory/. Inject the hooks dir on the import path
# so we can reuse the canonical observability module without duplication.
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.observability import (  # noqa: E402  (path injection above)
    append_framework_event,
    build_framework_event,
)

_COMPONENT = "memory"
_DEFAULT_ENGINE = "claude_code"


class Operation(str, Enum):
    """Memory event sub-operations (D-118-01: single kind, sub-discriminated)."""

    EPISODE_STORED = "episode_stored"
    KNOWLEDGE_OBJECT_ADDED = "knowledge_object_added"
    MEMORY_RETRIEVED = "memory_retrieved"
    DREAM_RUN = "dream_run"
    DECAY_APPLIED = "decay_applied"
    KNOWLEDGE_OBJECT_PROMOTED = "knowledge_object_promoted"
    KNOWLEDGE_OBJECT_RETIRED = "knowledge_object_retired"


def _now() -> str:
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(
    project_root: Path,
    *,
    operation: Operation,
    engine: str = _DEFAULT_ENGINE,
    source: str = "cli",
    detail: dict[str, Any] | None = None,
    session_id: str | None = None,
    correlation_id: str | None = None,
    component: str = _COMPONENT,
) -> dict:
    """Emit one `memory_event` audit record.

    Returns the on-disk dict for callers that want to introspect the chain
    pointer or the canonical timestamp. Side effect: appends a line to
    `framework-events.ndjson`.
    """
    if source not in {"cli", "hook"}:
        msg = f"memory.audit.emit refuses unknown source: {source!r}"
        raise ValueError(msg)

    payload: dict[str, Any] = {"operation": operation.value}
    if detail:
        payload.update(detail)

    entry = build_framework_event(
        project_root,
        engine=engine,
        kind="memory_event",
        component=component,
        detail=payload,
        source=source,
        session_id=session_id,
        correlation_id=correlation_id,
    )
    append_framework_event(project_root, entry)
    return entry


# ---------------------------------------------------------------------------
# Convenience helpers (one per operation; keeps the call sites readable)
# ---------------------------------------------------------------------------


def emit_episode_stored(
    project_root: Path,
    *,
    episode_id: str,
    embedding_status: str,
    duration_ms: int,
    source: str = "hook",
    session_id: str | None = None,
    correlation_id: str | None = None,
) -> dict:
    return emit(
        project_root,
        operation=Operation.EPISODE_STORED,
        source=source,
        detail={
            "episode_id": episode_id,
            "embedding_status": embedding_status,
            "duration_ms": duration_ms,
        },
        session_id=session_id,
        correlation_id=correlation_id,
    )


def emit_knowledge_object_added(
    project_root: Path,
    *,
    ko_hash: str,
    ko_kind: str,
    source: str = "cli",
    session_id: str | None = None,
) -> dict:
    return emit(
        project_root,
        operation=Operation.KNOWLEDGE_OBJECT_ADDED,
        source=source,
        detail={"ko_hash": ko_hash, "ko_kind": ko_kind},
        session_id=session_id,
    )


def emit_memory_retrieved(
    project_root: Path,
    *,
    retrieval_id: str,
    query_hash: str,
    top_k: int,
    result_count: int,
    duration_ms: int,
    source: str = "cli",
    session_id: str | None = None,
) -> dict:
    return emit(
        project_root,
        operation=Operation.MEMORY_RETRIEVED,
        source=source,
        detail={
            "retrieval_id": retrieval_id,
            "query_hash": query_hash,
            "top_k": top_k,
            "result_count": result_count,
            "duration_ms": duration_ms,
        },
        session_id=session_id,
    )


def emit_dream_run(
    project_root: Path,
    *,
    decay_factor: float,
    clusters_found: int,
    promoted_count: int,
    retired_count: int,
    duration_ms: int,
    outcome: str | None = None,
    source: str = "cli",
) -> dict:
    detail = {
        "decay_factor": decay_factor,
        "clusters_found": clusters_found,
        "promoted_count": promoted_count,
        "retired_count": retired_count,
        "duration_ms": duration_ms,
    }
    if outcome is not None:
        detail["outcome"] = outcome
    return emit(
        project_root,
        operation=Operation.DREAM_RUN,
        source=source,
        detail=detail,
    )


def emit_decay_applied(
    project_root: Path,
    *,
    decay_factor: float,
    result_count: int,
    duration_ms: int,
    source: str = "cli",
) -> dict:
    return emit(
        project_root,
        operation=Operation.DECAY_APPLIED,
        source=source,
        detail={
            "decay_factor": decay_factor,
            "result_count": result_count,
            "duration_ms": duration_ms,
        },
    )


def emit_ko_promoted(project_root: Path, *, ko_hash: str, source: str = "cli") -> dict:
    return emit(
        project_root,
        operation=Operation.KNOWLEDGE_OBJECT_PROMOTED,
        source=source,
        detail={"ko_hash": ko_hash},
    )


def emit_ko_retired(project_root: Path, *, ko_hash: str, source: str = "cli") -> dict:
    return emit(
        project_root,
        operation=Operation.KNOWLEDGE_OBJECT_RETIRED,
        source=source,
        detail={"ko_hash": ko_hash},
    )
