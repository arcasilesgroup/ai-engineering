"""Event sidecar overflow (spec-122-b T-2.7 / D-122-23).

Cross-IDE concurrent writers append to ``framework-events.ndjson`` via
POSIX ``O_APPEND``. POSIX guarantees atomic append for writes ≤ ``PIPE_BUF``
(4 KB on Linux/macOS). To stay safely under that ceiling we cap every
inline NDJSON line at **3 KB**; any event whose serialised JSON exceeds
that ceiling is offloaded to ``runtime/event-sidecars/<sha256>.json``
and the inline NDJSON line carries only the hash + a short summary.

Public surface
--------------
* ``SIDECAR_CEILING_BYTES`` -- the 3072-byte constant.
* :func:`maybe_offload(event_dict, project_root=None)` -- returns either
  the original dict (≤ ceiling) or a shrunken dict carrying
  ``{"sidecar_sha256", "summary", "kind", "timestamp"}``.

The sidecar file path is **content-addressed**: identical input bytes
produce the same path, so duplicate events are coalesced for free.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

# 3 KB ceiling. Headroom under the 4 KB POSIX_BUF guarantee for safety
# margin (timestamps, line terminator, future schema additions).
SIDECAR_CEILING_BYTES = 3072

# spec-125 Wave 2 (T-2.21): canonical runtime dir is ``.ai-engineering/runtime``
# (per ``hook_context.RUNTIME_DIR`` SSOT). Literal duplicated here to avoid
# CLI/state→hook-lib import boundary violation; same pattern as
# ``cli_commands/gate.py`` cache_dir resolution (T-2.13).
_SIDECAR_DIR_REL = Path(".ai-engineering") / "runtime" / "event-sidecars"


def _serialize(event: dict[str, Any]) -> bytes:
    """Canonical-JSON encoding (sorted keys, compact separators)."""
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _summary_for(event: dict[str, Any], max_chars: int = 160) -> str:
    """Build a stable one-line summary for the inline event."""
    kind = event.get("kind") or "unknown"
    component = event.get("component") or ""
    detail = event.get("detail")
    detail_summary: str
    if isinstance(detail, dict):
        # Pick a few interesting fields if present.
        fragments = []
        for key in ("operation", "tool", "skill", "agent", "error_code"):
            val = detail.get(key)
            if isinstance(val, str) and val:
                fragments.append(f"{key}={val}")
        detail_summary = " ".join(fragments) if fragments else f"keys={','.join(sorted(detail))}"
    elif isinstance(detail, list):
        detail_summary = f"list[{len(detail)}]"
    else:
        detail_summary = ""
    base = f"[{kind}@{component}] {detail_summary}".strip()
    return base[:max_chars]


def _resolve_sidecar_dir(project_root: Path | None = None) -> Path:
    if project_root is None:
        project_root = Path.cwd()
    return project_root / _SIDECAR_DIR_REL


def maybe_offload(
    event: dict[str, Any],
    *,
    project_root: Path | None = None,
    ceiling: int = SIDECAR_CEILING_BYTES,
) -> dict[str, Any]:
    """Offload an oversized event to sidecar; return the inline replacement.

    If the serialised event is at or below ``ceiling`` bytes, returns the
    original dict unchanged. Otherwise writes the full event to
    ``runtime/event-sidecars/<sha256>.json`` and returns a small
    inline dict carrying the hash + summary.
    """
    payload = _serialize(event)
    if len(payload) <= ceiling:
        return event

    digest = hashlib.sha256(payload).hexdigest()
    sidecar_dir = _resolve_sidecar_dir(project_root)
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    sidecar_path = sidecar_dir / f"{digest}.json"
    if not sidecar_path.exists():
        # Atomic write via tmp + rename (no partial-write windows on
        # Crash/concurrent open).
        tmp_path = sidecar_path.with_suffix(".json.tmp")
        tmp_path.write_bytes(payload)
        os.replace(tmp_path, sidecar_path)

    inline: dict[str, Any] = {
        "kind": event.get("kind") or "unknown",
        "engine": event.get("engine") or "unknown",
        "component": event.get("component") or "unknown",
        "outcome": event.get("outcome") or "success",
        "timestamp": event.get("timestamp") or "",
        "sidecar_sha256": digest,
        "sidecar_size_bytes": len(payload),
        "summary": _summary_for(event),
    }
    # Preserve correlation/trace pointers so audit-chain reasoning still
    # works on the projection.
    for key in ("correlationId", "correlation_id", "session_id", "trace_id", "prev_event_hash"):
        if key in event and event[key] is not None:
            inline[key] = event[key]
    return inline


__all__ = [
    "SIDECAR_CEILING_BYTES",
    "maybe_offload",
]
