"""Filesystem path helpers for ai-engineering."""

from __future__ import annotations

from pathlib import Path


AI_ENGINEERING_DIR = ".ai-engineering"


def repo_root(start: Path | None = None) -> Path:
    """Return repository root from current or provided start directory."""
    current = (start or Path.cwd()).resolve()
    if (current / ".git").exists():
        return current
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    raise FileNotFoundError("Not a git repository")


def ai_engineering_root(root: Path) -> Path:
    """Return `.ai-engineering` directory path."""
    return root / AI_ENGINEERING_DIR


def state_dir(root: Path) -> Path:
    """Return state directory path."""
    return ai_engineering_root(root) / "state"
