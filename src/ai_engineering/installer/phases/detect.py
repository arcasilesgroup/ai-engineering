"""Detect phase -- environment discovery and legacy migration.

Runs first in the pipeline to gather information about the target
project: VCS provider, existing installation, available tools, and
legacy directory structures that need migration.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from ai_engineering.installer.operations import InstallerError

from . import (
    InstallContext,
    PhasePlan,
    PhaseResult,
    PhaseVerdict,
    PlannedAction,
)

logger = logging.getLogger(__name__)

_CHECKED_TOOLS = ("gh", "az", "gitleaks", "ruff")

_MANIFEST_REL = ".ai-engineering/state/install-state.json"
_LEGACY_CONTEXT_REL = ".ai-engineering/context"
_CONTEXTS_REL = ".ai-engineering/contexts"


class DetectPhase:
    """Auto-detect VCS, tools, existing install, and legacy paths."""

    @property
    def name(self) -> str:
        return "detect"

    # ------------------------------------------------------------------
    # plan
    # ------------------------------------------------------------------

    def plan(self, context: InstallContext) -> PhasePlan:
        actions: list[PlannedAction] = []

        # --- Git init (if needed) ---
        if not (context.target / ".git").is_dir():
            actions.append(
                PlannedAction(
                    action_type="create",
                    source="",
                    destination=".git",
                    rationale="git init -- repository not initialized",
                )
            )

        # --- VCS detection ---
        vcs = _detect_vcs(context)
        actions.append(
            PlannedAction(
                action_type="skip",
                source="",
                destination="",
                rationale=f"VCS detected: {vcs}",
            )
        )

        # --- Existing installation ---
        manifest_path = context.target / _MANIFEST_REL
        if manifest_path.exists():
            actions.append(
                PlannedAction(
                    action_type="skip",
                    source="",
                    destination=_MANIFEST_REL,
                    rationale="Existing installation detected (install-state.json present)",
                )
            )

        # --- Tool availability ---
        for tool_name in _CHECKED_TOOLS:
            found = shutil.which(tool_name) is not None
            status = "available" if found else "NOT found"
            actions.append(
                PlannedAction(
                    action_type="skip",
                    source="",
                    destination="",
                    rationale=f"Tool check: {tool_name} {status}",
                )
            )

        # --- Legacy context/ path ---
        legacy_dir = context.target / _LEGACY_CONTEXT_REL
        if legacy_dir.is_dir():
            actions.append(
                PlannedAction(
                    action_type="delete",
                    source="",
                    destination=_LEGACY_CONTEXT_REL,
                    rationale="Legacy path migration to contexts/",
                )
            )

        return PhasePlan(phase_name=self.name, actions=actions)

    # ------------------------------------------------------------------
    # execute
    # ------------------------------------------------------------------

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        result = PhaseResult(phase_name=self.name)

        for action in plan.actions:
            # Git init
            if action.action_type == "create" and action.destination == ".git":
                self._run_git_init(context, result)
                continue

            # Apply VCS detection from plan metadata (only if non-empty)
            if action.rationale.startswith("VCS detected:"):
                detected_vcs = action.rationale.split(": ", 1)[1]
                if detected_vcs:
                    context.vcs_provider = detected_vcs
                continue

            if action.action_type == "skip":
                if action.destination:
                    result.skipped.append(action.destination)
                continue

            if action.action_type == "delete" and action.destination == _LEGACY_CONTEXT_REL:
                self._migrate_legacy_context(context, result)

        return result

    @staticmethod
    def _run_git_init(context: InstallContext, result: PhaseResult) -> None:
        """Initialize a git repository in the target directory."""
        try:
            subprocess.run(
                ["git", "init"],
                cwd=context.target,
                capture_output=True,
                check=True,
            )
        except FileNotFoundError:
            msg = "git is required but not installed. Install git and retry."
            raise InstallerError(msg) from None
        result.created.append(".git")

    # ------------------------------------------------------------------
    # verify
    # ------------------------------------------------------------------

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        warnings: list[str] = []

        for tool_name in _CHECKED_TOOLS:
            if shutil.which(tool_name) is None:
                warnings.append(f"Tool not found: {tool_name}")

        return PhaseVerdict(
            phase_name=self.name,
            passed=True,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _migrate_legacy_context(context: InstallContext, result: PhaseResult) -> None:
        """Move ``context/`` contents into ``contexts/`` and remove the empty tree."""
        legacy_dir = context.target / _LEGACY_CONTEXT_REL
        target_dir = context.target / _CONTEXTS_REL

        if not legacy_dir.is_dir():
            return

        target_dir.mkdir(parents=True, exist_ok=True)

        for item in legacy_dir.iterdir():
            dest = target_dir / item.name
            if dest.exists():
                result.warnings.append(
                    f"Skipped migration of {item.name}: already exists in {_CONTEXTS_REL}/"
                )
                result.skipped.append(str(item.relative_to(context.target)))
                continue

            shutil.move(str(item), str(dest))
            result.created.append(str(dest.relative_to(context.target)))

        # Remove empty legacy tree
        try:
            _remove_empty_tree(legacy_dir)
        except OSError:
            result.warnings.append(
                f"Could not fully remove legacy directory: {_LEGACY_CONTEXT_REL}"
            )


def _detect_vcs(context: InstallContext) -> str:
    """Detect VCS provider from the git remote URL.

    Returns ``""`` when detection fails (no git, no remote, timeout).
    """
    try:
        proc = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            cwd=context.target,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""

    if proc.returncode != 0:
        return ""

    url = proc.stdout.strip().lower()
    if "dev.azure.com" in url or "visualstudio.com" in url:
        return "azure_devops"

    return "github"


def _remove_empty_tree(path: Path) -> None:
    """Remove a directory tree only if all directories are empty."""
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_dir():
            child.rmdir()
    path.rmdir()
