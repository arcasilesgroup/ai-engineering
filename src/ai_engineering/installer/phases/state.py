"""State phase -- generate and persist canonical installation state files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ai_engineering import __version__
from ai_engineering.config.loader import load_manifest_root_entry_points
from ai_engineering.installer.capability_catalog import apply_capability_catalog
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


def _state_root(context: InstallContext) -> Path:
    """Return the root the state tree lives under for this scope (sub-003 D11).

    Global scope mirrors the install marker into ``~/.ai-engineering/state/`` so
    ``update`` can detect drift independently of any repo; local scope keeps
    today's repo-rooted behavior. Delegates to the single ``brain_root`` helper
    (spec-156 D-156-04).
    """
    from ai_engineering.installer.scope import brain_root

    return brain_root(context.scope, context.target)


def _stamp_framework_version(state_dir: Path) -> None:
    """Stamp ``framework_version`` into install-state.json (sub-003 D11).

    ``InstallState`` (pydantic, ignore-extra) does not carry the field, so the
    value is patched directly into the on-disk JSON after the model write. This
    lets ``update`` compare the recorded version against the running
    ``ai_engineering.__version__`` to detect drift without altering the shared
    state model.
    """
    path = state_dir / "install-state.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["framework_version"] = __version__
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _stamp_scope(state_dir: Path, scope: str) -> None:
    """Stamp the install ``scope`` into install-state.json (spec-156 D-156-07).

    ``InstallState`` now carries ``scope`` as a real field, but the write path
    seeds the file from ``default_install_state()`` (scope-agnostic), so the
    resolved scope is patched in after the model write — mirroring
    :func:`_stamp_framework_version`.
    """
    path = state_dir / "install-state.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    data["scope"] = scope
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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
        state_root = _state_root(context)

        # Spec-124 T-3.1: seed ownership map with manifest-derived root-entry
        # patterns (CLAUDE.md, AGENTS.md, .github/copilot-instructions.md)
        # so doctor's `ownership-coverage` probe passes on fresh install.
        # The manifest is already on disk by the time the state phase runs
        # (governance phase precedes state phase in pipeline.py).
        root_entry_points = load_manifest_root_entry_points(state_root)

        for action in plan.actions:
            if action.destination == _STATE:
                if action.action_type == "skip":
                    result.skipped.append(action.destination)
                    continue
                # spec-148 P4: write install-state.json (files-only).
                state_dir = state_root / _SD
                save_install_state(state_dir, default_install_state())
                # sub-003 D11: stamp framework_version so update detects drift.
                _stamp_framework_version(state_dir)
                # spec-156 D-156-07: record the scope this install lives under.
                _stamp_scope(state_dir, context.scope)
                result.created.append(action.destination)
                continue
            if action.destination == _FRAMEWORK_CAPABILITIES:
                if action.action_type == "skip":
                    result.skipped.append(action.destination)
                    continue
                # spec-148 P4: rebuild + write framework-capabilities.json.
                write_framework_capabilities(state_root)
                # spec-153 W5: regenerate the derived README catalog block
                # alongside it (fail-open when markers/generator are absent).
                apply_capability_catalog(state_root)
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
                ensure_instinct_artifacts(state_root)
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
                DurableStateRepository(state_root).save_ownership(
                    default_ownership_map(root_entry_points=root_entry_points),
                )
                result.created.append(action.destination)
                continue
            if action.destination == _DECISIONS:
                DurableStateRepository(state_root).save_decisions(default_decision_store())
                result.created.append(action.destination)
                continue

        legacy_audit_log_removed = remove_legacy_audit_log(state_root)

        # spec-148 P4 (files-only): install no longer bootstraps state.db —
        # every datum (events, decisions, ownership, install-state,
        # capabilities) is file-backed. The state.db layer is deleted in P5.
        emit_framework_operation(
            state_root,
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
        state_root = _state_root(context)
        # spec-148 P2/P3/P4 (files-only): every state datum is a file now.
        # The instinct triplet, install-state.json, framework-capabilities.json,
        # and ownership-map.json must all be present post-install. (decisions
        # may be an empty store on a fresh install, so it is not required.)
        for r in (_INSTINCT_OBSERVATIONS, _INSTINCTS, _INSTINCT_META):
            if not (state_root / r).exists():
                errors.append(f"State file missing: {r}")
        repo = DurableStateRepository(state_root)
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
        if (state_root / _LEGACY_AUDIT_LOG).exists():
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
        exists = (_state_root(context) / rel).exists()

        if context.mode is InstallMode.FRESH and regenerate_on_fresh:
            return PlannedAction("overwrite", "", rel, "FRESH: regenerate")
        if exists:
            return PlannedAction("skip", "", rel, "already exists")
        return PlannedAction("create", "", rel, "initialize state file")
