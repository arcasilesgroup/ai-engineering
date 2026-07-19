"""Tests for the error/integrity storm coalescer (spec-190 D-190-02).

The coalescer lives in ``_lib/runtime_state.py`` and backs an atomic,
gitignored JSON sidecar under ``.ai-engineering/runtime/``. Its job is to
collapse the ~18k-event storms that ~10 real incidents produced into a
single full event per window plus periodic rollups, and to raise a storm
alarm once repeats cross ``AIENG_ERROR_STORM_THRESHOLD``.

Contract pinned here:
  * N identical fingerprints -> 1 full event + one rollup carrying occurrences.
  * Threshold crossing flips ``storm_triggered`` exactly once per window.
  * Window expiry resets the counter (fresh full event).
  * A corrupt sidecar fails open (behaves as first-occurrence: emit_full=True).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"
RUNTIME_STATE_PATH = HOOKS_DIR / "_lib" / "runtime_state.py"


@pytest.fixture
def rs(monkeypatch: pytest.MonkeyPatch):
    """Load runtime_state.py with a small storm threshold pinned."""
    monkeypatch.setenv("AIENG_ERROR_STORM_THRESHOLD", "5")
    monkeypatch.setenv("AIENG_HOOK_CACHE_TTL_SEC", "300")
    if str(HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(HOOKS_DIR))
    sys.modules.pop("aieng_runtime_state", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_state", RUNTIME_STATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_runtime_state"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _fp(rs, summary: str = "boom") -> str:
    return rs.error_fingerprint("hook.x", "hook_execution_failed", "sess-1", summary)


def test_first_occurrence_emits_full(rs, project: Path) -> None:
    fp = _fp(rs)
    out = rs.record_error(project, fp, component="hook.x", error_code="hook_execution_failed")
    assert out["emit_full"] is True
    assert out["occurrences"] == 1
    assert out["storm_triggered"] is False
    assert out["is_rollup"] is False


def test_repeats_coalesce_to_one_full_plus_rollup(rs, project: Path) -> None:
    """Five identical fingerprints (threshold=5) -> 1 full + 1 rollup."""
    fp = _fp(rs)
    results = [
        rs.record_error(project, fp, component="hook.x", error_code="hook_execution_failed")
        for _ in range(5)
    ]
    full = [r for r in results if r["emit_full"]]
    # First (full) + threshold-crossing rollup == 2 emits out of 5 records.
    assert len(full) == 2
    assert results[0]["is_rollup"] is False
    rollup = results[4]
    assert rollup["emit_full"] is True
    assert rollup["is_rollup"] is True
    assert rollup["occurrences"] == 5
    # The three middle occurrences are fully suppressed.
    assert [r["emit_full"] for r in results[1:4]] == [False, False, False]


def test_storm_triggered_exactly_once(rs, project: Path) -> None:
    fp = _fp(rs)
    triggered = [
        rs.record_error(project, fp, component="hook.x", error_code="hook_execution_failed")[
            "storm_triggered"
        ]
        for _ in range(12)
    ]
    assert triggered.count(True) == 1
    # It fires on the first crossing of the threshold (5th occurrence).
    assert triggered.index(True) == 4


def test_window_expiry_resets_counter(rs, project: Path) -> None:
    fp = _fp(rs)
    rs.record_error(project, fp, component="hook.x", error_code="hook_execution_failed")
    # Age the sidecar past the window so the next record re-anchors.
    path = rs.error_ledger_path(project)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["fingerprints"][fp]["first_seen"] = time.time() - 100_000
    payload["fingerprints"][fp]["last_seen"] = time.time() - 100_000
    path.write_text(json.dumps(payload), encoding="utf-8")

    out = rs.record_error(project, fp, component="hook.x", error_code="hook_execution_failed")
    assert out["emit_full"] is True
    assert out["occurrences"] == 1


def test_corrupt_sidecar_fails_open(rs, project: Path) -> None:
    path = rs.error_ledger_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not valid json ", encoding="utf-8")
    out = rs.record_error(project, _fp(rs), component="hook.x", error_code="hook_execution_failed")
    assert out["emit_full"] is True


def test_active_error_storms_reports_active_storm(rs, project: Path) -> None:
    fp = _fp(rs)
    for _ in range(6):
        rs.record_error(project, fp, component="hook.x", error_code="hook_execution_failed")
    storms = rs.active_error_storms(project)
    assert len(storms) == 1
    assert storms[0]["component"] == "hook.x"
    assert storms[0]["error_code"] == "hook_execution_failed"
    assert storms[0]["count"] >= 5


def test_active_error_storms_empty_when_clean(rs, project: Path) -> None:
    fp = _fp(rs)
    # Below threshold -> no active storm.
    for _ in range(3):
        rs.record_error(project, fp, component="hook.x", error_code="hook_execution_failed")
    assert rs.active_error_storms(project) == []


def test_distinct_fingerprints_do_not_coalesce(rs, project: Path) -> None:
    a = _fp(rs, "alpha")
    b = _fp(rs, "beta")
    ra = rs.record_error(project, a, component="hook.x", error_code="hook_execution_failed")
    rb = rs.record_error(project, b, component="hook.x", error_code="hook_execution_failed")
    assert ra["emit_full"] is True
    assert rb["emit_full"] is True
    assert ra["occurrences"] == 1
    assert rb["occurrences"] == 1
