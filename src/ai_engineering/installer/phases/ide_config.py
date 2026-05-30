"""Surface config phase -- deploy Surface-specific templates.

Copies Surface agent/skill trees and instruction files for each selected
Surface. In RECONFIGURE mode, removed Surfaces have their files cleaned
up. spec-133 D-133-16: ``Surface`` fuses AI Provider + IDE Integration
into one axis; the legacy ide/provider phases collapsed here.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.installer.scope import GuidanceSentinel
from ai_engineering.installer.scope import dest as scope_dest
from ai_engineering.installer.templates import (
    copy_file_if_missing,
    copy_tree_for_mode,
    get_project_template_root,
    remove_surface_templates,
    resolve_template_maps,
    surface_template_dest_paths,
)

from . import InstallContext, InstallMode, PhasePlan, PhaseResult, PhaseVerdict, PlannedAction

# spec-133 common files (CONSTITUTION.md, .gitleaks.toml, .semgrep.yml) are not
# owned by any single surface; in global scope they ride with the brain root so
# they never pollute the operator's home root. ``None`` here means "use the
# claude-code/brain home root" via the default surface below.
_COMMON_SCOPE_SURFACE = "claude-code"


def _build_dest_surface_index(surfaces: list[str]) -> dict[str, str]:
    """Map each surface-owned destination (file or tree prefix) to its surface.

    Used by global scope to route every relative destination through the
    correct per-surface home root. File destinations map exactly; tree
    destinations map by their root segment so nested files inherit the owner.
    """
    index: dict[str, str] = {}
    for surface in surfaces:
        maps = resolve_template_maps([surface])
        for dest_rel in maps.file_map.values():
            index[dest_rel] = surface
        for _src_tree, dest_tree in maps.tree_list:
            index[dest_tree] = surface
    return index


def _owning_surface(dest_rel: str, index: dict[str, str]) -> str:
    """Return the surface that owns *dest_rel* (exact file or tree-prefix match)."""
    if dest_rel in index:
        return index[dest_rel]
    for owned, surface in index.items():
        if dest_rel == owned or dest_rel.startswith(f"{owned}/"):
            return surface
    return _COMMON_SCOPE_SURFACE


def _file_action(dest_rel: str, dest: Path, overwrite: bool, tag: str) -> PlannedAction:
    if overwrite:
        return PlannedAction("overwrite", "", dest_rel, f"FRESH: overwrite {tag}")
    if dest.exists():
        return PlannedAction("skip", "", dest_rel, f"{tag} exists")
    return PlannedAction("create", "", dest_rel, f"new {tag}")


def _tree_actions(
    phase: IdeConfigPhase,
    context: InstallContext,
    root: Path,
    src_tree: str,
    dest_tree: str,
    ow: bool,
    tag: str,
):
    src_dir = root / src_tree
    if not src_dir.is_dir():
        return
    for f in sorted(src_dir.rglob("*")):
        if not f.is_file():
            continue
        dr = f"{dest_tree}/{f.relative_to(src_dir).as_posix()}"
        resolved = phase._resolve_dest(context, dr)
        if resolved is None:
            continue  # guidance surface -- no file written
        yield _file_action(dr, resolved, ow, tag)


class IdeConfigPhase:
    """Deploy Surface-specific configuration files (Surfaces x VCS templates)."""

    def __init__(self) -> None:
        self._resolved_maps = None
        self._dest_index: dict[str, str] | None = None
        # Guidance sentinels gathered for surfaces with no home destination
        # (cursor / copilot under --global). The CLI surface prints these.
        self.guidance: list[GuidanceSentinel] = []

    @property
    def name(self) -> str:
        return "ide_config"

    def _resolve_dest(self, context: InstallContext, dest_rel: str) -> Path | None:
        """Resolve *dest_rel* for the active scope, or ``None`` for guidance.

        Local scope is always repo-rooted. Global scope routes each destination
        through its owning surface's home root; cursor/copilot have no home file
        and return ``None`` after recording a one-time guidance sentinel.
        """
        if context.scope != "global":
            return context.target / dest_rel
        if self._dest_index is None:
            self._dest_index = _build_dest_surface_index(context.surfaces)
        surface = _owning_surface(dest_rel, self._dest_index)
        resolved = scope_dest(surface, context.scope, context.target, dest_rel)
        if isinstance(resolved, GuidanceSentinel):
            if all(g.surface != resolved.surface for g in self.guidance):
                self.guidance.append(resolved)
            return None
        return resolved

    def plan(self, context: InstallContext) -> PhasePlan:
        self._resolved_maps = resolve_template_maps(context.surfaces, context.vcs_provider)
        maps = self._resolved_maps
        pr = get_project_template_root()
        ow = context.mode is InstallMode.FRESH
        actions: list[PlannedAction] = []

        for sr, dr in sorted(maps.file_map.items()):
            if (pr / sr).is_file():
                resolved = self._resolve_dest(context, dr)
                if resolved is not None:
                    actions.append(_file_action(dr, resolved, ow, "surface"))
        for sr, dr in sorted(maps.common_file_map.items()):
            if (pr / sr).is_file():
                resolved = self._resolve_dest(context, dr)
                if resolved is not None:
                    actions.append(_file_action(dr, resolved, ow, "common"))
        for st, dt in maps.tree_list:
            actions.extend(_tree_actions(self, context, pr, st, dt, ow, "surface tree"))
        for st, dt in maps.vcs_tree_list:
            actions.extend(_tree_actions(self, context, pr, st, dt, ow, "VCS"))

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
            src = pr / sr
            if not src.is_file():
                continue
            dest = self._resolve_dest(context, dr)
            if dest is None:
                continue  # guidance surface -- nothing written
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
            if not sd.is_dir():
                continue
            dest_root = self._resolve_dest(context, dt)
            if dest_root is None:
                continue  # guidance surface -- tree not materialized to home
            # Relative-path tracking root: strip the dest-tree suffix off the
            # resolved absolute dest so created/skipped entries stay relative
            # to the scope root (repo root for local, home prefix for global).
            tracking_root = dest_root
            for _ in Path(dt).parts:
                tracking_root = tracking_root.parent
            copy_tree_for_mode(
                sd,
                dest_root,
                tracking_root,
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
        errors: list[str] = []
        for _sr, dr in maps.file_map.items():
            resolved = self._resolve_dest(context, dr)
            if resolved is None:
                continue  # guidance surface -- no file expected
            if not resolved.exists():
                errors.append(f"Missing: {dr}")
        return PhaseVerdict(phase_name=self.name, passed=not errors, errors=errors)
