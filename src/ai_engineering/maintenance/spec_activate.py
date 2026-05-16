"""Activation flow for spec-scoped work planes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.maintenance.spec_reset import ensure_spec_buffer_files
from ai_engineering.state.work_plane import (
    active_work_plane_pointer_path,
    ensure_work_plane_artifacts,
    write_active_work_plane_pointer,
)


@dataclass
class SpecActivateResult:
    """Outcome of a spec work-plane activation."""

    specs_dir: Path
    pointer_enabled: bool = False
    spec_created: bool = False
    plan_created: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return True when activation finished without errors."""
        return not self.errors


def run_spec_activate(project_root: Path, specs_dir: Path) -> SpecActivateResult:
    """Activate a work plane and ensure its compatibility buffer files exist."""
    candidate = specs_dir if specs_dir.is_absolute() else project_root / specs_dir
    result = SpecActivateResult(specs_dir=candidate)

    try:
        candidate.resolve().relative_to(project_root.resolve())
    except ValueError:
        result.errors.append("Specs directory must stay inside the project root")
        return result

    try:
        candidate.mkdir(parents=True, exist_ok=True)
        result.spec_created, result.plan_created = ensure_spec_buffer_files(candidate)
        ensure_work_plane_artifacts(candidate)
        write_active_work_plane_pointer(project_root, candidate)
    except (OSError, ValueError) as exc:
        result.errors.append(f"Failed to activate spec work plane: {exc}")
        return result

    result.pointer_enabled = active_work_plane_pointer_path(project_root).exists()
    return result
