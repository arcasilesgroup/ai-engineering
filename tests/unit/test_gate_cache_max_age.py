"""Unit tests for ``ai_engineering.policy.gate_cache.lookup`` max-age enforcement.

RED phase for spec-104 T-1.5 (D-104-03 max-age 24h invalidation rule).

Target behaviour (does not exist yet — added in T-1.6 GREEN on top of T-1.4
GREEN which introduces ``lookup``/``persist``):

    ``lookup`` returns ``None`` (miss) when ``now() - verified_at > 24h``,
    AND the stale entry file is removed from disk so the next call regenerates
    cleanly. Entries with ``verified_at`` in the future (clock skew) are also
    treated as a miss + cleared.

Each test currently fails with ``ImportError`` because ``lookup`` is not yet
exported from ``ai_engineering.policy.gate_cache`` (T-1.4 GREEN adds it; T-1.6
GREEN adds the max-age semantic on top).

TDD CONSTRAINT: this file is IMMUTABLE after T-1.5 lands.

Test cases (8 total):

1. ``test_lookup_returns_entry_within_24h``
2. ``test_lookup_returns_none_after_24h``
3. ``test_lookup_after_24h_clears_stale_entry``
4. ``test_lookup_clock_skew_future_timestamp_treated_as_miss``
5. ``test_lookup_at_exactly_24h_boundary``
6. ``test_lookup_handles_iso8601_z_suffix``
7. ``test_lookup_handles_iso8601_explicit_offset``
8. ``test_lookup_handles_microseconds``
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Fixture helpers — write cache entries directly to disk so these tests do
# NOT depend on T-1.4's ``persist`` API surface (which lands in a later GREEN
# phase). The on-disk format is fixed by D-104-03:
#   filename: ``<cache-key>.json``
#   payload : {result, findings, verified_at, verified_by_version, key_inputs}
# ---------------------------------------------------------------------------


def _make_lookup_inputs(**overrides: Any) -> dict[str, Any]:
    """Canonical kwargs accepted by ``lookup`` (mirrors D-104-09 cache key inputs)."""
    base: dict[str, Any] = {
        "check_name": "ruff-check",
        "args": ["check", "src/"],
        "staged_blob_shas": [
            "0123456789abcdef0123456789abcdef01234567",
            "fedcba9876543210fedcba9876543210fedcba98",
        ],
        "tool_version": "0.6.4",
        "config_file_hashes": {
            "pyproject.toml": "a" * 64,
            ".ruff.toml": "b" * 64,
        },
    }
    base.update(overrides)
    return base


def _write_entry(
    cache_dir: Path,
    inputs: dict[str, Any],
    *,
    verified_at: str,
    result: str = "PASS",
    findings: list[dict[str, Any]] | None = None,
    verified_by_version: str = "0.6.4",
) -> Path:
    """Write a cache entry JSON file at ``<cache_dir>/<cache-key>.json``.

    The cache key is derived via ``_compute_cache_key`` so that the file name
    matches what ``lookup`` will compute internally for the same inputs.
    """
    from ai_engineering.policy.gate_cache import _compute_cache_key

    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _compute_cache_key(
        check_name=inputs["check_name"],
        args=inputs["args"],
        staged_blob_shas=inputs["staged_blob_shas"],
        tool_version=inputs["tool_version"],
        config_file_hashes=inputs["config_file_hashes"],
    )
    payload: dict[str, Any] = {
        "result": result,
        "findings": findings if findings is not None else [],
        "verified_at": verified_at,
        "verified_by_version": verified_by_version,
        "key_inputs": {
            "check_name": inputs["check_name"],
            "tool_version": inputs["tool_version"],
            "args": list(inputs["args"]),
            "staged_blob_shas": list(inputs["staged_blob_shas"]),
            "config_file_hashes": dict(inputs["config_file_hashes"]),
        },
    }
    entry_path = cache_dir / f"{key}.json"
    entry_path.write_text(json.dumps(payload), encoding="utf-8")
    return entry_path


def _freeze_now(monkeypatch: pytest.MonkeyPatch, frozen: datetime) -> None:
    """Pin ``datetime.now(tz=UTC)`` inside ``gate_cache`` to ``frozen``.

    The implementation under test is expected to import ``datetime`` from the
    stdlib at module level. Tests patch the module-level binding so any
    ``datetime.now(...)`` call inside ``gate_cache`` returns ``frozen``.
    """
    import ai_engineering.policy.gate_cache as gc_mod

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
            return frozen if tz is None else frozen.astimezone(tz)

    monkeypatch.setattr(gc_mod, "datetime", _FrozenDatetime)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_lookup_returns_entry_within_24h(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Entry verified 1 hour ago is fresh — ``lookup`` returns the cached payload."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    one_hour_ago = now - timedelta(hours=1)

    inputs = _make_lookup_inputs()
    entry_path = _write_entry(
        cache_dir,
        inputs,
        verified_at=one_hour_ago.isoformat().replace("+00:00", "Z"),
        result="PASS",
        findings=[],
    )
    _freeze_now(monkeypatch, now)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is not None, "Entry within 24h must be returned (cache hit)"
    assert entry.get("result") == "PASS"
    # Entry file must NOT be removed on a hit.
    assert entry_path.exists(), "Fresh entry must remain on disk after lookup hit"


def test_lookup_returns_none_after_24h(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Entry verified 25 hours ago is stale — ``lookup`` returns ``None`` (miss)."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    twenty_five_hours_ago = now - timedelta(hours=25)

    inputs = _make_lookup_inputs()
    _write_entry(
        cache_dir,
        inputs,
        verified_at=twenty_five_hours_ago.isoformat().replace("+00:00", "Z"),
    )
    _freeze_now(monkeypatch, now)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is None, "Entry older than 24h must be treated as a miss"


def test_lookup_after_24h_clears_stale_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stale entries are deleted from disk on lookup (read+delete pattern)."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    forty_eight_hours_ago = now - timedelta(hours=48)

    inputs = _make_lookup_inputs()
    entry_path = _write_entry(
        cache_dir,
        inputs,
        verified_at=forty_eight_hours_ago.isoformat().replace("+00:00", "Z"),
    )
    assert entry_path.exists(), "Pre-condition: stale entry written to disk"

    _freeze_now(monkeypatch, now)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is None
    assert not entry_path.exists(), (
        "Stale entry must be removed from disk after lookup so the next "
        "miss regenerates a fresh entry instead of recycling the stale file."
    )


def test_lookup_clock_skew_future_timestamp_treated_as_miss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Entry with ``verified_at`` in the future (clock skew) is a miss + cleared."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    five_minutes_in_future = now + timedelta(minutes=5)

    inputs = _make_lookup_inputs()
    entry_path = _write_entry(
        cache_dir,
        inputs,
        verified_at=five_minutes_in_future.isoformat().replace("+00:00", "Z"),
    )
    _freeze_now(monkeypatch, now)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is None, (
        "verified_at in the future indicates clock skew or tampering; "
        "lookup must treat it as a miss rather than returning a 'fresh' hit."
    )
    assert not entry_path.exists(), (
        "Future-timestamp entry must also be cleared from disk so it is "
        "regenerated with a sane verified_at on the next persist."
    )


def test_lookup_at_exactly_24h_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """At exactly the 24h boundary, lookup is a miss for clear semantics.

    Implementation choice (per T-1.5 spec): ``< 24h`` is a hit, ``>= 24h``
    is a miss. Equality at the boundary is conservative — the freshness
    window is half-open ``[verified_at, verified_at + 24h)``.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    exactly_24h_ago = now - timedelta(hours=24)

    inputs = _make_lookup_inputs()
    _write_entry(
        cache_dir,
        inputs,
        verified_at=exactly_24h_ago.isoformat().replace("+00:00", "Z"),
    )
    _freeze_now(monkeypatch, now)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is None, (
        "At exactly 24h elapsed, lookup must return a miss. "
        "Half-open window: [verified_at, verified_at + 24h) is fresh."
    )


def test_lookup_handles_iso8601_z_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``verified_at`` written with ``Z`` suffix (``...T12:00:00Z``) parses correctly."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    two_hours_ago = now - timedelta(hours=2)

    # Form: ``2026-04-26T10:00:00Z`` (no fractional seconds, Z suffix).
    z_suffix_iso = two_hours_ago.strftime("%Y-%m-%dT%H:%M:%SZ")

    inputs = _make_lookup_inputs()
    _write_entry(cache_dir, inputs, verified_at=z_suffix_iso)
    _freeze_now(monkeypatch, now)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is not None, (
        f"verified_at={z_suffix_iso!r} (Z suffix) must parse as UTC and the "
        "fresh entry must be returned."
    )


def test_lookup_handles_iso8601_explicit_offset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``verified_at`` written with ``+00:00`` explicit offset parses correctly."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    six_hours_ago = now - timedelta(hours=6)

    # Form: ``2026-04-26T06:00:00+00:00`` (explicit UTC offset, no Z).
    explicit_offset_iso = six_hours_ago.isoformat()
    assert explicit_offset_iso.endswith("+00:00"), (
        "Pre-condition: datetime.isoformat() emits explicit offset for tz-aware UTC."
    )

    inputs = _make_lookup_inputs()
    _write_entry(cache_dir, inputs, verified_at=explicit_offset_iso)
    _freeze_now(monkeypatch, now)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is not None, (
        f"verified_at={explicit_offset_iso!r} (+00:00 offset) must parse "
        "and the fresh entry must be returned."
    )


def test_lookup_handles_microseconds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``verified_at`` containing microseconds parses correctly."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    three_hours_ago_with_us = (now - timedelta(hours=3)).replace(microsecond=123456)

    # Form: ``2026-04-26T09:00:00.123456+00:00`` (microsecond precision).
    micro_iso = three_hours_ago_with_us.isoformat()
    assert ".123456" in micro_iso, "Pre-condition: microsecond field present in ISO string"

    inputs = _make_lookup_inputs()
    _write_entry(cache_dir, inputs, verified_at=micro_iso)
    _freeze_now(monkeypatch, now)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is not None, (
        f"verified_at={micro_iso!r} (microseconds) must parse and the fresh entry must be returned."
    )
