# T-1.1 Spike — spec-117 Replay/pass@k Functions

## Finding

The functions named in spec-119 D-119-07 (`build_replay_outcome`, `summarize_replay_outcomes`, `build_reliability_scorecard`) do not exist in `src/ai_engineering/`.

Search performed:
- `rg -l "build_replay_outcome|summarize_replay_outcomes|build_reliability_scorecard" src/` → zero hits
- `rg -l "pass_at_k|pass@k|replay" src/ai_engineering/` → matches only inside `src/ai_engineering/verify/scoring.py` (unrelated; that module is the `Verdict`/`Finding`/`SpecialistResult` scoring engine for `ai-verify`, not eval replay).

What spec-117 plan T-3.3 actually says (`.ai-engineering/specs/plan-117-hx-11-verification-and-eval-architecture.md:29`):

> `[x] T-3.3: Add reporting hooks for replay outcomes, pass@k or pass^k, and per-pack regression summaries as derived outputs (agent: build, blocked by T-3.2).`

The plan task is marked complete but no named functions exist. The names in spec-119 D-119-07 were inferred from spec narrative and not verified; this spike corrects that.

## Decision

Build the eval primitives fresh under `src/ai_engineering/eval/`, aligned with spec-117 T-3.3 intent (replay outcomes, pass@k, regression summaries) but without claiming to import non-existent functions. Treat this as forward-looking work: we are landing the runtime primitives that 117 envisioned but did not produce.

Module layout (added in Phase 1 foundation):

```
src/ai_engineering/eval/
├── __init__.py        # public re-exports
├── replay.py          # build_replay_outcome, summarize_replay_outcomes
├── pass_at_k.py       # compute_pass_at_k, compute_pass_caret_k
├── scorecard.py       # build_reliability_scorecard
├── regression.py      # detect_regression, regression_delta
└── thresholds.py      # ManifestEvaluationConfig loader
```

Public API (re-exported from `src/ai_engineering/eval/__init__.py`):

- `build_replay_outcome(scenario_id: str, trial_results: list[bool], metadata: dict) -> ReplayOutcome`
- `summarize_replay_outcomes(outcomes: list[ReplayOutcome]) -> ReplaySummary`
- `compute_pass_at_k(outcomes: list[ReplayOutcome], k: int) -> float`
- `build_reliability_scorecard(summary: ReplaySummary, baseline: dict | None) -> Scorecard`
- `detect_regression(scorecard: Scorecard, baseline: dict, tolerance: float) -> RegressionResult`
- `load_evaluation_config(manifest_path: Path) -> ManifestEvaluationConfig`

Dataclasses:

- `ReplayOutcome(scenario_id, trials_total, trials_passed, metadata)`
- `ReplaySummary(outcomes, total_scenarios, total_trials, total_passed)`
- `Scorecard(pass_at_k, hallucination_rate, regression_delta, verdict, failed_scenarios)`
- `RegressionResult(detected: bool, delta: float, threshold: float, tolerance: float)`

## Impact on spec-119

D-119-07 stays correct in spirit (no duplicated implementation, single source of truth for eval primitives). The amendment is that the SSOT lives at `src/ai_engineering/eval/` (this spec) instead of being inherited from spec-117. T-2.2 imports from `ai_engineering.eval` rather than from undocumented spec-117 paths.

Acceptance criterion in spec-119 ("spec-117 library functions are imported by ai-evaluator runtime") is amended to: "the eval primitives at `src/ai_engineering/eval/` are imported by ai-evaluator runtime; no duplicated implementation exists in agent files or hooks".

## Follow-up

If the team later wants to retroactively credit spec-117 with these primitives, the lineage is documented here. No spec-117 amendment is filed because the work is forward-looking and lands cleanly under spec-119.
