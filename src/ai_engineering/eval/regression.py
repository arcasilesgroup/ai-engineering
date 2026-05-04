"""Regression detection vs a baseline."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class RegressionResult:
    detected: bool
    delta: float
    threshold: float
    tolerance: float


def regression_delta(current: float, baseline: float) -> float:
    """Signed delta: positive = improvement, negative = drop."""
    return float(current) - float(baseline)


def detect_regression(
    current: float,
    baseline: Mapping[str, float] | None,
    *,
    threshold: float,
    tolerance: float,
) -> RegressionResult:
    """Detect a regression vs baseline.

    A regression is reported when the current value is below threshold AND
    the drop vs baseline exceeds tolerance. If baseline is missing, the
    function reports `detected=False` but still returns the threshold and
    tolerance so callers can render a complete envelope.
    """
    if baseline is None or "pass_at_k" not in baseline:
        return RegressionResult(
            detected=False,
            delta=0.0,
            threshold=float(threshold),
            tolerance=float(tolerance),
        )
    try:
        baseline_value = float(baseline["pass_at_k"])
    except (TypeError, ValueError):
        return RegressionResult(
            detected=False,
            delta=0.0,
            threshold=float(threshold),
            tolerance=float(tolerance),
        )
    delta = regression_delta(current, baseline_value)
    detected = (current < threshold) and ((-delta) > tolerance)
    return RegressionResult(
        detected=detected,
        delta=delta,
        threshold=float(threshold),
        tolerance=float(tolerance),
    )
