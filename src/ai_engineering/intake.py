"""The intake validator, spec 037 / B-037-3.

validate_intake(text) returns PASS when the opening request names the goal, the
constraints and an acceptance signal, and INCOMPLETE with the missing fields when it does
not. A well-formed free request passes without the template; the template
(specs/new-goal-template.md) is the fallback for malformed requests, and its own example
is the contract validated end to end.
"""

from __future__ import annotations

import re

_FIELDS = (
    ("goal", re.compile(r"\bgoal\b", re.I)),
    ("constraints", re.compile(r"\bconstraints?\b", re.I)),
    ("acceptance", re.compile(r"\bacceptance\b|when .* then .*|given .* when .* then", re.I)),
)


def validate_intake(text: str) -> str:
    """PASS when goal, constraints and an acceptance signal are present."""
    if not text or not text.strip():
        return "INCOMPLETE: empty request; name the goal, the constraints and an acceptance signal"
    present = [name for name, pat in _FIELDS if pat.search(text)]
    missing = [name for name, _ in _FIELDS if name not in present]
    if missing:
        return f"INCOMPLETE: missing {', '.join(missing)}"
    return "PASS"
