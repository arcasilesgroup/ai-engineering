"""RED tests for spec-104 T-2.3 — orchestrator Wave 2 (parallel checkers).

These tests assert the contract for the Wave 2 phase of the spec-104
orchestrator (D-104-01 second wave: parallel checkers, no fail-fast,
deterministic per-check ordering of aggregated output, cache hit/miss
tracking, wall-clock telemetry).

Target API (does not exist yet -- created in T-2.4):

    - ``ai_engineering.policy.orchestrator.run_wave2(
        staged_files: list[Path], mode: str = "local"
      ) -> Wave2Result``
        Spawns the Wave 2 checkers in parallel via
        ``concurrent.futures.ThreadPoolExecutor(max_workers=...)``, aggregates
        findings (no fail-fast: collects all), tracks cache hits/misses,
        returns a ``Wave2Result`` with deterministic per-check ordering.

    - ``ai_engineering.policy.orchestrator.Wave2Result``
        Container with fields:
          * ``findings: list[GateFinding]``
          * ``cache_hits: list[str]``
          * ``cache_misses: list[str]``
          * ``wall_clock_ms: int``  (max-not-sum because parallel)

Wave 2 checker set per D-104-01 / D-104-02:
    - Local mode (5 checkers): ``gitleaks``, ``ruff``, ``ty``,
      ``pytest-smoke``, ``validate``.
    - CI mode (8 checkers): adds ``semgrep``, ``pip-audit``,
      ``pytest-full`` to local set.

D-104-01 invariants that drive these tests:
    1. Parallel spawn -- all checkers START within a tight window
       (we assert <=100ms span across thread starts).
    2. No fail-fast -- exception in one checker does NOT kill the others.
    3. Deterministic output ordering -- findings list is sorted by
       check name regardless of completion order.
    4. Cache hit/miss bookkeeping -- per-check membership in
       ``cache_hits`` vs ``cache_misses`` lists.
    5. ThreadPoolExecutor sizing -- ``max_workers`` matches the
       checker count for the active mode.
    6. Wall-clock parallel semantics -- total ~ ``max(individual)``,
       NOT ``sum(individual)``. We allow up to 1.5x the slowest as
       overhead for thread spawn + GIL release.
    7. R-13 (``pytest -m smoke`` collects 0 tests) -- treated as a
       PASS with an info-level note, no findings emitted.
    8. Happy-path empty findings when every checker passes.

TDD CONSTRAINT: this file is IMMUTABLE after T-2.3 lands. T-2.4 GREEN
phase may only add behaviour to satisfy these assertions; it must NEVER
edit them.

Each test currently fails with ``ImportError`` because
``ai_engineering.policy.orchestrator`` does not exist yet.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any
from unittest import mock

from ai_engineering.state.models import GateFinding

# ---------------------------------------------------------------------------
# Constants documenting the D-104-01 / D-104-02 contract.
# ---------------------------------------------------------------------------

# Local-mode Wave 2 checkers (D-104-02 fast-slice).
_LOCAL_CHECKERS: tuple[str, ...] = (
    "gitleaks",
    "ruff",
    "ty",
    "pytest-smoke",
    "validate",
)

# CI-mode adds semgrep + pip-audit + pytest-full (D-104-02 authoritative).
_CI_EXTRA_CHECKERS: tuple[str, ...] = ("semgrep", "pip-audit", "pytest-full")
_CI_CHECKERS: tuple[str, ...] = _LOCAL_CHECKERS + _CI_EXTRA_CHECKERS

# Threshold for "spawned at the same time" — generous enough to survive a
# loaded CI runner but tight enough to catch a serial implementation that
# would gap by check duration (>=100ms typical).
_PARALLEL_SPAWN_WINDOW_S: float = 0.100  # 100 ms

# Wall-clock parallelism overhead allowance: total <= 1.5x slowest checker.
_PARALLEL_OVERHEAD_FACTOR: float = 1.5


# ---------------------------------------------------------------------------
# Helpers — fake checker registry / runner abstraction.
# ---------------------------------------------------------------------------


def _make_passing_finding(check: str) -> GateFinding:
    """Return a benign info-level finding tagged with the check name.

    Used in tests that assert per-check ordering of aggregated findings.
    """
    return GateFinding.model_validate(
        {
            "check": check,
            "rule_id": f"{check}-OK",
            "file": "src/example.py",
            "line": 1,
            "column": None,
            "severity": "info",
            "message": f"{check} clean",
            "auto_fixable": False,
            "auto_fix_command": None,
        }
    )


class _CheckerSpyState:
    """Thread-safe accumulator that records checker invocation timing.

    Used to assert parallel-spawn semantics: every checker records its
    monotonic start time the moment its thread enters the body. The test
    later asserts that ``max(start) - min(start) <= 100ms``.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.starts: dict[str, float] = {}
        self.finishes: dict[str, float] = {}
        self.invoked: list[str] = []

    def record_start(self, check: str) -> None:
        with self._lock:
            self.starts[check] = time.monotonic()
            self.invoked.append(check)

    def record_finish(self, check: str) -> None:
        with self._lock:
            self.finishes[check] = time.monotonic()


# ---------------------------------------------------------------------------
# 1. Parallel spawn — all 5 checkers start within 100 ms.
# ---------------------------------------------------------------------------


def test_wave2_spawns_checkers_in_parallel(tmp_path: Path) -> None:
    """All 5 Wave 2 checkers must start within ~100 ms of each other.

    A serial implementation would gap each start by the previous checker's
    duration. With a 50 ms sleep injected per checker, a serial run would
    span ~250 ms across 5 checkers; a parallel run spans <=100 ms.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    spy = _CheckerSpyState()
    sleep_per_checker = 0.050  # 50 ms each — magnifies serial vs parallel signal.

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        spy.record_start(check_name)
        time.sleep(sleep_per_checker)
        spy.record_finish(check_name)
        return {"check": check_name, "findings": [], "cache_hit": False}

    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        result = run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    assert sorted(spy.invoked) == sorted(_LOCAL_CHECKERS), (
        f"Wave 2 must invoke exactly the 5 local-mode checkers; got {sorted(spy.invoked)}"
    )
    span = max(spy.starts.values()) - min(spy.starts.values())
    assert span <= _PARALLEL_SPAWN_WINDOW_S, (
        f"All Wave 2 checkers must spawn within {_PARALLEL_SPAWN_WINDOW_S * 1000:.0f}ms "
        f"(parallel); spawn span was {span * 1000:.1f}ms — likely serial dispatch."
    )
    # Smoke-check the result shape so the test fails late if API drifts.
    assert hasattr(result, "findings")
    assert hasattr(result, "cache_hits")
    assert hasattr(result, "cache_misses")
    assert hasattr(result, "wall_clock_ms")


# ---------------------------------------------------------------------------
# 2. Local mode runs exactly the 5 D-104-02 fast-slice checkers.
# ---------------------------------------------------------------------------


def test_wave2_runs_all_5_checkers_in_local_mode(tmp_path: Path) -> None:
    """Local mode invokes gitleaks, ruff, ty, pytest-smoke, validate."""
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    invoked: list[str] = []
    invoked_lock = threading.Lock()

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        with invoked_lock:
            invoked.append(check_name)
        return {"check": check_name, "findings": [], "cache_hit": False}

    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    assert set(invoked) == set(_LOCAL_CHECKERS), (
        f"Local mode Wave 2 MUST invoke exactly: {sorted(_LOCAL_CHECKERS)}; got {sorted(invoked)}"
    )
    assert len(invoked) == 5, f"Expected 5 checker invocations, got {len(invoked)}"


# ---------------------------------------------------------------------------
# 3. CI mode adds semgrep + pip-audit + pytest-full.
# ---------------------------------------------------------------------------


def test_wave2_runs_all_8_checkers_in_ci_mode(tmp_path: Path) -> None:
    """CI mode adds semgrep, pip-audit, pytest-full to the local set."""
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    invoked: list[str] = []
    invoked_lock = threading.Lock()

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        with invoked_lock:
            invoked.append(check_name)
        return {"check": check_name, "findings": [], "cache_hit": False}

    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        run_wave2(staged_files=[tmp_path / "f.py"], mode="ci")

    assert set(invoked) == set(_CI_CHECKERS), (
        f"CI mode Wave 2 MUST invoke exactly: {sorted(_CI_CHECKERS)}; got {sorted(invoked)}"
    )
    assert len(invoked) == 8, f"Expected 8 checker invocations in ci mode, got {len(invoked)}"
    # All extras must appear.
    for extra in _CI_EXTRA_CHECKERS:
        assert extra in invoked, f"CI mode missing required extra checker {extra!r}"


# ---------------------------------------------------------------------------
# 4. No fail-fast — findings from every checker are aggregated.
# ---------------------------------------------------------------------------


def test_wave2_aggregates_findings_from_all_checkers(tmp_path: Path) -> None:
    """Failures from any checker are aggregated; no fail-fast (D-104-01).

    Every checker reports a single distinct finding; the result must
    contain all of them — proving the orchestrator does not stop on the
    first non-empty findings list.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "check": check_name,
            "findings": [_make_passing_finding(check_name)],
            "cache_hit": False,
        }

    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        result = run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    found_checks = {f.check for f in result.findings}
    assert found_checks == set(_LOCAL_CHECKERS), (
        "Wave 2 MUST aggregate findings from EVERY checker (no fail-fast); "
        f"expected checks {sorted(_LOCAL_CHECKERS)}, got {sorted(found_checks)}"
    )
    assert len(result.findings) == 5


# ---------------------------------------------------------------------------
# 5. Exception in one checker does not kill the others (collect-all).
# ---------------------------------------------------------------------------


def test_wave2_collects_findings_when_one_checker_raises(tmp_path: Path) -> None:
    """An exception in one checker MUST NOT abort the wave (D-104-01).

    The other 4 checkers complete and contribute their findings; the
    orchestrator should surface the exception as a finding (or at least
    NOT raise) but the test only asserts the 4 surviving checkers'
    findings are present.
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    crashing_check = "ty"  # pick one to blow up.

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        if check_name == crashing_check:
            raise RuntimeError(f"simulated {check_name} crash")
        return {
            "check": check_name,
            "findings": [_make_passing_finding(check_name)],
            "cache_hit": False,
        }

    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        # MUST NOT raise — exception is contained within the wave.
        result = run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    surviving = {f.check for f in result.findings}
    expected_survivors = set(_LOCAL_CHECKERS) - {crashing_check}
    assert expected_survivors.issubset(surviving), (
        "Surviving checkers MUST contribute findings even when a sibling "
        f"raises; expected {sorted(expected_survivors)} subset of "
        f"{sorted(surviving)}"
    )


# ---------------------------------------------------------------------------
# 6. Output ordering is deterministic (sorted by check name).
# ---------------------------------------------------------------------------


def test_wave2_per_check_ordering_deterministic(tmp_path: Path) -> None:
    """Output findings list is ordered by check name regardless of
    completion order. Different runs MUST produce identical sequences."""
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    # Reverse-alphabetic completion via sleeps to scramble ThreadPool order.
    delays = {
        "validate": 0.040,
        "ty": 0.030,
        "pytest-smoke": 0.020,
        "ruff": 0.010,
        "gitleaks": 0.005,
    }

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        time.sleep(delays.get(check_name, 0.001))
        return {
            "check": check_name,
            "findings": [_make_passing_finding(check_name)],
            "cache_hit": False,
        }

    sequences: list[list[str]] = []
    for _ in range(2):
        with mock.patch.object(
            orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
        ):
            result = run_wave2(staged_files=[tmp_path / "f.py"], mode="local")
        sequences.append([f.check for f in result.findings])

    # Both runs MUST be byte-identical in their per-check ordering.
    assert sequences[0] == sequences[1], (
        f"Output ordering MUST be deterministic across runs; got {sequences}"
    )
    # And alphabetically sorted by check name (the canonical ordering).
    assert sequences[0] == sorted(sequences[0]), (
        f"Output findings MUST be ordered alphabetically by check name; got {sequences[0]}"
    )


# ---------------------------------------------------------------------------
# 7. cache_hits list contains the names of checks that hit cache.
# ---------------------------------------------------------------------------


def test_wave2_cache_hits_logged_correctly(tmp_path: Path) -> None:
    """``cache_hits`` lists every checker that returned ``cache_hit=True``."""
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    hit_set = {"gitleaks", "ruff"}
    miss_set = set(_LOCAL_CHECKERS) - hit_set

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "check": check_name,
            "findings": [],
            "cache_hit": check_name in hit_set,
        }

    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        result = run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    assert set(result.cache_hits) == hit_set, (
        f"cache_hits MUST equal {sorted(hit_set)}; got {sorted(result.cache_hits)}"
    )
    # Misses must NOT bleed into hits.
    assert not (set(result.cache_hits) & miss_set), (
        f"cache_hits MUST NOT include any miss; cross-contamination "
        f"detected: {set(result.cache_hits) & miss_set}"
    )


# ---------------------------------------------------------------------------
# 8. cache_misses list contains the names that ran fresh.
# ---------------------------------------------------------------------------


def test_wave2_cache_misses_logged_correctly(tmp_path: Path) -> None:
    """``cache_misses`` lists every checker that returned ``cache_hit=False``."""
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    hit_set = {"gitleaks"}
    expected_misses = set(_LOCAL_CHECKERS) - hit_set

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "check": check_name,
            "findings": [],
            "cache_hit": check_name in hit_set,
        }

    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        result = run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    assert set(result.cache_misses) == expected_misses, (
        f"cache_misses MUST equal {sorted(expected_misses)}; got {sorted(result.cache_misses)}"
    )
    # And a complete partition: hits + misses == all checks.
    assert set(result.cache_hits) | set(result.cache_misses) == set(_LOCAL_CHECKERS), (
        "Union of cache_hits and cache_misses MUST equal the full local "
        "checker set (every checker reports exactly one of hit/miss)."
    )


# ---------------------------------------------------------------------------
# 9. ThreadPoolExecutor max_workers matches local mode checker count (5).
# ---------------------------------------------------------------------------


def test_wave2_uses_thread_pool_executor_max_workers_5(tmp_path: Path) -> None:
    """``run_wave2(mode="local")`` MUST size the pool to 5 workers (one
    per local checker), enabling true parallelism with no queueing."""
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    captured_max_workers: list[int] = []
    real_executor_init = (
        orchestrator.ThreadPoolExecutor.__init__  # type: ignore[attr-defined]
        if hasattr(orchestrator, "ThreadPoolExecutor")
        else None
    )
    _ = real_executor_init  # silence unused — guard for attr presence.

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"check": check_name, "findings": [], "cache_hit": False}

    # Patch ThreadPoolExecutor at the orchestrator-module level so we
    # observe how the orchestrator constructs its pool. ``create=True``
    # because the module does not exist yet (RED phase).
    original_init = None
    try:
        from concurrent.futures import ThreadPoolExecutor as _RealTPE

        original_init = _RealTPE.__init__
    except Exception:  # pragma: no cover - defensive only
        pass

    def spy_init(self: Any, *args: Any, max_workers: int | None = None, **kwargs: Any) -> None:
        if max_workers is not None:
            captured_max_workers.append(max_workers)
        if original_init is not None:
            original_init(self, *args, max_workers=max_workers, **kwargs)

    with (
        mock.patch(
            "ai_engineering.policy.orchestrator.ThreadPoolExecutor.__init__",
            new=spy_init,
            create=True,
        ),
        mock.patch.object(
            orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
        ),
    ):
        run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    assert captured_max_workers, (
        "Wave 2 MUST construct a ThreadPoolExecutor (none observed); "
        "implementation must use concurrent.futures.ThreadPoolExecutor."
    )
    assert 5 in captured_max_workers, (
        "Wave 2 local-mode pool MUST be sized to 5 (one worker per local "
        f"checker); observed max_workers values: {captured_max_workers}"
    )


# ---------------------------------------------------------------------------
# 10. Wall-clock is parallel (max-not-sum) within 1.5x of slowest checker.
# ---------------------------------------------------------------------------


def test_wave2_wall_clock_ms_is_max_not_sum(tmp_path: Path) -> None:
    """Total wall-clock MUST be ~ max(individual), not sum(individual).

    With staggered durations, a serial implementation would sum to the
    total; a parallel implementation finishes when the slowest is done
    (plus modest pool-spawn overhead).
    """
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    durations = {
        "gitleaks": 0.020,
        "ruff": 0.030,
        "ty": 0.040,
        "pytest-smoke": 0.050,
        "validate": 0.060,  # slowest = 60ms
    }
    slowest_s = max(durations.values())
    sum_s = sum(durations.values())  # for documentation in the assertion message

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        time.sleep(durations.get(check_name, 0.0))
        return {"check": check_name, "findings": [], "cache_hit": False}

    t0 = time.monotonic()
    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        result = run_wave2(staged_files=[tmp_path / "f.py"], mode="local")
    elapsed_s = time.monotonic() - t0

    upper_bound_s = slowest_s * _PARALLEL_OVERHEAD_FACTOR
    assert elapsed_s <= upper_bound_s, (
        f"Wave 2 wall-clock MUST be max-not-sum: parallel run should "
        f"finish in <= {upper_bound_s * 1000:.1f}ms ("
        f"{_PARALLEL_OVERHEAD_FACTOR}x slowest = {slowest_s * 1000:.1f}ms); "
        f"observed {elapsed_s * 1000:.1f}ms (serial sum would be "
        f"{sum_s * 1000:.1f}ms)"
    )
    # And the orchestrator's reported wall_clock_ms MUST be <= same bound.
    assert result.wall_clock_ms <= int(upper_bound_s * 1000) + 50, (
        "Reported wall_clock_ms MUST reflect parallel max-not-sum; got "
        f"{result.wall_clock_ms}ms vs expected <= "
        f"{int(upper_bound_s * 1000) + 50}ms"
    )


# ---------------------------------------------------------------------------
# 11. R-13 — pytest -m smoke with 0 collected tests is a skip-pass.
# ---------------------------------------------------------------------------


def test_wave2_skip_passes_when_no_smoke_marker_tests(tmp_path: Path) -> None:
    """Per R-13: if ``pytest --collect-only -m smoke`` returns 0 tests,
    the check is treated as a PASS with an info-level note (not a failure
    finding). The test asserts no finding of severity >= medium for
    ``pytest-smoke`` is emitted, and that ``pytest-smoke`` is NOT absent
    from the cache hit/miss bookkeeping (it ran, it just had nothing to
    do)."""
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        if check_name == "pytest-smoke":
            # Simulate the "0 tests collected" skip-pass contract: NO
            # findings emitted (or only an info-severity note), cache_hit
            # is False (we did execute pytest --collect-only), but the
            # check is treated as PASS.
            return {
                "check": "pytest-smoke",
                "findings": [],  # zero findings == skip-pass
                "cache_hit": False,
                "note": "no smoke-marked tests collected — skip-pass per R-13",
            }
        return {"check": check_name, "findings": [], "cache_hit": False}

    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        result = run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    # No medium+ severity findings for pytest-smoke (skip-pass contract).
    blocking_smoke = [
        f
        for f in result.findings
        if f.check == "pytest-smoke" and f.severity in {"critical", "high", "medium"}
    ]
    assert blocking_smoke == [], (
        "pytest-smoke with 0 collected tests MUST be skip-pass (R-13); "
        f"got blocking findings: {blocking_smoke}"
    )
    # pytest-smoke must still be accounted for in the cache bookkeeping
    # (it ran; it just had nothing to assert on).
    accounted = set(result.cache_hits) | set(result.cache_misses)
    assert "pytest-smoke" in accounted, (
        "pytest-smoke MUST appear in cache_hits OR cache_misses even on "
        f"skip-pass; got hits={result.cache_hits}, misses={result.cache_misses}"
    )


# ---------------------------------------------------------------------------
# 12. Happy path — all checkers pass, findings list is empty.
# ---------------------------------------------------------------------------


def test_wave2_returns_empty_findings_when_all_pass(tmp_path: Path) -> None:
    """When every Wave 2 checker passes (zero findings), the aggregated
    result has an empty ``findings`` list and a fully-populated
    ``cache_misses`` set (every checker ran fresh)."""
    from ai_engineering.policy import orchestrator
    from ai_engineering.policy.orchestrator import run_wave2

    def fake_run_one_check(check_name: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {"check": check_name, "findings": [], "cache_hit": False}

    with mock.patch.object(
        orchestrator, "_run_one_checker", side_effect=fake_run_one_check, create=True
    ):
        result = run_wave2(staged_files=[tmp_path / "f.py"], mode="local")

    assert result.findings == [], (
        f"Happy-path Wave 2 MUST emit zero findings; got {result.findings}"
    )
    assert set(result.cache_misses) == set(_LOCAL_CHECKERS), (
        "When all 5 local checkers run fresh, cache_misses MUST list all "
        f"of them; got {sorted(result.cache_misses)}"
    )
    assert result.cache_hits == [], (
        f"Happy-path with no warm cache MUST have empty cache_hits; got {result.cache_hits}"
    )
    # Wall-clock must be a non-negative int.
    assert isinstance(result.wall_clock_ms, int)
    assert result.wall_clock_ms >= 0


# ---------------------------------------------------------------------------
# Module-level invariant: every checker test had to import ``run_wave2``.
# If the orchestrator module is added to ``policy/`` but ``run_wave2`` is
# absent, the per-test imports above raise ``ImportError`` and the suite
# fails RED -- which is exactly what we want until T-2.4 lands.
# ---------------------------------------------------------------------------
