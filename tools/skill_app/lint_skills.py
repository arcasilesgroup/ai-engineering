"""``LintSkillsUseCase`` — apply :mod:`skill_domain.rubric` to scanned skills.

Pure use case: takes a :class:`SkillScannerPort` adapter, iterates the
returned ``Skill`` instances, evaluates ``SKILL_RULES`` for each, and
folds severity weights into a letter grade per
:func:`skill_domain.rubric.grade_for_score`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from skill_app.ports import SkillScannerPort
from skill_domain.rubric import (
    SKILL_RULES,
    RubricResult,
    grade_for_score,
)
from skill_domain.skill_model import Skill


@dataclass(frozen=True)
class SkillRubricResult:
    """Per-skill grading outcome."""

    path: Path
    skill: Skill
    rule_results: tuple[RubricResult, ...]
    score: int
    grade: str

    def rule_for(self, rule_name: str) -> RubricResult | None:
        for rr in self.rule_results:
            if rr.rule_name == rule_name:
                return rr
        return None

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(rr.reason for rr in self.rule_results if rr.severity != "OK")


@dataclass(frozen=True)
class SkillsRubricReport:
    """Aggregate report over all scanned skills."""

    per_skill: tuple[SkillRubricResult, ...]
    summary: dict[str, int] = field(default_factory=dict)


class LintSkillsUseCase:
    """Drive the rubric over a :class:`SkillScannerPort`."""

    def __init__(self, scanner: SkillScannerPort) -> None:
        self._scanner = scanner

    def run(self) -> SkillsRubricReport:
        per_skill: list[SkillRubricResult] = []
        for skill in self._scanner.scan_skills():
            rule_results = tuple(rule.evaluate(skill) for rule in SKILL_RULES)
            score = sum(rr.weight for rr in rule_results)
            per_skill.append(
                SkillRubricResult(
                    path=skill.path.parent,  # report the skill directory, not SKILL.md
                    skill=skill,
                    rule_results=rule_results,
                    score=score,
                    grade=grade_for_score(score),
                )
            )
        # Stable sort by path so report ordering is deterministic.
        per_skill.sort(key=lambda r: r.path.name)
        summary = dict(Counter(r.grade for r in per_skill))
        # Ensure all four letters are present in the summary, even if 0.
        for letter in ("A", "B", "C", "D"):
            summary.setdefault(letter, 0)
        return SkillsRubricReport(per_skill=tuple(per_skill), summary=summary)
