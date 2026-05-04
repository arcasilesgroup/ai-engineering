"""pass@k metric.

Standard definition (Kulal et al., HumanEval, 2021):

    pass@k = E_problems[ 1 - C(n - c, k) / C(n, k) ]

where for each problem:
    n = number of trials performed
    c = number of trials passed
    k = the "k" of pass@k

When n < k, the formula is undefined; we follow the convention used by
the HumanEval reference: treat the per-problem term as `1 - (0 / 1) = 1`
when c >= k (problem solvable within k trials in expectation) and as
`c / n` when k > n (best estimate without enough trials). The summarization
reports the mean across problems.

Stdlib-only; no scipy/numpy dependency for this primitive.
"""

from __future__ import annotations

from math import comb

from ai_engineering.eval.replay import ReplayOutcome, ReplaySummary


def _per_problem_pass_at_k(n: int, c: int, k: int) -> float:
    if n <= 0:
        return 0.0
    if c <= 0:
        return 0.0
    if k <= 0:
        return 0.0
    if k > n:
        # Underestimate gracefully: report the empirical pass rate.
        return c / n
    if n - c < k:
        # Every k-subset must contain at least one passing trial → pass@k = 1.
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def compute_pass_at_k(
    outcomes_or_summary: ReplaySummary | list[ReplayOutcome] | tuple[ReplayOutcome, ...],
    k: int,
) -> float:
    """Mean pass@k across scenarios. Accepts either a ReplaySummary or an
    iterable of ReplayOutcomes."""
    if isinstance(outcomes_or_summary, ReplaySummary):
        outcomes = outcomes_or_summary.outcomes
    else:
        outcomes = tuple(outcomes_or_summary)
    if not outcomes:
        return 0.0
    if k < 1:
        msg = "k must be a positive integer"
        raise ValueError(msg)
    per_problem = [_per_problem_pass_at_k(o.trials_total, o.trials_passed, k) for o in outcomes]
    return sum(per_problem) / len(per_problem)
