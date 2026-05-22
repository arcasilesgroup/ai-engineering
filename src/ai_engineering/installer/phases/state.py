"""State phase -- generate and persist canonical installation state files."""

from __future__ import annotations

import logging

from ai_engineering.config.loader import load_manifest_root_entry_points
from ai_engineering.state.defaults import (
    default_decision_store,
    default_install_state,
    default_ownership_map,
)
from ai_engineering.state.instincts import ensure_instinct_artifacts
from ai_engineering.state.observability import (
    emit_framework_operation,
    write_framework_capabilities,
)
from ai_engineering.state.repository import DurableStateRepository
from ai_engineering.state.service import remove_legacy_audit_log, save_install_state

from . import InstallContext, InstallMode, PhasePlan, PhaseResult, PhaseVerdict, PlannedAction

_logger = logging.getLogger(__name__)

_SD = ".ai-engineering/state"
# spec-148 P2/P3/P4 (files-only): every state datum is a real file under
# .ai-engineering/state/ — there are no state.db tables.
_STATE = f"{_SD}/install-state.json"
_OWNERSHIP = f"{_SD}/ownership-map.json"
_DECISIONS = f"{_SD}/decision-store.json"
_FRAMEWORK_CAPABILITIES = f"{_SD}/framework-capabilities.json"
_INSTINCT_OBSERVATIONS = f"{_SD}/observation-events.ndjson"
_INSTINCTS = ".ai-engineering/observations/observations.yml"
_INSTINCT_META = ".ai-engineering/observations/meta.json"
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

        # Spec-124 T-3.1: seed ownership map with manifest-derived root-entry
        # patterns (CLAUDE.md, AGENTS.md, .github/copilot-instructions.md)
        # so doctor's `ownership-coverage` probe passes on fresh install.
        # The manifest is already on disk by the time the state phase runs
        # (governance phase precedes state phase in pipeline.py).
        root_entry_points = load_manifest_root_entry_points(context.target)

        for action in plan.actions:
            if action.destination == _STATE:
                if action.action_type == "skip":
                    result.skipped.append(action.destination)
                    continue
                # spec-148 P4: write install-state.json (files-only).
                state_dir = context.target / _SD
                save_install_state(state_dir, default_install_state())
                result.created.append(action.destination)
                continue
            if action.destination == _FRAMEWORK_CAPABILITIES:
                if action.action_type == "skip":
                    result.skipped.append(action.destination)
                    continue
                # spec-148 P4: rebuild + write framework-capabilities.json.
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
            # spec-148 P2/P3 (files-only): ownership-map.json and
            # decision-store.json are the canonical stores, written via the
            # durable repository (the ``_OWNERSHIP`` / ``_DECISIONS``
            # pseudo-paths keep their plan/result keys).
            if action.destination == _OWNERSHIP:
                DurableStateRepository(context.target).save_ownership(
                    default_ownership_map(root_entry_points=root_entry_points),
                )
                result.created.append(action.destination)
                continue
            if action.destination == _DECISIONS:
                DurableStateRepository(context.target).save_decisions(default_decision_store())
                result.created.append(action.destination)
                continue

        legacy_audit_log_removed = remove_legacy_audit_log(context.target)

        # spec-148 P4 (files-only): install no longer bootstraps state.db —
        # every datum (events, decisions, ownership, install-state,
        # capabilities) is file-backed. The state.db layer is deleted in P5.
        emit_framework_operation(
            context.target,
            operation="install-state-phase",
            component="installer.state-phase",
            source="installer",
            metadata={
                "mode": context.mode.value,
                "surfaces": context.surfaces,
                "legacy_audit_log_removed": legacy_audit_log_removed,
            },
        )
        return result

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        errors: list[str] = []
        # spec-148 P2/P3/P4 (files-only): every state datum is a file now.
        # The instinct triplet, install-state.json, framework-capabilities.json,
        # and ownership-map.json must all be present post-install. (decisions
        # may be an empty store on a fresh install, so it is not required.)
        for r in (_INSTINCT_OBSERVATIONS, _INSTINCTS, _INSTINCT_META):
            if not (context.target / r).exists():
                errors.append(f"State file missing: {r}")
        repo = DurableStateRepository(context.target)
        if not repo.install_state_path.is_file():
            errors.append(f"State file missing: {_STATE}")
        if not repo.framework_capabilities_path.is_file():
            errors.append(f"State file missing: {_FRAMEWORK_CAPABILITIES}")
        # The default ownership map carries the root-entry patterns, so a
        # populated file is the post-install expectation.
        if not repo.ownership_map_path.is_file():
            errors.append(f"State file missing: {_OWNERSHIP}")
        elif not repo.load_ownership().paths:
            errors.append(f"State file empty: {_OWNERSHIP}")
        if (context.target / _LEGACY_AUDIT_LOG).exists():
            errors.append(f"Legacy state file should be absent: {_LEGACY_AUDIT_LOG}")
        return PhaseVerdict(phase_name=self.name, passed=not errors, errors=errors)

    @staticmethod
    def _plan_file(
        context: InstallContext, rel: str, *, regenerate_on_fresh: bool
    ) -> PlannedAction:
        # spec-148 P4 (files-only, reverses spec-125): every state datum is
        # a regular file, so the filesystem-existence signal governs the
        # plan again. FRESH + regenerate_on_fresh overwrites; an existing
        # file is skipped (so a reinstall never wipes decisions/ownership
        # with a default seed); an absent file is created.
        exists = (context.target / rel).exists()

        if context.mode is InstallMode.FRESH and regenerate_on_fresh:
            return PlannedAction("overwrite", "", rel, "FRESH: regenerate")
        if exists:
            return PlannedAction("skip", "", rel, "already exists")
        return PlannedAction("create", "", rel, "initialize state file")
