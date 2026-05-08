"""Ports (Protocols) the application layer depends on.

These ``typing.Protocol`` classes define the structural contracts that
infrastructure adapters in :mod:`tools.skill_infra` implement. The app
layer only depends on these abstractions — it never imports adapters
directly.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from skill_domain.agent_model import Agent
from skill_domain.skill_model import Skill


class SkillScannerPort(Protocol):
    """Read SKILL.md files into ``Skill`` domain objects.

    Implementations must walk a skills root directory in parallel and
    return one ``Skill`` per ``<root>/<name>/SKILL.md`` discovered.
    """

    def scan_skills(self) -> list[Skill]: ...


class AgentScannerPort(Protocol):
    """Read agent ``.md`` files into ``Agent`` domain objects.

    Implementations must walk an agents root directory in parallel and
    return one ``Agent`` per ``<root>/<name>.md`` discovered.
    """

    def scan_agents(self) -> list[Agent]: ...

    def scan_dispatch_sources(self) -> Iterable[str]:
        """Yield text bodies of files that may dispatch agents.

        Used by ``LintAgentsUseCase`` to determine whether each agent has
        at least one dispatch-source reference (rule 4 of the agent
        rubric).
        """
        ...


class ReporterPort(Protocol):
    """Render a ``RubricReport`` into a target format (e.g., Markdown)."""

    def render(self, report: object) -> str: ...
