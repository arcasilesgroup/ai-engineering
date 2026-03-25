"""State phase -- generate and persist installation state files.

Creates ``install-state.json``, ``ownership-map.json``, and
``decision-store.json``.  Append-only files are never overwritten.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ai_engineering.state.defaults import (
    default_decision_store,
    default_install_state,
    default_ownership_map,
)
from ai_engineering.state.io import append_ndjson, write_json_model
from ai_engineering.state.models import AuditEntry

from . import InstallContext, InstallMode, PhasePlan, PhaseResult, PhaseVerdict, PlannedAction

_SD = ".ai-engineering/state"
_STATE = f"{_SD}/install-state.json"
_OWNERSHIP = f"{_SD}/ownership-map.json"
_DECISIONS = f"{_SD}/decision-store.json"
_AUDIT_LOG = f"{_SD}/audit-log.ndjson"


class StatePhase:
    """Generate installation state files."""

    @property
    def name(self) -> str:
        return "state"

    def plan(self, context: InstallContext) -> PhasePlan:
        actions = [
            self._plan_file(context, _STATE, regenerate_on_fresh=True),
            self._plan_file(context, _OWNERSHIP, regenerate_on_fresh=True),
            self._plan_file(context, _DECISIONS, regenerate_on_fresh=False),
            PlannedAction("skip", "", _AUDIT_LOG, "append-only; created on first write"),
        ]
        return PhasePlan(phase_name=self.name, actions=actions)

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        result = PhaseResult(phase_name=self.name)
        generators = {
            _STATE: default_install_state,
            _OWNERSHIP: default_ownership_map,
            _DECISIONS: default_decision_store,
        }

        for action in plan.actions:
            if action.action_type == "skip":
                result.skipped.append(action.destination)
                continue
            gen = generators.get(action.destination)
            if gen:
                write_json_model(context.target / action.destination, gen())
                result.created.append(action.destination)

        append_ndjson(
            context.target / _AUDIT_LOG,
            AuditEntry(
                timestamp=datetime.now(tz=UTC),
                event="install",
                actor="ai-eng",
                detail={"mode": context.mode.value, "providers": context.providers},
            ),
        )
        return result

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        errors = [
            f"State file missing: {r}"
            for r in (_STATE, _OWNERSHIP, _DECISIONS)
            if not (context.target / r).exists()
        ]
        return PhaseVerdict(phase_name=self.name, passed=not errors, errors=errors)

    @staticmethod
    def _plan_file(
        context: InstallContext, rel: str, *, regenerate_on_fresh: bool
    ) -> PlannedAction:
        exists = (context.target / rel).exists()

        if rel == _DECISIONS:
            if exists:
                return PlannedAction("skip", "", rel, "append-only; never overwrite")
            return PlannedAction("create", "", rel, "initialize decision store")

        if context.mode is InstallMode.FRESH and regenerate_on_fresh:
            return PlannedAction("overwrite", "", rel, "FRESH: regenerate")
        if exists:
            return PlannedAction("skip", "", rel, "already exists")
        return PlannedAction("create", "", rel, "initialize state file")
