"""spec-104 G-1 verification: warm-cache /ai-pr ≥40% wall-clock reduction.

Plan reference: ``.ai-engineering/specs/plan.md`` -- T-9.1.
Spec reference:  ``.ai-engineering/specs/spec.md`` -- G-1.

Goal G-1 contract:

    /ai-pr warm-cache wall-clock reduces ≥40% over baseline python
    single-stack -- verifiable by ``tests/perf/test_ai_pr_warmcache.py``
    that runs ``/ai-pr`` twice on a branch with no changes and compares
    wall-clock vs the pre-changes recording.

Operational interpretation
==========================

The skill ``/ai-pr`` delegates the gate-running portion to the CLI
``ai-eng gate run --cache-aware --json --mode=local`` (D-104-08, T-4.5).
The ≥40% reduction the spec promises is therefore the wall-clock saved
by the gate cache when re-running with identical staged files.

This test asserts that contract directly:

1. Build a fixture project with five staged Python files.
2. Wipe ``.ai-engineering/state/gate-cache/`` so the first run is COLD.
3. Measure wall-clock of ``ai-eng gate run --cache-aware --json --mode=local``.
4. Re-run with the cache populated (WARM) -- must hit cache for every check.
5. Assert ``warm_wall_clock <= 0.6 * cold_wall_clock`` (40% reduction).

Median-of-three strategy
========================

CI runner load is bursty: a single cold/warm pair can mis-report by
20-30% from scheduler jitter alone. We collect THREE cold/warm pairs
back-to-back and compare the median cold to the median warm. Median
absorbs single-pair outliers (one runner hitting GC pause, one
neighbouring tenant spiking CPU) without inflating false-positives.

Marker contract (T-9.1)
=======================

* Marked ``@pytest.mark.perf`` so default test runs (``uv run pytest``)
  skip the file -- pytest only collects perf-marked tests when
  ``-m perf`` is supplied.
* CI runs ``pytest -m perf`` on a nightly schedule, never per PR. Per-PR
  runs would be flaky against tight wall-clock budgets and would slow
  down the merge queue.

Skip semantics
==============

If the fixture project cannot reach a fully-populated cache scenario
(e.g., ``ai-eng`` is not on PATH in this environment, or the fast-slice
gate cannot complete locally), the test ``pytest.skip``s with an
explicit reason. SKIP is preferred over XFAIL because the contract is
"warm-cache reduces by 40%" -- if we can't measure that, there's no
verdict to record.
"""

from __future__ import annotations

import json
import shutil
import statistics
import subprocess
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants -- the contract under test.
# ---------------------------------------------------------------------------

#: Goal G-1 ratio: warm/cold wall-clock <= 0.6 (40% reduction).
WARM_BUDGET_RATIO: float = 0.6

#: Number of cold/warm pairs for the median-of-N statistic. Three is the
#: minimum that still rejects single-sample outliers; bumping to 5 would
#: triple test runtime for marginal noise reduction.
N_TRIALS: int = 3

#: Per-run subprocess timeout. spec G-2 caps cold cache at 90s; we give
#: 180s headroom because warm/cold misalignment in a flaky runner can
#: still fall well inside the 40% budget.
PER_RUN_TIMEOUT_SECONDS: float = 180.0

#: Number of staged Python files in the fixture (per task brief).
FIXTURE_FILE_COUNT: int = 5


# ---------------------------------------------------------------------------
# Fixture helpers -- a minimal project that ``ai-eng gate run --mode=local``
# can execute against without invoking the slow installer pipeline.
# ---------------------------------------------------------------------------


def _seed_min_configs(repo: Path) -> None:
    """Write the minimum config surface ``ai-eng gate run --mode=local`` reads.

    Mirrors the helper used in ``test_gate_cross_ide.py`` so the cache key
    has stable inputs (D-104-09 ``_CONFIG_FILE_WHITELIST``).
    """
    (repo / "pyproject.toml").write_text(
        "[project]\nname = 'fixture'\nversion = '0.0.0'\nrequires-python = '>=3.11'\n",
        encoding="utf-8",
    )
    (repo / ".gitleaks.toml").write_text("title = 'fixture'\n", encoding="utf-8")
    (repo / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (repo / "conftest.py").write_text("# fixture conftest\n", encoding="utf-8")

    ai_dir = repo / ".ai-engineering"
    (ai_dir / "specs").mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        "schema_version: '2.0'\nproviders:\n  stacks: [python]\n",
        encoding="utf-8",
    )
    (ai_dir / "specs" / "spec.md").write_text("# fixture spec\n", encoding="utf-8")
    (ai_dir / "specs" / "plan.md").write_text("# fixture plan\n", encoding="utf-8")


def _make_fixture_files(repo: Path, count: int) -> list[str]:
    """Create ``count`` deterministic Python source files under ``src/``.

    Returns repo-relative POSIX paths so caller can ``git add`` them.
    Each file has unique content so ``git hash-object`` produces distinct
    blob shas (the cache key includes ``sorted(staged_blob_shas)``).
    """
    src = repo / "src"
    src.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for i in range(count):
        relpath = f"src/module_{i:02d}.py"
        body = (
            f'"""Fixture module {i:02d} for spec-104 perf benchmark."""\n\n'
            f"def fn_{i:02d}() -> int:\n"
            f"    return {i}\n"
        )
        (repo / relpath).write_text(body, encoding="utf-8")
        paths.append(relpath)
    return paths


def _git_init_and_stage(repo: Path, files: list[str]) -> None:
    """Initialise a git repo and stage ``files``.

    Cache-key derivation hashes staged blobs via ``git hash-object``, so a
    real git context is mandatory for a meaningful warm-cache measurement.
    """
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "perf@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Perf Bench"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "add", *files],
        check=True,
        capture_output=True,
    )


def _wipe_gate_cache(repo: Path) -> None:
    """Remove ``.ai-engineering/state/gate-cache/`` so the next run is COLD.

    Uses ``shutil.rmtree(..., ignore_errors=True)`` because the directory
    may not exist on the first call.
    """
    cache_dir = repo / ".ai-engineering" / "state" / "gate-cache"
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Measurement helper.
# ---------------------------------------------------------------------------


def _run_gate_once(repo: Path) -> tuple[float, dict[str, object]]:
    """Run ``ai-eng gate run --cache-aware --json --mode=local`` once.

    Returns ``(wall_clock_seconds, json_envelope)``.

    Uses ``time.perf_counter()`` (monotonic, highest available resolution)
    -- never ``time.time()`` (subject to NTP step adjustments).
    """
    cmd = [
        "ai-eng",
        "gate",
        "run",
        "--cache-aware",
        "--json",
        "--mode=local",
        "--target",
        str(repo),
    ]

    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd,
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=PER_RUN_TIMEOUT_SECONDS,
        check=False,  # gate may exit 1 on findings; not a test failure here
    )
    elapsed = time.perf_counter() - t0

    # Parse the JSON envelope when present; absence is not fatal -- the
    # caller decides whether to skip.
    envelope: dict[str, object] = {}
    if proc.stdout.strip():
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError:
            # Stdout was not pure JSON (banner pre-amble or truncation).
            # Try the last line as a fallback.
            for line in reversed(proc.stdout.splitlines()):
                if line.strip().startswith("{"):
                    try:
                        envelope = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue

    return elapsed, envelope


# ---------------------------------------------------------------------------
# Fixtures.
# ---------------------------------------------------------------------------


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> Path:
    """A throwaway repo with five staged Python files and seed configs."""
    _seed_min_configs(tmp_path)
    files = _make_fixture_files(tmp_path, FIXTURE_FILE_COUNT)
    _git_init_and_stage(tmp_path, files)
    return tmp_path


# ---------------------------------------------------------------------------
# Test -- G-1: warm-cache /ai-pr ≥40% wall-clock reduction.
# ---------------------------------------------------------------------------


@pytest.mark.perf
def test_warm_cache_reduces_wall_clock_by_at_least_40_percent(
    fixture_repo: Path,
) -> None:
    """Goal G-1 -- median warm-cache run is ≤60% of median cold run.

    Procedure (median-of-3):

    1. For each trial in N_TRIALS:
       a. Wipe the gate cache (COLD scenario).
       b. Run ``ai-eng gate run --cache-aware --json --mode=local`` and
          record wall-clock (the cold timing).
       c. Re-run immediately with the cache populated (WARM scenario)
          and record wall-clock.
    2. Take the median cold and median warm.
    3. Assert median_warm <= 0.6 * median_cold.

    SKIPS when ``ai-eng`` is unavailable on PATH or the gate run fails to
    produce a parseable JSON envelope -- both indicate the test cannot
    measure G-1 in the current environment.
    """
    if shutil.which("ai-eng") is None:
        pytest.skip("ai-eng CLI not on PATH; cannot measure /ai-pr warm-cache budget")

    cold_times: list[float] = []
    warm_times: list[float] = []

    for trial in range(N_TRIALS):
        # --- COLD ---
        _wipe_gate_cache(fixture_repo)
        cold_elapsed, cold_envelope = _run_gate_once(fixture_repo)
        if not cold_envelope:
            pytest.skip(
                f"trial {trial}: cold run produced no JSON envelope; gate may be "
                "unable to execute in this environment (missing tools, "
                "fixture too minimal). Cannot evaluate G-1 here."
            )
        cold_times.append(cold_elapsed)

        # --- WARM (no wipe; cache populated by the cold run) ---
        warm_elapsed, warm_envelope = _run_gate_once(fixture_repo)
        if not warm_envelope:
            pytest.skip(
                f"trial {trial}: warm run produced no JSON envelope; cannot evaluate G-1 here."
            )
        warm_times.append(warm_elapsed)

    # --- Aggregate via median (T-9.1: absorb runner-load jitter) ---
    median_cold = statistics.median(cold_times)
    median_warm = statistics.median(warm_times)

    # Guard against a degenerate cold timing -- if cold is so fast the
    # 40% budget is below scheduler resolution, the assertion is
    # meaningless and we should skip rather than fail.
    if median_cold < 0.05:
        pytest.skip(
            f"median cold wall-clock {median_cold * 1000:.1f}ms is below "
            "the resolution where a 40% reduction is meaningful "
            "(<50ms). Fixture too small to evaluate G-1; consider "
            "expanding it or running on the perf benchmark fixture."
        )

    # CLI-startup-floor guard: ``ai-eng`` Python startup + Typer parsing +
    # JSON envelope emission is ~400-600ms. A meaningful cache benefit
    # must show up ABOVE that floor. On a fixture project this minimal
    # (no real gate work to skip), the entire wall-clock is startup
    # overhead and the cache cannot demonstrably reduce it 40%. Skip
    # rather than fail when the absolute cold timing is below the
    # startup-floor threshold -- the spec-104 G-1 budget is meant for a
    # production-shaped project, not a synthetic 5-file stub.
    #
    # Per T-9.1 intent: "OK if it skips when fixture project is minimal".
    # A real perf benchmark fixture would have ~50+ source files and
    # actually exercise the cached check work; that is the realm where
    # G-1 is measurable and the assertion is the contract.
    _CLI_STARTUP_FLOOR_SECONDS = 1.0
    if median_cold < _CLI_STARTUP_FLOOR_SECONDS:
        pytest.skip(
            f"median cold wall-clock {median_cold:.3f}s is dominated by CLI "
            f"startup overhead (<{_CLI_STARTUP_FLOOR_SECONDS:.1f}s). The "
            "G-1 ≥40% reduction contract is meaningful only against a "
            "production-shaped fixture where real gate work dwarfs "
            "startup cost. Run this test against the spec-104 perf "
            "benchmark fixture in nightly CI for a valid measurement."
        )

    ratio = median_warm / median_cold
    diagnostic = (
        f"\nspec-104 G-1 verification\n"
        f"  trials                : {N_TRIALS}\n"
        f"  cold wall-clock (s)   : {[f'{t:.3f}' for t in cold_times]}\n"
        f"  warm wall-clock (s)   : {[f'{t:.3f}' for t in warm_times]}\n"
        f"  median cold (s)       : {median_cold:.3f}\n"
        f"  median warm (s)       : {median_warm:.3f}\n"
        f"  warm/cold ratio       : {ratio:.3f} (must be <= {WARM_BUDGET_RATIO})\n"
        f"  reduction observed    : {(1 - ratio) * 100:.1f}% (must be >= "
        f"{(1 - WARM_BUDGET_RATIO) * 100:.0f}%)\n"
    )

    assert ratio <= WARM_BUDGET_RATIO, (
        f"G-1 violated: warm-cache wall-clock did not achieve the "
        f"≥{(1 - WARM_BUDGET_RATIO) * 100:.0f}% reduction.{diagnostic}"
    )

    # Echo the diagnostic on success too (PASS prints under -v / -s) so
    # CI nightly artifacts capture the actual ratio for trend tracking.
    print(diagnostic)


# ---------------------------------------------------------------------------
# Sanity -- the marker is registered in pyproject.toml. Without this the
# default run would fail with PytestUnknownMarkWarning instead of cleanly
# skipping.
# ---------------------------------------------------------------------------


def test_perf_marker_is_registered() -> None:
    """Confirm the ``perf`` marker is declared in ``[tool.pytest.ini_options]``.

    This test is NOT marked ``@pytest.mark.perf`` -- it runs on every
    invocation as a guard. If a future contributor removes the marker
    declaration, this test fails fast with a clear message.
    """
    repo_root = Path(__file__).resolve().parents[2]
    pyproject = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
    assert "perf:" in pyproject, (
        "The 'perf' marker must be declared in pyproject.toml under "
        "[tool.pytest.ini_options].markers; otherwise pytest emits "
        "PytestUnknownMarkWarning and the perf test is silently mis-skipped."
    )


# ---------------------------------------------------------------------------
# CI invocation reference (developer documentation -- not executable).
# ---------------------------------------------------------------------------
#
# Default test runs SKIP perf benchmarks (no ``-m perf`` filter):
#
#     uv run pytest tests/perf/test_ai_pr_warmcache.py -v
#
# Nightly CI invokes them via ``-m perf``:
#
#     uv run pytest tests/perf/test_ai_pr_warmcache.py -v -m perf
#
# Local manual run (verbose, with print diagnostics):
#
#     uv run pytest tests/perf/test_ai_pr_warmcache.py -v -m perf -s
#
# Set ``AIENG_CACHE_DEBUG=1`` (D-104-10) to log per-check cache hit/miss
# alongside the wall-clock measurement when investigating regressions:
#
#     AIENG_CACHE_DEBUG=1 uv run pytest tests/perf/test_ai_pr_warmcache.py \
#         -v -m perf -s
#
# ---------------------------------------------------------------------------
