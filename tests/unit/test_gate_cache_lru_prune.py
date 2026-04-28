"""Unit tests for ``ai_engineering.policy.gate_cache._prune_if_oversize``.

RED phase for spec-104 T-1.7 (D-104-03 size-bound: LRU prune to 256 entries on
every ``_persist``; total disk cap ``<= 16 MB`` per cache directory).

Target function (does not exist yet -- created in T-1.8):
    - ``_prune_if_oversize(cache_dir: Path, max_entries: int = 256) -> int``
        Walks ``cache_dir`` for ``*.json`` cache files, evicts the
        oldest-by-``verified_at`` entries until at most ``max_entries`` remain,
        cleans entries that fail to parse as gate-cache JSON, and returns the
        number of files removed.

Each test currently fails with ``ImportError`` because the function is not
implemented. T-1.8 GREEN phase will implement it and these tests become the
contract for the LRU + budget invariant in D-104-03.

TDD CONSTRAINT: this file is IMMUTABLE after T-1.7 lands.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

# Constants documenting the contract (D-104-03):
MAX_ENTRIES = 256
MAX_DISK_BYTES = 16 * 1024 * 1024  # 16 MB total cap.
MAX_ENTRY_BYTES = 64 * 1024  # 64 KB per entry (256 * 64KB = 16 MB).


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(
    *,
    verified_at: datetime,
    check_name: str = "ruff-check",
    payload_size: int = 256,
) -> dict[str, Any]:
    """Return a canonical gate-cache entry dict with controllable size.

    ``payload_size`` controls a filler ``findings_blob`` field so callers can
    target a specific on-disk byte budget per entry. The ``verified_at`` field
    drives LRU ordering (oldest evicted first per D-104-03).
    """

    return {
        "check_name": check_name,
        "result": "PASS",
        "findings": [],
        "verified_at": verified_at.isoformat(),
        "verified_by_version": "0.6.4",
        "key_inputs": {
            "tool_version": "0.6.4",
            "args": ["check", "src/"],
        },
        # Filler ensures we can hit the 64 KB target per entry deterministically.
        "findings_blob": "x" * max(0, payload_size),
    }


def _write_entry(cache_dir: Path, key: str, entry: dict[str, Any]) -> Path:
    """Write a cache entry as ``<key>.json`` under ``cache_dir``."""

    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{key}.json"
    path.write_text(json.dumps(entry), encoding="utf-8")
    return path


def _populate(
    cache_dir: Path,
    count: int,
    *,
    base_time: datetime | None = None,
    payload_size: int = 256,
) -> list[Path]:
    """Populate ``cache_dir`` with ``count`` entries, oldest first.

    Returns the list of file paths in chronological insertion order so callers
    can refer to "the oldest" / "the newest" by index.
    """

    base = base_time or datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    paths: list[Path] = []
    for idx in range(count):
        verified_at = base + timedelta(seconds=idx)
        entry = _make_entry(verified_at=verified_at, payload_size=payload_size)
        # 32-char hex-style key (matches D-104-09 filename convention).
        key = f"{idx:032x}"
        paths.append(_write_entry(cache_dir, key, entry))
    return paths


def _count_entries(cache_dir: Path) -> int:
    """Count ``*.json`` cache files in ``cache_dir`` (non-recursive)."""

    if not cache_dir.exists():
        return 0
    return sum(1 for p in cache_dir.iterdir() if p.is_file() and p.suffix == ".json")


def _total_dir_size(cache_dir: Path) -> int:
    """Return total size in bytes of all files under ``cache_dir``."""

    if not cache_dir.exists():
        return 0
    return sum(p.stat().st_size for p in cache_dir.iterdir() if p.is_file())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_prune_no_op_when_under_cap(tmp_path: Path) -> None:
    """200 entries (< 256 cap) -> no eviction, all entries remain."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    paths = _populate(cache_dir, count=200)
    pre_paths = {p.name for p in paths}

    # Act
    removed = _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)

    # Assert
    assert removed == 0, f"Expected no evictions under cap, got {removed}"
    assert _count_entries(cache_dir) == 200
    post_paths = {p.name for p in cache_dir.iterdir() if p.is_file()}
    assert post_paths == pre_paths, "Entry set must be unchanged when under cap"


def test_prune_triggers_at_257th_entry(tmp_path: Path) -> None:
    """Adding a 257th entry causes prune to bring count back down to 256."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    _populate(cache_dir, count=257)
    assert _count_entries(cache_dir) == 257, "Pre-condition: 257 entries on disk"

    # Act
    removed = _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)

    # Assert
    assert removed == 1, f"Expected 1 eviction at 257->256, got {removed}"
    assert _count_entries(cache_dir) == MAX_ENTRIES


def test_prune_evicts_oldest_by_verified_at(tmp_path: Path) -> None:
    """The entry with the oldest ``verified_at`` is evicted first."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    paths = _populate(cache_dir, count=257)
    oldest_path = paths[0]  # idx=0 -> base_time + 0s, the oldest.
    assert oldest_path.exists(), "Pre-condition: oldest entry present"

    # Act
    removed = _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)

    # Assert
    assert removed == 1
    assert not oldest_path.exists(), (
        f"Oldest entry {oldest_path.name!r} must be evicted first per LRU contract"
    )
    # Newer entries survive.
    for survivor in paths[1:]:
        assert survivor.exists(), f"Survivor {survivor.name!r} unexpectedly removed"


def test_prune_preserves_recently_accessed(tmp_path: Path) -> None:
    """The most-recent ``verified_at`` is always retained after prune."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    # Over-populate by a wide margin so eviction has many candidates to choose.
    paths = _populate(cache_dir, count=300)
    newest_path = paths[-1]

    # Act
    _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)

    # Assert
    assert _count_entries(cache_dir) == MAX_ENTRIES
    assert newest_path.exists(), "The newest-by-verified_at entry must always survive prune"
    # Sanity: the youngest 256 should be the survivors.
    expected_survivors = {p.name for p in paths[-MAX_ENTRIES:]}
    actual_survivors = {p.name for p in cache_dir.iterdir() if p.is_file()}
    assert actual_survivors == expected_survivors, (
        "Surviving set must equal the youngest 256 entries"
    )


def test_prune_idempotent(tmp_path: Path) -> None:
    """Running prune a second time on an already-pruned cache is a no-op."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    _populate(cache_dir, count=300)

    # Act -- first prune brings us to the cap.
    first_removed = _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)
    after_first = _count_entries(cache_dir)
    snapshot_first = {p.name for p in cache_dir.iterdir() if p.is_file()}

    # Act -- second prune should be a no-op.
    second_removed = _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)
    after_second = _count_entries(cache_dir)
    snapshot_second = {p.name for p in cache_dir.iterdir() if p.is_file()}

    # Assert
    assert first_removed == 300 - MAX_ENTRIES, (
        f"First prune should evict {300 - MAX_ENTRIES}, got {first_removed}"
    )
    assert after_first == MAX_ENTRIES
    assert second_removed == 0, "Second prune on capped cache must remove nothing"
    assert after_second == MAX_ENTRIES
    assert snapshot_first == snapshot_second, (
        "Idempotent prune must not perturb the surviving entry set"
    )


def test_prune_handles_corrupted_entries(tmp_path: Path) -> None:
    """Entries that fail to parse are treated as evictable and cleaned out."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 250 healthy entries -- under the 256 cap by themselves.
    healthy_paths = _populate(cache_dir, count=250)
    assert len(healthy_paths) == 250

    # Inject corrupted siblings: one truncated JSON, one binary garbage,
    # one with valid JSON but missing required ``verified_at`` field.
    truncated = cache_dir / ("a" * 32 + ".json")
    truncated.write_text('{"check_name": "ruff-check", "result":', encoding="utf-8")

    binary_garbage = cache_dir / ("b" * 32 + ".json")
    binary_garbage.write_bytes(b"\x00\x01\x02\xff\xfeNOT-JSON\x00")

    missing_field = cache_dir / ("c" * 32 + ".json")
    missing_field.write_text(
        json.dumps({"check_name": "ruff-check", "result": "PASS"}),
        encoding="utf-8",
    )

    pre_count = _count_entries(cache_dir)
    assert pre_count == 253, f"Pre-condition: 250 healthy + 3 corrupt = 253, got {pre_count}"

    # Act
    removed = _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)

    # Assert -- corrupted entries are removed unconditionally even when total
    # is below the cap, because they cannot participate in LRU ordering.
    assert removed == 3, (
        f"All 3 corrupted entries must be evicted (parse failure = evictable), got {removed}"
    )
    assert not truncated.exists(), "Truncated JSON entry must be cleaned out"
    assert not binary_garbage.exists(), "Binary-garbage entry must be cleaned out"
    assert not missing_field.exists(), (
        "Entry missing required verified_at field must be cleaned out"
    )
    # Healthy entries untouched.
    for healthy in healthy_paths:
        assert healthy.exists(), f"Healthy entry {healthy.name!r} unexpectedly removed"


def test_total_disk_budget_under_16mb(tmp_path: Path) -> None:
    """Populated near max-size entries -- total dir size remains <= 16 MB."""
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    # Over-populate with near-max-size entries to force prune to enforce the
    # disk budget. Each entry ~64 KB; 300 entries pre-prune ~= 19.2 MB.
    # After prune to 256 entries the total must be <= 16 MB.
    payload_size = MAX_ENTRY_BYTES - 1024  # ~63 KB filler; framing brings to ~64 KB.
    _populate(cache_dir, count=300, payload_size=payload_size)
    pre_size = _total_dir_size(cache_dir)
    assert pre_size > MAX_DISK_BYTES, (
        f"Pre-condition: must over-fill above 16 MB cap, got {pre_size} bytes "
        f"({pre_size / 1024 / 1024:.2f} MB)"
    )

    # Act
    _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)

    # Assert
    post_count = _count_entries(cache_dir)
    post_size = _total_dir_size(cache_dir)
    assert post_count <= MAX_ENTRIES, (
        f"Post-prune entry count {post_count} exceeds cap {MAX_ENTRIES}"
    )
    assert post_size <= MAX_DISK_BYTES, (
        f"Post-prune total size {post_size} bytes "
        f"({post_size / 1024 / 1024:.2f} MB) exceeds 16 MB cap"
    )


def test_prune_handles_concurrent_writes_gracefully(tmp_path: Path) -> None:
    """Interleaved persist + prune must not corrupt the cache.

    Two writer threads continuously add new entries while a third thread
    repeatedly invokes ``_prune_if_oversize``. After all threads join:

    * The cache directory contains <= ``max_entries`` valid JSON files.
    * Every surviving file parses as valid JSON with the required
      ``verified_at`` field (no torn writes left behind).
    * No exception escapes from the prune calls (race-free contract).
    """
    # Arrange
    from ai_engineering.policy.gate_cache import _prune_if_oversize

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    base = datetime(2026, 4, 26, 12, 0, 0, tzinfo=UTC)
    stop = threading.Event()
    errors: list[BaseException] = []
    writes_per_thread = 200

    def writer(thread_idx: int) -> None:
        try:
            for i in range(writes_per_thread):
                if stop.is_set():
                    return
                key = f"{thread_idx:016x}{i:016x}"  # 32-char hex key.
                entry = _make_entry(verified_at=base + timedelta(seconds=i))
                # Atomic-style write to mimic _atomic_write semantics: write
                # to a temp sibling then rename, so prune never observes a
                # partial file under the canonical name.
                tmp = cache_dir / f"{key}.json.tmp{thread_idx}"
                tmp.write_text(json.dumps(entry), encoding="utf-8")
                tmp.replace(cache_dir / f"{key}.json")
        except BaseException as exc:  # record for assertion.
            errors.append(exc)

    def pruner() -> None:
        try:
            for _ in range(50):
                if stop.is_set():
                    return
                _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)
        except BaseException as exc:  # record for assertion.
            errors.append(exc)

    threads = [
        threading.Thread(target=writer, args=(0,), name="writer-0"),
        threading.Thread(target=writer, args=(1,), name="writer-1"),
        threading.Thread(target=pruner, name="pruner"),
    ]

    # Act
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30.0)
        if t.is_alive():
            stop.set()
            pytest.fail(f"Thread {t.name!r} hung beyond 30s -- prune may deadlock")

    # Final settling prune.
    _prune_if_oversize(cache_dir, max_entries=MAX_ENTRIES)

    # Assert -- no exceptions from any thread.
    assert not errors, f"Concurrent prune raised: {errors!r}"

    # Assert -- count within cap.
    final_count = _count_entries(cache_dir)
    assert final_count <= MAX_ENTRIES, (
        f"Final count {final_count} exceeds cap {MAX_ENTRIES} after concurrent run"
    )

    # Assert -- every surviving file is valid JSON with required fields
    # (no torn writes / partial files lingering under canonical names).
    for path in cache_dir.iterdir():
        if not path.is_file() or path.suffix != ".json":
            continue
        raw = path.read_text(encoding="utf-8")
        try:
            doc = json.loads(raw)
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"Surviving entry {path.name!r} is not valid JSON: {exc}; contents={raw[:80]!r}"
            )
        assert "verified_at" in doc, (
            f"Surviving entry {path.name!r} missing required ``verified_at`` field"
        )
