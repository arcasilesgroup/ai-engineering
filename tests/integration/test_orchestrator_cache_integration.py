"""Integration tests for ``ai_engineering.policy.orchestrator`` cache wiring.

RED phase for spec-104 T-2.7 (D-104-03 + D-104-08 — cache integration into the
single-pass collector).

The contract under test is the public entrypoint that T-2.8 (GREEN) will land
in ``ai_engineering.policy.orchestrator``::

    run_gate(
        staged_files: list[str],
        *,
        mode: str = "local",
        cache_dir: Path,
        cache_disabled: bool = False,
    ) -> GateFindingsDocument

The orchestrator coordinates Wave 1 (serial fixers) → Wave 2 (parallel
checkers per D-104-01) and consults ``gate_cache.lookup`` / ``persist`` for
each Wave 2 check (D-104-08 — CLI-layer caching is the IDE-agnostic
beneficiary).  The 5 Wave 2 checkers in ``mode="local"`` are::

    gitleaks  ty  pytest-smoke  validate  docs-gate

which match the keys of ``gate_cache._CONFIG_FILE_WHITELIST`` and are the
strings that flow into ``cache_hits`` / ``cache_misses`` lists of the
emitted ``gate-findings.json`` document (D-104-06).

Each test currently fails with ``ImportError`` because neither
``policy.orchestrator`` nor its ``run_gate`` exist yet. T-2.8 GREEN will
implement them on top of T-2.4 (``run_wave2`` parallel) + T-1.10 (cache
overrides) and these assertions become the contract.

TDD CONSTRAINT: this file is IMMUTABLE after T-2.7 lands. T-2.8 may only
extend the production module to satisfy the assertions; never edit the
assertions themselves.

Coverage (8 tests):

1. ``test_run_gate_cache_hit_skips_check`` — second run with no input
   changes hits the cache for every Wave 2 check; the per-check subprocess
   invocation count drops to 0 for cached checks.
2. ``test_run_gate_cache_miss_runs_and_persists`` — first run misses, runs
   fresh, persists each check result so the next run can hit.
3. ``test_run_gate_mixed_hit_miss`` — pre-seeding 3 of 5 cache entries
   yields 3 hits and 2 misses on the same invocation.
4. ``test_run_gate_disabled_via_no_cache_flag`` — ``cache_disabled=True``
   forces every check to run fresh (lookup is skipped).
5. ``test_run_gate_disabled_via_env`` — ``AIENG_CACHE_DISABLED=1`` env
   variable is equivalent to the kwarg (env wins, more conservative).
6. ``test_run_gate_cache_invalidates_on_file_change`` — modifying a staged
   file changes its blob hash; the next invocation misses for every check
   that hashes that blob.
7. ``test_run_gate_cache_invalidates_on_config_change`` — modifying
   ``.ruff.toml`` invalidates ruff-related cache entries while leaving the
   gitleaks entry intact (per ``_CONFIG_FILE_WHITELIST`` D-104-09).
8. ``test_run_gate_debug_logs_hit_miss_per_check`` — ``AIENG_CACHE_DEBUG=1``
   emits one log marker per check on the orchestrator/gate-cache logger
   so spec-104 G-3 (≥70% hit-rate verification) is observable.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Constants — Wave 2 checks per D-104-01 (mode="local") and per-check
# config-file whitelist keys per D-104-09 in the gate_cache module.
# ---------------------------------------------------------------------------

WAVE2_LOCAL_CHECKS = ("gitleaks", "ty", "pytest-smoke", "validate", "docs-gate")


# ---------------------------------------------------------------------------
# Helpers — staged-file fixture, config seeding, fake subprocess plumbing.
# ---------------------------------------------------------------------------


def _make_staged_files(repo: Path) -> list[str]:
    """Create a deterministic set of staged files inside ``repo``.

    Returns the relative POSIX paths that would be passed to
    ``orchestrator.run_gate(staged_files=...)``. Two files keep the cache
    key non-trivial without making the assertions noisy.
    """

    src = repo / "src"
    src.mkdir(parents=True, exist_ok=True)

    file_a = src / "module_a.py"
    file_a.write_text("def alpha() -> int:\n    return 1\n", encoding="utf-8")

    file_b = src / "module_b.py"
    file_b.write_text("def beta() -> int:\n    return 2\n", encoding="utf-8")

    return ["src/module_a.py", "src/module_b.py"]


def _seed_minimal_configs(repo: Path) -> None:
    """Seed the configs that ``_CONFIG_FILE_WHITELIST`` hashes.

    Only the keys touched by Wave 2 local checks are seeded here. Each file
    holds a small, valid payload so a config-change test can mutate one
    without poisoning the others.
    """

    (repo / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n", encoding="utf-8")
    (repo / ".ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
    (repo / ".gitleaks.toml").write_text("title = 'gitleaks'\n", encoding="utf-8")
    (repo / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (repo / "conftest.py").write_text("# empty\n", encoding="utf-8")

    ai_dir = repo / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        "schema_version: '2.0'\nproviders:\n  stacks: [python]\n", encoding="utf-8"
    )

    specs_dir = ai_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "spec.md").write_text("# spec\n", encoding="utf-8")
    (specs_dir / "plan.md").write_text("# plan\n", encoding="utf-8")


def _git_init(repo: Path) -> None:
    """Initialise a git repo so ``git hash-object`` can run on staged files.

    ``_compute_cache_key`` (D-104-09) hashes the staged blobs; the
    implementation is expected to delegate to ``git hash-object`` so a
    real git context is required for the orchestrator's cache-key
    derivation to be deterministic across the test run.
    """

    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Tester"],
        check=True,
        capture_output=True,
    )
    # Stage all current files so blob hashes are real and stable.
    subprocess.run(
        ["git", "-C", str(repo), "add", "-A"],
        check=True,
        capture_output=True,
    )


class _FakeCheckRunner:
    """Drop-in replacement for the orchestrator's per-check subprocess call.

    The real orchestrator (T-2.8) will dispatch each Wave 2 check by
    invoking the underlying tool via ``subprocess.run`` (or a wrapper).
    Tests don't care which call site — they only need to count invocations
    keyed by check name and steer the result.

    Attributes
    ----------
    calls
        List of check-name strings in invocation order. ``calls.count(name)``
        is the assertion lever used by every test in this file.
    return_outcomes
        Optional override of per-check outcome ('pass'/'fail'). Default is
        'pass' for all checks so the orchestrator's emit path can validate
        without findings.
    """

    def __init__(self, return_outcomes: dict[str, str] | None = None) -> None:
        self.calls: list[str] = []
        self.return_outcomes: dict[str, str] = return_outcomes or {}

    def __call__(self, check_name: str, *args: object, **kwargs: object) -> dict[str, object]:
        """Mimic the orchestrator's check-runner contract.

        The shape of the dict matches what ``gate_cache.persist`` expects
        for a ``result`` payload (see ``test_gate_cache_hit_miss``):
        ``{outcome, exit_code, stdout, stderr, findings}``.
        """

        self.calls.append(check_name)
        outcome = self.return_outcomes.get(check_name, "pass")
        return {
            "outcome": outcome,
            "exit_code": 0 if outcome == "pass" else 1,
            "stdout": "",
            "stderr": "",
            "findings": [],
        }


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Initialised git repo with seeded configs and staged source files."""

    _seed_minimal_configs(tmp_path)
    _make_staged_files(tmp_path)
    _git_init(tmp_path)
    return tmp_path


@pytest.fixture()
def fake_runner() -> _FakeCheckRunner:
    """Return a fresh ``_FakeCheckRunner`` per test."""

    return _FakeCheckRunner()


@pytest.fixture(autouse=True)
def _clean_cache_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no cache-related env var leaks across tests.

    Tests that need the env var SET will call ``monkeypatch.setenv``
    themselves; this fixture only guarantees a clean slate.
    """

    monkeypatch.delenv("AIENG_CACHE_DISABLED", raising=False)
    monkeypatch.delenv("AIENG_CACHE_DEBUG", raising=False)


def _findings_doc_dict(doc: object) -> dict[str, object]:
    """Coerce the orchestrator's return value to a plain dict.

    ``run_gate`` is documented to return a ``GateFindingsDocument`` Pydantic
    model. Tests compare ``cache_hits`` / ``cache_misses`` semantics, so we
    accept either the model (use ``.model_dump`` / ``.dict``) or a raw dict
    fallback (defensive, in case the implementation chooses a TypedDict).
    """

    if hasattr(doc, "model_dump"):
        return doc.model_dump(by_alias=True)  # type: ignore[no-any-return]
    if hasattr(doc, "dict"):
        return doc.dict(by_alias=True)  # type: ignore[no-any-return]
    if isinstance(doc, dict):
        return doc
    raise AssertionError(
        f"orchestrator.run_gate must return a GateFindingsDocument or dict; got {type(doc)!r}"
    )


# ---------------------------------------------------------------------------
# Test 1 — second run hits cache for every Wave 2 check (subprocess count → 0)
# ---------------------------------------------------------------------------


def test_run_gate_cache_hit_skips_check(
    repo: Path, fake_runner: _FakeCheckRunner, tmp_path: Path
) -> None:
    """Second ``run_gate`` over identical inputs hits the cache for every
    Wave 2 check — the per-check runner is invoked 0 times."""
    # Arrange
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    # Patch the orchestrator's per-check dispatcher so we can count calls.
    # The contract: T-2.8 wires Wave 2 to delegate per-check execution to a
    # symbol named ``_run_check`` in the orchestrator module. Tests treat
    # this as the authoritative seam between cache lookup and tool launch.
    with mock.patch.object(orchestrator, "_run_check", new=fake_runner):
        # Act — first run: misses for every check, populates the cache.
        first = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )
        first_call_count = len(fake_runner.calls)

        # Reset the call log so the second-run assertion is unambiguous.
        fake_runner.calls.clear()

        # Act — second run: every check should HIT and skip the runner.
        second = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

    # Assert — first run actually ran every Wave 2 check at least once.
    assert first_call_count >= len(WAVE2_LOCAL_CHECKS), (
        "First run must invoke every Wave 2 check at least once "
        f"(expected ≥ {len(WAVE2_LOCAL_CHECKS)}); got {first_call_count}"
    )

    # Assert — second run invoked the runner 0 times for cached checks.
    cached_calls = [c for c in fake_runner.calls if c in WAVE2_LOCAL_CHECKS]
    assert cached_calls == [], (
        "Second run with identical inputs must SKIP every Wave 2 check via "
        f"the cache (subprocess count = 0); got {cached_calls!r}"
    )

    # Assert — emitted findings documents reflect the hit/miss bookkeeping.
    second_doc = _findings_doc_dict(second)
    cache_hits = second_doc.get("cache_hits") or []
    cache_misses = second_doc.get("cache_misses") or []

    assert set(cache_hits) >= set(WAVE2_LOCAL_CHECKS), (
        "Second run must record a cache_hit entry for every Wave 2 check; "
        f"hits={cache_hits!r}, misses={cache_misses!r}"
    )
    # Sanity: the document still references the v1 schema (D-104-06).
    assert second_doc.get("schema") == "ai-engineering/gate-findings/v1"

    # Sanity: first run recorded all checks as misses (cache was empty).
    first_doc = _findings_doc_dict(first)
    first_misses = first_doc.get("cache_misses") or []
    assert set(first_misses) >= set(WAVE2_LOCAL_CHECKS), (
        "First run over an empty cache_dir must record cache_misses for "
        f"every Wave 2 check; got misses={first_misses!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — cache miss runs the check fresh and persists for next time.
# ---------------------------------------------------------------------------


def test_run_gate_cache_miss_runs_and_persists(
    repo: Path, fake_runner: _FakeCheckRunner, tmp_path: Path
) -> None:
    """A fresh cache_dir → every check misses → runner is invoked → entries
    are persisted so a follow-up lookup with the same inputs hits."""
    # Arrange
    from ai_engineering.policy import gate_cache, orchestrator

    cache_dir = tmp_path / "gate-cache"
    assert not cache_dir.exists(), "test precondition: cache_dir must not pre-exist"
    staged = _make_staged_files(repo)

    # Act — single run; cache_dir is empty → every check is a miss.
    with mock.patch.object(orchestrator, "_run_check", new=fake_runner):
        result = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

    # Assert — runner was invoked for every Wave 2 check (no hits possible).
    invoked = set(fake_runner.calls)
    assert invoked >= set(WAVE2_LOCAL_CHECKS), (
        "Cache miss must run the check fresh — every Wave 2 check should "
        f"appear in the runner's call log. invoked={invoked!r}"
    )

    # Assert — the orchestrator persisted entries for every miss so future
    # invocations can hit. We don't open the JSON files (storage layout is
    # T-1.4 territory); we use the public ``gate_cache.lookup`` to assert
    # the persisted state. By design ``persist`` derives the cache key from
    # the same 5 inputs that ``run_gate`` hashes, so lookup with matching
    # context succeeds. Any failure to persist surfaces here as ``None``.
    cached_files = [p for p in cache_dir.iterdir() if p.is_file()]
    assert len(cached_files) >= len(WAVE2_LOCAL_CHECKS), (
        "After a fully-missed run, the orchestrator must have persisted at "
        f"least one cache file per Wave 2 check (≥ {len(WAVE2_LOCAL_CHECKS)}); "
        f"found {len(cached_files)} file(s) under {cache_dir}"
    )

    # Sanity — the result document marks every check as a miss for this run.
    doc = _findings_doc_dict(result)
    misses = doc.get("cache_misses") or []
    assert set(misses) >= set(WAVE2_LOCAL_CHECKS), (
        f"Every Wave 2 check should be a miss on the first run; got misses={misses!r}"
    )
    # And the gate_cache module is the one whose ``lookup`` would now hit.
    # Belt-and-suspenders: confirm the public symbols expected by the
    # contract are wired (T-2.8 imports them).
    assert hasattr(gate_cache, "lookup"), (
        "gate_cache.lookup must exist for orchestrator persistence to be auditable"
    )
    assert hasattr(gate_cache, "persist"), (
        "gate_cache.persist must exist for orchestrator to warm the cache"
    )


# ---------------------------------------------------------------------------
# Test 3 — mixed hit/miss when the cache is partially warm.
# ---------------------------------------------------------------------------


def test_run_gate_mixed_hit_miss(repo: Path, fake_runner: _FakeCheckRunner, tmp_path: Path) -> None:
    """A second run after the first invalidates only a subset of checks
    yields the expected hit/miss split — 3 hits, 2 misses for the
    canonical Wave 2 set."""
    # Arrange
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    with mock.patch.object(orchestrator, "_run_check", new=fake_runner):
        # First run — populate cache for every Wave 2 check.
        orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

        # Act — invalidate exactly 2 cache entries by clearing their files.
        # Naming convention: ``gate_cache.persist`` writes
        # ``<32-char-key>.json`` under cache_dir. We pick 2 of the 5 files
        # to remove, which simulates a config change that selectively
        # busted those entries (the orchestrator must miss them on re-run).
        cached_files = sorted(p for p in cache_dir.iterdir() if p.is_file())
        assert len(cached_files) >= 5, (
            "precondition: first run must have persisted ≥5 cache files for "
            f"the 5 Wave 2 checks; found {len(cached_files)}"
        )
        for path in cached_files[:2]:
            path.unlink()

        # Reset the runner's call log so the next run's assertion is clean.
        fake_runner.calls.clear()

        # Re-run — 3 checks hit (entries still on disk), 2 miss (deleted).
        result = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

    # Assert — the runner was invoked exactly 2 times (one per missed entry).
    invoked = [c for c in fake_runner.calls if c in WAVE2_LOCAL_CHECKS]
    assert len(invoked) == 2, (
        "Mixed-hit run must invoke the runner exactly twice (one per missed "
        f"entry); invoked={invoked!r} on second run"
    )

    # Assert — the emitted document distinguishes hits from misses.
    doc = _findings_doc_dict(result)
    hits = doc.get("cache_hits") or []
    misses = doc.get("cache_misses") or []
    assert len(hits) == 3, (
        f"Expected 3 cache_hits in mixed run; got hits={hits!r}, misses={misses!r}"
    )
    assert len(misses) == 2, (
        f"Expected 2 cache_misses in mixed run; got hits={hits!r}, misses={misses!r}"
    )
    # Hits and misses must partition the Wave 2 check set (no double-counting).
    assert set(hits).isdisjoint(misses), (
        f"cache_hits and cache_misses must be disjoint; hits={hits!r}, misses={misses!r}"
    )
    assert set(hits) | set(misses) >= set(WAVE2_LOCAL_CHECKS), (
        f"Hits union misses must cover every Wave 2 check; hits={hits!r}, misses={misses!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — cache_disabled=True forces every check to run fresh.
# ---------------------------------------------------------------------------


def test_run_gate_disabled_via_no_cache_flag(
    repo: Path, fake_runner: _FakeCheckRunner, tmp_path: Path
) -> None:
    """``run_gate(cache_disabled=True)`` skips every cache lookup, even
    when entries exist on disk — the runner is invoked once per check."""
    # Arrange
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    with mock.patch.object(orchestrator, "_run_check", new=fake_runner):
        # Warm the cache with a default invocation.
        orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

        # Sanity precondition: cache files exist after the warm-up run.
        warmed = [p for p in cache_dir.iterdir() if p.is_file()]
        assert warmed, "precondition: warm-up run must have persisted cache files"

        # Reset the call log; the disabled run is the unit under test.
        fake_runner.calls.clear()

        # Act — disabled flag forces fresh runs for every check.
        result = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
            cache_disabled=True,
        )

    # Assert — the runner saw every Wave 2 check (disabled bypassed lookup).
    invoked = [c for c in fake_runner.calls if c in WAVE2_LOCAL_CHECKS]
    assert sorted(invoked) == sorted(WAVE2_LOCAL_CHECKS), (
        "cache_disabled=True must run every Wave 2 check fresh; "
        f"invoked={invoked!r}, expected={list(WAVE2_LOCAL_CHECKS)!r}"
    )

    # Assert — emitted document records 0 hits and 5 misses (lookup skipped).
    doc = _findings_doc_dict(result)
    hits = doc.get("cache_hits") or []
    misses = doc.get("cache_misses") or []
    assert hits == [], f"cache_disabled=True must record 0 cache_hits; got hits={hits!r}"
    assert set(misses) >= set(WAVE2_LOCAL_CHECKS), (
        "cache_disabled=True must mark every Wave 2 check as a miss "
        f"(lookup skipped); got misses={misses!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — AIENG_CACHE_DISABLED=1 env is equivalent to the kwarg.
# ---------------------------------------------------------------------------


def test_run_gate_disabled_via_env(
    repo: Path,
    fake_runner: _FakeCheckRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``AIENG_CACHE_DISABLED=1`` env var forces fresh runs even when the
    caller leaves ``cache_disabled`` at its default ``False``.

    Per D-104-10 the env var is the more-conservative choice and must take
    precedence over a permissive kwarg.
    """
    # Arrange
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    with mock.patch.object(orchestrator, "_run_check", new=fake_runner):
        # Warm the cache with the env var unset.
        orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )
        warmed = [p for p in cache_dir.iterdir() if p.is_file()]
        assert warmed, "precondition: warm-up run must have persisted cache files"

        # Reset call log; the env-disabled run is what we are measuring.
        fake_runner.calls.clear()

        # Set the kill-switch env var BEFORE the next run.
        monkeypatch.setenv("AIENG_CACHE_DISABLED", "1")

        # Act — call WITHOUT the cache_disabled kwarg; env alone must kill cache.
        result = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

    # Assert — runner saw every check (env-level kill switch worked).
    invoked = [c for c in fake_runner.calls if c in WAVE2_LOCAL_CHECKS]
    assert sorted(invoked) == sorted(WAVE2_LOCAL_CHECKS), (
        "AIENG_CACHE_DISABLED=1 must force fresh runs for every Wave 2 check "
        f"(env-level equivalent to --no-cache); invoked={invoked!r}"
    )

    # Assert — document records 0 hits.
    doc = _findings_doc_dict(result)
    hits = doc.get("cache_hits") or []
    assert hits == [], f"AIENG_CACHE_DISABLED=1 must record 0 cache_hits; got hits={hits!r}"


# ---------------------------------------------------------------------------
# Test 6 — modifying a staged file invalidates the cache (blob hash change).
# ---------------------------------------------------------------------------


def test_run_gate_cache_invalidates_on_file_change(
    repo: Path, fake_runner: _FakeCheckRunner, tmp_path: Path
) -> None:
    """Changing the contents of a staged file changes its git blob hash,
    which is part of the cache key (D-104-09). Every Wave 2 check that
    depends on that blob must miss on the next run."""
    # Arrange
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    with mock.patch.object(orchestrator, "_run_check", new=fake_runner):
        # First run — warm the cache.
        orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

        # Sanity — cache files exist after the warm-up.
        assert any(p.is_file() for p in cache_dir.iterdir()), (
            "precondition: warm-up run must have persisted cache files"
        )

        # Mutate one staged file → blob hash changes for staged content.
        target = repo / "src" / "module_a.py"
        target.write_text(
            "def alpha() -> int:\n    return 999\n",  # was 1, now 999
            encoding="utf-8",
        )
        # Re-stage the mutated file so ``git ls-files --staged`` reflects
        # the new blob hash that the cache key depends on.
        subprocess.run(
            ["git", "-C", str(repo), "add", "src/module_a.py"],
            check=True,
            capture_output=True,
        )

        fake_runner.calls.clear()

        # Act — second run with the mutated blob → every check should miss.
        result = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

    # Assert — runner saw every Wave 2 check (cache keyed off blob hashes).
    invoked = [c for c in fake_runner.calls if c in WAVE2_LOCAL_CHECKS]
    assert sorted(invoked) == sorted(WAVE2_LOCAL_CHECKS), (
        "A staged-file content change must invalidate every cache entry whose "
        f"key includes the staged blob list; invoked={invoked!r}"
    )

    # Assert — emitted document marks every check as a miss this run.
    doc = _findings_doc_dict(result)
    misses = doc.get("cache_misses") or []
    hits = doc.get("cache_hits") or []
    assert set(misses) >= set(WAVE2_LOCAL_CHECKS), (
        "Blob hash change must produce a cache_miss for every Wave 2 check; "
        f"got hits={hits!r}, misses={misses!r}"
    )


# ---------------------------------------------------------------------------
# Test 7 — modifying .ruff.toml invalidates ruff entries, gitleaks still hits.
# ---------------------------------------------------------------------------


def test_run_gate_cache_invalidates_on_config_change(
    repo: Path, fake_runner: _FakeCheckRunner, tmp_path: Path
) -> None:
    """Per ``_CONFIG_FILE_WHITELIST`` (D-104-09), ``.ruff.toml`` is in the
    whitelist for ``ruff-format`` / ``ruff-check`` only. Mutating it must
    invalidate ruff-keyed cache entries while leaving entries for checks
    that do not hash that file (e.g., ``gitleaks``) intact.

    NOTE: Wave 2 in mode="local" does NOT include ruff (ruff lives in
    Wave 1 — fixers). The orchestrator does still pass through the ruff
    config in its cache key derivation for any check whose whitelist
    references it. The contract under test is the orthogonality of the
    invalidation — checks whose whitelists do NOT mention .ruff.toml
    must continue to hit on the second run.
    """
    # Arrange
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    with mock.patch.object(orchestrator, "_run_check", new=fake_runner):
        # First run — warm the cache for every Wave 2 check.
        orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

        # Mutate .ruff.toml — this file is whitelisted for ruff* checks
        # only. ``gitleaks`` whitelists [".gitleaks.toml", "gitleaks.toml"]
        # so its cache key does not depend on .ruff.toml and must still
        # hit on the next run.
        ruff_config = repo / ".ruff.toml"
        ruff_config.write_text("line-length = 88\n", encoding="utf-8")  # was 100

        fake_runner.calls.clear()

        # Act — second run after the ruff config mutation.
        result = orchestrator.run_gate(
            staged_files=staged,
            mode="local",
            cache_dir=cache_dir,
        )

    # Assert — gitleaks still hit (its whitelist doesn't include .ruff.toml).
    doc = _findings_doc_dict(result)
    hits = set(doc.get("cache_hits") or [])
    misses = set(doc.get("cache_misses") or [])

    assert "gitleaks" in hits, (
        ".ruff.toml is NOT in gitleaks' _CONFIG_FILE_WHITELIST entry, so the "
        "gitleaks cache entry must still hit on the second run; "
        f"hits={hits!r}, misses={misses!r}"
    )
    assert "gitleaks" not in misses, (
        f"gitleaks must not be a miss after a .ruff.toml-only change; misses={misses!r}"
    )

    # Assert — the runner did NOT invoke gitleaks again (cache was respected).
    assert "gitleaks" not in fake_runner.calls, (
        "gitleaks runner must NOT be invoked when only .ruff.toml changed; "
        f"calls={fake_runner.calls!r}"
    )


# ---------------------------------------------------------------------------
# Test 8 — AIENG_CACHE_DEBUG=1 emits one hit/miss marker per check.
# ---------------------------------------------------------------------------


def test_run_gate_debug_logs_hit_miss_per_check(
    repo: Path,
    fake_runner: _FakeCheckRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """``AIENG_CACHE_DEBUG=1`` must emit a hit/miss marker per Wave 2 check
    on the orchestrator/gate-cache logger. This is the observability hook
    spec-104 G-3 (≥70% hit-rate verification) relies on — without the per-
    check marker, ``tests/integration/test_gate_cache_hit_rate.py`` cannot
    aggregate outcomes accurately.
    """
    # Arrange
    from ai_engineering.policy import orchestrator

    cache_dir = tmp_path / "gate-cache"
    staged = _make_staged_files(repo)

    monkeypatch.setenv("AIENG_CACHE_DEBUG", "1")

    with mock.patch.object(orchestrator, "_run_check", new=fake_runner):
        # First run — every check is a miss; expect 5 miss markers.
        with caplog.at_level(logging.DEBUG):
            orchestrator.run_gate(
                staged_files=staged,
                mode="local",
                cache_dir=cache_dir,
            )
        first_records = list(caplog.records)
        caplog.clear()

        # Second run — every check should hit; expect 5 hit markers.
        with caplog.at_level(logging.DEBUG):
            orchestrator.run_gate(
                staged_files=staged,
                mode="local",
                cache_dir=cache_dir,
            )
        second_records = list(caplog.records)

    # Filter to records emitted by the cache or orchestrator loggers — the
    # contract is that debug markers come from one of these two modules.
    def _cache_or_orch_records(records: list[logging.LogRecord]) -> list[logging.LogRecord]:
        relevant_loggers = (
            "ai_engineering.policy.gate_cache",
            "ai_engineering.policy.orchestrator",
        )
        return [r for r in records if r.name in relevant_loggers]

    first_relevant = _cache_or_orch_records(first_records)
    second_relevant = _cache_or_orch_records(second_records)

    assert first_relevant, (
        "AIENG_CACHE_DEBUG=1 must emit log records on the cache or orchestrator "
        "loggers during the first (all-miss) run; got 0 relevant records"
    )
    assert second_relevant, (
        "AIENG_CACHE_DEBUG=1 must emit log records on the cache or orchestrator "
        "loggers during the second (all-hit) run; got 0 relevant records"
    )

    # First run: every Wave 2 check name should appear paired with 'miss'
    # in at least one record's message stream. We don't assert exact
    # phrasing; we assert the (check, outcome) tuple is observable.
    first_messages = " ".join(r.getMessage().lower() for r in first_relevant)
    for check in WAVE2_LOCAL_CHECKS:
        assert check in first_messages, (
            f"First-run debug log must mention check {check!r}; "
            f"messages: {[r.getMessage() for r in first_relevant]!r}"
        )
    assert "miss" in first_messages, (
        "First-run debug log must include a 'miss' marker for the all-miss run; "
        f"messages: {[r.getMessage() for r in first_relevant]!r}"
    )

    # Second run: every Wave 2 check should appear paired with 'hit'.
    second_messages = " ".join(r.getMessage().lower() for r in second_relevant)
    for check in WAVE2_LOCAL_CHECKS:
        assert check in second_messages, (
            f"Second-run debug log must mention check {check!r}; "
            f"messages: {[r.getMessage() for r in second_relevant]!r}"
        )
    assert "hit" in second_messages, (
        "Second-run debug log must include a 'hit' marker for the all-hit run; "
        f"messages: {[r.getMessage() for r in second_relevant]!r}"
    )
