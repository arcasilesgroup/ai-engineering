"""spec-119 evaluation primitives.

Provides pure-Python primitives for replay outcomes, pass@k computation,
reliability scorecards, regression detection, and manifest-driven thresholds.
Stdlib-only at import-time; deepeval is loaded lazily inside graders that
opt into LLM grading (follow-up work) so the bare module can be exercised
in CI without paying the deepeval transitive footprint.

Forward-looking landing of the work spec-117 plan T-3.3 envisioned but did
not produce; see `.ai-engineering/specs/spec-119-progress/spike-spec-117-funcs.md`.
"""

from __future__ import annotations

from ai_engineering.eval.pass_at_k import compute_pass_at_k
from ai_engineering.eval.regression import (
    RegressionResult,
    detect_regression,
    regression_delta,
)
from ai_engineering.eval.replay import (
    ReplayOutcome,
    ReplaySummary,
    build_replay_outcome,
    summarize_replay_outcomes,
)
from ai_engineering.eval.scorecard import Scorecard, Verdict, build_reliability_scorecard
from ai_engineering.eval.thresholds import (
    ManifestEvaluationConfig,
    load_evaluation_config,
)

__all__ = [
    "ManifestEvaluationConfig",
    "RegressionResult",
    "ReplayOutcome",
    "ReplaySummary",
    "Scorecard",
    "Verdict",
    "build_reliability_scorecard",
    "build_replay_outcome",
    "compute_pass_at_k",
    "detect_regression",
    "load_evaluation_config",
    "regression_delta",
    "summarize_replay_outcomes",
]
