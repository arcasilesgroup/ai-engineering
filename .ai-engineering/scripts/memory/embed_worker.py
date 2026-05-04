"""spec-118 T-3.2 deferred → harness gap closure 2026-05-04 (P2.2): async embedding worker.

Polls ``episodes WHERE embedding_status='pending'``, batches calls to
``semantic.embed_and_upsert_episode`` (which lazy-loads fastembed and
writes to the sqlite-vec ``memory_vectors`` table), and updates the
status to ``complete`` (or ``failed`` if vec0 is unavailable / the
ONNX model returns the wrong dim).

The worker is designed for two deployment modes:

* **One-shot** (``ai-eng memory embed --once``): processes the current
  pending queue and exits. Suitable for cron / launchd / systemd timers.
  Recommended cadence: every 5 minutes when no daemon is running.

* **Daemon** (``ai-eng memory embed --daemon``): poll-sleep loop that
  runs forever; SIGTERM-safe (catches the signal and exits between
  batches). Suitable for environments that already manage long-running
  processes (kubernetes, supervisor, etc.).

Hot-path guard: the module raises ``HotPathInvocationError`` at run-once
entry if ``AIENG_HOOK_RUNTIME=1`` is set, mirroring the existing
convention in ``semantic.py`` so a future hook author doesn't accidentally
import the worker into a runtime hook.

The worker is idempotent: re-running ``--once`` against an empty queue
exits 0 with no side effects. Per-row failures (vec0 missing, dim
mismatch, ONNX runtime error) flip the row to ``embedding_status='failed'``
so subsequent sweeps skip it instead of looping forever.
"""

from __future__ import annotations

import os
import signal
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# This module lives at .ai-engineering/scripts/memory/embed_worker.py.
# When invoked as `python3 -m memory.embed_worker` from the canonical
# ai-eng entry point, the parent package is reachable on sys.path; we
# also add it explicitly here so direct invocations (`python3
# embed_worker.py`) work for ad-hoc operator use.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR.parent) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR.parent))

from memory.semantic import HotPathInvocationError  # noqa: E402


@dataclass(frozen=True)
class EmbedRunReport:
    """Summary of a single ``run_once`` invocation."""

    processed: int
    succeeded: int
    failed: int
    duration_ms: int


def _assert_not_hot_path() -> None:
    """Refuse to run from inside a runtime hook (cold-load is multi-100ms)."""
    if os.environ.get("AIENG_HOOK_RUNTIME") == "1":
        msg = (
            "embed_worker must not run inside a runtime hook "
            "(AIENG_HOOK_RUNTIME=1 set). Schedule it via cron or invoke "
            "ai-eng memory embed --once from the CLI instead."
        )
        raise HotPathInvocationError(msg)


def _pending_episode_ids(conn: sqlite3.Connection, *, batch_size: int) -> list[tuple[str, str]]:
    """Return up to ``batch_size`` ``(episode_id, summary)`` tuples awaiting embedding."""
    cur = conn.execute(
        """
        SELECT episode_id, summary
        FROM episodes
        WHERE embedding_status = 'pending'
        ORDER BY started_at ASC
        LIMIT ?
        """,
        (batch_size,),
    )
    return [(row[0], row[1]) for row in cur.fetchall()]


def run_once(project_root: Path, *, batch_size: int = 32) -> EmbedRunReport:
    """Embed up to ``batch_size`` pending episodes. Returns a run report.

    The function is fail-soft: per-row exceptions are caught and the
    row is flipped to ``embedding_status='failed'`` so subsequent sweeps
    skip it. A run with zero pending rows returns
    ``EmbedRunReport(0, 0, 0, ...)`` and exits 0.
    """
    _assert_not_hot_path()
    from memory import semantic, store

    t0 = time.monotonic()
    processed = 0
    succeeded = 0
    failed = 0

    store.bootstrap(project_root)
    with store.connect(project_root) as conn:
        pending = _pending_episode_ids(conn, batch_size=batch_size)
    if not pending:
        return EmbedRunReport(
            processed=0,
            succeeded=0,
            failed=0,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    for episode_id, summary in pending:
        processed += 1
        try:
            rowid = semantic.embed_and_upsert_episode(
                project_root, episode_id=episode_id, text=summary or ""
            )
        except Exception as exc:
            # The semantic layer flips the row to 'failed' for vec0
            # absence; a pure ONNX/runtime failure ends up here. Mark
            # the row failed and emit telemetry so the operator knows
            # to investigate.
            failed += 1
            try:
                with store.connect(project_root) as conn:
                    conn.execute(
                        "UPDATE episodes SET embedding_status = 'failed' WHERE episode_id = ?",
                        (episode_id,),
                    )
                    conn.commit()
            except Exception:
                pass
            try:
                from memory import audit

                audit.emit(
                    project_root,
                    operation=audit.Operation.EPISODE_STORED,
                    source="cli",
                    detail={
                        "episode_id": episode_id,
                        "embedding_status": "failed",
                        "failure_reason": str(exc)[:200],
                        "embed_worker": True,
                    },
                )
            except Exception:
                pass
            continue
        if rowid is None:
            # ``embed_and_upsert_episode`` already flipped the row to
            # 'failed' (vec0 unavailable, dim mismatch on rebuild path).
            failed += 1
        else:
            succeeded += 1

    return EmbedRunReport(
        processed=processed,
        succeeded=succeeded,
        failed=failed,
        duration_ms=int((time.monotonic() - t0) * 1000),
    )


def run_daemon(
    project_root: Path,
    *,
    poll_interval_sec: int = 60,
    batch_size: int = 32,
) -> None:  # pragma: no cover - run_once is the unit-tested surface
    """Long-running poll loop. SIGTERM exits cleanly between batches.

    Not unit-tested directly; the loop body is just ``run_once`` plus
    sleep, and run_once carries the meaningful semantics.
    """
    _assert_not_hot_path()
    stop = {"flag": False}

    def _on_signal(_signum, _frame) -> None:  # pragma: no cover
        stop["flag"] = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    while not stop["flag"]:
        # Daemon must never die on a transient error. Per-row failures
        # are already swallowed inside run_once; this outer guard
        # catches sqlite-locked / disk-full / etc.
        import contextlib

        with contextlib.suppress(Exception):
            run_once(project_root, batch_size=batch_size)
        # Sleep in 1s slices so SIGTERM is noticed within ~1s.
        for _ in range(max(1, poll_interval_sec)):
            if stop["flag"]:
                break
            time.sleep(1)


__all__ = ["EmbedRunReport", "run_daemon", "run_once"]
