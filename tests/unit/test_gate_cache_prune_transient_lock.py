"""Regression: ``_prune_if_oversize`` must not evict momentarily-unreadable entries.

Root cause of the spec-104 Windows Integration flake (ARC-305a / #625): the
gate orchestrator runs Wave 2 checks in parallel, and ``persist`` calls
``_prune_if_oversize`` after every write. On Windows a prune running in one
thread opens sibling ``.json`` files via ``_read_safe`` while another thread is
publishing a fresh entry with ``os.replace``; the momentary share-lock raises
``PermissionError`` (an ``OSError``), which the old code funnelled to
``_read_safe`` -> ``None`` -> "corrupted" -> ``path.unlink()``. That deleted a
healthy just-written cache file, so the first run persisted only 4 of the 5
Wave 2 entries and ``test_run_gate_mixed_hit_miss`` failed its precondition.

POSIX never surfaces this (readers of an atomically-replaced file never get a
lock error), which is why the flake is Windows-only. These tests reproduce it
deterministically on any platform by making ``read_bytes`` raise ``OSError``
for a specific present file, and assert that such a file is KEPT while genuine
content corruption is still evicted.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest


def _write_entry(cache_dir: Path, key: str, *, second: int = 0) -> Path:
    """Write a valid gate-cache entry named ``<key>.json`` and return its path."""
    path = cache_dir / f"{key}.json"
    path.write_text(
        json.dumps(
            {
                "check_name": "ruff",
                "result": {"outcome": "pass", "findings": []},
                "verified_at": datetime(2026, 4, 26, 12, 0, second, tzinfo=UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    return path


def test_prune_keeps_present_but_unreadable_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file that raises ``OSError`` on read is a transient lock, not corruption."""
    from ai_engineering.policy import gate_cache

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    readable = _write_entry(cache_dir, "a" * 32, second=1)
    locked = _write_entry(cache_dir, "b" * 32, second=2)

    real_read_bytes = Path.read_bytes

    def flaky_read_bytes(self: Path) -> bytes:
        # Simulate the Windows share-lock: the sibling being published is
        # momentarily un-openable, exactly as a concurrent os.replace induces.
        if self == locked:
            raise PermissionError(13, "The process cannot access the file")
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", flaky_read_bytes)

    removed = gate_cache._prune_if_oversize(cache_dir, max_entries=gate_cache.MAX_ENTRIES)

    assert removed == 0, "A momentarily-locked healthy entry must not be evicted"
    assert locked.exists(), "Locked-but-present entry was wrongly deleted (the flake)"
    assert readable.exists(), "Unrelated healthy entry must survive"


def test_prune_still_evicts_genuine_content_corruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lock carve-out must not weaken eviction of readable-but-malformed files."""
    from ai_engineering.policy import gate_cache

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    healthy = _write_entry(cache_dir, "a" * 32, second=1)
    locked = _write_entry(cache_dir, "b" * 32, second=2)

    # Readable but malformed content — still corruption, still evictable.
    truncated = cache_dir / ("c" * 32 + ".json")
    truncated.write_text('{"check_name": "ruff", "result":', encoding="utf-8")
    binary_garbage = cache_dir / ("d" * 32 + ".json")
    binary_garbage.write_bytes(b"\x00\x01\x02\xffNOT-JSON")

    real_read_bytes = Path.read_bytes

    def flaky_read_bytes(self: Path) -> bytes:
        if self == locked:
            raise OSError(13, "locked")
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", flaky_read_bytes)

    removed = gate_cache._prune_if_oversize(cache_dir, max_entries=gate_cache.MAX_ENTRIES)

    assert removed == 2, f"Both malformed files must be evicted; removed={removed}"
    assert not truncated.exists()
    assert not binary_garbage.exists()
    assert healthy.exists()
    assert locked.exists(), "Locked healthy entry must be kept even amid corruption"
