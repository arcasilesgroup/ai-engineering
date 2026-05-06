"""Hooks phase -- deploy hook scripts, install git hooks, merge settings.

Copies the governance-managed hook runtime into
``.ai-engineering/scripts/hooks/``, installs gate hooks into ``.git/hooks/``,
and performs an intelligent merge of ``.claude/settings.json`` when the
``claude-code`` provider is active.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
from pathlib import Path

from ai_engineering.hooks.manager import install_hooks
from ai_engineering.installer.merge import merge_settings
from ai_engineering.installer.templates import (
    copy_file_if_missing,
    copy_tree_for_mode,
    get_ai_engineering_template_root,
    get_project_template_root,
    resolve_template_maps,
)

from . import InstallContext, InstallMode, PhasePlan, PhaseResult, PhaseVerdict, PlannedAction

_SETTINGS_REL = ".claude/settings.json"
_HOOK_RUNTIME_REL = ".ai-engineering/scripts/hooks"


class HooksPhase:
    """Deploy hook scripts, install git hooks, and merge settings.json."""

    def __init__(self) -> None:
        self._resolved_maps = None

    @property
    def name(self) -> str:
        return "hooks"

    def plan(self, context: InstallContext) -> PhasePlan:
        self._resolved_maps = resolve_template_maps(context.providers, context.vcs_provider)
        actions: list[PlannedAction] = []
        fresh = context.mode is InstallMode.FRESH

        at = "overwrite" if fresh else "create"
        actions.append(PlannedAction(at, _HOOK_RUNTIME_REL, _HOOK_RUNTIME_REL, "hook scripts tree"))

        actions.append(PlannedAction("create", "", ".git/hooks", "install git gate hooks"))

        if "claude-code" in context.providers:
            pr = get_project_template_root()
            src = pr / ".claude" / "settings.json"
            if src.is_file():
                dest = context.target / _SETTINGS_REL
                if dest.is_file():
                    actions.append(
                        PlannedAction("merge", _SETTINGS_REL, _SETTINGS_REL, "merge hooks")
                    )
                else:
                    at = "overwrite" if fresh else "create"
                    actions.append(
                        PlannedAction(at, _SETTINGS_REL, _SETTINGS_REL, "deploy settings")
                    )

        return PhasePlan(phase_name=self.name, actions=actions)

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        result = PhaseResult(phase_name=self.name)
        pr = get_project_template_root()
        governance_root = get_ai_engineering_template_root()
        hook_source_dir = governance_root / "scripts" / "hooks"
        hook_dest_dir = context.target / _HOOK_RUNTIME_REL

        if hook_source_dir.is_dir():
            copy_tree_for_mode(
                hook_source_dir,
                hook_dest_dir,
                context.target,
                fresh=context.mode is InstallMode.FRESH,
                created=result.created,
                skipped=result.skipped,
            )

        # Restore executable permissions on hook scripts
        # (shutil.copy2 may not preserve them on all platforms).
        # Skip on Windows where Unix permission bits are not supported.
        if os.name != "nt" and hook_dest_dir.is_dir():
            for script in hook_dest_dir.rglob("*"):
                if (
                    script.is_file()
                    and script.suffix in (".sh", ".py")
                    and "_lib" not in script.parts
                ):
                    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)

        hr = install_hooks(context.target)
        result.created.extend(f".git/hooks/{h}" for h in hr.installed)
        result.skipped.extend(f".git/hooks/{h}" for h in hr.skipped)

        self._handle_settings(plan, context, pr, result)
        return result

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        w: list[str] = []
        errors: list[str] = []
        passed = True
        if not (context.target / ".git/hooks/pre-commit").exists():
            errors.append("pre-commit hook not installed")
            passed = False
        hd = context.target / ".ai-engineering" / "scripts" / "hooks"
        if not hd.is_dir() or not any(hd.iterdir()):
            w.append(".ai-engineering/scripts/hooks/ empty or missing")
        return PhaseVerdict(phase_name=self.name, passed=passed, warnings=w, errors=errors)

    @staticmethod
    def _handle_settings(
        plan: PhasePlan, context: InstallContext, pr: Path, result: PhaseResult
    ) -> None:
        actions = [a for a in plan.actions if a.destination == _SETTINGS_REL]
        if not actions:
            return
        action = actions[0]
        src, dest = pr / ".claude/settings.json", context.target / _SETTINGS_REL
        if not src.is_file():
            return
        if action.action_type == "merge":
            template_data = json.loads(src.read_text(encoding="utf-8"))
            merge_settings(template_data, dest, base=context.target)
            result.created.append(_SETTINGS_REL)
        elif action.action_type == "create":
            if copy_file_if_missing(src, dest):
                result.created.append(_SETTINGS_REL)
            else:
                result.skipped.append(_SETTINGS_REL)
        elif action.action_type == "overwrite":
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            result.created.append(_SETTINGS_REL)
