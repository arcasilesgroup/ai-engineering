"""``AgentScannerPort`` — read agent .md files into domain ``Agent`` objects.

Migrated from ``tools/skill_app/ports.py`` per spec-127 sub-006 M5.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from skill_domain.agent_model import Agent


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
