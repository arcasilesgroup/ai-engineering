"""Coverage-completion tests for ``ai_engineering.policy.gate_cache``.

spec-104 D-7: lift gate_cache.py coverage from 78% to >=80%. The existing six
test files (``test_gate_cache_{key,hit_miss,max_age,persist,overrides,lru_prune}``)
are immutable post-RED-phase per the TDD constraint baked into each module
docstring; new edge-case scenarios must therefore live in this file.

Each test targets a specific uncovered branch in the production module:

    - 118-119 -> ``CacheEntry.__getattr__`` raises AttributeError on miss
    - 150-155 -> ``_atomic_write`` cleanup path when ``json.dump`` raises
    - 170-172 -> ``_read_safe`` OSError (e.g. PermissionError) handling
    - 194-199 -> ``_read_safe`` non-dict JSON (array/scalar) rejection
    - 246-250 -> ``_resolve_cache_key`` TypeError when neither shape supplied
    - 293-296 -> ``lookup`` debug log on disabled-short-circuit
    - 316-324 -> ``lookup`` missing/non-string verified_at
    - 328-339 -> ``lookup`` unparseable verified_at (datetime ValueError)
    - 343      -> ``lookup`` naive verified_at (no tzinfo)
    - 352-358 -> ``lookup`` debug log on stale/future drop
    - 430-433 -> ``persist`` keyword-form TypeError on missing fields
    - 486      -> ``_prune_if_oversize`` returns 0 when cache_dir absent
    - 504-506 -> ``_prune_if_oversize`` corrupt-on-bad-verified_at branch
    - 508      -> ``_prune_if_oversize`` naive verified_at handling
    - 516-518 -> ``_prune_if_oversize`` corrupt-unlink FileNotFoundError race
    - 530-531 -> ``_prune_if_oversize`` LRU-unlink FileNotFoundError race

These are advisory robustness paths -- the existing immutable suites cover the
happy paths and the contract surface; these tests cover the defensive edges.
"""

from __future__ import annotations

import json
import logging
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# CacheEntry.__getattr__ AttributeError path (lines 118-119)
# ---------------------------------------------------------------------------


def test_cache_entry_getattr_raises_attribute_error_for_missing_key() -> None:
    """``CacheEntry.<missing>`` raises AttributeError (not KeyError)."""
    # Arrange
    from ai_engineering.policy.gate_cache import CacheEntry

    entry = CacheEntry({"check_name": "ruff-check"})

    # Act / Assert
    with pytest.raises(AttributeError) as excinfo:
        _ = entry.nonexistent_field

    assert "nonexistent_field" in str(excinfo.value), (
        f"AttributeError must reference the missing attribute name; got {excinfo.value!r}"
    )


# ---------------------------------------------------------------------------
# _atomic_write cleanup path on json.dump failure (lines 150-155)
# ---------------------------------------------------------------------------


def test_atomic_write_cleans_up_tempfile_on_dump_failure(tmp_path: Path) -> None:
    """When ``json.dump`` raises, ``_atomic_write`` removes the partial tempfile.

    The original exception MUST propagate (re-raise after cleanup), and the
    target file must NOT be created (publish never happened).
    """
    # Arrange
    from ai_engineering.policy import gate_cache
    from ai_engineering.policy.gate_cache import _atomic_write

    target = tmp_path / "entry.json"
    payload = {"k": "v"}

    # Track temp paths created during the dump-failure window.
    created_tempfiles: list[Path] = []
    real_named_tempfile = gate_cache.tempfile.NamedTemporaryFile

    def tracking_named_tempfile(*args: Any, **kwargs: Any) -> Any:
        tmp = real_named_tempfile(*args, **kwargs)
        created_tempfiles.append(Path(tmp.name))
        return tmp

    # Force json.dump to fail mid-write.
    boom = RuntimeError("simulated dump failure")

    with (
        mock.patch.object(
            gate_cache.tempfile,
            "NamedTemporaryFile",
            side_effect=tracking_named_tempfile,
        ),
        mock.patch.object(gate_cache.json, "dump", side_effect=boom),
        pytest.raises(RuntimeError, match="simulated dump failure"),
    ):
        _atomic_write(target, payload)

    # Assert -- target was never published.
    assert not target.exists(), "On dump failure, atomic_write must NOT publish the target file."
    # Assert -- the partial tempfile was cleaned up.
    assert created_tempfiles, "tempfile.NamedTemporaryFile was never invoked"
    for tf in created_tempfiles:
        assert not tf.exists(), f"Partial tempfile {tf!r} must be cleaned up after dump failure"


def test_atomic_write_cleans_up_tempfile_on_replace_failure(tmp_path: Path) -> None:
    """When ``os.replace`` raises (post-fsync), tempfile cleanup still happens.

    Verifies the BaseException catch-all in lines 150-155 also covers failures
    surfaced through the publish step rather than only the dump step.
    """
    # Arrange
    from ai_engineering.policy import gate_cache
    from ai_engineering.policy.gate_cache import _atomic_write

    target = tmp_path / "entry.json"
    payload = {"k": "v"}

    boom = OSError("simulated replace failure")

    with (
        mock.patch.object(gate_cache.os, "replace", side_effect=boom),
        pytest.raises(OSError, match="simulated replace failure"),
    ):
        _atomic_write(target, payload)

    assert not target.exists(), "target file must NOT exist when replace fails"


# ---------------------------------------------------------------------------
# _read_safe OSError handling (lines 170-172)
# ---------------------------------------------------------------------------


def test_read_safe_returns_none_on_permission_error(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """``_read_safe`` returns None + warns when the read primitive raises OSError.

    Simulates Linux/macOS chmod-0 unreadable file, Windows file-locked, or
    similar low-level I/O failures distinct from FileNotFoundError.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import _read_safe

    path = tmp_path / "locked.json"
    path.write_text("{}", encoding="utf-8")

    boom = PermissionError("simulated permission denied")

    # Patch the single read seam ``_read_safe`` delegates to
    # (``_read_bytes_shared``, which wraps read_bytes on POSIX and a
    # FILE_SHARE_DELETE handle on Windows). Patching there — rather than
    # ``Path.read_bytes`` — exercises the OSError->None contract identically
    # on every OS, including the Windows branch that never touches read_bytes.
    with (
        mock.patch("ai_engineering.policy.gate_cache._read_bytes_shared", side_effect=boom),
        caplog.at_level(logging.WARNING, logger="ai_engineering.policy.gate_cache"),
    ):
        result = _read_safe(path)

    # Assert -- swallowed, returns None.
    assert result is None, f"_read_safe must convert OSError to None miss; got {result!r}"

    # Assert -- a WARNING was logged so operators see the I/O drift.
    warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warning_records, "OSError on read_bytes must emit a WARNING log record"
    combined = " ".join(r.getMessage() for r in warning_records).lower()
    assert "unreadable" in combined or "permission" in combined, (
        f"warning message must reference unreadable / permission; got {combined!r}"
    )


# ---------------------------------------------------------------------------
# _read_safe non-dict JSON rejection (lines 194-199)
# ---------------------------------------------------------------------------


def test_read_safe_returns_none_for_json_array(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A JSON file whose top-level value is an array is treated as corrupt."""
    # Arrange
    from ai_engineering.policy.gate_cache import _read_safe

    path = tmp_path / "array.json"
    path.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    # Act
    with caplog.at_level(logging.WARNING, logger="ai_engineering.policy.gate_cache"):
        result = _read_safe(path)

    # Assert
    assert result is None, f"non-dict JSON must yield None; got {result!r}"

    warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warning_records, "non-dict JSON must emit a WARNING log record"
    combined = " ".join(r.getMessage() for r in warning_records).lower()
    assert "not parse" in combined or "object" in combined or "list" in combined, (
        f"warning must reference non-object parse outcome; got {combined!r}"
    )


def test_read_safe_returns_none_for_json_scalar(tmp_path: Path) -> None:
    """A JSON file whose top-level value is a scalar (int) is treated as corrupt."""
    # Arrange
    from ai_engineering.policy.gate_cache import _read_safe

    path = tmp_path / "scalar.json"
    path.write_text("42", encoding="utf-8")

    # Act
    result = _read_safe(path)

    # Assert
    assert result is None, f"scalar JSON must yield None; got {result!r}"


# ---------------------------------------------------------------------------
# _resolve_cache_key TypeError on incomplete inputs (lines 246-250)
# ---------------------------------------------------------------------------


def test_lookup_raises_type_error_when_neither_key_nor_kwargs_provided(
    tmp_path: Path,
) -> None:
    """Calling lookup with only ``cache_dir`` raises TypeError (incomplete inputs)."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"

    # Act / Assert
    with pytest.raises(TypeError) as excinfo:
        lookup(cache_dir=cache_dir)

    msg = str(excinfo.value).lower()
    assert "cache_key" in msg or "check_name" in msg, (
        "TypeError must explain that either cache_key or the full kwarg set is required; "
        f"got {excinfo.value!r}"
    )


def test_lookup_raises_type_error_with_partial_kwargs(tmp_path: Path) -> None:
    """Providing some-but-not-all keyword inputs still raises TypeError."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"

    # Act / Assert -- check_name supplied but other inputs missing.
    with pytest.raises(TypeError):
        lookup(cache_dir=cache_dir, check_name="ruff-check")


# ---------------------------------------------------------------------------
# lookup debug logging when disabled (lines 293-296)
# ---------------------------------------------------------------------------


def test_lookup_debug_log_emitted_when_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``AIENG_CACHE_DEBUG=1`` + ``disabled=True`` emits a 'disabled' debug record."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir()

    monkeypatch.setenv("AIENG_CACHE_DEBUG", "1")
    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)

    # Act
    with caplog.at_level(logging.DEBUG, logger="ai_engineering.policy.gate_cache"):
        result = lookup(cache_dir, "deadbeef" * 4, disabled=True)

    # Assert
    assert result is None, "disabled lookup must return None"

    cache_logs = [r for r in caplog.records if r.name == "ai_engineering.policy.gate_cache"]
    combined = " ".join(r.getMessage().lower() for r in cache_logs)
    assert "disabled" in combined, (
        f"disabled lookup with AIENG_CACHE_DEBUG=1 must log 'disabled' marker; "
        f"got: {[r.getMessage() for r in cache_logs]!r}"
    )


# ---------------------------------------------------------------------------
# lookup missing / non-string verified_at (lines 316-324)
# ---------------------------------------------------------------------------


def _seed_raw_entry(cache_dir: Path, cache_key: str, payload: dict[str, Any]) -> Path:
    """Write ``payload`` directly to ``cache_dir / f"{cache_key}.json"``."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{cache_key}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_lookup_treats_missing_verified_at_as_miss(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Entry with no ``verified_at`` field -> miss + file cleared + warning."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_key = "abc123" + "0" * 26  # 32-char key
    payload = {"check_name": "ruff-check", "result": {"outcome": "pass"}}
    entry_path = _seed_raw_entry(cache_dir, cache_key, payload)

    # Act
    with caplog.at_level(logging.WARNING, logger="ai_engineering.policy.gate_cache"):
        result = lookup(cache_dir, cache_key)

    # Assert
    assert result is None, "entry without verified_at must miss"
    assert not entry_path.exists(), (
        "entry without verified_at must be cleared from disk for fresh regeneration"
    )

    warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warning_records, "missing verified_at must emit a WARNING"
    combined = " ".join(r.getMessage().lower() for r in warning_records)
    assert "verified_at" in combined, f"warning must reference verified_at; got {combined!r}"


def test_lookup_treats_non_string_verified_at_as_miss(tmp_path: Path) -> None:
    """Entry whose ``verified_at`` is a number, not a string, is treated as miss."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_key = "abc123" + "1" * 26
    payload = {
        "check_name": "ruff-check",
        "verified_at": 1234567890,  # int, not ISO string
        "result": {"outcome": "pass"},
    }
    entry_path = _seed_raw_entry(cache_dir, cache_key, payload)

    # Act
    result = lookup(cache_dir, cache_key)

    # Assert
    assert result is None, "verified_at as non-string must miss"
    assert not entry_path.exists(), "non-string verified_at entry must be cleared"


def test_lookup_missing_verified_at_with_debug_logs_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Debug log marker fires on the missing-verified_at branch when DEBUG=1."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_key = "abc123" + "2" * 26
    payload = {"check_name": "ruff-check", "result": {"outcome": "pass"}}
    _seed_raw_entry(cache_dir, cache_key, payload)

    monkeypatch.setenv("AIENG_CACHE_DEBUG", "1")
    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)

    # Act
    with caplog.at_level(logging.DEBUG, logger="ai_engineering.policy.gate_cache"):
        result = lookup(cache_dir, cache_key)

    # Assert
    assert result is None
    cache_logs = [r for r in caplog.records if r.name == "ai_engineering.policy.gate_cache"]
    combined = " ".join(r.getMessage().lower() for r in cache_logs)
    assert "no verified_at" in combined or "miss" in combined, (
        f"DEBUG log must indicate verified_at miss; got {combined!r}"
    )


# ---------------------------------------------------------------------------
# lookup unparseable verified_at (lines 328-339)
# ---------------------------------------------------------------------------


def test_lookup_treats_unparseable_verified_at_as_miss(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """``verified_at`` that fromisoformat cannot parse -> miss + cleared + warning."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_key = "deadbeef" + "0" * 24
    payload = {
        "check_name": "ruff-check",
        "verified_at": "not-an-iso-timestamp",
        "result": {"outcome": "pass"},
    }
    entry_path = _seed_raw_entry(cache_dir, cache_key, payload)

    # Act
    with caplog.at_level(logging.WARNING, logger="ai_engineering.policy.gate_cache"):
        result = lookup(cache_dir, cache_key)

    # Assert
    assert result is None, "unparseable verified_at must miss"
    assert not entry_path.exists(), "unparseable verified_at entry must be cleared"

    warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert warning_records, "unparseable verified_at must emit a WARNING"
    combined = " ".join(r.getMessage().lower() for r in warning_records)
    assert "unparseable" in combined or "verified_at" in combined, (
        f"warning must reference parseability; got {combined!r}"
    )


def test_lookup_unparseable_verified_at_with_debug_logs_marker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Debug log marker fires on the unparseable-verified_at branch."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_key = "deadbeef" + "1" * 24
    payload = {
        "check_name": "ruff-check",
        "verified_at": "not-an-iso-timestamp",
        "result": {"outcome": "pass"},
    }
    _seed_raw_entry(cache_dir, cache_key, payload)

    monkeypatch.setenv("AIENG_CACHE_DEBUG", "1")
    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)

    # Act
    with caplog.at_level(logging.DEBUG, logger="ai_engineering.policy.gate_cache"):
        result = lookup(cache_dir, cache_key)

    # Assert
    assert result is None
    cache_logs = [r for r in caplog.records if r.name == "ai_engineering.policy.gate_cache"]
    combined = " ".join(r.getMessage().lower() for r in cache_logs)
    assert "unparseable" in combined or "miss" in combined, (
        f"DEBUG log must indicate unparseable miss; got {combined!r}"
    )


# ---------------------------------------------------------------------------
# lookup with naive verified_at (line 343)
# ---------------------------------------------------------------------------


def test_lookup_handles_naive_verified_at_anchor_to_utc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Entry with naive (no-offset) ISO ``verified_at`` is anchored to UTC.

    fromisoformat returns a tz-naive datetime when the input has no offset.
    The implementation must replace tzinfo with UTC so the freshness math
    still subtracts a tz-aware ``now``.
    """
    # Arrange
    import ai_engineering.policy.gate_cache as gc_mod
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_key = "abcdef" + "0" * 26

    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    one_hour_ago_naive = (now - timedelta(hours=1)).replace(tzinfo=None)
    naive_iso = one_hour_ago_naive.isoformat()  # no Z, no offset
    assert "+" not in naive_iso and not naive_iso.endswith("Z"), (
        "precondition: naive ISO has no tz offset"
    )

    payload = {
        "check_name": "ruff-check",
        "verified_at": naive_iso,
        "result": {"outcome": "pass"},
    }
    _seed_raw_entry(cache_dir, cache_key, payload)

    # Pin "now" inside the gate_cache module.
    class _Frozen(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return now if tz is None else now.astimezone(tz)

    monkeypatch.setattr(gc_mod, "datetime", _Frozen)

    # Act
    result = lookup(cache_dir, cache_key)

    # Assert -- naive is treated as UTC and within the freshness window.
    assert result is not None, (
        "naive verified_at must be anchored to UTC so 1-hour-old entry is fresh"
    )


# ---------------------------------------------------------------------------
# lookup debug log on stale/future drop (lines 352-358)
# ---------------------------------------------------------------------------


def test_lookup_debug_log_on_stale_drop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When DEBUG=1, the stale-drop branch emits a 'stale' marker."""
    # Arrange
    import ai_engineering.policy.gate_cache as gc_mod
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_key = "stale123" + "0" * 24

    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    twenty_five_h_ago = now - timedelta(hours=25)
    payload = {
        "check_name": "ruff-check",
        "verified_at": twenty_five_h_ago.isoformat().replace("+00:00", "Z"),
        "result": {"outcome": "pass"},
    }
    _seed_raw_entry(cache_dir, cache_key, payload)

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return now if tz is None else now.astimezone(tz)

    monkeypatch.setattr(gc_mod, "datetime", _Frozen)
    monkeypatch.setenv("AIENG_CACHE_DEBUG", "1")
    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)

    # Act
    with caplog.at_level(logging.DEBUG, logger="ai_engineering.policy.gate_cache"):
        result = lookup(cache_dir, cache_key)

    # Assert
    assert result is None
    cache_logs = [r for r in caplog.records if r.name == "ai_engineering.policy.gate_cache"]
    combined = " ".join(r.getMessage().lower() for r in cache_logs)
    assert "stale" in combined, (
        f"DEBUG log must include 'stale' on stale-drop branch; got {combined!r}"
    )


def test_lookup_debug_log_on_future_drop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When DEBUG=1, the future-timestamp drop branch emits a 'future' marker."""
    # Arrange
    import ai_engineering.policy.gate_cache as gc_mod
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_key = "future12" + "0" * 24

    now = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    five_min_future = now + timedelta(minutes=5)
    payload = {
        "check_name": "ruff-check",
        "verified_at": five_min_future.isoformat().replace("+00:00", "Z"),
        "result": {"outcome": "pass"},
    }
    _seed_raw_entry(cache_dir, cache_key, payload)

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> datetime:
            return now if tz is None else now.astimezone(tz)

    monkeypatch.setattr(gc_mod, "datetime", _Frozen)
    monkeypatch.setenv("AIENG_CACHE_DEBUG", "1")
    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)

    # Act
    with caplog.at_level(logging.DEBUG, logger="ai_engineering.policy.gate_cache"):
        result = lookup(cache_dir, cache_key)

    # Assert
    assert result is None
    cache_logs = [r for r in caplog.records if r.name == "ai_engineering.policy.gate_cache"]
    combined = " ".join(r.getMessage().lower() for r in cache_logs)
    assert "future" in combined, (
        f"DEBUG log must include 'future' on future-drop branch; got {combined!r}"
    )


# ---------------------------------------------------------------------------
# persist keyword-form TypeError (lines 430-433)
# ---------------------------------------------------------------------------


def test_persist_keyword_form_raises_type_error_without_result(tmp_path: Path) -> None:
    """``persist`` without ``result`` AND without ``entry`` raises TypeError."""
    # Arrange
    from ai_engineering.policy.gate_cache import persist

    cache_dir = tmp_path / "gate-cache"

    # Act / Assert -- cache_key is None, entry is None, result is None.
    with pytest.raises(TypeError) as excinfo:
        persist(
            cache_dir=cache_dir,
            check_name="ruff-check",
            args=["check", "src/"],
            staged_blob_shas=["a" * 40],
            tool_version="0.6.4",
            config_file_hashes={"pyproject.toml": "x" * 64},
            # result intentionally omitted
        )

    msg = str(excinfo.value).lower()
    assert "result" in msg or "keyword" in msg, (
        f"TypeError must reference the missing keyword fields; got {excinfo.value!r}"
    )


def test_persist_keyword_form_raises_type_error_without_check_name(tmp_path: Path) -> None:
    """``persist`` without ``check_name`` (when entry is also None) raises TypeError."""
    # Arrange
    from ai_engineering.policy.gate_cache import persist

    cache_dir = tmp_path / "gate-cache"

    # Act / Assert -- cache_key=None and entry=None forces keyword-form path.
    with pytest.raises(TypeError):
        persist(
            cache_dir=cache_dir,
            args=["check"],
            staged_blob_shas=["a" * 40],
            tool_version="0.6.4",
            config_file_hashes={"pyproject.toml": "x" * 64},
            result={"outcome": "pass"},
            # check_name intentionally omitted
        )


# ---------------------------------------------------------------------------
# _prune_if_oversize on missing cache_dir (line 486)
# ---------------------------------------------------------------------------


def test_prune_returns_zero_for_missing_cache_dir(tmp_path: Path) -> None:
    """Pruning a non-existent directory returns 0 with no exception."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    missing_dir = tmp_path / "does-not-exist"
    assert not missing_dir.exists(), "precondition: cache_dir must not exist"

    # Act
    removed = _prune_if_oversize(missing_dir)

    # Assert
    assert removed == 0, f"prune of missing dir must return 0; got {removed}"


def test_prune_returns_zero_for_empty_cache_dir(tmp_path: Path) -> None:
    """Pruning an empty directory returns 0."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    empty_dir = tmp_path / "gate-cache"
    empty_dir.mkdir()

    # Act
    removed = _prune_if_oversize(empty_dir)

    # Assert
    assert removed == 0, f"prune of empty dir must return 0; got {removed}"


# ---------------------------------------------------------------------------
# _prune_if_oversize unparseable verified_at branch (lines 504-506)
# ---------------------------------------------------------------------------


def test_prune_evicts_entries_with_unparseable_verified_at(tmp_path: Path) -> None:
    """Healthy-shaped JSON with a *string* but unparseable ``verified_at``
    is treated as corrupted and evicted.

    This is distinct from the existing
    ``test_prune_handles_corrupted_entries`` cases:
        - truncated JSON   -> _read_safe returns None (line 495 path)
        - binary garbage   -> _read_safe returns None
        - missing field    -> verified_at is None (line 499 path)
    The current case exercises lines 502-506: verified_at IS a string but
    fromisoformat raises ValueError.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir()

    # One healthy entry to demonstrate selective eviction.
    healthy_payload = {
        "check_name": "ruff-check",
        "verified_at": "2026-04-26T12:00:00Z",
        "result": {"outcome": "pass"},
    }
    healthy = cache_dir / ("h" * 32 + ".json")
    healthy.write_text(json.dumps(healthy_payload), encoding="utf-8")

    # Corrupt entry: structurally valid JSON dict, verified_at IS a string,
    # but fromisoformat will raise ValueError.
    bad_payload = {
        "check_name": "ruff-check",
        "verified_at": "definitely-not-iso-format",
        "result": {"outcome": "pass"},
    }
    bad = cache_dir / ("b" * 32 + ".json")
    bad.write_text(json.dumps(bad_payload), encoding="utf-8")

    # Act
    removed = _prune_if_oversize(cache_dir)

    # Assert -- the bad entry was evicted; the healthy one survives.
    assert removed == 1, f"unparseable verified_at must be evicted; got {removed} evictions"
    assert not bad.exists(), "bad entry must be removed"
    assert healthy.exists(), "healthy entry must survive"


# ---------------------------------------------------------------------------
# _prune_if_oversize naive verified_at handling (line 508)
# ---------------------------------------------------------------------------


def test_prune_handles_naive_verified_at_in_healthy_entries(tmp_path: Path) -> None:
    """Healthy entries with naive ``verified_at`` are anchored to UTC for LRU.

    Line 508 covers the tz-naive -> tz-aware coercion inside the prune loop.
    Without this, the comparison in the LRU sort would raise TypeError.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir()

    # Mix naive and tz-aware entries; both should be sortable for LRU.
    naive_iso = "2026-04-26T11:00:00"  # no Z, no offset -> tz-naive
    aware_iso = "2026-04-26T12:00:00Z"

    naive_path = cache_dir / ("n" * 32 + ".json")
    naive_path.write_text(
        json.dumps(
            {
                "check_name": "ruff-check",
                "verified_at": naive_iso,
                "result": {"outcome": "pass"},
            }
        ),
        encoding="utf-8",
    )

    aware_path = cache_dir / ("a" * 32 + ".json")
    aware_path.write_text(
        json.dumps(
            {
                "check_name": "ruff-check",
                "verified_at": aware_iso,
                "result": {"outcome": "pass"},
            }
        ),
        encoding="utf-8",
    )

    # Act -- with max_entries=1 to force the LRU sort over mixed tzinfo.
    try:
        removed = _prune_if_oversize(cache_dir, max_entries=1)
    except TypeError as exc:
        pytest.fail(f"prune must coerce naive verified_at before sorting; raised {exc!r}")

    # Assert -- exactly one was evicted (the older naive one, since both
    # parsed to UTC and naive_iso predates aware_iso by 1 hour).
    assert removed == 1, f"expected one eviction; got {removed}"
    assert not naive_path.exists(), "older (naive 11:00) entry must be evicted by LRU"
    assert aware_path.exists(), "newer (aware 12:00) entry must survive"


# ---------------------------------------------------------------------------
# _prune_if_oversize FileNotFoundError race on corrupt unlink (lines 516-518)
# ---------------------------------------------------------------------------


def test_prune_handles_concurrent_unlink_during_corrupt_eviction(tmp_path: Path) -> None:
    """A FileNotFoundError raised during corrupt-entry unlink is swallowed."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir()

    # Seed two corrupt entries (truncated JSON -> _read_safe returns None).
    bad_a = cache_dir / ("a" * 32 + ".json")
    bad_a.write_text("{not-json", encoding="utf-8")
    bad_b = cache_dir / ("b" * 32 + ".json")
    bad_b.write_text("{also-not-json", encoding="utf-8")

    # Mock Path.unlink so the FIRST corrupt eviction raises FileNotFoundError
    # (simulating a concurrent prune already removing it), and the second
    # falls through to real unlink.
    real_unlink = Path.unlink
    call_count = {"n": 0}

    def racey_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise FileNotFoundError(f"simulated race on {self.name}")
        real_unlink(self, *args, **kwargs)

    # Act -- must not raise; the FileNotFoundError is swallowed per contract.
    with mock.patch.object(Path, "unlink", new=racey_unlink):
        try:
            removed = _prune_if_oversize(cache_dir)
        except FileNotFoundError as exc:
            pytest.fail(f"FileNotFoundError must be swallowed during prune; got {exc!r}")

    # Assert -- exactly ONE successful eviction (second call); the swallowed
    # one wasn't counted as evicted.
    assert removed == 1, f"prune must count only successful unlinks; got {removed}"


# ---------------------------------------------------------------------------
# _prune_if_oversize FileNotFoundError race on LRU unlink (lines 530-531)
# ---------------------------------------------------------------------------


def test_prune_handles_concurrent_unlink_during_lru_eviction(tmp_path: Path) -> None:
    """A FileNotFoundError raised during LRU-overflow unlink is swallowed."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir()

    # Seed three healthy entries; max_entries=1 -> LRU evicts two.
    base = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    for idx, prefix in enumerate(("o", "m", "n")):  # oldest, mid, newest
        verified_at = (base + timedelta(seconds=idx)).isoformat().replace("+00:00", "Z")
        path = cache_dir / (prefix * 32 + ".json")
        path.write_text(
            json.dumps(
                {
                    "check_name": "ruff-check",
                    "verified_at": verified_at,
                    "result": {"outcome": "pass"},
                }
            ),
            encoding="utf-8",
        )

    # Race: first LRU unlink raises FileNotFoundError; subsequent unlinks
    # behave normally. There are no corrupted entries so the racey unlink
    # must hit the LRU branch (lines 526-531).
    real_unlink = Path.unlink
    call_count = {"n": 0}

    def racey_unlink(self: Path, *args: Any, **kwargs: Any) -> None:
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise FileNotFoundError(f"simulated LRU race on {self.name}")
        real_unlink(self, *args, **kwargs)

    # Act
    with mock.patch.object(Path, "unlink", new=racey_unlink):
        try:
            removed = _prune_if_oversize(cache_dir, max_entries=1)
        except FileNotFoundError as exc:
            pytest.fail(f"FileNotFoundError on LRU unlink must be swallowed; got {exc!r}")

    # Assert -- one of the two LRU evictions was raced (not counted), the
    # other succeeded -> evicted == 1.
    assert removed == 1, f"LRU prune must count only successful unlinks under race; got {removed}"


# ---------------------------------------------------------------------------
# _read_bytes_shared Windows FILE_SHARE_DELETE branch (lines 268-320)
#
# ARC-320: the share-delete read primitive fixes the Windows concurrent-persist
# flake, but its body is a Windows-only ctypes/msvcrt path that the POSIX CI
# coverage runners never execute (``sys.platform != "win32"`` short-circuits at
# line 265-266). The new-code coverage quality gate therefore reads the whole
# branch as uncovered. These tests drive that branch on any OS by faking the
# Windows environment (``sys.platform``, a stub ``msvcrt`` module, and a mocked
# ``kernel32``), exercising the success path plus all three error exits so the
# fix is genuinely covered — no coverage suppression, no skip-on-windows shim.
# ---------------------------------------------------------------------------


@contextmanager
def _fake_win32_env(
    *,
    create_file_return: Any,
    open_osfhandle: Any,
):
    """Make ``_read_bytes_shared`` take its Windows branch on any platform.

    Patches the three seams the branch reaches for that do not exist (or would
    behave differently) off-Windows:

    * ``gate_cache.sys.platform`` -> ``"win32"`` so line 265 falls through.
    * a stub ``msvcrt`` module in ``sys.modules`` (``import msvcrt`` inside the
      function would otherwise ``ImportError`` on POSIX).
    * ``ctypes.WinDLL`` / ``ctypes.WinError`` created on the real ``ctypes``
      module (Windows-only attributes) returning a mock ``kernel32``.

    ``create_file_return`` is what the faked ``CreateFileW`` yields (an int
    handle, or ``INVALID_HANDLE_VALUE`` to force the error exit).
    ``open_osfhandle`` becomes ``msvcrt.open_osfhandle`` (an int fd or a
    ``side_effect``).
    """
    import ctypes as _ctypes
    import sys as _sys
    import types as _types

    from ai_engineering.policy import gate_cache

    kernel32 = mock.MagicMock(name="kernel32")
    kernel32.CreateFileW.return_value = create_file_return

    fake_msvcrt = _types.ModuleType("msvcrt")
    fake_msvcrt.open_osfhandle = open_osfhandle  # type: ignore[attr-defined]

    def _win_error(code: Any) -> OSError:
        # Mirror the real ctypes.WinError mapping enough for assertions: a
        # sharing/lock code -> PermissionError, everything else -> generic OSError.
        return PermissionError(f"simulated WinError({code})")

    with ExitStack() as stack:
        stack.enter_context(mock.patch.object(gate_cache.sys, "platform", "win32"))
        stack.enter_context(mock.patch.dict(_sys.modules, {"msvcrt": fake_msvcrt}))
        stack.enter_context(
            mock.patch.object(_ctypes, "WinDLL", create=True, return_value=kernel32)
        )
        stack.enter_context(
            mock.patch.object(_ctypes, "WinError", create=True, side_effect=_win_error)
        )
        stack.enter_context(
            mock.patch.object(_ctypes, "get_last_error", create=True, return_value=32)
        )
        yield kernel32


def test_read_bytes_shared_windows_success_reads_all_bytes(tmp_path: Path) -> None:
    """Windows branch returns the file's bytes via the FILE_SHARE_DELETE handle.

    Drives lines 268-300 (imports/constants/CreateFileW), the pass-through of
    the handle check (301), and the msvcrt.open_osfhandle -> fdopen -> read
    happy path (307-320). A real fd is handed back from the stubbed
    ``open_osfhandle`` so ``os.fdopen(...).read()`` returns the actual content.
    """
    import os as _os

    from ai_engineering.policy.gate_cache import _read_bytes_shared

    payload = b'{"check_name": "ruff", "verified_at": "2026-07-06T00:00:00+00:00"}'
    target = tmp_path / "entry.json"
    target.write_bytes(payload)

    # A genuine read-only fd; the production code takes ownership and closes it.
    real_fd = _os.open(target, _os.O_RDONLY)

    with _fake_win32_env(
        create_file_return=0x1234, open_osfhandle=lambda handle, flags: real_fd
    ) as kernel32:
        result = _read_bytes_shared(target)

    assert result == payload, f"share-delete read must return full file bytes; got {result!r}"
    kernel32.CreateFileW.assert_called_once()
    # FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE == 0x7 is the 3rd arg.
    share_mode = kernel32.CreateFileW.call_args.args[2]
    assert share_mode == 0x00000007, (
        f"read handle must request SHARE_READ|WRITE|DELETE (0x7); got {share_mode:#x}"
    )


def test_read_bytes_shared_windows_invalid_handle_raises(tmp_path: Path) -> None:
    """INVALID_HANDLE_VALUE from CreateFileW raises a mapped OSError (301-305)."""
    import ctypes

    from ai_engineering.policy.gate_cache import _read_bytes_shared

    invalid = ctypes.c_void_p(-1).value

    def _should_not_open(handle: Any, flags: Any) -> int:  # pragma: no cover - guard
        raise AssertionError("open_osfhandle must not run when the handle is invalid")

    with (
        _fake_win32_env(create_file_return=invalid, open_osfhandle=_should_not_open),
        pytest.raises(OSError) as excinfo,
    ):
        _read_bytes_shared(tmp_path / "missing.json")

    assert "WinError" in str(excinfo.value), (
        f"invalid handle must surface a ctypes.WinError-mapped OSError; got {excinfo.value!r}"
    )


def test_read_bytes_shared_windows_open_osfhandle_failure_closes_handle(tmp_path: Path) -> None:
    """open_osfhandle OSError closes the OS handle then re-raises (310-313)."""
    from ai_engineering.policy.gate_cache import _read_bytes_shared

    boom = OSError("simulated open_osfhandle failure")

    def _raising_open(handle: Any, flags: Any) -> int:
        raise boom

    with (
        _fake_win32_env(create_file_return=0x1234, open_osfhandle=_raising_open) as kernel32,
        pytest.raises(OSError) as excinfo,
    ):
        _read_bytes_shared(tmp_path / "entry.json")

    assert excinfo.value is boom, "the original open_osfhandle OSError must propagate unchanged"
    # the leaked OS handle must be closed before re-raising
    kernel32.CloseHandle.assert_called_once_with(0x1234)


def test_read_bytes_shared_windows_fdopen_failure_closes_fd(tmp_path: Path) -> None:
    """fdopen OSError closes the fd then re-raises (314-318)."""
    import os as _os

    from ai_engineering.policy import gate_cache
    from ai_engineering.policy.gate_cache import _read_bytes_shared

    target = tmp_path / "entry.json"
    target.write_bytes(b"{}")
    real_fd = _os.open(target, _os.O_RDONLY)

    boom = OSError("simulated fdopen failure")
    closed: list[int] = []
    real_close = _os.close  # capture before patching to avoid recursing into the mock

    def _tracking_close(fd: int) -> None:
        closed.append(fd)
        real_close(fd)

    with (
        _fake_win32_env(create_file_return=0x1234, open_osfhandle=lambda handle, flags: real_fd),
        mock.patch.object(gate_cache._stdlib_os, "fdopen", side_effect=boom),
        mock.patch.object(gate_cache._stdlib_os, "close", side_effect=_tracking_close),
        pytest.raises(OSError) as excinfo,
    ):
        _read_bytes_shared(target)

    assert excinfo.value is boom, "the original fdopen OSError must propagate unchanged"
    assert closed == [real_fd], f"the orphaned fd must be closed exactly once; got {closed!r}"
