"""Eval-harness domain types — sub-007 M6 pilot scope.

Hexagonal layer rule (D-127-09): pure stdlib only. No imports from
``skill_app`` or ``skill_infra``. The four immutable dataclasses below
are the canonical wire format for the skill-set eval corpus, the
captured baseline, and the regression report consumed by the
application-layer regression gate.

Design choices
~~~~~~~~~~~~~~

- All dataclasses are ``frozen=True`` so the regression gate can
  hash-and-cache results without worrying about post-construction
  mutation.
- Each dataclass exposes a symmetrical ``to_dict`` / ``from_dict``
  pair so the JSON wire format stays stable across the CLI
  (``scripts/run_loop_skill_evals.py``) and the CI workflow
  (``.github/workflows/skill-evals.yml``). Round-trip equality is
  asserted in ``tests/integration/test_eval_regression_gate.py`` to
  pin the contract.
- ``RegressionReport.failed`` is computed eagerly at construction
  time so the regression gate stays a one-line predicate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# EvalCase — a single eval row (should-trigger / near-miss).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvalCase:
    """One eval case — paired prompt and expected skill outcome.

    ``kind`` is constrained to the two values consumed by the optimizer
    pass@k math: ``should_trigger`` (the skill should fire on this prompt)
    and ``near_miss`` (an adversarial prompt that *looks* like it would
    trigger but should not). The corpus generator emits 8 of each per
    skill in the M6 design; the regression gate is agnostic to the mix.
    """

    skill: str
    prompt: str
    kind: str  # "should_trigger" | "near_miss"
    expected: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Wire-format serialization. Stable key order for diff-friendly JSON."""
        return {
            "skill": self.skill,
            "prompt": self.prompt,
            "kind": self.kind,
            "expected": self.expected,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalCase:
        """Inverse of :meth:`to_dict`. Missing ``notes`` defaults to ``""``."""
        return cls(
            skill=str(data["skill"]),
            prompt=str(data["prompt"]),
            kind=str(data["kind"]),
            expected=bool(data["expected"]),
            notes=str(data.get("notes", "")),
        )


# ---------------------------------------------------------------------------
# EvalCorpus — the bag of cases for one skill.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvalCorpus:
    """All eval cases for one skill. Tuple-backed to preserve immutability."""

    skill: str
    cases: tuple[EvalCase, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Wire-format serialization (cases as a list for JSON compatibility)."""
        return {
            "skill": self.skill,
            "cases": [case.to_dict() for case in self.cases],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvalCorpus:
        """Inverse of :meth:`to_dict`."""
        cases_data = data.get("cases", [])
        cases = tuple(EvalCase.from_dict(c) for c in cases_data)
        return cls(skill=str(data["skill"]), cases=cases)


# ---------------------------------------------------------------------------
# BaselineEntry — captured pass@1 for one skill at a known SHA.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BaselineEntry:
    """One row of ``evals/baseline.json``.

    ``threshold_pp`` is the per-skill regression threshold in
    *percentage points*. The default (5.0) matches D-127-07; a future
    skill that is intrinsically noisier may pin a wider threshold
    without forcing the gate to widen for everybody.
    """

    skill: str
    pass_at_1: float
    captured_at_sha: str = ""
    threshold_pp: float = 5.0

    def to_dict(self) -> dict[str, Any]:
        """Wire-format serialization. ``threshold_pp`` always emitted to keep
        the baseline file self-describing."""
        return {
            "skill": self.skill,
            "pass_at_1": self.pass_at_1,
            "captured_at_sha": self.captured_at_sha,
            "threshold_pp": self.threshold_pp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BaselineEntry:
        """Inverse of :meth:`to_dict`."""
        return cls(
            skill=str(data["skill"]),
            pass_at_1=float(data["pass_at_1"]),
            captured_at_sha=str(data.get("captured_at_sha", "")),
            threshold_pp=float(data.get("threshold_pp", 5.0)),
        )


# ---------------------------------------------------------------------------
# RegressionReport — the gate's decision payload.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RegressionReport:
    """Per-skill drop summary plus a precomputed ``failed`` flag.

    ``regressions`` is a tuple of ``(skill, baseline_pass_at_1,
    current_pass_at_1, drop_pp)`` triples for skills that dropped at
    least one threshold's worth. The CLI prints this; the CI workflow
    exits non-zero whenever ``failed`` is ``True``.

    ``failed`` is populated by :meth:`compute` (the only constructor
    callers should use). Direct construction is supported for tests
    that synthesize a report inline.
    """

    failed: bool
    regressions: tuple[tuple[str, float, float, float], ...] = field(default_factory=tuple)
    skills_evaluated: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Wire-format serialization."""
        return {
            "failed": self.failed,
            "skills_evaluated": self.skills_evaluated,
            "regressions": [
                {
                    "skill": skill,
                    "baseline_pass_at_1": baseline,
                    "current_pass_at_1": current,
                    "drop_pp": drop_pp,
                }
                for skill, baseline, current, drop_pp in self.regressions
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegressionReport:
        """Inverse of :meth:`to_dict`."""
        regressions = tuple(
            (
                str(row["skill"]),
                float(row["baseline_pass_at_1"]),
                float(row["current_pass_at_1"]),
                float(row["drop_pp"]),
            )
            for row in data.get("regressions", [])
        )
        return cls(
            failed=bool(data["failed"]),
            regressions=regressions,
            skills_evaluated=int(data.get("skills_evaluated", 0)),
        )


__all__ = [
    "BaselineEntry",
    "EvalCase",
    "EvalCorpus",
    "RegressionReport",
]
