"""Regression-gate integration test — sub-007 M6 TDD anchor.

D-127-07: a >5 percentage-point drop in pass@1 must fail the CI gate
when ``ai-eval --skill-set --regression`` runs on a PR touching
``.claude/skills/**``. This test pins that contract by:

1. Constructing a synthetic baseline of 5 skills, all at pass@1 = 1.0.
2. Constructing a "current" pass@1 vector where one skill drops to
   0.93 (a 7 pp drop, comfortably above the 5 pp threshold).
3. Asserting the regression gate flags the report as failed,
   identifies the regressed skill, and emits a non-empty regressions
   tuple.

Round-trip equality of the four eval-types dataclasses is also
asserted here so the JSON wire format stays stable across the CLI
(``scripts/run_loop_skill_evals.py``) and the CI workflow.

The gate logic itself is a pure function over baseline and current
pass@1 values — no LLM, no subprocess, no disk I/O. The dependency
on :class:`OptimizerPort` is preserved at the use-case import surface
so future tests that exercise the full runner can substitute a stub
adapter, but this test deliberately keeps the surface narrow to stay
deterministic in CI.
"""

from __future__ import annotations

import json

import pytest

from skill_app.eval_regression_gate import compute_regression_report
from skill_domain.eval_types import (
    BaselineEntry,
    EvalCase,
    EvalCorpus,
    RegressionReport,
)

# ---------------------------------------------------------------------------
# Round-trip serialization (T-1.1 follow-on, in the same RED suite).
# ---------------------------------------------------------------------------


def test_eval_case_round_trip() -> None:
    """``EvalCase.from_dict(case.to_dict())`` returns an equal instance."""
    case = EvalCase(
        skill="ai-debug",
        prompt="why is my regex matching empty strings",
        kind="should_trigger",
        expected=True,
        notes="seed",
    )
    assert EvalCase.from_dict(case.to_dict()) == case


def test_eval_corpus_round_trip() -> None:
    """``EvalCorpus`` round-trips through JSON without losing case order."""
    corpus = EvalCorpus(
        skill="ai-test",
        cases=(
            EvalCase("ai-test", "write a test for foo", "should_trigger", True),
            EvalCase("ai-test", "fix the broken pipeline", "near_miss", False),
        ),
    )
    serialized = json.dumps(corpus.to_dict())
    restored = EvalCorpus.from_dict(json.loads(serialized))
    assert restored == corpus


def test_baseline_entry_default_threshold_is_five_pp() -> None:
    """``BaselineEntry.threshold_pp`` defaults to 5.0 — D-127-07 contract."""
    entry = BaselineEntry(skill="ai-plan", pass_at_1=0.92)
    assert entry.threshold_pp == 5.0
    assert BaselineEntry.from_dict(entry.to_dict()) == entry


def test_regression_report_round_trip() -> None:
    """``RegressionReport`` round-trips with regressions tuple intact."""
    report = RegressionReport(
        failed=True,
        regressions=(("ai-debug", 1.0, 0.93, 7.0),),
        skills_evaluated=5,
    )
    assert RegressionReport.from_dict(report.to_dict()) == report


def test_dataclasses_are_frozen() -> None:
    """All four eval-type dataclasses must be immutable post-construction."""
    case = EvalCase("s", "p", "should_trigger", True)
    with pytest.raises(Exception):  # noqa: B017 — project pattern; FrozenInstanceError subclass.
        case.skill = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Regression gate — the heart of the contract.
# ---------------------------------------------------------------------------


def test_regression_gate_flags_seven_pp_drop_as_failure() -> None:
    """A 7 pp drop on one skill (baseline 1.0 → current 0.93) must fail.

    This is the canonical D-127-07 regression: the gate pins the
    >5 pp threshold so any single-skill drop above 5 pp blocks merge.
    """
    skills = ("ai-debug", "ai-test", "ai-verify", "ai-review", "ai-commit")
    baseline = tuple(BaselineEntry(skill=s, pass_at_1=1.0) for s in skills)
    current = {
        "ai-debug": 0.93,  # -7 pp — the regressor.
        "ai-test": 1.0,
        "ai-verify": 1.0,
        "ai-review": 1.0,
        "ai-commit": 1.0,
    }

    report = compute_regression_report(baseline=baseline, current=current)

    assert report.failed is True, "report must mark failed=True for >5 pp drop"
    assert report.skills_evaluated == 5
    assert len(report.regressions) == 1
    skill, baseline_score, current_score, drop_pp = report.regressions[0]
    assert skill == "ai-debug"
    assert baseline_score == pytest.approx(1.0)
    assert current_score == pytest.approx(0.93)
    assert drop_pp == pytest.approx(7.0)


def test_regression_gate_passes_when_drop_is_below_threshold() -> None:
    """A 4 pp drop is within tolerance — gate must NOT fail."""
    skills = ("ai-debug", "ai-test")
    baseline = tuple(BaselineEntry(skill=s, pass_at_1=1.0) for s in skills)
    current = {"ai-debug": 0.96, "ai-test": 1.0}  # -4 pp, tolerated.

    report = compute_regression_report(baseline=baseline, current=current)

    assert report.failed is False
    assert report.skills_evaluated == 2
    assert report.regressions == ()


def test_regression_gate_treats_exactly_five_pp_as_tolerated() -> None:
    """Exactly 5 pp is tolerated — only *above* 5 pp fails (D-127-07: ``>5%``)."""
    baseline = (BaselineEntry(skill="ai-debug", pass_at_1=1.0),)
    current = {"ai-debug": 0.95}  # -5.0 pp — boundary, must be tolerated.

    report = compute_regression_report(baseline=baseline, current=current)

    assert report.failed is False, "exactly 5 pp must be tolerated (gate is >5%)"


def test_regression_gate_handles_missing_current_skill_as_drop_to_zero() -> None:
    """A skill present in baseline but missing from current scores as 0.0."""
    baseline = (
        BaselineEntry(skill="ai-debug", pass_at_1=1.0),
        BaselineEntry(skill="ai-test", pass_at_1=1.0),
    )
    current = {"ai-debug": 1.0}  # ``ai-test`` absent — treated as 0.0.

    report = compute_regression_report(baseline=baseline, current=current)

    assert report.failed is True
    assert any(skill == "ai-test" for skill, *_ in report.regressions)


def test_regression_gate_respects_per_skill_threshold_override() -> None:
    """A skill with ``threshold_pp=10.0`` tolerates wider drops on its own."""
    baseline = (
        BaselineEntry(skill="ai-noisy", pass_at_1=1.0, threshold_pp=10.0),
        BaselineEntry(skill="ai-strict", pass_at_1=1.0),  # default 5.0
    )
    current = {"ai-noisy": 0.93, "ai-strict": 1.0}  # ai-noisy -7 pp, but threshold 10.

    report = compute_regression_report(baseline=baseline, current=current)

    assert report.failed is False, "per-skill threshold override must absorb noisier skills"
