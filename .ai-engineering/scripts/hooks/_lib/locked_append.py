"""Bounded-retry NDJSON append helper for hook-side audit-grade writers.

Spec-126 D-126-05: closes the hook-side multi-IDE concurrent-append race
(POSIX ``O_APPEND`` masks the bug locally, Windows offers no atomic
guarantee). Wraps a single-line append in
``artifact_lock(project_root, lock_name)`` with bounded retry. On
exhaustion, falls open: appends unlocked and records a
``framework_error`` to a sidecar ``lock-failures.ndjson`` artifact so
the failure record cannot itself recurse into the same race.

The helper is intentionally placed in its OWN module rather than added
to ``_lib/locking.py`` so that the byte-level parity gate
(``tests/unit/hooks/test_locking_parity.py``, spec-126 D-126-01) keeps
``_lib/locking.py`` a pure mirror of the pkg-side primitive.

Phase 3 (spec-126 T-3.0) added :func:`with_lock_retry` — a context
manager mirror of :func:`locked_append` that exposes the lock-acquired
state to the caller. Writers that compute ``prev_event_hash`` from the
file tail must hold the lock while computing the hash AND writing
(otherwise two concurrent writers can observe the same prev value and
append duplicate-pointer entries — the same TOCTOU the spec exists to
fix). :func:`locked_append` is preserved as a thin wrapper for simple
single-line writers.

Stdlib + ``_lib.locking`` only — no transitive ``ai_engineering``
package imports (Article V hook-standalone contract).
"""

from __future__ import annotations

import contextlib
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from _lib import locking as _locking

__all__ = ["locked_append", "with_lock_retry"]


_LOCK_FAILURE_SIDECAR_NAME = "lock-failures.ndjson"
_FRAMEWORK_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


def _sidecar_path(target: Path) -> Path:
    """Return the sidecar path for fail-open telemetry next to ``target``.

    Co-locates the ``lock-failures.ndjson`` sidecar in the same directory
    as the target NDJSON so a single ``state/`` mount captures both the
    primary chain and the failure breadcrumbs.
    """
    return target.with_name(_LOCK_FAILURE_SIDECAR_NAME)


def _emit_lock_failure(
    target: Path,
    lock_name: str,
    max_retries: int,
    err: BaseException,
) -> None:
    """Write a single ``framework_error`` line to the sidecar.

    Uses a bare ``open("a")`` — emitting through ``append_framework_event``
    would re-enter the same lock that just failed and risk infinite
    recursion. The sidecar artifact is dedicated to lock-failure
    breadcrumbs and is not part of the audit hash chain.
    """
    sidecar = _sidecar_path(target)
    try:
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "schema_version": "1.0",
            "event_id": str(uuid4()),
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "engine": "ai_engineering",
            "kind": "framework_error",
            "outcome": "failure",
            "component": "hooks._lib.locking",
            "detail": {
                "error_code": "lock_acquisition_failed",
                "summary": str(err)[:200],
                "lock_name": lock_name,
                "max_retries": max_retries,
            },
        }
        line = json.dumps(entry, sort_keys=True)
        with sidecar.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        # The sidecar emit is best-effort breadcrumb telemetry; never
        # raise into the hot path on failure to record a failure.
        return


@contextmanager
def with_lock_retry(
    project_root: Path,
    lock_name: str,
    *,
    max_retries: int = 3,
    backoff_ms: int = 50,
) -> Iterator[bool]:
    """Acquire ``artifact_lock(lock_name)`` with bounded retry.

    Yields ``True`` if the lock was acquired (caller's block runs under
    mutual exclusion). Yields ``False`` if all retries failed (caller's
    block runs without protection — fail-open). On the fail-open path,
    emits one ``framework_error`` event with
    ``detail.error_code = "lock_acquisition_failed"`` to the sidecar
    ``lock-failures.ndjson`` (NOT to ``framework-events.ndjson`` — the
    failed lock is on framework-events itself, recursion would be
    fatal).

    On normal exit (locked path), releases the lock. On fail-open path,
    no release needed (lock was never held). Exceptions in the caller's
    block propagate after the lock is released.

    The sidecar is co-located with the canonical
    ``framework-events.ndjson`` path under
    ``.ai-engineering/state/`` regardless of which caller invokes this
    primitive — the chain writers that use :func:`with_lock_retry` all
    operate on the canonical events file, so a single fixed sidecar
    location is the desirable surface here.

    This deliberately diverges from :func:`locked_append`, which emits
    its sidecar adjacent to the caller-supplied ``path``. The two
    primitives serve different audiences (chain writers vs. generic
    single-line appenders) and the sidecar location reflects that.
    """
    lock_path = _locking.artifact_lock_path(project_root, lock_name)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: BaseException | None = None
    handle = None
    locked = False
    for attempt in range(1, max_retries + 1):
        try:
            handle = lock_path.open("a+b")
            _locking._seed_lock_file(handle)
            _locking._acquire_lock(handle)
            locked = True
            break
        except OSError as err:
            last_error = err
            if handle is not None:
                with contextlib.suppress(OSError):
                    handle.close()
                handle = None
            if attempt < max_retries:
                time.sleep(backoff_ms / 1000)
            continue

    if locked:
        try:
            yield True
        finally:
            with contextlib.suppress(OSError):
                _locking._release_lock(handle)  # type: ignore[arg-type]
            if handle is not None:
                with contextlib.suppress(OSError):
                    handle.close()
        return

    # Exhausted retries — fall open. Emit telemetry then yield False so
    # the caller still performs its work (preserves fail-open posture).
    if last_error is not None:
        target = project_root / _FRAMEWORK_EVENTS_REL
        _emit_lock_failure(target, lock_name, max_retries, last_error)
    yield False


def locked_append(
    project_root: Path,
    path: Path,
    line: str,
    lock_name: str,
    *,
    max_retries: int = 3,
    backoff_ms: int = 50,
) -> bool:
    """Append a single line to ``path`` under ``artifact_lock(lock_name)``.

    Bounded retry: tries to acquire the lock up to ``max_retries`` times
    with ``backoff_ms`` ms between attempts. On final failure, falls
    open: writes the line unlocked, emits a ``framework_error`` event
    with ``detail.error_code = "lock_acquisition_failed"`` to the
    ``lock-failures.ndjson`` sidecar next to ``path``, and returns
    ``False``. On success, returns ``True``.

    The line is written exactly as given plus a single trailing newline.
    The caller is responsible for hash-chain stamping (caller must
    compute ``prev_event_hash`` inside the same critical section by
    using :func:`with_lock_retry` directly if needed; this helper
    provides only the append primitive for simple single-line writers).

    Implementation note (spec-126 T-3.0): this function intentionally
    duplicates the acquire-retry-fail-open loop from
    :func:`with_lock_retry` rather than delegating to it. The
    duplication preserves a per-call invariant required by the
    Phase-2 sidecar contract: the fail-open sidecar
    (``lock-failures.ndjson``) is emitted **next to** ``path`` for
    generic callers. :func:`with_lock_retry`, by contrast, always
    emits its sidecar adjacent to the canonical
    ``framework-events.ndjson`` because it is only used by chain
    writers operating on that file. Consolidating into a single
    primitive would force all callers into one sidecar location;
    keeping the loops parallel preserves both surfaces while sharing
    the helper primitives (``_emit_lock_failure``, ``_locking``).
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lock_path = _locking.artifact_lock_path(project_root, lock_name)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: BaseException | None = None
    for attempt in range(1, max_retries + 1):
        try:
            with lock_path.open("a+b") as handle:
                _locking._seed_lock_file(handle)
                _locking._acquire_lock(handle)
                try:
                    with path.open("a", encoding="utf-8") as fh:
                        fh.write(line + "\n")
                finally:
                    _locking._release_lock(handle)
            return True
        except OSError as err:
            last_error = err
            if attempt < max_retries:
                time.sleep(backoff_ms / 1000)
            continue

    # Exhausted retries — fall open. Append unlocked so the user-visible
    # work continues, then emit a breadcrumb to the sidecar.
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        # If even the unlocked append fails the caller has bigger
        # problems; still try to emit the failure breadcrumb below.
        pass

    if last_error is not None:
        _emit_lock_failure(path, lock_name, max_retries, last_error)
    return False
