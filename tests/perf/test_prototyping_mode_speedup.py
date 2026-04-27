"""spec-105 Phase 5 G-3 -- prototyping mode wall-clock speedup.

Asserts that ``manifest.gates.mode: prototyping`` reduces wall-clock of
``ai-eng gate run`` >= 40% over the regulated baseline. Comparison
protocol per spec G-3:

* 5-run median wall-clock per mode (warmup discarded).
* Sigma <= 15% of mean for validity (otherwise skip -- noisy host).
* Assertion ``prototyping_p50_ms <= 0.6 * regulated_p50_ms``.

Status: GREEN body lands in Phase 5 T-5.18, but the perf fixture
(``tests/fixtures/perf_single_stack/``) is intentionally out-of-scope
for spec-105 -- the test auto-skips when the fixture is missing so CI
remains green. Operators that want to enable the perf gate run
``pytest -m perf`` after seeding the fixture.

The ``spec_105_red`` marker is retained as a nightly opt-in gate per
the Phase 5 plan: spec-105 declares perf gates a follow-up surface,
not a Phase-1-blocking invariant. Removing the marker would make the
test fail-by-skip on every CI run, which adds noise without value.
"""

from __future__ import annotations

import statistics
from pathlib import Path

import pytest

pytestmark = [pytest.mark.spec_105_red, pytest.mark.perf]


_PERF_FIXTURE_REL = Path("tests") / "fixtures" / "perf_single_stack"
_REPS = 5
_WARMUP = 1
_RATIO_MAX = 0.6
_SIGMA_MAX_RATIO = 0.15


def _project_root() -> Path:
    """Resolve the repo root from this test file location."""
    return Path(__file__).resolve().parents[2]


def _fixture_available() -> bool:
    """True iff the perf single-stack fixture directory exists."""
    return (_project_root() / _PERF_FIXTURE_REL).is_dir()


def _measure_mode_p50(mode: str, fixture_dir: Path) -> tuple[float, float]:
    """Run ``run_gate`` 5 times for ``mode`` and return ``(median_ms, sigma_ms)``.

    A single warmup run is discarded so the JIT / cache-warming penalty
    doesn't poison the measurement. The remaining 4 samples feed the
    median + stdev computation.
    """
    import time

    from ai_engineering.policy import orchestrator

    samples_ms: list[float] = []
    for _i in range(_REPS + _WARMUP):
        start = time.monotonic()
        orchestrator.run_gate(
            project_root=fixture_dir,
            staged_files=[],
            mode="local",
            gate_mode=mode,
            cache_disabled=True,
            produced_by="ai-commit",
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        samples_ms.append(elapsed_ms)
    # Drop warmup samples and use the remaining N for median/stdev.
    measured = samples_ms[_WARMUP:]
    median_ms = statistics.median(measured)
    sigma_ms = statistics.pstdev(measured) if len(measured) > 1 else 0.0
    return median_ms, sigma_ms


def test_prototyping_mode_p50_at_most_60_percent_of_regulated() -> None:
    """G-3 -- prototyping p50 <= 0.6 * regulated p50 wall-clock."""
    if not _fixture_available():
        pytest.skip(
            "perf fixture missing at tests/fixtures/perf_single_stack/. "
            "spec-105 declares this fixture as a follow-up surface; "
            "create it and unmark this test to enable the perf gate."
        )
    fixture_dir = _project_root() / _PERF_FIXTURE_REL

    regulated_p50, regulated_sigma = _measure_mode_p50("regulated", fixture_dir)
    prototyping_p50, prototyping_sigma = _measure_mode_p50("prototyping", fixture_dir)

    # Validity: sigma <= 15% of mean per G-3. Skip on noisy host so the
    # comparison stays meaningful rather than producing a false fail.
    if regulated_sigma > _SIGMA_MAX_RATIO * regulated_p50:
        pytest.skip(
            f"regulated sigma {regulated_sigma:.1f}ms > {_SIGMA_MAX_RATIO:.0%} "
            f"of mean {regulated_p50:.1f}ms (noisy host); rerun on a quieter machine."
        )
    if prototyping_sigma > _SIGMA_MAX_RATIO * prototyping_p50:
        pytest.skip(
            f"prototyping sigma {prototyping_sigma:.1f}ms > {_SIGMA_MAX_RATIO:.0%} "
            f"of mean {prototyping_p50:.1f}ms (noisy host); rerun on a quieter machine."
        )

    ratio = prototyping_p50 / regulated_p50 if regulated_p50 > 0 else 1.0
    assert ratio <= _RATIO_MAX, (
        f"prototyping p50 {prototyping_p50:.1f}ms is {ratio:.0%} of regulated "
        f"p50 {regulated_p50:.1f}ms; spec G-3 requires <= {_RATIO_MAX:.0%}."
    )
