"""Unit tests for ``ai_engineering.policy.gate_cache`` hit/miss semantics.

RED phase for spec-104 T-1.3 (D-104-03 hit semantics + miss handling).

Target functions/classes (do not exist yet — created in T-1.4 GREEN):
    - ``lookup(cache_dir, check_name, args, staged_blob_shas, tool_version,
      config_file_hashes) -> CacheEntry | None``
        Returns the persisted ``CacheEntry`` on hit (with ``cache_hit=True``);
        returns ``None`` on miss.
    - ``persist(cache_dir, check_name, args, staged_blob_shas, tool_version,
      config_file_hashes, result) -> None``
        Writes the result keyed by the same 5 inputs the lookup hashes.
    - ``CacheEntry`` Pydantic model with the fields:
        ``check_name: str``, ``key_inputs: dict``, ``result: dict``,
        ``verified_at: datetime``, ``cache_hit: bool``.

Each test currently fails with ``ImportError`` because the new symbols are
not implemented. T-1.4 GREEN phase wires ``lookup`` and ``persist`` on top
of the cache-key primitives shipped in T-0.6 (`_compute_cache_key`,
`_CONFIG_FILE_WHITELIST`); these tests then turn GREEN and become the
contract for D-104-03 hit / miss semantics.

TDD CONSTRAINT: this file is IMMUTABLE after T-1.3 lands. T-1.4 may only
extend the production module to satisfy these assertions; never edit the
assertions themselves.

Governance covered (per D-104-03):
    - Empty cache directory yields a clean miss.
    - Different inputs yield distinct cache keys → independent miss.
    - Round-trip persist → lookup with identical inputs → hit.
    - Sensitivity to ``args`` and ``tool_version`` (cache key inputs).
    - PASS results replay PASS; FAIL results replay FAIL with original
      findings list intact.
    - Re-persist for the same key overwrites the prior entry.
    - Returned entries set ``cache_hit=True`` so the orchestrator can
      log replay decisions in ``gate-findings.json``.
    - Lookups never mutate cache files (read-only on hit).
    - ``persist`` auto-creates ``.ai-engineering/state/gate-cache/``.
    - Concurrent persist + lookup yields a consistent (non-corrupt) view.
    - Persisted entries record ``key_inputs`` for audit trail.
    - Manual ``cache_dir`` clear → next lookup returns ``None``.
    - Persisted filename uses the 32-char ``_compute_cache_key`` digest
      (verifies integration with T-0.6 primitives).
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers — canonical inputs for hit/miss exercises
# ---------------------------------------------------------------------------


def _baseline_inputs() -> dict[str, object]:
    """Return canonical lookup/persist kwargs (excluding ``cache_dir``)."""
    return {
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


def _pass_result() -> dict[str, object]:
    """Return a canonical PASS result dict (no findings)."""
    return {
        "outcome": "pass",
        "findings": [],
        "exit_code": 0,
        "stdout": "All checks passed.\n",
        "stderr": "",
    }


def _fail_result() -> dict[str, object]:
    """Return a canonical FAIL result dict with deterministic findings."""
    return {
        "outcome": "fail",
        "exit_code": 1,
        "stdout": "",
        "stderr": "ruff-check found issues.\n",
        "findings": [
            {
                "check": "ruff",
                "rule_id": "E501",
                "file": "src/example.py",
                "line": 42,
                "column": 80,
                "severity": "low",
                "message": "Line too long",
                "auto_fixable": True,
                "auto_fix_command": "ruff format src/example.py",
            },
            {
                "check": "ruff",
                "rule_id": "F401",
                "file": "src/example.py",
                "line": 1,
                "column": 1,
                "severity": "info",
                "message": "Unused import",
                "auto_fixable": True,
                "auto_fix_command": "ruff check --fix src/example.py",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Tests — 15 failing assertions (RED) wired to the T-1.4 contract
# ---------------------------------------------------------------------------


def test_lookup_returns_none_when_cache_dir_empty(tmp_path: Path) -> None:
    """Fresh, empty cache directory → miss (returns ``None``)."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir()
    inputs = _baseline_inputs()

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is None


def test_lookup_returns_none_when_key_missing(tmp_path: Path) -> None:
    """Persisted entry under one key → lookup with different inputs misses."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    persist(cache_dir=cache_dir, result=_pass_result(), **_baseline_inputs())

    # Different staged blob shas → different cache key → miss expected.
    different_inputs = _baseline_inputs()
    different_inputs["staged_blob_shas"] = [
        "1111111111111111111111111111111111111111",
    ]

    # Act
    entry = lookup(cache_dir=cache_dir, **different_inputs)

    # Assert
    assert entry is None


def test_persist_then_lookup_returns_entry(tmp_path: Path) -> None:
    """Round-trip: persist then lookup with identical inputs returns the entry."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    inputs = _baseline_inputs()
    persist(cache_dir=cache_dir, result=_pass_result(), **inputs)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is not None
    assert entry.check_name == inputs["check_name"]
    assert entry.result["outcome"] == "pass"


def test_persist_then_lookup_with_different_args_returns_none(tmp_path: Path) -> None:
    """Changing ``args`` must invalidate the cache (different hash key)."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    persist(cache_dir=cache_dir, result=_pass_result(), **_baseline_inputs())

    other_inputs = _baseline_inputs()
    other_inputs["args"] = ["check", "tests/"]  # different argv

    # Act
    entry = lookup(cache_dir=cache_dir, **other_inputs)

    # Assert
    assert entry is None


def test_persist_then_lookup_with_different_tool_version_returns_none(
    tmp_path: Path,
) -> None:
    """Bumping ``tool_version`` must invalidate the cache."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    persist(cache_dir=cache_dir, result=_pass_result(), **_baseline_inputs())

    other_inputs = _baseline_inputs()
    other_inputs["tool_version"] = "0.6.5"  # version bump

    # Act
    entry = lookup(cache_dir=cache_dir, **other_inputs)

    # Assert
    assert entry is None


def test_lookup_returns_pass_result_replays_pass(tmp_path: Path) -> None:
    """A cached PASS replays PASS verbatim on hit (D-104-03 hit semantics)."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    pass_result = _pass_result()
    persist(cache_dir=cache_dir, result=pass_result, **_baseline_inputs())

    # Act
    entry = lookup(cache_dir=cache_dir, **_baseline_inputs())

    # Assert
    assert entry is not None
    assert entry.result["outcome"] == "pass"
    assert entry.result["exit_code"] == 0
    assert entry.result["findings"] == []


def test_lookup_returns_fail_result_replays_fail_with_findings(tmp_path: Path) -> None:
    """A cached FAIL replays FAIL with the original findings list intact."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    fail_result = _fail_result()
    persist(cache_dir=cache_dir, result=fail_result, **_baseline_inputs())

    # Act
    entry = lookup(cache_dir=cache_dir, **_baseline_inputs())

    # Assert
    assert entry is not None
    assert entry.result["outcome"] == "fail"
    assert entry.result["exit_code"] == 1
    findings = entry.result["findings"]
    assert isinstance(findings, list)
    assert len(findings) == 2
    rule_ids = {f["rule_id"] for f in findings}
    assert rule_ids == {"E501", "F401"}


def test_persist_overwrites_existing_entry(tmp_path: Path) -> None:
    """A second ``persist`` for the same key replaces the prior entry."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    inputs = _baseline_inputs()
    persist(cache_dir=cache_dir, result=_fail_result(), **inputs)

    # Act — re-persist with PASS for the same key.
    persist(cache_dir=cache_dir, result=_pass_result(), **inputs)
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is not None
    assert entry.result["outcome"] == "pass"
    assert entry.result["findings"] == []


def test_lookup_includes_cache_hit_true_in_returned_entry(tmp_path: Path) -> None:
    """Returned entry signals ``cache_hit=True`` so callers can log replays."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    inputs = _baseline_inputs()
    persist(cache_dir=cache_dir, result=_pass_result(), **inputs)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is not None
    assert entry.cache_hit is True


def test_lookup_does_not_mutate_cache_files(tmp_path: Path) -> None:
    """Lookup must be read-only — file mtime unchanged after a hit."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    inputs = _baseline_inputs()
    persist(cache_dir=cache_dir, result=_pass_result(), **inputs)

    # Capture the mtime of every file in the cache directory.
    cached_files = sorted(cache_dir.rglob("*"))
    pre_lookup_mtimes = {p: p.stat().st_mtime_ns for p in cached_files if p.is_file()}
    assert pre_lookup_mtimes, "persist did not write any file under cache_dir"

    # Sleep to ensure any spurious write would shift mtime resolution.
    time.sleep(0.01)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is not None
    post_lookup_mtimes = {p: p.stat().st_mtime_ns for p in pre_lookup_mtimes}
    assert post_lookup_mtimes == pre_lookup_mtimes, (
        "Lookup mutated cache files (mtime drift): "
        f"before={pre_lookup_mtimes}, after={post_lookup_mtimes}"
    )


def test_persist_creates_cache_dir_if_missing(tmp_path: Path) -> None:
    """``persist`` auto-creates ``.ai-engineering/state/gate-cache/`` when absent."""
    # Arrange
    from ai_engineering.policy.gate_cache import persist

    # Use a deeply nested path that does NOT exist yet.
    cache_dir = tmp_path / ".ai-engineering" / "state" / "gate-cache"
    assert not cache_dir.exists(), "test precondition: cache_dir must not pre-exist"

    # Act
    persist(cache_dir=cache_dir, result=_pass_result(), **_baseline_inputs())

    # Assert
    assert cache_dir.is_dir(), "persist should have auto-created cache_dir"
    cached_files = [p for p in cache_dir.iterdir() if p.is_file()]
    assert cached_files, "persist should have written at least one file"


def test_lookup_handles_concurrent_persist_safely(tmp_path: Path) -> None:
    """Interleaved persist + lookup yield a consistent, non-corrupt view.

    Spawn multiple writer threads persisting different results for the same
    cache key while a reader thread polls ``lookup``. The reader must never
    observe a corrupted state — every successful read returns either the
    sentinel ``None`` (write hasn't completed yet) or a fully-formed entry
    whose ``result`` dict round-trips through dict-access without raising.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    inputs = _baseline_inputs()
    iterations = 25
    results_observed: list[dict[str, object]] = []
    exceptions: list[Exception] = []

    def writer() -> None:
        try:
            for i in range(iterations):
                # Alternate PASS/FAIL to maximise inter-write divergence.
                payload = _pass_result() if i % 2 == 0 else _fail_result()
                persist(cache_dir=cache_dir, result=payload, **inputs)
        except Exception as exc:
            # Cross-thread errors must be captured so the main thread can fail loudly.
            exceptions.append(exc)

    def reader() -> None:
        try:
            for _ in range(iterations * 2):
                entry = lookup(cache_dir=cache_dir, **inputs)
                if entry is not None:
                    # Touch the result dict to force any lazy decoding errors.
                    outcome = entry.result["outcome"]
                    assert outcome in {"pass", "fail"}
                    results_observed.append(entry.result)
        except Exception as exc:
            exceptions.append(exc)

    writer_thread = threading.Thread(target=writer, name="cache-writer")
    reader_thread = threading.Thread(target=reader, name="cache-reader")

    # Act
    writer_thread.start()
    reader_thread.start()
    writer_thread.join(timeout=10.0)
    reader_thread.join(timeout=10.0)

    # Assert
    assert not exceptions, f"Concurrent persist/lookup raised: {exceptions!r}"
    assert not writer_thread.is_alive()
    assert not reader_thread.is_alive()
    final = lookup(cache_dir=cache_dir, **inputs)
    assert final is not None, "After all writers finished, the entry must exist."
    assert final.result["outcome"] in {"pass", "fail"}


def test_persist_stores_key_inputs_for_audit(tmp_path: Path) -> None:
    """Persisted entry includes ``key_inputs`` carrying the 5 hashed fields."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    inputs = _baseline_inputs()
    persist(cache_dir=cache_dir, result=_pass_result(), **inputs)

    # Act
    entry = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert entry is not None
    assert isinstance(entry.key_inputs, dict)
    expected_keys = {
        "check_name",
        "args",
        "staged_blob_shas",
        "tool_version",
        "config_file_hashes",
    }
    assert set(entry.key_inputs.keys()) == expected_keys, (
        "key_inputs must record exactly the 5 hashed fields for audit trail; "
        f"got {set(entry.key_inputs.keys())!r}"
    )
    assert entry.key_inputs["check_name"] == inputs["check_name"]
    assert entry.key_inputs["tool_version"] == inputs["tool_version"]


def test_lookup_returns_none_after_clear(tmp_path: Path) -> None:
    """Manually clearing ``cache_dir`` → next lookup misses (returns ``None``)."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    inputs = _baseline_inputs()
    persist(cache_dir=cache_dir, result=_pass_result(), **inputs)

    # Sanity check: hit after persist.
    pre_clear = lookup(cache_dir=cache_dir, **inputs)
    assert pre_clear is not None, "test precondition: persist+lookup should hit"

    # Manually clear every file (simulate ``ai-eng gate cache --clear``).
    for path in cache_dir.iterdir():
        if path.is_file():
            path.unlink()

    # Act
    post_clear = lookup(cache_dir=cache_dir, **inputs)

    # Assert
    assert post_clear is None


def test_persist_uses_correct_filename_per_key(tmp_path: Path) -> None:
    """Persisted filename uses the 32-char ``_compute_cache_key`` digest.

    Verifies integration with T-0.6 primitives: ``persist`` must derive the
    cache filename from ``_compute_cache_key`` so ``lookup`` (using the same
    helper) finds it. This is the storage-layer contract in D-104-09.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import _compute_cache_key, persist

    cache_dir = tmp_path / "gate-cache"
    inputs = _baseline_inputs()

    # Act
    persist(cache_dir=cache_dir, result=_pass_result(), **inputs)
    expected_key = _compute_cache_key(**inputs)
    cached_files = [p for p in cache_dir.iterdir() if p.is_file()]

    # Assert
    assert cached_files, "persist must write at least one file"
    matching = [p for p in cached_files if expected_key in p.name]
    assert matching, (
        f"No persisted file embedded the expected 32-char cache key {expected_key!r}; "
        f"found files: {[p.name for p in cached_files]}"
    )
    # Belt-and-suspenders: assert the basename starts with the digest so the
    # filename is deterministic (no random prefix).
    leading = matching[0].name
    assert leading.startswith(expected_key), (
        f"Cache filename {leading!r} must start with the 32-char digest {expected_key!r} "
        "to keep the storage layout auditable per D-104-09."
    )

    # Cross-platform path sanity (Windows + POSIX): no path separators leaked
    # into the basename through the digest.
    assert os.sep not in leading.replace(os.sep, "")  # tautology, kept for clarity
    assert "/" not in leading and "\\" not in leading, (
        "Cache filename must not contain path separators."
    )
