"""Tests for the bounded-retry context-manager primitive (spec-126 T-3.0).

Covers two behaviors of ``with_lock_retry`` (in
``.ai-engineering/scripts/hooks/_lib/locked_append.py``):

1. First-attempt success — context yields ``True``, no telemetry.
2. Three failures — context yields ``False`` (fail-open), exactly one
   ``framework_error`` line written to the canonical
   ``lock-failures.ndjson`` sidecar.

The context manager is the primitive used by the three migrated
``framework-events.ndjson`` writers (T-3.3 / T-3.4 / T-3.5) so that
``prev_event_hash`` can be computed INSIDE the lock — preventing the
TOCTOU race the spec exists to fix.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_LIB = _REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib"


@pytest.fixture
def lib(monkeypatch: pytest.MonkeyPatch):
    """Load the ``_lib.locked_append`` and ``_lib.locking`` modules.

    Hook scripts are loaded by file path (the ``_lib`` directory is not
    a pip-installed package). We bind both modules under a stable
    parent package name ``_lib`` so the helper's
    ``from _lib import locking`` resolves.
    """
    hooks_dir = _HOOKS_LIB.parent  # .ai-engineering/scripts/hooks
    monkeypatch.syspath_prepend(str(hooks_dir))

    for mod_name in ("_lib.locking", "_lib.locked_append", "_lib"):
        sys.modules.pop(mod_name, None)

    locking = importlib.import_module("_lib.locking")
    locked_append = importlib.import_module("_lib.locked_append")
    return locked_append, locking


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state" / "locks").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _sidecar(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "lock-failures.ndjson"


def test_with_lock_retry_yields_true_on_first_acquire(
    lib,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lock succeeds on first try → context yields True; no telemetry."""
    locked_append_mod, locking_mod = lib

    real_acquire = locking_mod._acquire_lock
    calls = {"count": 0}

    def spy_acquire(handle):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        return real_acquire(handle)

    monkeypatch.setattr(locking_mod, "_acquire_lock", spy_acquire)

    seen_locked: list[bool] = []
    with locked_append_mod.with_lock_retry(project_root, "framework-events") as locked:
        seen_locked.append(locked)

    assert seen_locked == [True]
    assert calls["count"] == 1
    assert not _sidecar(project_root).exists(), "no telemetry expected on first-attempt success"


def test_with_lock_retry_yields_false_after_max_retries_with_telemetry(
    lib,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3 OSError → context yields False; exactly one sidecar entry written."""
    locked_append_mod, locking_mod = lib

    state = {"calls": 0}

    def always_fail(handle):  # type: ignore[no-untyped-def]
        state["calls"] += 1
        raise OSError("persistent-toctou")

    monkeypatch.setattr(locking_mod, "_acquire_lock", always_fail)

    seen_locked: list[bool] = []
    with locked_append_mod.with_lock_retry(project_root, "framework-events") as locked:
        seen_locked.append(locked)

    assert seen_locked == [False], "fail-open path must yield False"
    assert state["calls"] == 3, "expected exactly 3 acquisition attempts"

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
    assert "persistent-toctou" in err["detail"].get("summary", "")
