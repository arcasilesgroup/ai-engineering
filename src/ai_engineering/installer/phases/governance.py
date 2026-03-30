"""Governance phase -- copy the ``.ai-engineering/`` framework tree.

Copies governance files (contexts, specs, manifest YAML) while
respecting ownership boundaries: team-owned and system-managed files
are never overwritten outside of FRESH mode.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ai_engineering.installer.templates import (
    copy_file_if_missing,
    get_ai_engineering_template_root,
)

from . import (
    InstallContext,
    InstallMode,
    PhasePlan,
    PhaseResult,
    PhaseVerdict,
    PlannedAction,
)

_EXCLUDE_PREFIXES = ("agents/", "skills/")

_TEAM_OWNED = "contexts/team/"
_STATE_PREFIX = "state/"
_STATE_REGENERATED = {"state/install-state.json", "state/ownership-map.json"}

# Migration mappings: new_rel -> old_rel (for files that moved between versions)
_MIGRATIONS: dict[str, str] = {
    "LESSONS.md": "contexts/team/lessons.md",
}


class GovernancePhase:
    """Copy the ``.ai-engineering/`` governance tree to the target project."""

    @property
    def name(self) -> str:
        return "governance"

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def plan(self, context: InstallContext) -> PhasePlan:
        src_root = get_ai_engineering_template_root()
        dest_root = context.target / ".ai-engineering"
        actions: list[PlannedAction] = []

        for src_file in sorted(src_root.rglob("*")):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(src_root).as_posix()
            if any(rel.startswith(p) for p in _EXCLUDE_PREFIXES):
                continue

            dest_rel = f".ai-engineering/{rel}"
            dest_path = dest_root / rel

            action_type, rationale = self._classify(rel, dest_path, context.mode)
            actions.append(
                PlannedAction(
                    action_type=action_type,
                    source=rel,
                    destination=dest_rel,
                    rationale=rationale,
                )
            )

        return PhasePlan(phase_name=self.name, actions=actions)

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        result = PhaseResult(phase_name=self.name)
        src_root = get_ai_engineering_template_root()

        for action in plan.actions:
            dest = context.target / action.destination

            if action.action_type == "skip":
                result.skipped.append(action.destination)
                continue

            if action.action_type == "migrate":
                old_rel = _MIGRATIONS.get(action.source, "")
                old_path = context.target / ".ai-engineering" / old_rel
                if old_path.exists() and not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_path), str(dest))
                    result.created.append(action.destination)
                elif not dest.exists():
                    src = src_root / action.source
                    if copy_file_if_missing(src, dest):
                        result.created.append(action.destination)
                    else:
                        result.skipped.append(action.destination)
                else:
                    result.skipped.append(action.destination)
                continue

            if action.action_type == "create":
                src = src_root / action.source
                if copy_file_if_missing(src, dest):
                    result.created.append(action.destination)
                else:
                    result.skipped.append(action.destination)
                continue

            if action.action_type == "overwrite":
                src = src_root / action.source
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                result.created.append(action.destination)

        return result

    # ------------------------------------------------------------------
    # verify
    # ------------------------------------------------------------------

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        errors: list[str] = []

        for path_str in result.created:
            if not (context.target / path_str).exists():
                errors.append(f"Expected file missing after write: {path_str}")

        return PhaseVerdict(
            phase_name=self.name,
            passed=not errors,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify(rel: str, dest_path: Path, mode: InstallMode) -> tuple[str, str]:
        """Return (action_type, rationale) for a single file."""
        # Check for files that migrated to a new location
        if rel in _MIGRATIONS and mode in (InstallMode.INSTALL, InstallMode.REPAIR):
            old_rel = _MIGRATIONS[rel]
            old_path = dest_path.parent / old_rel
            if old_path.exists():
                return "migrate", f"migrate from {old_rel} to {rel}"

        if rel.startswith(_TEAM_OWNED):
            if mode is InstallMode.INSTALL:
                if dest_path.exists():
                    return "skip", "team seed already exists"
                return "create", "team seed file"
            if mode is InstallMode.FRESH:
                return "overwrite", "FRESH mode: overwrite framework-owned"
            return "skip", "team-owned file"

        if rel.startswith(_STATE_PREFIX):
            if rel in _STATE_REGENERATED and mode is InstallMode.FRESH:
                return "skip", "regenerated by state phase in FRESH mode"
            return "skip", "state file managed by state phase"

        exists = dest_path.exists()

        if mode is InstallMode.FRESH:
            return "overwrite", "FRESH mode: overwrite framework-owned"

        # INSTALL and REPAIR: create-only
        if exists:
            return "skip", "file already exists"
        return "create", "new file"
