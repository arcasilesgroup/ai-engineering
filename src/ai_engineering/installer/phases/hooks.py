"""Hooks phase -- deploy hook scripts, install git hooks, merge settings.

Copies ``scripts/hooks/`` tree, installs gate hooks into ``.git/hooks/``,
and performs an intelligent merge of ``.claude/settings.json`` when the
``claude_code`` provider is active.
"""

from __future__ import annotations

import contextlib
import shutil
from pathlib import Path

from ai_engineering.hooks.manager import install_hooks
from ai_engineering.installer.merge import merge_settings
from ai_engineering.installer.templates import (
    copy_file_if_missing,
    copy_template_tree,
    get_project_template_root,
    resolve_template_maps,
)

from . import InstallContext, InstallMode, PhasePlan, PhaseResult, PhaseVerdict, PlannedAction

_SETTINGS_REL = ".claude/settings.json"


class HooksPhase:
    """Deploy hook scripts, install git hooks, and merge settings.json."""

    @property
    def name(self) -> str:
        return "hooks"

    def plan(self, context: InstallContext) -> PhasePlan:
        maps = resolve_template_maps(context.providers, context.vcs_provider)
        actions: list[PlannedAction] = []
        fresh = context.mode is InstallMode.FRESH

        for src_tree, dest_tree in maps.common_tree_list:
            at = "overwrite" if fresh else "create"
            actions.append(PlannedAction(at, src_tree, dest_tree, "hook scripts tree"))

        actions.append(PlannedAction("create", "", ".git/hooks", "install git gate hooks"))

        if "claude_code" in context.providers:
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
        maps = resolve_template_maps(context.providers, context.vcs_provider)

        for src_tree, dest_tree in maps.common_tree_list:
            sd = pr / src_tree
            if not sd.is_dir():
                continue
            if context.mode is InstallMode.FRESH:
                for f in sorted(sd.rglob("*")):
                    if not f.is_file():
                        continue
                    d = context.target / dest_tree / f.relative_to(sd)
                    d.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, d)
                    result.created.append(str(d.relative_to(context.target)))
            else:
                tr = copy_template_tree(sd, context.target / dest_tree)
                result.created.extend(str(p.relative_to(context.target)) for p in tr.created)
                result.skipped.extend(str(p.relative_to(context.target)) for p in tr.skipped)

        with contextlib.suppress(FileNotFoundError):
            hr = install_hooks(context.target)
            result.created.extend(f".git/hooks/{h}" for h in hr.installed)
            result.skipped.extend(f".git/hooks/{h}" for h in hr.skipped)

        self._handle_settings(plan, context, pr, result)
        return result

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        w: list[str] = []
        if not (context.target / ".git/hooks/pre-commit").exists():
            w.append("pre-commit hook not installed")
        hd = context.target / "scripts/hooks"
        if not hd.is_dir() or not any(hd.iterdir()):
            w.append("scripts/hooks/ empty or missing")
        return PhaseVerdict(phase_name=self.name, passed=True, warnings=w)

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
            merge_settings(src, dest)
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
