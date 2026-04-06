"""Tools phase -- verify/install required CLI tools and check VCS auth.

This phase is informational: missing tools produce warnings, not errors.
Users can run ``ai-eng setup`` to resolve missing dependencies.
"""

from __future__ import annotations

import logging

from ai_engineering.installer.tools import ensure_tool, manual_install_step, provider_required_tools

from . import (
    InstallContext,
    PhasePlan,
    PhaseResult,
    PhaseVerdict,
    PlannedAction,
)

logger = logging.getLogger(__name__)


class ToolsPhase:
    """Verify availability of required CLI tools and VCS authentication."""

    @property
    def name(self) -> str:
        return "tools"

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def plan(self, context: InstallContext) -> PhasePlan:
        actions: list[PlannedAction] = []
        required = provider_required_tools(context.vcs_provider)

        for tool_name in required:
            actions.append(
                PlannedAction(
                    action_type="skip",
                    source="",
                    destination="",
                    rationale=f"Check tool: {tool_name}",
                )
            )

        return PhasePlan(phase_name=self.name, actions=actions)

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        result = PhaseResult(phase_name=self.name)
        required = provider_required_tools(context.vcs_provider)

        for tool_name in required:
            tool_result = ensure_tool(tool_name, allow_install=True)
            if tool_result.available:
                result.created.append(f"tool:{tool_name}:ok")
            else:
                result.warnings.append(manual_install_step(tool_name))
                result.skipped.append(f"tool:{tool_name}:missing")

        return result

    # ------------------------------------------------------------------
    # verify
    # ------------------------------------------------------------------

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        return PhaseVerdict(
            phase_name=self.name,
            passed=True,
            warnings=list(result.warnings),
        )
