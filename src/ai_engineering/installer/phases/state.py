"""State phase -- generate and persist canonical installation state files."""

from __future__ import annotations

import logging

from ai_engineering.config.loader import load_manifest_root_entry_points
from ai_engineering.state import state_db
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
from ai_engineering.state.service import remove_legacy_audit_log, save_install_state

from . import InstallContext, InstallMode, PhasePlan, PhaseResult, PhaseVerdict, PlannedAction

_logger = logging.getLogger(__name__)

_SD = ".ai-engineering/state"
# spec-125: install-state.json and framework-capabilities.json are now
# state.db tables (install_state, tool_capabilities). The pseudo-paths
# below are retained as plan/result identifiers so external callers
# that inspect ``PhaseResult.created`` keep their stable string keys.
_STATE = f"{_SD}/install-state.json"
_OWNERSHIP = f"{_SD}/ownership-map.json"
_DECISIONS = f"{_SD}/decision-store.json"
_FRAMEWORK_CAPABILITIES = f"{_SD}/framework-capabilities.json"
_INSTINCT_OBSERVATIONS = f"{_SD}/observation-events.ndjson"
_INSTINCTS = ".ai-engineering/observations/observations.yml"
_INSTINCT_META = ".ai-engineering/observations/meta.json"
_LEGACY_AUDIT_LOG = f"{_SD}/audit-log.ndjson"

# Pseudo-paths backed by state.db tables (spec-125 cutover). These keys
# still flow through the plan/result API but no JSON file is written.
_DB_BACKED_PSEUDO_PATHS = frozenset({_STATE, _FRAMEWORK_CAPABILITIES})


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
        # patterns (CLAUDE.md, AGENTS.md, GEMINI.md, .github/copilot-instructions.md)
        # so doctor's `ownership-coverage` probe passes on fresh install.
        # The manifest is already on disk by the time the state phase runs
        # (governance phase precedes state phase in pipeline.py).
        root_entry_points = load_manifest_root_entry_points(context.target)

        def _seeded_ownership_map():
            return default_ownership_map(root_entry_points=root_entry_points)

        generators = {
            _OWNERSHIP: _seeded_ownership_map,
            _DECISIONS: default_decision_store,
        }

        for action in plan.actions:
            if action.destination == _STATE:
                if action.action_type == "skip":
                    result.skipped.append(action.destination)
                    continue
                # spec-125 T-1.4: write singleton row into the
                # install_state state.db table (no JSON file).
                state_dir = context.target / _SD
                save_install_state(state_dir, default_install_state())
                result.created.append(action.destination)
                continue
            if action.destination == _FRAMEWORK_CAPABILITIES:
                if action.action_type == "skip":
                    result.skipped.append(action.destination)
                    continue
                # spec-125 T-1.12: write_framework_capabilities now
                # populates the tool_capabilities table (added by
                # migration 0005).
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

        # spec-123 T-3.3: bootstrap state.db now that the JSON state files
        # are on disk. The lazy connect() runs migrations and replays the
        # NDJSON; subsequent installs no-op (ledger already records every
        # migration). Failure is logged but never blocks the install --
        # the projection is rebuildable from NDJSON, so a one-off failure
        # here does not lose source-of-truth data.
        state_db_bootstrapped = False
        try:
            conn = state_db.connect(context.target)
            try:
                ledger_rows = conn.execute("SELECT count(*) FROM _migrations").fetchone()[0]
            finally:
                conn.close()
            state_db_bootstrapped = bool(ledger_rows)
        except Exception as exc:  # pragma: no cover -- defensive
            _logger.warning("state.db bootstrap failed during install: %s", exc)

        emit_framework_operation(
            context.target,
            operation="install-state-phase",
            component="installer.state-phase",
            source="installer",
            metadata={
                "mode": context.mode.value,
                "providers": context.providers,
                "legacy_audit_log_removed": legacy_audit_log_removed,
                "state_db_bootstrapped": state_db_bootstrapped,
            },
        )
        return result

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        errors: list[str] = []
        # spec-125: install_state and tool_capabilities live in state.db.
        # The pseudo-path strings remain in the manifest API but the
        # filesystem check is replaced by a state.db row probe.
        for r in (_OWNERSHIP, _DECISIONS, _INSTINCT_OBSERVATIONS, _INSTINCTS, _INSTINCT_META):
            if not (context.target / r).exists():
                errors.append(f"State file missing: {r}")
        # state.db backed: install_state singleton + tool_capabilities cards.
        try:
            conn = state_db.connect(context.target, read_only=True)
            try:
                install_count = conn.execute(
                    "SELECT COUNT(*) FROM install_state WHERE id = 1"
                ).fetchone()[0]
                if not install_count:
                    errors.append(f"State file missing: {_STATE}")
                # tool_capabilities table only exists once migration 0005 has run.
                tbl = conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='tool_capabilities'"
                ).fetchone()
                if tbl is not None:
                    cap_count = conn.execute("SELECT COUNT(*) FROM tool_capabilities").fetchone()[0]
                    if not cap_count:
                        errors.append(f"State file missing: {_FRAMEWORK_CAPABILITIES}")
                else:  # pragma: no cover -- transient until 0005 lands
                    errors.append(f"State file missing: {_FRAMEWORK_CAPABILITIES}")
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover -- defensive
            errors.append(f"state.db verification failed: {exc}")
        if (context.target / _LEGACY_AUDIT_LOG).exists():
            errors.append(f"Legacy state file should be absent: {_LEGACY_AUDIT_LOG}")
        return PhaseVerdict(phase_name=self.name, passed=not errors, errors=errors)

    @staticmethod
    def _plan_file(
        context: InstallContext, rel: str, *, regenerate_on_fresh: bool
    ) -> PlannedAction:
        # spec-125: db-backed pseudo paths skip the filesystem-existence
        # signal. They are always treated as 'create' on first install
        # and 'overwrite' on FRESH; the table-level UPSERT is idempotent.
        if rel in _DB_BACKED_PSEUDO_PATHS:
            if context.mode is InstallMode.FRESH and regenerate_on_fresh:
                return PlannedAction("overwrite", "", rel, "FRESH: regenerate state.db row")
            return PlannedAction("create", "", rel, "ensure state.db row")

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
