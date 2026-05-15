"""Surface config phase -- deploy Surface-specific templates.

Copies Surface agent/skill trees and instruction files for each selected
Surface. In RECONFIGURE mode, removed Surfaces have their files cleaned
up. spec-133 D-133-16: ``Surface`` fuses AI Provider + IDE Integration
into one axis; the legacy ide/provider phases collapsed here.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.installer.templates import (
    copy_file_if_missing,
    copy_tree_for_mode,
    get_project_template_root,
    remove_surface_templates,
    resolve_template_maps,
    surface_template_dest_paths,
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


class IdeConfigPhase:
    """Deploy Surface-specific configuration files (Surfaces x VCS templates)."""

    def __init__(self) -> None:
        self._resolved_maps = None

    @property
    def name(self) -> str:
        return "ide_config"

    def plan(self, context: InstallContext) -> PhasePlan:
        self._resolved_maps = resolve_template_maps(context.surfaces, context.vcs_provider)
        maps = self._resolved_maps
        pr = get_project_template_root()
        ow = context.mode is InstallMode.FRESH
        actions: list[PlannedAction] = []

        for sr, dr in sorted(maps.file_map.items()):
            if (pr / sr).is_file():
                actions.append(_file_action(dr, context.target / dr, ow, "surface"))
        for sr, dr in sorted(maps.common_file_map.items()):
            if (pr / sr).is_file():
                actions.append(_file_action(dr, context.target / dr, ow, "common"))
        for st, dt in maps.tree_list:
            actions.extend(_tree_actions(pr, st, dt, context.target, ow, "surface tree"))
        for st, dt in maps.vcs_tree_list:
            actions.extend(_tree_actions(pr, st, dt, context.target, ow, "VCS"))

        if context.mode is InstallMode.RECONFIGURE and context.existing_state:
            old = load_manifest_config(context.target).surfaces.enabled
            for rm in set(old) - set(context.surfaces):
                for dp in surface_template_dest_paths(rm):
                    actions.append(PlannedAction("delete", "", dp, f"remove {rm}"))

        return PhasePlan(phase_name=self.name, actions=actions)

    def execute(self, plan: PhasePlan, context: InstallContext) -> PhaseResult:
        result = PhaseResult(phase_name=self.name)
        maps = self._resolved_maps or resolve_template_maps(context.surfaces, context.vcs_provider)
        pr = get_project_template_root()
        import shutil

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
                copy_tree_for_mode(
                    sd,
                    context.target / dt,
                    context.target,
                    fresh=context.mode is InstallMode.FRESH,
                    created=result.created,
                    skipped=result.skipped,
                )

        if context.mode is InstallMode.RECONFIGURE and context.existing_state:
            old = load_manifest_config(context.target).surfaces.enabled
            for rm in set(old) - set(context.surfaces):
                deleted = remove_surface_templates(context.target, rm, context.surfaces)
                result.deleted.extend(str(p) for p in deleted)

        return result

    def verify(self, result: PhaseResult, context: InstallContext) -> PhaseVerdict:
        maps = self._resolved_maps or resolve_template_maps(context.surfaces, context.vcs_provider)
        errors = [
            f"Missing: {dr}"
            for _sr, dr in maps.file_map.items()
            if not (context.target / dr).exists()
        ]
        return PhaseVerdict(phase_name=self.name, passed=not errors, errors=errors)
