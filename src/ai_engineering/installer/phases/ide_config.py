"""IDE config phase -- deploy provider-specific templates.

Copies IDE agent/skill trees and configuration files for each selected
AI provider.  In RECONFIGURE mode, removed providers have their files
cleaned up.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ai_engineering.installer.templates import (
    copy_file_if_missing,
    copy_template_tree,
    get_project_template_root,
    provider_template_dest_paths,
    remove_provider_templates,
    resolve_template_maps,
)

from . import InstallContext, InstallMode, PhasePlan, PhaseResult, PhaseVerdict, PlannedAction


def _file_action(dest_rel: str, dest: Path, overwrite: bool, tag: str) -> PlannedAction:
    if overwrite:
        return PlannedAction("overwrite", "", dest_rel, f"FRESH: overwrite {tag}")
    if dest.exists():
        return PlannedAction("skip", "", dest_rel, f"{tag} exists")
    return PlannedAction("create", "", dest_rel, f"new {tag}")


def _tree_actions(root: Path, src_tree: str, dest_tree: str, target: Path, ow: bool, tag: str):
    src_dir = root / src_tree
    if not src_dir.is_dir():
        return
    for f in sorted(src_dir.rglob("*")):
        if not f.is_file():
            continue
        dr = f"{dest_tree}/{f.relative_to(src_dir).as_posix()}"
        yield _file_action(dr, target / dr, ow, tag)


def _copy_tree(src_dir: Path, dest_dir: Path, mode: InstallMode, result: PhaseResult) -> None:
    if mode is InstallMode.FRESH:
        for f in sorted(src_dir.rglob("*")):
            if not f.is_file():
                continue
            d = dest_dir / f.relative_to(src_dir)
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d)
            result.created.append(str(d))
    else:
        tr = copy_template_tree(src_dir, dest_dir)
        result.created.extend(str(p) for p in tr.created)
        result.skipped.extend(str(p) for p in tr.skipped)


class IdeConfigPhase:
    """Deploy IDE-specific configuration files based on selected providers."""

    @property
    def name(self) -> str:
        return "ide_config"

    def plan(self, context: InstallContext) -> PhasePlan:
        maps = resolve_template_maps(context.providers, context.vcs_provider)
        pr = get_project_template_root()
        ow = context.mode is InstallMode.FRESH
        actions: list[PlannedAction] = []

        for sr, dr in sorted(maps.file_map.items()):
            if (pr / sr).is_file():
                actions.append(_file_action(dr, context.target / dr, ow, "provider"))
        for sr, dr in sorted(maps.common_file_map.items()):
            if (pr / sr).is_file():
                actions.append(_file_action(dr, context.target / dr, ow, "common"))
        for st, dt in maps.tree_list:
            actions.extend(_tree_actions(pr, st, dt, context.target, ow, "provider tree"))
        for st, dt in maps.vcs_tree_list:
            actions.extend(_tree_actions(pr, st, dt, context.target, ow, "VCS"))

        if context.mode is InstallMode.RECONFIGURE and context.existing_manifest:
            old = context.existing_manifest.ai_providers.enabled
            for rm in set(old) - set(context.providers):
                for dp in provider_template_dest_paths(rm):
                    actions.append(PlannedAction("delete", "", dp, f"remove {rm}"))

        return PhasePlan(phase_name=self.name, actions=actions)

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        result = PhaseResult(phase_name=self.name)
        maps = resolve_template_maps(context.providers, context.vcs_provider)
        pr = get_project_template_root()

        for sr, dr in sorted({**maps.file_map, **maps.common_file_map}.items()):
            src, dest = pr / sr, context.target / dr
            if not src.is_file():
                continue
            if context.mode is InstallMode.FRESH:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                result.created.append(dr)
            elif copy_file_if_missing(src, dest):
                result.created.append(dr)
            else:
                result.skipped.append(dr)

        for st, dt in maps.tree_list + maps.vcs_tree_list:
            sd = pr / st
            if sd.is_dir():
                _copy_tree(sd, context.target / dt, context.mode, result)

        if context.mode is InstallMode.RECONFIGURE and context.existing_manifest:
            old = context.existing_manifest.ai_providers.enabled
            for rm in set(old) - set(context.providers):
                deleted = remove_provider_templates(context.target, rm, context.providers)
                result.created.extend(f"deleted:{p}" for p in deleted)

        return result

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        maps = resolve_template_maps(context.providers, context.vcs_provider)
        errors = [
            f"Missing: {dr}"
            for _sr, dr in maps.file_map.items()
            if not (context.target / dr).exists()
        ]
        return PhaseVerdict(phase_name=self.name, passed=not errors, errors=errors)
