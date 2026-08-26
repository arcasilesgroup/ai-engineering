"""Named decision frameworks, spec 034 / B-034-2.

A decision that ranks chooses a named framework and applies it — RICE, Effort/Value, or
Kano — so the ranking is repeatable across sessions instead of whatever the model reached
for. A bare "ranked by impact" with no named method is not a decision this framework
supports (contains-studio).
"""

from __future__ import annotations

FRAMEWORKS = ("rice", "effort_value", "kano")


def rice(reach: float, impact: float, confidence: float, effort: float) -> float:
    """RICE score: Reach x Impact x Confidence / Effort. Deterministic."""
    return reach * impact * confidence / effort


def effort_value(value: float, effort: float) -> float:
    """Effort/Value score: value per unit of effort. Deterministic."""
    return value / effort


def kano(category: str) -> str:
    """Kano category: basic, performance or delighter. Closed."""
    if category not in ("basic", "performance", "delighter"):
        raise ValueError(f"kano category must be basic/performance/delighter, got {category!r}")
    return category


def named(rationale: str) -> str | None:
    """The framework a rationale names, or None when none is named.

    "ranked by impact" names no framework — refused. "RICE" normalises to "rice".
    """
    folded = rationale.strip().casefold().replace("-", "_").replace(" ", "_")
    for framework in FRAMEWORKS:
        if framework in folded:
            return framework
    return None
