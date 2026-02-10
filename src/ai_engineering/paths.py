"""Path utilities for ai-engineering.

Resolves the target project root and governance directory paths
used throughout the CLI and service layers.
"""

from __future__ import annotations

from pathlib import Path


def resolve_project_root(target: Path | None = None) -> Path:
    """Resolve the target project root directory.

    If no explicit target is provided, uses the current working directory.

    Args:
        target: Explicit project root, or None to use cwd.

    Returns:
        Resolved absolute path to the project root.

    Raises:
        FileNotFoundError: If the resolved path does not exist.
    """
    root = (target or Path.cwd()).resolve()
    if not root.is_dir():
        msg = f"Project root not found: {root}"
        raise FileNotFoundError(msg)
    return root


def ai_engineering_dir(project_root: Path) -> Path:
    """Return the ``.ai-engineering`` directory for a project.

    Args:
        project_root: Root directory of the target project.

    Returns:
        Path to the ``.ai-engineering`` directory.
    """
    return project_root / ".ai-engineering"


def state_dir(project_root: Path) -> Path:
    """Return the ``state`` directory for a project.

    Args:
        project_root: Root directory of the target project.

    Returns:
        Path to the ``.ai-engineering/state`` directory.
    """
    return project_root / ".ai-engineering" / "state"
