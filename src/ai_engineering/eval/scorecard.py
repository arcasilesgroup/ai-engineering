"""Reliability scorecard combining pass@k, hallucination rate, and regression delta."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from ai_engineering.eval.pass_at_k import compute_pass_at_k
from ai_engineering.eval.replay import ReplaySummary


class Verdict(StrEnum):
    GO = "GO"
    CONDITIONAL = "CONDITIONAL"
    NO_GO = "NO_GO"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class Scorecard:
    """Single-run reliability scorecard.

    `regression_delta` is a *signed* number: negative means a drop relative
    to baseline, positive means improvement, zero means parity. The agent
    layer maps verdict by combining `pass_at_k` against threshold and
    `regression_delta` against tolerance.
    """

    pass_at_k: float
    k: int
    hallucination_rate: float
    regression_delta: float
    verdict: Verdict
    failed_scenarios: tuple[str, ...]
    total_scenarios: int
    total_trials: int


def _verdict(
    pass_at_k_value: float,
    threshold: float,
    regression_delta_value: float,
    regression_tolerance: float,
    hallucination_rate_value: float,
    hallucination_max: float,
) -> Verdict:
    if pass_at_k_value < threshold and (-regression_delta_value) > regression_tolerance:
        return Verdict.NO_GO
    if hallucination_rate_value > hallucination_max:
        return Verdict.NO_GO
    if pass_at_k_value < threshold:
        return Verdict.CONDITIONAL
    if (-regression_delta_value) > regression_tolerance:
        return Verdict.CONDITIONAL
    return Verdict.GO


def build_reliability_scorecard(
    summary: ReplaySummary,
    k: int,
    *,
    threshold: float,
    regression_tolerance: float,
    hallucination_rate: float,
    hallucination_max: float,
    baseline: Mapping[str, float] | None = None,
) -> Scorecard:
    """Build a scorecard from a replay summary plus thresholds.

    `baseline` is an optional mapping that may carry `pass_at_k` from the
    last accepted run; when present, regression_delta is `current - baseline`.
    """
    score = compute_pass_at_k(summary, k)
    if baseline is None or "pass_at_k" not in baseline:
        regression_delta = 0.0
    else:
        try:
            baseline_value = float(baseline["pass_at_k"])
        except (TypeError, ValueError):
            baseline_value = 0.0
        regression_delta = score - baseline_value
    verdict = _verdict(
        pass_at_k_value=score,
        threshold=threshold,
        regression_delta_value=regression_delta,
        regression_tolerance=regression_tolerance,
        hallucination_rate_value=hallucination_rate,
        hallucination_max=hallucination_max,
    )
    return Scorecard(
        pass_at_k=score,
        k=k,
        hallucination_rate=hallucination_rate,
        regression_delta=regression_delta,
        verdict=verdict,
        failed_scenarios=summary.failed_scenario_ids(),
        total_scenarios=summary.total_scenarios,
        total_trials=summary.total_trials,
    )
