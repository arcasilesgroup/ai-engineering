"""State phase -- generate and persist canonical installation state files."""

from __future__ import annotations

from ai_engineering.state.defaults import (
    default_decision_store,
    default_install_state,
    default_ownership_map,
)
from ai_engineering.state.instincts import ensure_instinct_artifacts
from ai_engineering.state.io import write_json_model
from ai_engineering.state.observability import (
    emit_framework_operation,
    write_framework_capabilities,
)
from ai_engineering.state.service import remove_legacy_audit_log

from . import InstallContext, InstallMode, PhasePlan, PhaseResult, PhaseVerdict, PlannedAction

_SD = ".ai-engineering/state"
_STATE = f"{_SD}/install-state.json"
_OWNERSHIP = f"{_SD}/ownership-map.json"
_DECISIONS = f"{_SD}/decision-store.json"
_FRAMEWORK_CAPABILITIES = f"{_SD}/framework-capabilities.json"
_INSTINCT_OBSERVATIONS = f"{_SD}/instinct-observations.ndjson"
_INSTINCTS = ".ai-engineering/instincts/instincts.yml"
_INSTINCT_META = ".ai-engineering/instincts/meta.json"
_LEGACY_AUDIT_LOG = f"{_SD}/audit-log.ndjson"


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
            self._plan_file(context, _FRAMEWORK_CAPABILITIES, regenerate_on_fresh=True),
            self._plan_file(context, _INSTINCT_OBSERVATIONS, regenerate_on_fresh=True),
            self._plan_file(context, _INSTINCTS, regenerate_on_fresh=True),
            self._plan_file(context, _INSTINCT_META, regenerate_on_fresh=True),
        ]
        return PhasePlan(phase_name=self.name, actions=actions)

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        result = PhaseResult(phase_name=self.name)
        legacy_audit_log_removed = False
        generators = {
            _STATE: default_install_state,
            _OWNERSHIP: default_ownership_map,
            _DECISIONS: default_decision_store,
        }

        for action in plan.actions:
            if action.destination == _FRAMEWORK_CAPABILITIES:
                if action.action_type == "skip":
                    result.skipped.append(action.destination)
                    continue
                write_framework_capabilities(context.target)
                result.created.append(action.destination)
                continue
            if action.destination in {
                _INSTINCT_OBSERVATIONS,
                _INSTINCTS,
                _INSTINCT_META,
            }:
                if action.action_type == "skip":
                    result.skipped.append(action.destination)
                    continue
                ensure_instinct_artifacts(context.target)
                result.created.append(action.destination)
                continue
            if action.action_type == "skip":
                result.skipped.append(action.destination)
                continue
            gen = generators.get(action.destination)
            if gen:
                write_json_model(context.target / action.destination, gen())
                result.created.append(action.destination)

        legacy_audit_log_removed = remove_legacy_audit_log(context.target)

        emit_framework_operation(
            context.target,
            operation="install-state-phase",
            component="installer.state-phase",
            source="installer",
            metadata={
                "mode": context.mode.value,
                "providers": context.providers,
                "legacy_audit_log_removed": legacy_audit_log_removed,
            },
        )
        return result

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        errors = [
            f"State file missing: {r}"
            for r in (
                _STATE,
                _OWNERSHIP,
                _DECISIONS,
                _FRAMEWORK_CAPABILITIES,
                _INSTINCT_OBSERVATIONS,
                _INSTINCTS,
                _INSTINCT_META,
            )
            if not (context.target / r).exists()
        ]
        if (context.target / _LEGACY_AUDIT_LOG).exists():
            errors.append(f"Legacy state file should be absent: {_LEGACY_AUDIT_LOG}")
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
