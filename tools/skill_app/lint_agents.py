"""``LintAgentsUseCase`` — apply :mod:`skill_domain.rubric` to scanned agents."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from skill_app.ports import AgentScannerPort
from skill_domain.agent_model import Agent
from skill_domain.rubric import (
    AGENT_RULES,
    RubricResult,
    grade_for_score,
)


@dataclass(frozen=True)
class AgentRubricResult:
    path: Path
    agent: Agent
    rule_results: tuple[RubricResult, ...]
    score: int
    grade: str

    def rule_for(self, rule_name: str) -> RubricResult | None:
        for rr in self.rule_results:
            if rr.rule_name == rule_name:
                return rr
        return None


@dataclass(frozen=True)
class AgentsRubricReport:
    per_agent: tuple[AgentRubricResult, ...]
    summary: dict[str, int] = field(default_factory=dict)


class LintAgentsUseCase:
    def __init__(self, scanner: AgentScannerPort) -> None:
        self._scanner = scanner

    def run(self) -> AgentsRubricReport:
        per_agent: list[AgentRubricResult] = []
        for agent in self._scanner.scan_agents():
            rule_results = tuple(rule.evaluate(agent) for rule in AGENT_RULES)
            score = sum(rr.weight for rr in rule_results)
            per_agent.append(
                AgentRubricResult(
                    path=agent.path,
                    agent=agent,
                    rule_results=rule_results,
                    score=score,
                    grade=grade_for_score(score),
                )
            )
        per_agent.sort(key=lambda r: r.path.name)
        summary = dict(Counter(r.grade for r in per_agent))
        for letter in ("A", "B", "C", "D"):
            summary.setdefault(letter, 0)
        return AgentsRubricReport(per_agent=tuple(per_agent), summary=summary)
