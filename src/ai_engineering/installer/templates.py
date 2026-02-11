"""Template discovery and create-only file operations.

Provides:
- Resolution of bundled template paths (.ai-engineering/ and project/).
- Create-only copy semantics: existing files are never overwritten.
- Directory tree copying with reporting of created and skipped files.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

TEMPLATES_ROOT: Path = Path(__file__).resolve().parent.parent / "templates"
"""Root directory containing bundled template trees."""

AI_ENGINEERING_TEMPLATES: str = ".ai-engineering"
"""Subdirectory name for governance framework templates."""

PROJECT_TEMPLATES: str = "project"
"""Subdirectory name for IDE agent configuration templates."""

# Mapping of project template files to their target paths relative to the
# target project root.  Keys are relative paths inside the ``project/``
# template directory; values are destination paths in the target project.
_PROJECT_TEMPLATE_MAP: dict[str, str] = {
    "AGENTS.md": "AGENTS.md",
    "CLAUDE.md": "CLAUDE.md",
    "codex.md": "codex.md",
    "copilot-instructions.md": ".github/copilot-instructions.md",
    "copilot/code-generation.md": ".github/copilot/code-generation.md",
    "copilot/code-review.md": ".github/copilot/code-review.md",
    "copilot/commit-message.md": ".github/copilot/commit-message.md",
    "copilot/test-generation.md": ".github/copilot/test-generation.md",
    "instructions/python.instructions.md": ".github/instructions/python.instructions.md",
    "instructions/testing.instructions.md": ".github/instructions/testing.instructions.md",
    "instructions/markdown.instructions.md": ".github/instructions/markdown.instructions.md",
}

_PROJECT_TEMPLATE_TREES: list[tuple[str, str]] = [
    (".claude/commands", ".claude/commands"),
]


@dataclass
class CopyResult:
    """Tracks files created and skipped during a copy operation."""

    created: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)


def get_ai_engineering_template_root() -> Path:
    """Return the path to the bundled ``.ai-engineering/`` template tree.

    Raises:
        FileNotFoundError: If the template directory is missing.
    """
    root = TEMPLATES_ROOT / AI_ENGINEERING_TEMPLATES
    if not root.is_dir():
        msg = f"Template directory not found: {root}"
        raise FileNotFoundError(msg)
    return root


def get_project_template_root() -> Path:
    """Return the path to the bundled ``project/`` template tree.

    Raises:
        FileNotFoundError: If the template directory is missing.
    """
    root = TEMPLATES_ROOT / PROJECT_TEMPLATES
    if not root.is_dir():
        msg = f"Template directory not found: {root}"
        raise FileNotFoundError(msg)
    return root


def copy_file_if_missing(src: Path, dest: Path) -> bool:
    """Copy a single file only if the destination does not already exist.

    Creates parent directories as needed.

    Args:
        src: Source file path.
        dest: Destination file path.

    Returns:
        True if the file was created, False if it was skipped.
    """
    if dest.exists():
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


def copy_template_tree(src_root: Path, dest_root: Path) -> CopyResult:
    """Recursively copy a template directory tree with create-only semantics.

    Walks *src_root* and copies each file to the corresponding relative path
    under *dest_root*.  Existing files are never overwritten.

    Args:
        src_root: Root of the source template tree.
        dest_root: Root of the destination tree.

    Returns:
        CopyResult with lists of created and skipped paths.
    """
    result = CopyResult()
    for src_file in sorted(src_root.rglob("*")):
        if not src_file.is_file():
            continue
        relative = src_file.relative_to(src_root)
        dest_file = dest_root / relative
        if copy_file_if_missing(src_file, dest_file):
            result.created.append(dest_file)
        else:
            result.skipped.append(dest_file)
    return result


def copy_project_templates(target: Path) -> CopyResult:
    """Copy project-level templates to the target project root.

    Maps bundled ``project/`` template files to their intended locations
    in the target project (e.g., ``copilot/`` → ``.github/copilot/``).
    Also copies entire directory trees defined in ``_PROJECT_TEMPLATE_TREES``.

    Args:
        target: Target project root directory.

    Returns:
        CopyResult with lists of created and skipped paths.
    """
    project_root = get_project_template_root()
    result = CopyResult()
    for src_relative, dest_relative in sorted(_PROJECT_TEMPLATE_MAP.items()):
        src_file = project_root / src_relative
        if not src_file.is_file():
            continue
        dest_file = target / dest_relative
        if copy_file_if_missing(src_file, dest_file):
            result.created.append(dest_file)
        else:
            result.skipped.append(dest_file)

    for src_tree, dest_tree in _PROJECT_TEMPLATE_TREES:
        src_dir = project_root / src_tree
        if not src_dir.is_dir():
            continue
        tree_result = copy_template_tree(src_dir, target / dest_tree)
        result.created.extend(tree_result.created)
        result.skipped.extend(tree_result.skipped)

    return result
