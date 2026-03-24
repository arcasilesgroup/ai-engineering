"""Template discovery and create-only file operations.

Provides:
- Resolution of bundled template paths (.ai-engineering/ and project/).
- Create-only copy semantics: existing files are never overwritten.
- Directory tree copying with reporting of created and skipped files.
- Provider-aware template selection for AI coding assistants.
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

# ---------------------------------------------------------------------------
# Provider-specific template maps
# ---------------------------------------------------------------------------

# Each provider maps source template paths → destination paths in the target
# project.  No shared files — each provider owns its files exclusively.
# AGENTS.md is used by multiple providers but deduplication is handled at copy time.

_PROVIDER_FILE_MAPS: dict[str, dict[str, str]] = {
    "claude_code": {
        "CLAUDE.md": "CLAUDE.md",
    },
    "github_copilot": {
        "AGENTS.md": "AGENTS.md",
        "copilot-instructions.md": ".github/copilot-instructions.md",
    },
    "gemini": {
        "AGENTS.md": "AGENTS.md",
    },
    "codex": {
        "AGENTS.md": "AGENTS.md",
    },
}

# Files deployed regardless of AI provider (security, quality tooling).
_COMMON_FILE_MAPS: dict[str, str] = {
    ".gitleaks.toml": ".gitleaks.toml",
    ".semgrep.yml": ".semgrep.yml",
}

_PROVIDER_TREE_MAPS: dict[str, list[tuple[str, str]]] = {
    "claude_code": [
        (".claude", ".claude"),
    ],
    "github_copilot": [
        ("prompts", ".github/prompts"),
        ("agents", ".github/agents"),
        ("instructions", ".github/instructions"),
    ],
    "gemini": [
        (".agents", ".agents"),
    ],
    "codex": [
        (".agents", ".agents"),
    ],
}

# VCS-platform-specific templates (independent of AI provider).
# When a VCS provider is specified, these trees are also copied.
# Common templates copied for ALL providers (observability hooks).
_COMMON_TREE_MAPS: list[tuple[str, str]] = [
    ("scripts/hooks", "scripts/hooks"),
]

# VCS-platform-specific templates (independent of AI provider).
# When a VCS provider is specified, these trees are also copied.
_VCS_TEMPLATE_TREES: dict[str, list[tuple[str, str]]] = {
    "github": [
        ("github_templates", ".github"),
    ],
    "azure_devops": [],
}


@dataclass
class ResolvedTemplateMaps:
    """Complete set of template maps for a given configuration."""

    file_map: dict[str, str]
    tree_list: list[tuple[str, str]]
    common_file_map: dict[str, str]
    common_tree_list: list[tuple[str, str]]
    vcs_tree_list: list[tuple[str, str]]


def resolve_template_maps(
    providers: list[str] | None = None,
    vcs_provider: str | None = None,
) -> ResolvedTemplateMaps:
    """Resolve the complete set of template maps for a given configuration.

    This is the public API for determining which templates should be installed.
    Used by the installer, updater, and phase pipeline.

    Args:
        providers: AI provider identifiers, or None for all providers.
        vcs_provider: VCS platform identifier (e.g., ``"github"``).

    Returns:
        ResolvedTemplateMaps with all file and tree maps.
    """
    file_map, tree_list = _resolve_provider_maps(providers)
    vcs_trees = list(_VCS_TEMPLATE_TREES.get(vcs_provider or "", []))
    return ResolvedTemplateMaps(
        file_map=file_map,
        tree_list=tree_list,
        common_file_map=dict(_COMMON_FILE_MAPS),
        common_tree_list=list(_COMMON_TREE_MAPS),
        vcs_tree_list=vcs_trees,
    )


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


def copy_tree_for_mode(
    src_dir: Path,
    dest_dir: Path,
    target_root: Path,
    *,
    fresh: bool,
    created: list[str],
    skipped: list[str],
) -> None:
    """Copy a template tree using FRESH (overwrite) or create-only semantics.

    All paths appended to *created* and *skipped* are relative to *target_root*.

    Args:
        src_dir: Source directory to copy from.
        dest_dir: Destination directory to copy to.
        target_root: Project root for computing relative paths.
        fresh: When True, overwrite existing files (FRESH mode).
        created: List to append created relative paths to.
        skipped: List to append skipped relative paths to.
    """
    if fresh:
        for f in sorted(src_dir.rglob("*")):
            if not f.is_file():
                continue
            d = dest_dir / f.relative_to(src_dir)
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, d)
            created.append(str(d.relative_to(target_root)))
    else:
        tr = copy_template_tree(src_dir, dest_dir)
        created.extend(str(p.relative_to(target_root)) for p in tr.created)
        skipped.extend(str(p.relative_to(target_root)) for p in tr.skipped)


def copy_template_tree(
    src_root: Path,
    dest_root: Path,
    *,
    exclude: list[str] | None = None,
) -> CopyResult:
    """Recursively copy a template directory tree with create-only semantics.

    Walks *src_root* and copies each file to the corresponding relative path
    under *dest_root*.  Existing files are never overwritten.

    Args:
        src_root: Root of the source template tree.
        dest_root: Root of the destination tree.
        exclude: Optional list of path prefixes to skip (e.g., ``["agents/", "skills/"]``).

    Returns:
        CopyResult with lists of created and skipped paths.
    """
    result = CopyResult()
    for src_file in sorted(src_root.rglob("*")):
        if not src_file.is_file():
            continue
        relative = src_file.relative_to(src_root)
        if exclude and any(relative.as_posix().startswith(e) for e in exclude):
            continue
        dest_file = dest_root / relative
        if copy_file_if_missing(src_file, dest_file):
            result.created.append(dest_file)
        else:
            result.skipped.append(dest_file)
    return result


def _resolve_provider_maps(
    providers: list[str] | None,
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    """Merge file maps and tree maps for the given providers.

    When *providers* is ``None``, returns the union of all provider maps.
    Otherwise returns only the union of maps for the requested providers,
    deduplicating destination paths.

    Returns:
        Tuple of (file_map, tree_list).
    """
    if providers is None:
        providers = list(_PROVIDER_FILE_MAPS.keys())

    file_map: dict[str, str] = {}
    tree_list: list[tuple[str, str]] = []
    seen_trees: set[tuple[str, str]] = set()

    for prov in providers:
        for src, dst in _PROVIDER_FILE_MAPS.get(prov, {}).items():
            if src not in file_map:
                file_map[src] = dst
        for entry in _PROVIDER_TREE_MAPS.get(prov, []):
            if entry not in seen_trees:
                tree_list.append(entry)
                seen_trees.add(entry)

    return file_map, tree_list


def copy_project_templates(
    target: Path,
    *,
    providers: list[str] | None = None,
    vcs_provider: str | None = None,
) -> CopyResult:
    """Copy project-level templates to the target project root.

    Maps bundled ``project/`` template files to their intended locations
    in the target project (e.g., ``copilot/`` → ``.github/copilot/``).
    Also copies entire directory trees defined per provider.

    When *providers* is ``None``, copies **all** templates (backward compat
    for the updater).  Otherwise copies only templates for the requested
    providers, deduplicating shared files like ``AGENTS.md``.

    When *vcs_provider* is set, also copies VCS-platform-specific templates
    (e.g., GitHub issue/PR templates).

    Args:
        target: Target project root directory.
        providers: List of AI provider identifiers, or None for all.
        vcs_provider: VCS platform identifier (e.g., ``"github"``).

    Returns:
        CopyResult with lists of created and skipped paths.
    """
    project_root = get_project_template_root()
    file_map, tree_list = _resolve_provider_maps(providers)
    result = CopyResult()

    for src_relative, dest_relative in sorted(file_map.items()):
        src_file = project_root / src_relative
        if not src_file.is_file():
            continue
        dest_file = target / dest_relative
        if copy_file_if_missing(src_file, dest_file):
            result.created.append(dest_file)
        else:
            result.skipped.append(dest_file)

    for src_tree, dest_tree in tree_list:
        src_dir = project_root / src_tree
        if not src_dir.is_dir():
            continue
        tree_result = copy_template_tree(src_dir, target / dest_tree)
        result.created.extend(tree_result.created)
        result.skipped.extend(tree_result.skipped)

    # Common file templates (security/quality — all providers)
    for src_relative, dest_relative in sorted(_COMMON_FILE_MAPS.items()):
        src_file = project_root / src_relative
        if not src_file.is_file():
            continue
        dest_file = target / dest_relative
        if copy_file_if_missing(src_file, dest_file):
            result.created.append(dest_file)
        else:
            result.skipped.append(dest_file)

    # Common tree templates (observability hooks — all providers)
    for src_tree, dest_tree in _COMMON_TREE_MAPS:
        src_dir = project_root / src_tree
        if not src_dir.is_dir():
            continue
        tree_result = copy_template_tree(src_dir, target / dest_tree)
        result.created.extend(tree_result.created)
        result.skipped.extend(tree_result.skipped)

    # VCS-platform-specific templates
    if vcs_provider:
        for src_tree, dest_tree in _VCS_TEMPLATE_TREES.get(vcs_provider, []):
            src_dir = project_root / src_tree
            if not src_dir.is_dir():
                continue
            tree_result = copy_template_tree(src_dir, target / dest_tree)
            result.created.extend(tree_result.created)
            result.skipped.extend(tree_result.skipped)

    return result


def provider_template_dest_paths(provider: str) -> list[str]:
    """Return the destination paths that a provider would install.

    Used by ``remove_provider_templates`` to know which files to clean up.

    Args:
        provider: AI provider identifier.

    Returns:
        List of destination paths relative to the project root.
    """
    paths: list[str] = []
    for _src, dst in _PROVIDER_FILE_MAPS.get(provider, {}).items():
        paths.append(dst)
    # Tree destinations are directory roots; files inside are enumerated at runtime
    for _src_tree, dest_tree in _PROVIDER_TREE_MAPS.get(provider, []):
        paths.append(dest_tree)
    return paths


def _dest_path_used_by_other_providers(
    dest_path: str,
    provider: str,
    active_providers: list[str],
) -> bool:
    """Check if a destination path is needed by another active provider.

    Args:
        dest_path: The destination path to check.
        provider: The provider being removed.
        active_providers: Currently active providers.

    Returns:
        True if another active provider also maps to this destination path.
    """
    for other in active_providers:
        if other == provider:
            continue
        other_files = _PROVIDER_FILE_MAPS.get(other, {})
        if dest_path in other_files.values():
            return True
        for _src_tree, dest_tree in _PROVIDER_TREE_MAPS.get(other, []):
            if dest_path == dest_tree:
                return True
    return False


def remove_provider_templates(
    target: Path,
    provider: str,
    active_providers: list[str],
) -> list[Path]:
    """Remove templates installed by a provider.

    Does NOT remove files that are still needed by another active provider
    (e.g., AGENTS.md shared between github_copilot, gemini, and codex).

    Args:
        target: Target project root directory.
        provider: The provider being removed.
        active_providers: Providers that will remain active after removal.

    Returns:
        List of paths that were deleted.
    """
    deleted: list[Path] = []

    for _src, dst in _PROVIDER_FILE_MAPS.get(provider, {}).items():
        if _dest_path_used_by_other_providers(dst, provider, active_providers):
            continue
        path = target / dst
        if path.is_file():
            path.unlink()
            deleted.append(path)

    for _src_tree, dest_tree in _PROVIDER_TREE_MAPS.get(provider, []):
        if _dest_path_used_by_other_providers(dest_tree, provider, active_providers):
            continue
        tree_path = target / dest_tree
        if tree_path.is_dir():
            for f in sorted(tree_path.rglob("*"), reverse=True):
                if f.is_file():
                    f.unlink()
                    deleted.append(f)
            # Remove empty directories
            for d in sorted(tree_path.rglob("*"), reverse=True):
                if d.is_dir() and not any(d.iterdir()):
                    d.rmdir()
            if tree_path.is_dir() and not any(tree_path.iterdir()):
                tree_path.rmdir()

    return deleted
