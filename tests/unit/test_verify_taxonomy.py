"""Tests for HX-11 verification taxonomy and eval reporting helpers."""

from __future__ import annotations

import pytest

from ai_engineering.standards import EngineeringStandard
from ai_engineering.verify.taxonomy import (
    ReportingSurface,
    VerificationCheckSpec,
    VerificationPlane,
    VerificationTestShape,
    build_reliability_scorecard,
    build_replay_outcome,
    build_seed_eval_pack,
    build_verification_registry,
    classify_check_name,
    summarize_replay_outcomes,
    validate_verification_registry,
)


def test_registry_assigns_stable_ids_and_primary_planes() -> None:
    registry = build_verification_registry()
    by_name = {name: entry for entry in registry for name in entry.current_names}

    assert by_name["ruff"].primary_plane == VerificationPlane.KERNEL
    assert by_name["manifest-coherence"].primary_plane == VerificationPlane.REPO_GOVERNANCE
    assert by_name["verify:quality"].primary_plane == VerificationPlane.VERIFY_REPORT
    assert by_name["install-time-budget"].primary_plane == VerificationPlane.PERF_STABILITY
    assert by_name["eval.scenario.seed"].primary_plane == VerificationPlane.EVAL
    assert by_name["verify:quality"].derived is True
    assert by_name["verify:quality"].blocking is False
    assert all(entry.standards for entry in registry)
    assert EngineeringStandard.TDD in by_name["verify:quality"].standards
    assert EngineeringStandard.SDD in by_name["verify:governance"].standards
    assert EngineeringStandard.HARNESS_ENGINEERING in by_name["validate"].standards


def test_classify_check_name_supports_current_names_and_stable_ids() -> None:
    by_current_name = classify_check_name("pytest-smoke")
    by_stable_id = classify_check_name("check.kernel.pytest_smoke")

    assert by_current_name is not None
    assert by_stable_id is not None
    assert by_current_name.stable_id == by_stable_id.stable_id
    assert classify_check_name("not-a-known-check") is None


def test_registry_validation_rejects_duplicate_names_and_missing_provenance() -> None:
    first = VerificationCheckSpec(
        stableId="check.test.one",
        primaryPlane=VerificationPlane.EVAL,
        currentNames=("same",),
        owner="eval",
        reportingSurfaces=(ReportingSurface.EVAL,),
        testShape=VerificationTestShape.SCENARIO,
        standards=(EngineeringStandard.KISS,),
    )
    second = VerificationCheckSpec(
        stableId="check.test.two",
        primaryPlane=VerificationPlane.EVAL,
        currentNames=("same",),
        owner="eval",
        reportingSurfaces=(ReportingSurface.EVAL,),
        testShape=VerificationTestShape.SCENARIO,
        standards=(EngineeringStandard.KISS,),
    )
    derived_without_provenance = VerificationCheckSpec(
        stableId="check.test.derived",
        primaryPlane=VerificationPlane.VERIFY_REPORT,
        currentNames=("derived",),
        owner="verify",
        reportingSurfaces=(ReportingSurface.VERIFY,),
        testShape=VerificationTestShape.STATIC,
        derived=True,
        standards=(EngineeringStandard.KISS,),
    )

    with pytest.raises(ValueError, match="Duplicate verification current name"):
        validate_verification_registry((first, second))
    with pytest.raises(ValueError, match="lacks provenance"):
        validate_verification_registry((derived_without_provenance,))


def test_seed_eval_pack_delegates_to_existing_runners() -> None:
    pack = build_seed_eval_pack()

    assert pack.reporting_only is True
    assert pack.baseline_ref == ".ai-engineering/evals/baselines/seed.json"
    assert {scenario.runner for scenario in pack.scenarios} == {"pytest"}
    assert {scenario.test_shape for scenario in pack.scenarios} == {
        VerificationTestShape.SCENARIO,
        VerificationTestShape.E2E,
        VerificationTestShape.PERF,
    }
    assert all(scenario.provenance_refs for scenario in pack.scenarios)


def test_replay_outcome_computes_pass_at_k_and_pass_power_k() -> None:
    outcome = build_replay_outcome(
        pack_id="eval.scenario.seed",
        attempts=5,
        successes=3,
        k=2,
        regressions=("scenario.e2e.clean-install",),
        provenance_refs=("tests/e2e/test_install_clean.py",),
    )

    assert outcome.pass_at_k == pytest.approx(0.9)
    assert outcome.pass_power_k == pytest.approx(0.36)
    assert outcome.derived is True


def test_reliability_scorecard_is_derived_and_requires_provenance() -> None:
    outcome = build_replay_outcome(
        pack_id="eval.scenario.seed",
        attempts=5,
        successes=4,
        k=2,
        regressions=("scenario.integration.research-tier0",),
        provenance_refs=("tests/integration/test_ai_research_tier0.py",),
    )

    scorecard = build_reliability_scorecard(
        scorecard_id="scorecard.eval.seed",
        outcomes=(outcome,),
        latency_samples_ms=(10.0, 20.0, 30.0, 40.0, 50.0),
        retry_count=1,
        provenance_refs=(".ai-engineering/evals/baselines/seed.json",),
    )

    assert scorecard.derived is True
    assert scorecard.blocking is False
    assert scorecard.pass_rate == pytest.approx(0.8)
    assert scorecard.regression_count == 1
    assert scorecard.latency_p95_ms == pytest.approx(50.0)

    with pytest.raises(ValueError, match="provenanceRefs"):
        build_reliability_scorecard(scorecard_id="scorecard.bad", outcomes=(outcome,))


def test_summarize_replay_outcomes_groups_regressions_by_pack() -> None:
    first = build_replay_outcome(pack_id="one", attempts=3, successes=2, regressions=("b",))
    second = build_replay_outcome(pack_id="two", attempts=2, successes=2, regressions=("a",))

    summary = summarize_replay_outcomes((first, second))

    assert summary == {
        "packs": 2,
        "attempts": 5,
        "successes": 4,
        "regressions": ["a", "b"],
        "derived": True,
    }
