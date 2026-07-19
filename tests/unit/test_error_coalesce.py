"""Tests for the pip-twin error/integrity storm coalescer (spec-190 D-190-02).

``src/ai_engineering/state/error_coalesce.py`` is the functional twin of the
hook-side coalescer in ``_lib/runtime_state.py``. Both writers target the same
atomic JSON sidecar (``.ai-engineering/runtime/error-coalesce.json``) so
repeated error/integrity emits collapse into one full event per window plus
periodic rollups.

The whole surface is fail-open: any read/write/parse failure degrades to a
first-occurrence verdict (``emit_full=True``) so no incident is silently lost.
This suite exercises the defensive fail-open branches directly (invalid env,
corrupt sidecar, an ``os.replace`` that raises, window expiry, pruning, and the
``active_error_storms`` reader) rather than only via ``emit_framework_error``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from ai_engineering.state import error_coalesce as ec


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project root with a small storm threshold and default window pinned."""
    monkeypatch.setenv("AIENG_ERROR_STORM_THRESHOLD", "5")
    monkeypatch.setenv("AIENG_HOOK_CACHE_TTL_SEC", "300")
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _fp(summary: str = "boom") -> str:
    return ec.error_fingerprint("pip.x", "hook_execution_failed", "sess-1", summary)


def _seed_ledger(project_root: Path, fingerprints: dict) -> None:
    path = ec.error_ledger_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fingerprints": fingerprints}), encoding="utf-8")


# ---------------------------------------------------------------------------
# error_fingerprint parity + record_error happy path
# ---------------------------------------------------------------------------


def test_error_fingerprint_is_stable_16_hex() -> None:
    fp = _fp()
    assert fp == _fp()
    assert len(fp) == 16
    int(fp, 16)  # hex-parseable


def test_first_occurrence_emits_full(project: Path) -> None:
    out = ec.record_error(project, _fp(), component="pip.x", error_code="hook_execution_failed")
    assert out == {
        "emit_full": True,
        "occurrences": 1,
        "storm_triggered": False,
        "is_rollup": False,
    }


def test_repeats_coalesce_to_one_full_plus_rollup(project: Path) -> None:
    fp = _fp()
    results = [
        ec.record_error(project, fp, component="pip.x", error_code="hook_execution_failed")
        for _ in range(5)
    ]
    full = [r for r in results if r["emit_full"]]
    assert len(full) == 2  # first occurrence + threshold-crossing rollup
    assert results[0]["is_rollup"] is False
    assert results[4]["is_rollup"] is True
    assert results[4]["occurrences"] == 5
    assert [r["emit_full"] for r in results[1:4]] == [False, False, False]


def test_storm_triggered_exactly_once(project: Path) -> None:
    fp = _fp()
    triggered = [
        ec.record_error(project, fp, component="pip.x", error_code="hook_execution_failed")[
            "storm_triggered"
        ]
        for _ in range(12)
    ]
    assert triggered.count(True) == 1
    assert triggered.index(True) == 4  # first crossing of threshold=5


# ---------------------------------------------------------------------------
# Fail-open defensive branches
# ---------------------------------------------------------------------------


def test_invalid_threshold_env_falls_back_to_default(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-integer AIENG_ERROR_STORM_THRESHOLD must not raise (``_env_int``)."""
    monkeypatch.setenv("AIENG_ERROR_STORM_THRESHOLD", "not-a-number")
    out = ec.record_error(project, _fp(), component="pip.x", error_code="hook_execution_failed")
    assert out["emit_full"] is True
    assert out["occurrences"] == 1


def test_corrupt_sidecar_read_fails_open(project: Path) -> None:
    """A non-JSON sidecar degrades to a first-occurrence verdict (``_read_json``)."""
    path = ec.error_ledger_path(project)
    path.write_text("{ not valid json ", encoding="utf-8")
    out = ec.record_error(project, _fp(), component="pip.x", error_code="hook_execution_failed")
    assert out["emit_full"] is True


def test_replace_failure_fails_open_and_cleans_tmp(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A raising ``os.replace`` must be swallowed (record_error fallback) and
    the leftover temp file cleaned up in the ``finally`` guard."""
    runtime_dir = ec.error_ledger_path(project).parent

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr(ec.os, "replace", _boom)

    out = ec.record_error(project, _fp(), component="pip.x", error_code="hook_execution_failed")
    # Fail-open first-occurrence verdict — no incident dropped.
    assert out == {
        "emit_full": True,
        "occurrences": 1,
        "storm_triggered": False,
        "is_rollup": False,
    }
    # The unique temp file was unlinked in the finally block; nothing lingers.
    assert not list(runtime_dir.glob("*.tmp"))


def test_prune_drops_fully_expired_entries(project: Path) -> None:
    """Recording a fresh fingerprint prunes a stale one so the file stays bounded."""
    stale_fp = _fp("stale-incident")
    _seed_ledger(
        project,
        {
            stale_fp: {
                "first_seen": time.time() - 100_000,
                "last_seen": time.time() - 100_000,
                "count": 3,
                "storm_notified": False,
            }
        },
    )

    ec.record_error(project, _fp("fresh"), component="pip.x", error_code="hook_execution_failed")

    ledger = json.loads(ec.error_ledger_path(project).read_text(encoding="utf-8"))
    assert stale_fp not in ledger["fingerprints"]


def test_window_expiry_reanchors_counter(project: Path) -> None:
    """An existing record whose window has elapsed re-anchors as a fresh full event."""
    fp = _fp()
    _seed_ledger(
        project,
        {
            fp: {
                "first_seen": time.time() - 100_000,
                "last_seen": time.time() - 100_000,
                "count": 9,
                "storm_notified": True,
            }
        },
    )

    out = ec.record_error(project, fp, component="pip.x", error_code="hook_execution_failed")
    assert out["emit_full"] is True
    assert out["occurrences"] == 1
    assert out["storm_triggered"] is False


# ---------------------------------------------------------------------------
# active_error_storms reader
# ---------------------------------------------------------------------------


def test_active_error_storms_reports_active_storm(project: Path) -> None:
    fp = _fp()
    for _ in range(6):
        ec.record_error(project, fp, component="pip.x", error_code="hook_execution_failed")
    storms = ec.active_error_storms(project)
    assert len(storms) == 1
    assert storms[0]["fingerprint"] == fp
    assert storms[0]["component"] == "pip.x"
    assert storms[0]["error_code"] == "hook_execution_failed"
    assert storms[0]["count"] >= 5


def test_active_error_storms_empty_below_threshold(project: Path) -> None:
    fp = _fp()
    for _ in range(3):
        ec.record_error(project, fp, component="pip.x", error_code="hook_execution_failed")
    assert ec.active_error_storms(project) == []


def test_active_error_storms_skips_non_storm_and_stale_and_malformed(project: Path) -> None:
    """Non-dict recs, non-storm recs, and stale/invalid first_seen are all skipped."""
    _seed_ledger(
        project,
        {
            "non-dict": "corrupt",
            "not-a-storm": {"storm_notified": False, "first_seen": time.time()},
            "stale-storm": {"storm_notified": True, "first_seen": time.time() - 100_000},
            "bad-first-seen": {"storm_notified": True, "first_seen": "nope"},
        },
    )
    assert ec.active_error_storms(project) == []


def test_active_error_storms_empty_when_fingerprints_not_a_dict(project: Path) -> None:
    _seed_ledger(project, fingerprints="not-a-dict")  # type: ignore[arg-type]
    assert ec.active_error_storms(project) == []


def test_active_error_storms_fails_open_on_read_error(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Any exception inside the reader degrades to ``[]`` (never raises)."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated read failure")

    monkeypatch.setattr(ec, "_read_json", _boom)
    assert ec.active_error_storms(project) == []
