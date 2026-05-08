"""Tests for the bounded-retry NDJSON append helper (spec-126 T-2.1).

Covers three behaviors of ``locked_append`` (in
``.ai-engineering/scripts/hooks/_lib/locked_append.py``):

1. First-attempt success — single write, no telemetry.
2. Two transient failures then success — retried write, no telemetry,
   total elapsed roughly 2 * 50 ms backoff.
3. Three failures — fail-open: unlocked append succeeds, a single
   ``framework_error`` event with ``detail.error_code =
   "lock_acquisition_failed"`` is emitted to the sidecar
   ``lock-failures.ndjson`` artifact, helper returns ``False``.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_LIB = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib"


@pytest.fixture
def lib(monkeypatch: pytest.MonkeyPatch):
    """Load the ``_lib.locked_append`` and ``_lib.locking`` modules.

    Hook scripts are loaded by file path (the ``_lib`` directory is not a
    pip-installed package). We bind both modules under a stable parent
    package name ``aieng_hooks_lib`` so the helper's lazy
    ``from _lib.locking import ...`` style imports resolve.
    """
    # Make the hooks/_lib parent directory importable as the package root
    # used by sibling modules in the helper.
    hooks_dir = _HOOKS_LIB.parent  # .ai-engineering/scripts/hooks
    monkeypatch.syspath_prepend(str(hooks_dir))

    # Drop any cached versions so monkeypatching the lock primitive sticks.
    for mod_name in ("_lib.locking", "_lib.locked_append", "_lib"):
        sys.modules.pop(mod_name, None)

    locking = importlib.import_module("_lib.locking")
    locked_append = importlib.import_module("_lib.locked_append")
    return locked_append, locking


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state" / "locks").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def target(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _sidecar(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "lock-failures.ndjson"


def test_locked_append_acquires_first_attempt_no_telemetry(
    lib,
    project_root: Path,
    target: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locked_append_mod, locking_mod = lib
    line = json.dumps({"k": "first", "n": 1}, sort_keys=True)

    real_acquire = locking_mod._acquire_lock
    calls = {"count": 0}

    def spy_acquire(handle):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        return real_acquire(handle)

    monkeypatch.setattr(locking_mod, "_acquire_lock", spy_acquire)

    result = locked_append_mod.locked_append(
        project_root,
        target,
        line,
        "framework-events",
    )

    assert result is True
    assert calls["count"] == 1
    lines = _read_lines(target)
    assert lines == [line]
    assert not _sidecar(project_root).exists(), "no telemetry expected on success"


def test_locked_append_retries_after_two_failures_then_succeeds(
    lib,
    project_root: Path,
    target: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locked_append_mod, locking_mod = lib
    line = json.dumps({"k": "retried", "n": 2}, sort_keys=True)

    real_acquire = locking_mod._acquire_lock
    state = {"calls": 0}

    def flaky_acquire(handle):  # type: ignore[no-untyped-def]
        state["calls"] += 1
        if state["calls"] <= 2:
            raise OSError("transient")
        return real_acquire(handle)

    monkeypatch.setattr(locking_mod, "_acquire_lock", flaky_acquire)

    start = time.monotonic()
    result = locked_append_mod.locked_append(
        project_root,
        target,
        line,
        "framework-events",
    )
    elapsed_ms = (time.monotonic() - start) * 1000

    assert result is True
    assert state["calls"] == 3, "expected 3 acquisition attempts"
    assert _read_lines(target) == [line]
    assert not _sidecar(project_root).exists(), (
        "no telemetry expected when retry eventually succeeds"
    )
    # Windows hosted runners take ~5x the POSIX wall-clock for the
    # same retry path (NTFS metadata flush per acquire). Widen the
    # ceiling there while keeping the POSIX assertion tight.
    upper_ms = 800 if sys.platform.startswith("win") else 400
    assert 90 <= elapsed_ms <= upper_ms, (
        f"expected ~100ms (2x50ms backoff) plus overhead, got {elapsed_ms:.1f}ms"
    )


def test_locked_append_three_failures_falls_back_unlocked_with_telemetry(
    lib,
    project_root: Path,
    target: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locked_append_mod, locking_mod = lib
    line = json.dumps({"k": "fallback", "n": 3}, sort_keys=True)

    state = {"calls": 0}

    def always_fail(handle):  # type: ignore[no-untyped-def]
        state["calls"] += 1
        raise OSError("persistent")

    monkeypatch.setattr(locking_mod, "_acquire_lock", always_fail)

    start = time.monotonic()
    result = locked_append_mod.locked_append(
        project_root,
        target,
        line,
        "framework-events",
    )
    elapsed_ms = (time.monotonic() - start) * 1000

    assert result is False, "fail-open path should return False"
    assert state["calls"] == 3, "expected exactly 3 acquisition attempts"
    assert _read_lines(target) == [line], (
        "unlocked fallback append must still write the line exactly once"
    )

    sidecar = _sidecar(project_root)
    assert sidecar.exists(), "framework_error must be emitted to sidecar on exhaustion"
    sidecar_lines = sidecar.read_text(encoding="utf-8").splitlines()
    assert len(sidecar_lines) == 1, "exactly one framework_error per fallback"
    err = json.loads(sidecar_lines[0])
    assert err["kind"] == "framework_error"
    assert err.get("outcome") == "failure"
    assert err["detail"]["error_code"] == "lock_acquisition_failed"
    assert err["detail"]["lock_name"] == "framework-events"
    assert err["detail"]["max_retries"] == 3
    assert "persistent" in err["detail"].get("summary", "")

    # Windows hosted runners take longer per acquire+sleep cycle than POSIX
    # tmpfs because of NTFS metadata churn; widen the ceiling there. The
    # POSIX assertion stays tight to catch real regressions.
    budget_ms = 800 if sys.platform.startswith("win") else 400
    assert elapsed_ms <= budget_ms, (
        f"fail-open path must stay within retry budget, got {elapsed_ms:.1f}ms"
    )
