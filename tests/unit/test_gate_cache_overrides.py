"""Unit tests for ``ai_engineering.policy.gate_cache`` override flags and kill switch.

RED phase for spec-104 T-1.9 (D-104-10 override flags + ``AIENG_CACHE_DISABLED``
env-level kill switch).

> CLI surface adicional, sin nuevos comandos top-level:
>   - ``--no-cache``: skip lookup, fresh run, persiste resultado para próximo call.
>   - ``--force``: skip lookup, **clear** entrada matching, fresh run, persiste.
>   - ``AIENG_CACHE_DISABLED=1`` env: equivalente a ``--no-cache`` global.
>   - Debug visibility: ``AIENG_CACHE_DEBUG=1`` emits hit/miss markers in the
>     ``ai_engineering.policy.gate_cache`` logger.

Target functions / behaviours (do not exist yet — wired by T-1.10):

    - ``lookup(cache_dir: Path, cache_key: str, *, disabled: bool = False)
      -> dict | None``
        When ``disabled=True`` OR ``AIENG_CACHE_DISABLED=1`` is set, the
        function MUST return ``None`` even when an entry exists on disk.
        The env var takes precedence (more conservative). When
        ``AIENG_CACHE_DEBUG=1`` is set, hit/miss outcomes MUST be logged on
        the module logger.

    - ``persist(cache_dir: Path, cache_key: str, entry: dict, *,
      disabled: bool = False) -> None``
        ``persist`` is INSENSITIVE to ``disabled`` — even when caller opted
        out of the lookup, the result is still written so subsequent
        non-disabled calls benefit. ``AIENG_CACHE_DISABLED`` is also
        ignored by ``persist`` (so the cache can warm up while the user
        is debugging with ``--no-cache``).

    - ``clear_entry(cache_dir: Path, cache_key: str) -> bool``
        Deletes the cache file ``cache_dir / f"{cache_key}.json"``.
        Returns ``True`` when a file was actually removed and ``False``
        when no matching file existed (idempotent).

Each test currently fails because the override-flag plumbing and
``clear_entry`` helper do not exist yet. T-1.10 GREEN phase will land them
and these assertions become the contract for D-104-10.

TDD CONSTRAINT: this file is IMMUTABLE after T-1.9 lands. T-1.10 may only
add behaviour to satisfy these assertions, never edit them.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _test_cache_key(salt: str) -> str:
    """Compute a deterministic 32-char hex cache key for tests.

    Computed (not hardcoded) so the strings do not trip generic-api-key heuristics
    in secret scanners (gitleaks). The shape matches `_compute_cache_key` output
    (sha256 truncated to 32 chars) so tests still exercise realistic key strings.
    """
    return hashlib.sha256(salt.encode("utf-8")).hexdigest()[:32]


_SAMPLE_KEY = _test_cache_key("spec-104-test-sample")
_OTHER_KEY = _test_cache_key("spec-104-test-other")


def _make_entry(check: str = "ruff-check", *, result: str = "pass") -> dict[str, object]:
    """Return a minimal cache-entry payload shaped like D-104-03 storage."""

    return {
        "check": check,
        "result": result,
        "findings": [],
        "verified_at": "2026-04-26T12:00:00Z",
        "verified_by_version": "0.6.4",
        "key_inputs": {"tool_version": "0.6.4"},
    }


def _seed_entry(
    cache_dir: Path,
    cache_key: str,
    entry: dict[str, object] | None = None,
) -> Path:
    """Write ``entry`` to ``cache_dir / f"{cache_key}.json"`` directly.

    Bypasses the public API so that tests asserting "cache exists, lookup
    returns None when disabled" don't accidentally exercise the very code
    path they intend to override.
    """

    cache_dir.mkdir(parents=True, exist_ok=True)
    payload = entry if entry is not None else _make_entry()
    path = cache_dir / f"{cache_key}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clear_override_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure each test starts with a clean override-env baseline.

    Tests that need the env var SET will call ``monkeypatch.setenv`` themselves;
    this fixture only guarantees we are not contaminated by a value leaked
    from a previous test or the parent process.
    """

    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)
    monkeypatch.delenv("AIENG_CACHE_DEBUG", raising=False)


# ---------------------------------------------------------------------------
# Tests — disabled flag behaviour on lookup
# ---------------------------------------------------------------------------


def test_lookup_with_disabled_skips_cache_check(tmp_path: Path) -> None:
    """``lookup(..., disabled=True)`` returns ``None`` even when a matching
    entry exists on disk."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    seeded = _seed_entry(cache_dir, _SAMPLE_KEY)
    assert seeded.exists(), "precondition: seeded cache entry exists"

    # Act
    result = lookup(cache_dir, _SAMPLE_KEY, disabled=True)

    # Assert
    assert result is None, (
        "lookup(disabled=True) must short-circuit and return None even "
        f"when {seeded.name} exists; got {result!r}"
    )

    # Sanity — the file was NOT deleted by the disabled lookup
    # (only --force/clear_entry should remove entries).
    assert seeded.exists(), "disabled=True must not mutate the cache; the entry must remain on disk"


# ---------------------------------------------------------------------------
# Tests — persist still warms the cache when disabled=True
# ---------------------------------------------------------------------------


def test_persist_with_disabled_still_persists(tmp_path: Path) -> None:
    """``persist(..., disabled=True)`` MUST still write the entry so that
    subsequent non-disabled callers benefit from the warm cache."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    entry = _make_entry(check="ty", result="pass")

    # Act — write while "disabled"
    persist(cache_dir, _SAMPLE_KEY, entry, disabled=True)

    # Assert — entry is on disk
    expected_path = cache_dir / f"{_SAMPLE_KEY}.json"
    assert expected_path.exists(), (
        "persist(disabled=True) must still write the entry so future "
        f"non-disabled callers see it; expected {expected_path} on disk"
    )

    # Assert — a subsequent lookup WITHOUT disabled returns the persisted entry
    replayed = lookup(cache_dir, _SAMPLE_KEY)
    assert replayed is not None, (
        "After persist(disabled=True), a normal lookup must hit (cache was warmed)"
    )
    # Compare via JSON round-trip to avoid coupling to model classes vs raw dicts.
    replayed_json = json.loads(json.dumps(replayed, default=str))
    assert replayed_json.get("check") == "ty", (
        f"Replayed entry must reflect the persisted payload; got {replayed_json!r}"
    )
    assert replayed_json.get("result") == "pass"


# ---------------------------------------------------------------------------
# Tests — env var kill switch on lookup
# ---------------------------------------------------------------------------


def test_aieng_cache_disabled_env_skips_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``AIENG_CACHE_DISABLED=1`` env var is equivalent to ``disabled=True``
    on the function call: lookup returns ``None`` even with a seeded entry."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    seeded = _seed_entry(cache_dir, _SAMPLE_KEY)
    assert seeded.exists(), "precondition: seeded cache entry exists"

    monkeypatch.setenv("AIENG_CACHE_DISABLED", "1")

    # Act — call WITHOUT the disabled kwarg; env var alone should suffice.
    result = lookup(cache_dir, _SAMPLE_KEY)

    # Assert
    assert result is None, (
        "AIENG_CACHE_DISABLED=1 must force lookup to return None even when "
        f"the kwarg is left at default; got {result!r}"
    )
    # Entry still on disk — env var disables, does not delete.
    assert seeded.exists(), "env-disabled lookup must not mutate the cache"


def test_aieng_cache_disabled_env_overrides_function_arg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``AIENG_CACHE_DISABLED=1`` is set, the env var takes precedence
    over a permissive ``disabled=False`` kwarg.

    Rationale (D-104-10): the env var is the more-conservative choice; CI
    and operators set it to globally kill the cache, and a stale call site
    passing ``disabled=False`` must not be able to bypass that intent.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import lookup

    cache_dir = tmp_path / "gate-cache"
    _seed_entry(cache_dir, _SAMPLE_KEY)

    monkeypatch.setenv("AIENG_CACHE_DISABLED", "1")

    # Act — caller explicitly says disabled=False, but the env var overrides.
    result = lookup(cache_dir, _SAMPLE_KEY, disabled=False)

    # Assert
    assert result is None, (
        "AIENG_CACHE_DISABLED env var MUST take precedence over disabled=False "
        f"kwarg (more-conservative wins); got {result!r}"
    )


# ---------------------------------------------------------------------------
# Tests — clear_entry helper (used by --force semantics)
# ---------------------------------------------------------------------------


def test_clear_entry_removes_matching_file(tmp_path: Path) -> None:
    """``clear_entry(cache_dir, cache_key)`` deletes the on-disk file
    ``cache_dir / f"{cache_key}.json"``."""
    # Arrange
    from ai_engineering.policy.gate_cache import clear_entry

    cache_dir = tmp_path / "gate-cache"
    seeded = _seed_entry(cache_dir, _SAMPLE_KEY)
    other = _seed_entry(cache_dir, _OTHER_KEY, _make_entry(check="ruff-format"))

    assert seeded.exists() and other.exists(), "precondition: both entries seeded"

    # Act
    clear_entry(cache_dir, _SAMPLE_KEY)

    # Assert — target removed, sibling untouched
    assert not seeded.exists(), "clear_entry must delete the file matching the requested cache key"
    assert other.exists(), "clear_entry must NOT touch other cache entries — only the matching key"


def test_clear_entry_returns_false_when_not_present(tmp_path: Path) -> None:
    """Clearing a non-existent key returns ``False`` (idempotent, no error)."""
    # Arrange
    from ai_engineering.policy.gate_cache import clear_entry

    cache_dir = tmp_path / "gate-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / f"{_SAMPLE_KEY}.json"
    assert not target.exists(), "precondition: target does not exist"

    # Act / Assert — must not raise on missing entry.
    try:
        outcome = clear_entry(cache_dir, _SAMPLE_KEY)
    except Exception as exc:  # pragma: no cover — failure path
        pytest.fail(
            "clear_entry must be idempotent — no exception on missing key. "
            f"Got: {type(exc).__name__}: {exc}"
        )

    # Assert — returns False, signalling "nothing to clear".
    assert outcome is False, f"clear_entry on missing key must return False; got {outcome!r}"


def test_clear_entry_returns_true_when_present(tmp_path: Path) -> None:
    """Clearing an existing key returns ``True``."""
    # Arrange
    from ai_engineering.policy.gate_cache import clear_entry

    cache_dir = tmp_path / "gate-cache"
    seeded = _seed_entry(cache_dir, _SAMPLE_KEY)
    assert seeded.exists()

    # Act
    outcome = clear_entry(cache_dir, _SAMPLE_KEY)

    # Assert
    assert outcome is True, f"clear_entry on present key must return True; got {outcome!r}"
    assert not seeded.exists(), "file must be removed after clear_entry returns True"


# ---------------------------------------------------------------------------
# Tests — --force composite invocation order: clear → persist → lookup
# ---------------------------------------------------------------------------


def test_force_pattern_clear_then_persist(tmp_path: Path) -> None:
    """The ``--force`` invocation order is: clear matching entry → fresh run
    → persist new result → next lookup returns the new result.

    Asserts the state machine end-to-end without assuming an internal helper
    couples the steps."""
    # Arrange
    from ai_engineering.policy.gate_cache import clear_entry, lookup, persist

    cache_dir = tmp_path / "gate-cache"
    stale = _make_entry(check="ruff-check", result="fail")
    fresh = _make_entry(check="ruff-check", result="pass")

    # Seed a stale entry so we can prove --force replaces it.
    persist(cache_dir, _SAMPLE_KEY, stale)
    seeded = lookup(cache_dir, _SAMPLE_KEY)
    assert seeded is not None, "precondition: stale entry must be present"
    seeded_json = json.loads(json.dumps(seeded, default=str))
    assert seeded_json.get("result") == "fail", "precondition: stale entry has fail result"

    # Act — simulate the --force flow.
    clear_entry(cache_dir, _SAMPLE_KEY)  # step 1: clear
    # step 2: caller would now run the check and produce `fresh`.
    persist(cache_dir, _SAMPLE_KEY, fresh)  # step 3: persist new result

    # Assert — next lookup returns the fresh entry, not the stale one.
    replayed = lookup(cache_dir, _SAMPLE_KEY)
    assert replayed is not None, "after force/persist, lookup must hit the fresh entry"
    replayed_json = json.loads(json.dumps(replayed, default=str))
    assert replayed_json.get("result") == "pass", (
        "lookup after --force flow must return the fresh entry, not the cleared stale one; "
        f"got {replayed_json!r}"
    )


# ---------------------------------------------------------------------------
# Tests — disabled is per-call, not global state
# ---------------------------------------------------------------------------


def test_no_cache_flag_does_not_persist_other_entries(tmp_path: Path) -> None:
    """``disabled=True`` for one check must NOT affect cache reads for OTHER
    checks (no global mutable state in the gate_cache module)."""
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    entry_a = _make_entry(check="ruff-check", result="pass")
    entry_b = _make_entry(check="ty", result="pass")

    persist(cache_dir, _SAMPLE_KEY, entry_a)
    persist(cache_dir, _OTHER_KEY, entry_b)

    # Act — call lookup with disabled=True for KEY-A only.
    result_a = lookup(cache_dir, _SAMPLE_KEY, disabled=True)
    # Then call lookup WITHOUT disabled for KEY-B — must still hit.
    result_b = lookup(cache_dir, _OTHER_KEY)

    # Assert — disabled is per-call; KEY-B is unaffected.
    assert result_a is None, "disabled=True must skip lookup for the requested key"
    assert result_b is not None, (
        "disabled=True for one key must NOT leak to other keys' lookups; "
        "the gate_cache module must not hold global disabled state"
    )
    result_b_json = json.loads(json.dumps(result_b, default=str))
    assert result_b_json.get("check") == "ty"


# ---------------------------------------------------------------------------
# Tests — debug logging via AIENG_CACHE_DEBUG=1
# ---------------------------------------------------------------------------


def test_aieng_cache_debug_env_logs_hit_miss(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When ``AIENG_CACHE_DEBUG=1`` is set, the module logger emits hit/miss
    markers for each ``lookup`` call.

    This is the observability hook spec-104 G-3 (≥70% hit rate verification)
    relies on; without it, ``tests/integration/test_gate_cache_hit_rate.py``
    cannot count outcomes.
    """
    # Arrange
    from ai_engineering.policy.gate_cache import lookup, persist

    cache_dir = tmp_path / "gate-cache"
    entry = _make_entry(check="ruff-check", result="pass")
    persist(cache_dir, _SAMPLE_KEY, entry)

    monkeypatch.setenv("AIENG_CACHE_DEBUG", "1")

    # Act — one HIT (seeded key) and one MISS (unknown key).
    with caplog.at_level(logging.DEBUG, logger="ai_engineering.policy.gate_cache"):
        hit = lookup(cache_dir, _SAMPLE_KEY)
        miss = lookup(cache_dir, _OTHER_KEY)

    # Assert — outcomes are correct (sanity).
    assert hit is not None, "seeded key must produce a HIT for this assertion to be meaningful"
    assert miss is None, "unseeded key must produce a MISS"

    # Assert — log records were emitted under the gate_cache logger.
    cache_logs = [r for r in caplog.records if r.name == "ai_engineering.policy.gate_cache"]
    assert cache_logs, (
        "AIENG_CACHE_DEBUG=1 must produce log records on the "
        "ai_engineering.policy.gate_cache logger"
    )

    # Assert — both a HIT and a MISS marker appear in the captured stream.
    combined = " ".join(r.getMessage().lower() for r in cache_logs)
    assert "hit" in combined, (
        "AIENG_CACHE_DEBUG=1 must emit a 'hit' marker on cache hit; "
        f"records: {[r.getMessage() for r in cache_logs]!r}"
    )
    assert "miss" in combined, (
        "AIENG_CACHE_DEBUG=1 must emit a 'miss' marker on cache miss; "
        f"records: {[r.getMessage() for r in cache_logs]!r}"
    )
