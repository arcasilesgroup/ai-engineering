"""Path utilities for AI Engineering Framework."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_package_root() -> Path:
    """Get the root directory of the ai_engineering package."""
    return Path(__file__).parent.parent


def get_templates_dir() -> Path:
    """Get the templates directory within the package."""
    return get_package_root() / "templates"


def find_ai_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the .ai/ directory starting from the given path and searching upward.

    Args:
        start_path: Starting directory. Defaults to current working directory.

    Returns:
        Path to .ai/ directory if found, None otherwise.
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Search upward through parent directories
    while current != current.parent:
        ai_dir = current / ".ai"
        if ai_dir.is_dir():
            return ai_dir
        current = current.parent

    # Check root directory
    ai_dir = current / ".ai"
    if ai_dir.is_dir():
        return ai_dir

    return None


def find_repo_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find the repository root (containing .git or .ai) starting from the given path.

    Args:
        start_path: Starting directory. Defaults to current working directory.

    Returns:
        Path to repository root if found, None otherwise.
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    # Search upward through parent directories
    while current != current.parent:
        # Check for common root indicators
        if (current / ".git").exists() or (current / ".ai").exists():
            return current
        current = current.parent

    # Check root directory
    if (current / ".git").exists() or (current / ".ai").exists():
        return current

    return None


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory.

    Returns:
        The path (for chaining).
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_relative_path(path: Path, base: Path) -> str:
    """
    Get a relative path string, handling cases where path is not under base.

    Args:
        path: The path to convert.
        base: The base path.

    Returns:
        Relative path string or absolute path if not under base.
    """
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)
