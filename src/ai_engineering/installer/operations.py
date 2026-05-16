"""Stack and Surface add/remove/list operations for ai-engineering.

spec-133 D-133-16 hard-cut: ``providers.ides`` and ``ai_providers.enabled``
were deleted. The unified ``Surface`` primitive (domain) replaces both
axes. CRUD here operates on ``surfaces.enabled`` against the closed
:data:`ai_engineering.domain.surface.SURFACE_IDS` enum.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.loader import load_manifest_config, update_manifest_field
from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.domain.surface import SURFACE_IDS
from ai_engineering.state.observability import emit_framework_operation

from .templates import TEMPLATES_ROOT, copy_project_templates, remove_surface_templates


class InstallerError(Exception):
    """Raised when an installer operation cannot proceed."""


def get_available_stacks() -> list[str]:
    """Return the list of stack names that have bundled overrides.

    Scans the ``overrides/`` template directory for per-stack
    subdirectories (spec-128 D-128-03) and returns their names as valid
    stack identifiers. The ``_shared/`` sibling is excluded — it carries
    cross-stack conventions, not a stack.

    Returns:
        Sorted list of available stack names (e.g. ``["python", "typescript"]``).
    """
    overrides_dir = TEMPLATES_ROOT / ".ai-engineering" / "overrides"
    if not overrides_dir.is_dir():
        return []
    return sorted(p.name for p in overrides_dir.iterdir() if p.is_dir() and p.name != "_shared")


def get_available_surfaces() -> list[str]:
    """Return the list of recognised Surface identifiers (closed enum).

    The source of truth is :data:`ai_engineering.domain.surface.SURFACE_IDS`.
    """
    return sorted(SURFACE_IDS)


def _ensure_framework_install(target: Path) -> None:
    """Ensure the framework is installed in the target project root."""
    ai_eng_dir = target / ".ai-engineering"
    if not ai_eng_dir.is_dir():
        msg = f"Framework not installed at {target}. Run 'ai-eng install' first."
        raise InstallerError(msg)


def _load_config(target: Path) -> ManifestConfig:
    """Load the manifest config from manifest.yml.

    Args:
        target: Root directory of the target project.

    Returns:
        Parsed ManifestConfig.

    Raises:
        InstallerError: If the ``.ai-engineering/`` directory does not exist.
    """
    ai_eng_dir = target / ".ai-engineering"
    if not ai_eng_dir.is_dir():
        msg = f"Framework not installed at {target}. Run 'ai-eng install' first."
        raise InstallerError(msg)
    return load_manifest_config(target)


def _log_operation(
    project_root: Path,
    *,
    operation: str,
    detail: str,
) -> None:
    """Emit a canonical framework operation event."""
    emit_framework_operation(
        project_root,
        operation=operation,
        component="installer.operations",
        source="cli",
        metadata={"message": detail},
    )


def add_stack(target: Path, stack: str) -> ManifestConfig:
    """Add a stack to the manifest config.

    Args:
        target: Root directory of the target project.
        stack: Stack identifier to add (e.g., ``"python"``).

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed, stack already exists,
            or stack name is not recognised.
    """
    available = get_available_stacks()
    if available and stack not in available:
        msg = f"Unknown stack '{stack}'. Available stacks: {', '.join(available)}"
        raise InstallerError(msg)

    _ensure_framework_install(target)
    config = _load_config(target)

    if stack in config.providers.stacks:
        msg = f"Stack '{stack}' is already installed."
        raise InstallerError(msg)

    new_stacks = [*config.providers.stacks, stack]
    update_manifest_field(target, "providers.stacks", new_stacks)
    _log_operation(target, operation="stack-add", detail=f"added stack: {stack}")

    return load_manifest_config(target)


def remove_stack(target: Path, stack: str) -> ManifestConfig:
    """Remove a stack from the manifest config.

    Args:
        target: Root directory of the target project.
        stack: Stack identifier to remove.

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed or stack not found.
    """
    _ensure_framework_install(target)
    config = _load_config(target)

    if stack not in config.providers.stacks:
        msg = f"Stack '{stack}' is not installed."
        raise InstallerError(msg)

    new_stacks = [s for s in config.providers.stacks if s != stack]
    update_manifest_field(target, "providers.stacks", new_stacks)
    _log_operation(target, operation="stack-remove", detail=f"removed stack: {stack}")

    return load_manifest_config(target)


def list_status(target: Path) -> ManifestConfig:
    """Load and return the current manifest config.

    Args:
        target: Root directory of the target project.

    Returns:
        Current ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed.
    """
    return _load_config(target)


# ---------------------------------------------------------------------------
# Surface operations (replaces legacy add_ide / add_provider).
# ---------------------------------------------------------------------------


def add_surface(target: Path, surface: str) -> ManifestConfig:
    """Add a Surface to the manifest config and copy its templates.

    A Surface fuses AI Provider + IDE Integration into one capability
    matrix (spec-133 D-133-16). Allowed values live in
    :data:`ai_engineering.domain.surface.SURFACE_IDS`.

    Args:
        target: Root directory of the target project.
        surface: Surface identifier to add (e.g., ``"github-copilot"``).

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed, the surface is
            already enabled, or the identifier is not recognised.
    """
    if surface not in SURFACE_IDS:
        msg = f"Unknown surface '{surface}'. Known: {', '.join(get_available_surfaces())}."
        raise InstallerError(msg)

    _ensure_framework_install(target)
    config = _load_config(target)

    if surface in config.surfaces.enabled:
        msg = f"Surface '{surface}' is already enabled."
        raise InstallerError(msg)

    copy_project_templates(target, surfaces=[surface])

    new_enabled = [*config.surfaces.enabled, surface]
    update_manifest_field(target, "surfaces.enabled", new_enabled)

    _log_operation(target, operation="surface-add", detail=f"added surface: {surface}")

    return load_manifest_config(target)


def remove_surface(target: Path, surface: str) -> ManifestConfig:
    """Remove a Surface from the manifest config and delete its templates.

    The last remaining Surface cannot be removed — every install must keep
    at least one active surface so the framework has somewhere to render
    its instruction files.

    Args:
        target: Root directory of the target project.
        surface: Surface identifier to remove.

    Returns:
        Updated ManifestConfig.

    Raises:
        InstallerError: If the framework is not installed, the surface is
            not enabled, or it is the last remaining surface.
    """
    _ensure_framework_install(target)
    config = _load_config(target)

    enabled = list(config.surfaces.enabled)
    if surface not in enabled:
        msg = f"Surface '{surface}' is not enabled."
        raise InstallerError(msg)

    remaining = [s for s in enabled if s != surface]
    if not remaining:
        msg = "Cannot remove the last Surface — every install must keep at least one."
        raise InstallerError(msg)

    remove_surface_templates(target, surface, remaining)
    update_manifest_field(target, "surfaces.enabled", remaining)

    _log_operation(
        target,
        operation="surface-remove",
        detail=f"removed surface: {surface}",
    )

    return load_manifest_config(target)
