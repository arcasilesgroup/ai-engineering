"""Replay outcomes per scenario, plus aggregation across scenarios."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReplayOutcome:
    """One scenario replayed N times. Boolean per trial.

    `metadata` carries arbitrary scenario metadata (description, expected
    result, grader name) and is preserved verbatim through summarization.
    """

    scenario_id: str
    trials_total: int
    trials_passed: int
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:  # type: ignore[override]
        if self.trials_total < 0:
            msg = "trials_total must be non-negative"
            raise ValueError(msg)
        if self.trials_passed < 0 or self.trials_passed > self.trials_total:
            msg = "trials_passed must be in [0, trials_total]"
            raise ValueError(msg)

    @property
    def pass_rate(self) -> float:
        if self.trials_total == 0:
            return 0.0
        return self.trials_passed / self.trials_total


@dataclass(frozen=True)
class ReplaySummary:
    """Aggregated replay across scenarios."""

    outcomes: tuple[ReplayOutcome, ...]
    total_scenarios: int
    total_trials: int
    total_passed: int

    @property
    def overall_pass_rate(self) -> float:
        if self.total_trials == 0:
            return 0.0
        return self.total_passed / self.total_trials

    def failed_scenario_ids(self) -> tuple[str, ...]:
        """Scenario IDs whose pass_rate is strictly less than 1.0."""
        return tuple(o.scenario_id for o in self.outcomes if o.pass_rate < 1.0)


def build_replay_outcome(
    scenario_id: str,
    trial_results: Sequence[bool],
    metadata: Mapping[str, object] | None = None,
) -> ReplayOutcome:
    """Construct a ReplayOutcome from a sequence of boolean per-trial results.

    `trial_results[i]` is True if trial i passed. The function counts True
    values; the ordering of trials is irrelevant for pass@k computation.
    """
    if not isinstance(scenario_id, str) or not scenario_id.strip():
        msg = "scenario_id must be a non-empty string"
        raise ValueError(msg)
    trials_total = len(trial_results)
    trials_passed = sum(1 for r in trial_results if bool(r))
    return ReplayOutcome(
        scenario_id=scenario_id.strip(),
        trials_total=trials_total,
        trials_passed=trials_passed,
        metadata=dict(metadata or {}),
    )


def summarize_replay_outcomes(outcomes: Iterable[ReplayOutcome]) -> ReplaySummary:
    """Aggregate ReplayOutcomes into a ReplaySummary."""
    materialized = tuple(outcomes)
    total_trials = sum(o.trials_total for o in materialized)
    total_passed = sum(o.trials_passed for o in materialized)
    return ReplaySummary(
        outcomes=materialized,
        total_scenarios=len(materialized),
        total_trials=total_trials,
        total_passed=total_passed,
    )
