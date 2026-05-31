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


def test_write_fail_open_when_atomic_write_raises(
    _home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # spec-157 review F5: a read-only home (atomic write raises OSError) must
    # never crash the CLI — write() swallows it and persists nothing.
    def _boom(*_a: object, **_k: object) -> None:
        raise OSError("read-only home directory")

    monkeypatch.setattr(cache, "_atomic_write", _boom)
    cache.write("0.9.0")  # must not raise
    assert cache.read() == {}


def test_touch_checked_at_preserves_latest_and_last_shown(_home: Path) -> None:
    # spec-157 review F5 (D-156-13): touch advances checked_at WITHOUT
    # clobbering latest/last_shown_at/source.
    old_checked = (datetime.now(UTC) - timedelta(hours=10)).isoformat()
    path = cache.cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "latest": "0.9.0",
                "checked_at": old_checked,
                "last_shown_at": "2020-01-01T00:00:00+00:00",
                "source": "pypi",
            }
        ),
        encoding="utf-8",
    )
    cache.touch_checked_at()
    after = cache.read()
    assert after["latest"] == "0.9.0"
    assert after["last_shown_at"] == "2020-01-01T00:00:00+00:00"
    assert after["source"] == "pypi"
    assert after["checked_at"] != old_checked  # advanced to now


def test_touch_checked_at_fail_open_when_no_cache(_home: Path) -> None:
    # No prior cache file -> must not raise (fail-open).
    cache.touch_checked_at()


def test_atomic_write_cleans_temp_on_replace_error(
    _home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # spec-157 review F5: if os.replace fails mid-write, the temp file is
    # unlinked and the error re-raised — no orphaned *.tmp left behind.
    path = cache.cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    def _boom_replace(*_a: object, **_k: object) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(cache.os, "replace", _boom_replace)
    with pytest.raises(OSError):
        cache._atomic_write(path, {"latest": "1.0.0"})
    assert list(path.parent.glob("*.tmp")) == []
