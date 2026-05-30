"""Tests for the version-check cache repository (spec version-update-notice).

Covers read/write round-trip, the on-disk path under HOME, staleness
evaluation against ``ttl_hours``, the ``last_shown_at`` throttle stamp,
and fail-open behaviour on corrupt / unreadable cache files.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ai_engineering.version import cache


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def test_cache_path_under_home(_home: Path) -> None:
    assert cache.cache_path() == _home / ".ai-engineering" / "state" / "version-check.json"


def test_read_missing_returns_empty(_home: Path) -> None:
    assert cache.read() == {}


def test_write_then_read_round_trips(_home: Path) -> None:
    cache.write("0.9.0", source="pypi")
    data = cache.read()
    assert data["latest"] == "0.9.0"
    assert data["source"] == "pypi"
    assert "checked_at" in data
    # last_shown_at is only set on mark_shown
    assert data.get("last_shown_at") in (None, "")


def test_write_creates_parent_dirs(_home: Path) -> None:
    cache.write("1.0.0")
    assert cache.cache_path().is_file()


def test_corrupt_json_reads_empty(_home: Path) -> None:
    path = cache.cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json", encoding="utf-8")
    assert cache.read() == {}


def test_is_stale_true_when_no_cache(_home: Path) -> None:
    assert cache.is_stale(24) is True


def test_is_stale_false_when_fresh(_home: Path) -> None:
    cache.write("0.9.0")
    assert cache.is_stale(24) is False


def test_is_stale_true_past_ttl(_home: Path) -> None:
    old = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    path = cache.cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"latest": "0.9.0", "checked_at": old, "source": "pypi"}),
        encoding="utf-8",
    )
    assert cache.is_stale(24) is True


def test_is_stale_fail_open_on_bad_timestamp(_home: Path) -> None:
    path = cache.cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"latest": "0.9.0", "checked_at": "not-a-date"}),
        encoding="utf-8",
    )
    # Unparseable timestamp -> treat as stale (fail-open, never raise).
    assert cache.is_stale(24) is True


def test_mark_shown_stamps_last_shown_at(_home: Path) -> None:
    cache.write("0.9.0")
    cache.mark_shown()
    data = cache.read()
    assert data.get("last_shown_at")
    # Preserves the latest field
    assert data["latest"] == "0.9.0"


def test_mark_shown_fail_open_when_no_cache(_home: Path) -> None:
    # Should not raise even with no prior cache file.
    cache.mark_shown()
