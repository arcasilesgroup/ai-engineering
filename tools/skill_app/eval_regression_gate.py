"""Regression-gate use case — pure function over baseline + current pass@1.

Sub-007 M6 application layer. Per D-127-07, a >5 percentage-point
drop in pass@1 must fail the CI gate when ``ai-eval --skill-set
--regression`` runs on a PR touching ``.claude/skills/**``. This
module owns the comparison logic; running the optimizer to *produce*
the current pass@1 vector belongs in :mod:`skill_app.eval_runner`.

Design choices
~~~~~~~~~~~~~~

- Pure function — no I/O, no LLM calls, no subprocess. The runner
  injects the optimizer adapter and feeds the resulting pass@1
  mapping straight into :func:`compute_regression_report`. This keeps
  the gate trivially testable and re-runnable.
- ``threshold_pp`` is read from each :class:`BaselineEntry`, defaulting
  to 5.0 (the D-127-07 contract). Per-skill overrides let intrinsically
  noisier skills carry a wider tolerance without weakening the global
  default.
- Boundary semantics: D-127-07 says ``>5%``, so exactly 5 pp is
  *tolerated*. The test suite pins this in
  ``test_regression_gate_treats_exactly_five_pp_as_tolerated``. A
  small epsilon (1e-9) absorbs the IEEE-754 noise on
  ``1.0 - 0.95 == 0.04999999999999...`` so the boundary case stays
  tolerated rather than flickering on rounding.
- Missing skills (present in baseline, absent from current) score 0.0
  to surface the regression rather than silently skip the skill —
  baseline coverage shrinking is itself a regression signal.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from skill_domain.eval_types import BaselineEntry, RegressionReport


def compute_regression_report(
    *,
    baseline: Sequence[BaselineEntry],
    current: Mapping[str, float],
) -> RegressionReport:
    """Return a :class:`RegressionReport` comparing ``current`` to ``baseline``.

    Parameters
    ----------
    baseline:
        The captured pass@1 values from ``evals/baseline.json``. Each
        entry carries its own ``threshold_pp``; the gate uses that
        threshold per-skill.
    current:
        The freshly-measured pass@1 values keyed by skill name. Skills
        present in baseline but absent from this mapping are scored as
        0.0 to surface dropped coverage as a regression.

    Returns
    -------
    RegressionReport
        ``failed=True`` iff at least one skill dropped by *more than*
        its ``threshold_pp`` (per-skill, default 5.0). The
        ``regressions`` tuple lists every skill that crossed its
        threshold, ordered by skill name for stable diffs.
    """
    regressions: list[tuple[str, float, float, float]] = []

    # IEEE-754 epsilon — absorbs e.g. ``1.0 - 0.95 == 0.0500…04`` so
    # the exactly-5pp boundary case stays tolerated. The 1e-9 floor is
    # twelve orders of magnitude smaller than the 5pp threshold; it
    # cannot mask any real-world regression but it stops the gate from
    # flickering on rounding alone.
    _EPSILON = 1e-9

    for entry in baseline:
        # Missing skill ⇒ pass@1 floor of 0.0; the drop is the full
        # baseline value. This intentionally amplifies dropped-coverage
        # regressions over silent skips.
        current_pass_at_1 = float(current.get(entry.skill, 0.0))
        drop_pp = (entry.pass_at_1 - current_pass_at_1) * 100.0

        # D-127-07 boundary: ``>5%`` means exactly 5 pp is tolerated.
        # Strict greater-than keeps the gate forgiving on the noise floor.
        if drop_pp > entry.threshold_pp + _EPSILON:
            regressions.append((entry.skill, entry.pass_at_1, current_pass_at_1, drop_pp))

    # Sort by skill name so the report is diff-stable across CI runs.
    regressions.sort(key=lambda row: row[0])

    return RegressionReport(
        failed=bool(regressions),
        regressions=tuple(regressions),
        skills_evaluated=len(baseline),
    )


__all__ = ["compute_regression_report"]
