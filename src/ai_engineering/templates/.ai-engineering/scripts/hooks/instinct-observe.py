#!/usr/bin/env python3
"""Pre/PostToolUse hook: append sanitized observations for instinct learning.

Fail-open: exit 0 always and preserve hook chaining for all IDEs.

spec-139 M5.T2: per-process write batching. The PreToolUse + PostToolUse
hooks both fire on every tool call, so naive flush-per-event doubles
the NDJSON write rate for the instinct ratchet. We accumulate
observations in a module-scope buffer and flush only when:

  - ``_OBSERVATION_BUFFER`` reaches 50 entries, OR
  - 5 seconds have elapsed since the last flush, OR
  - the host hook is a ``stop`` event (SubagentStop natural drain point).

A single flush call appends every buffered NDJSON line in one write,
turning N file appends into 1. Failure-mode: if a flush raises (disk
full, lock contention, corrupt meta), the buffered events stay in
``_OBSERVATION_BUFFER`` and the next invocation retries — we never
crash the host hook or drop the observation entirely.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import contextlib

from _lib.audit import passthrough_stdin
from _lib.hook_common import run_hook_safe
from _lib.hook_context import get_hook_context
from _lib.instincts import append_instinct_observation

_SUPPORTED_EVENTS = {"PreToolUse", "PostToolUse"}

# spec-139 M5.T2: per-process batch. Each entry is the kwargs dict for
# ``append_instinct_observation`` so we can defer the actual write to
# the next flush trigger. The buffer is intentionally append-only so a
# failed flush keeps the events for the next attempt.
_OBSERVATION_BUFFER: list[dict[str, Any]] = []
_BUFFER_LAST_FLUSH: float = 0.0
_BUFFER_MAX_EVENTS = 50
_BUFFER_MAX_AGE_SEC = 5.0


def _should_flush(now: float, hook_kind: str | None) -> bool:
    """Return True when at least one flush trigger has fired.

    Triggers (any one is sufficient):
      - SubagentStop / Stop event (drain on natural cascade point).
      - Buffer has reached the 50-entry threshold.
      - 5 seconds since last flush (or first call after import).
    """
    if hook_kind == "stop":
        return True
    if len(_OBSERVATION_BUFFER) >= _BUFFER_MAX_EVENTS:
        return True
    if _BUFFER_LAST_FLUSH == 0.0:
        # First flush after import — fire as soon as anything is queued
        # so a single observation isn't held for the full 5 s window.
        return len(_OBSERVATION_BUFFER) > 0
    return (now - _BUFFER_LAST_FLUSH) >= _BUFFER_MAX_AGE_SEC


def _flush_observations() -> None:
    """Drain the buffer through ``append_instinct_observation``.

    On success the buffer is cleared and ``_BUFFER_LAST_FLUSH`` advances.
    On partial failure the failing entry stays at the head of the queue
    so the next call can retry — we never silently drop observations.
    Errors raised by ``append_instinct_observation`` itself are
    swallowed (it already has its own fail-open contract), but a
    process-level exception (KeyboardInterrupt etc.) propagates.
    """
    global _BUFFER_LAST_FLUSH
    if not _OBSERVATION_BUFFER:
        _BUFFER_LAST_FLUSH = time.monotonic()
        return
    # Snapshot then iterate; on any unhandled failure we re-insert the
    # remaining entries so the next flush retries them in order.
    pending = list(_OBSERVATION_BUFFER)
    _OBSERVATION_BUFFER.clear()
    for idx, kwargs in enumerate(pending):
        try:
            append_instinct_observation(**kwargs)
        except Exception:
            # Re-queue this entry and everything after it; preserve order.
            _OBSERVATION_BUFFER[:0] = pending[idx:]
            return
    _BUFFER_LAST_FLUSH = time.monotonic()


def _enqueue_observation(
    *,
    project_root: Path,
    engine: str,
    hook_event: str,
    data: dict[str, Any],
    session_id: str | None,
) -> None:
    """Append the observation kwargs to the buffer (no I/O)."""
    _OBSERVATION_BUFFER.append(
        {
            "project_root": project_root,
            "engine": engine,
            "hook_event": hook_event,
            "data": data,
            "session_id": session_id,
        }
    )


def _disable_batching() -> bool:
    """Allow tests / debug runs to opt out of batching via env var.

    ``AIENG_INSTINCT_BATCH_DISABLED=1`` reverts to the legacy
    flush-per-event behaviour. Default is batched (production path).
    """
    return (os.environ.get("AIENG_INSTINCT_BATCH_DISABLED") or "").strip() == "1"


def main() -> None:
    ctx = get_hook_context()

    if ctx.event_name not in _SUPPORTED_EVENTS:
        # Stop-class events still drain the queue so observations don't
        # linger past session end (SubagentStop / Stop). The spec wires
        # this hook only for Pre/PostToolUse, but defence in depth keeps
        # the contract correct if a future SessionEnd path imports this
        # module.
        if ctx.event_name in ("Stop", "SubagentStop"):
            with contextlib.suppress(Exception):
                _flush_observations()
        passthrough_stdin(ctx.data)
        return

    if _disable_batching():
        append_instinct_observation(
            ctx.project_root,
            engine=ctx.engine,
            hook_event=ctx.event_name,
            data=ctx.data,
            session_id=ctx.session_id,
        )
        passthrough_stdin(ctx.data)
        return

    _enqueue_observation(
        project_root=ctx.project_root,
        engine=ctx.engine,
        hook_event=ctx.event_name,
        data=ctx.data,
        session_id=ctx.session_id,
    )

    # ``hook_kind`` cue: the runner passes ``post-tool-use`` here, but we
    # also flush whenever the buffer threshold or 5 s wall-clock window
    # fires. SubagentStop integration: see the early-return branch above.
    if _should_flush(time.monotonic(), hook_kind=None):
        # _flush_observations re-queues remaining entries on failure
        # but a guard against unforeseen wrapper exceptions keeps the
        # hook fail-open per the module contract.
        with contextlib.suppress(Exception):
            _flush_observations()

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main, component="hook.instinct-observe", hook_kind="post-tool-use", script_path=__file__
    )
