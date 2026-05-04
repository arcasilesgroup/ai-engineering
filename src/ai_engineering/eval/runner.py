"""Scenario-pack runner glue used by ai-evaluator agent and /ai-eval-gate.

A scenario pack is a JSON document with the shape:

    {
      "version": "1",
      "scenarios": [
        {
          "id": "scn-1",
          "description": "...",
          "k": 5,
          "grader": "deterministic.exact_match",
          "expected": "...",
          "trial_runner": "<runner-id>",
          "metadata": {...}
        },
        ...
      ]
    }

The runner does not perform actual code execution. It is the thin glue
between a pack JSON, a callable that returns boolean per-trial outcomes,
and the scorecard primitives. Agents and skills supply the trial callable
so deterministic CI tests can stub it.

Telemetry is emitted via _lib.observability through the project hooks
when callers pass a project_root and an emit-helper module.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.eval.replay import (
    ReplayOutcome,
    ReplaySummary,
    build_replay_outcome,
    summarize_replay_outcomes,
)
from ai_engineering.eval.scorecard import Scorecard, build_reliability_scorecard
from ai_engineering.eval.thresholds import ManifestEvaluationConfig

TrialRunner = Callable[[Mapping[str, object], int], bool]


@dataclass(frozen=True)
class ScenarioRunResult:
    pack_path: str
    summary: ReplaySummary
    scorecard: Scorecard


def _load_pack(path: Path) -> Mapping[str, object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "scenarios" not in raw:
        msg = f"scenario pack {path} missing top-level `scenarios` array"
        raise ValueError(msg)
    return raw


def _scenarios(pack: Mapping[str, object]) -> Iterable[Mapping[str, object]]:
    return tuple(pack.get("scenarios", []))  # type: ignore[arg-type]


def run_scenario_pack(
    pack_path: Path,
    *,
    config: ManifestEvaluationConfig,
    trial_runner: TrialRunner,
    baseline: Mapping[str, float] | None = None,
    hallucination_rate: float = 0.0,
) -> ScenarioRunResult:
    """Run every scenario in `pack_path` through `trial_runner` and build
    a Scorecard. The trial runner receives `(scenario, trial_id)` and
    returns True for pass / False for fail.
    """
    pack = _load_pack(pack_path)
    outcomes: list[ReplayOutcome] = []
    for scenario in _scenarios(pack):
        scenario_id = str(scenario.get("id", "")).strip()
        if not scenario_id:
            msg = f"scenario in {pack_path} missing required `id`"
            raise ValueError(msg)
        scenario_k = int(scenario.get("k", config.pass_at_k_k))
        results = [trial_runner(scenario, t) for t in range(scenario_k)]
        outcomes.append(
            build_replay_outcome(
                scenario_id=scenario_id,
                trial_results=results,
                metadata=scenario.get("metadata", {}),  # type: ignore[arg-type]
            )
        )
    summary = summarize_replay_outcomes(outcomes)
    scorecard = build_reliability_scorecard(
        summary,
        config.pass_at_k_k,
        threshold=config.pass_at_k_threshold,
        regression_tolerance=config.regression_tolerance,
        hallucination_rate=hallucination_rate,
        hallucination_max=config.hallucination_rate_max,
        baseline=baseline,
    )
    return ScenarioRunResult(
        pack_path=str(pack_path),
        summary=summary,
        scorecard=scorecard,
    )


def load_baseline(pack_path: Path) -> Mapping[str, float] | None:
    """Read the baseline section from a scenario pack if present.

    Convention: scenario pack JSON may carry a top-level `baseline` object,
    e.g. `{"baseline": {"pass_at_k": 0.85}}`. Missing baseline returns None.
    """
    if not pack_path.exists():
        return None
    raw = json.loads(pack_path.read_text(encoding="utf-8"))
    baseline = raw.get("baseline") if isinstance(raw, dict) else None
    if not isinstance(baseline, dict):
        return None
    out: dict[str, float] = {}
    for k, v in baseline.items():
        try:
            out[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    return out
