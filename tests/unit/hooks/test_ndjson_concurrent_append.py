"""Concurrent stress test for hook-side NDJSON appenders (spec-126 T-3.1).

Spawns N=8 worker processes via ``multiprocessing.Pool``, each appending
M=50 events to ``framework-events.ndjson`` via the hook-side
``append_framework_event``. Post-run assertions:

1. Total line count == N * M.
2. Every line parses as JSON.
3. Audit hash chain is valid end-to-end (validates via a stdlib
   re-implementation of ``compute_entry_hash`` so the test does not
   require the hook layer to import the ``ai_engineering`` package).
4. End-to-end wall-clock <= 30 s.

Marked ``@pytest.mark.slow`` so it's skipped from the default unit
sweep but executed on the cross-OS hooks matrix per spec-126 D-126-03.

Each worker process must reload the hook ``_lib`` modules from a fresh
``sys.path`` entry — child processes from ``multiprocessing`` (spawn
context on macOS / Windows) start with an empty module cache for the
ad-hoc ``_lib`` package.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks"

N_WORKERS = 8
M_PER_WORKER = 50
TOTAL_EVENTS = N_WORKERS * M_PER_WORKER
WALL_CLOCK_BUDGET_S = 30.0


def _worker_append(args: tuple[str, int, int]) -> int:
    """Worker entry point — appends ``count`` events under worker-local IDs."""
    project_root_str, worker_idx, count = args
    project_root = Path(project_root_str)

    # Ensure the hook _lib package is importable in this child process.
    if str(_HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(_HOOKS_DIR))

    # Fresh import so monkeypatched state from a parent test (if any)
    # doesn't leak across spawn boundary.
    for mod_name in list(sys.modules):
        if mod_name == "_lib" or mod_name.startswith("_lib."):
            del sys.modules[mod_name]

    from _lib.observability import append_framework_event

    written = 0
    for i in range(count):
        entry = {
            "schemaVersion": "1.0",
            "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "project": project_root.name,
            "engine": "claude_code",
            "kind": "skill_invoked",
            "outcome": "success",
            "component": "hook.test_concurrent",
            "correlationId": uuid4().hex,
            "detail": {
                "worker": worker_idx,
                "seq": i,
                "pid": os.getpid(),
            },
        }
        append_framework_event(project_root, entry)
        written += 1
    return written


def _compute_entry_hash(event: dict) -> str:
    """Stdlib mirror of ``ai_engineering.state.audit_chain.compute_entry_hash``.

    Stripping ``prev_event_hash`` / ``prevEventHash`` matches the canonical
    rule so the hash chain validates round-trip on the round-tripped
    pointer.
    """
    stripped = {k: v for k, v in event.items() if k not in ("prev_event_hash", "prevEventHash")}
    canonical = json.dumps(stripped, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_chain(path: Path) -> tuple[bool, str | None, int]:
    """Walk the NDJSON file and verify each event's prev_event_hash."""
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return True, None, 0

    lines = text.strip().splitlines()
    prior_hash: str | None = None
    for lineno, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            return False, f"line {lineno}: malformed JSON: {exc}", lineno
        declared = event.get("prev_event_hash")
        if lineno == 1:
            # First event establishes anchor; declared may be None.
            prior_hash = _compute_entry_hash(event)
            continue
        if declared != prior_hash:
            return (
                False,
                f"line {lineno}: chain break — declared={declared!r} expected={prior_hash!r}",
                lineno,
            )
        prior_hash = _compute_entry_hash(event)
    return True, None, len(lines)


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state" / "locks").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.mark.slow
def test_concurrent_append_preserves_chain_integrity(project_root: Path) -> None:
    """NxM concurrent appends -> line count exact AND hash chain valid."""
    events_path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"

    # Use spawn context for cross-OS parity (macOS/Windows default).
    ctx = multiprocessing.get_context("spawn")
    args = [(str(project_root), worker_idx, M_PER_WORKER) for worker_idx in range(N_WORKERS)]

    start = time.monotonic()
    with ctx.Pool(N_WORKERS) as pool:
        results = pool.map(_worker_append, args)
    elapsed_s = time.monotonic() - start

    assert results == [M_PER_WORKER] * N_WORKERS, (
        f"each worker must report {M_PER_WORKER} writes; got {results}"
    )

    # Assertion (a): line count == N * M.
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == TOTAL_EVENTS, (
        f"expected {TOTAL_EVENTS} lines, got {len(lines)} — concurrent appends interleaved/lost"
    )

    # Assertion (b): every line parses as JSON.
    for lineno, raw in enumerate(lines, start=1):
        try:
            json.loads(raw)
        except json.JSONDecodeError as exc:
            pytest.fail(f"line {lineno} not valid JSON: {exc} — {raw[:120]!r}")

    # Assertion (c): audit chain validates end-to-end.
    valid, reason, last_line = _validate_chain(events_path)
    assert valid, f"chain validation failed: {reason} (validated up to line {last_line})"

    # Assertion (d): end-to-end wall-clock <= budget.
    assert elapsed_s <= WALL_CLOCK_BUDGET_S, (
        f"stress test exceeded {WALL_CLOCK_BUDGET_S}s budget: {elapsed_s:.2f}s"
    )
