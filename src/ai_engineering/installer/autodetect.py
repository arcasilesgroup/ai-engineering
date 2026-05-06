"""Auto-detection of project stacks, AI providers, IDEs, and VCS.

Scans a project root directory recursively for known marker files and
directories to determine the technology stacks, AI provider configurations,
IDE integrations, and version control system in use.

Uses a single-pass ``os.walk`` walker with exclusion pruning for efficiency.
AI provider detection remains root-level only by design.

Functions:
    detect_stacks     -- recursive markers -> popularity-ordered stack list
    detect_ai_providers -- root-level AI tool config -> sorted provider list
    detect_ides       -- recursive IDE config dirs -> popularity-ordered list
    detect_vcs        -- delegate to vcs.factory -> provider string
    detect_all        -- aggregate all detections into DetectionResult
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.vcs.factory import detect_from_remote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Popularity ordering (GitHub Octoverse 2025)
# ---------------------------------------------------------------------------

_STACK_POPULARITY: tuple[str, ...] = (
    "typescript",  # #1 Octoverse 2025
    "python",  # #2
    "javascript",  # #3
    "java",  # #4
    "csharp",  # #5
    "go",  # #6
    "php",  # #7
    "rust",  # #8
    "ruby",  # #9
    "kotlin",  # #10
    "swift",  # #11
    "dart",  # #12
    "elixir",  # #13
    "sql",  # utility
    "bash",  # utility
    "universal",  # meta — always last
)

_IDE_POPULARITY: tuple[str, ...] = (
    "vscode",  # ~74% market share
    "jetbrains",  # ~27%
    "cursor",  # growing
    "antigravity",  # niche
    "terminal",  # niche
)

_PROVIDER_POPULARITY: tuple[str, ...] = (
    "github-copilot",
    "claude-code",
    "gemini-cli",
    "codex",
)

_VCS_POPULARITY: tuple[str, ...] = (
    "github",
    "azure_devops",
)


def _order_by_popularity(items: Iterable[str], ranking: tuple[str, ...]) -> list[str]:
    """Sort *items* by *ranking* position; unknowns appended alphabetically."""
    item_set = dict.fromkeys(items)  # deduplicate, preserve insertion order
    rank_map = {name: idx for idx, name in enumerate(ranking)}
    sentinel = len(ranking)
    return sorted(item_set, key=lambda x: (rank_map.get(x, sentinel), x))


@dataclass
class DetectionResult:
    """Aggregated auto-detection result for a project root."""

    stacks: list[str]
    providers: list[str]
    ides: list[str]
    vcs: str


# ---------------------------------------------------------------------------
# Recursive walker
# ---------------------------------------------------------------------------

# Mapping: marker filename -> stack name(s).
# Note: package.json and tsconfig.json are handled separately for per-directory
# ts-overrides-js logic.
_FILE_MARKERS: dict[str, list[str]] = {
    "pyproject.toml": ["python"],
    "setup.py": ["python"],
    "setup.cfg": ["python"],
    "Pipfile": ["python"],
    "go.mod": ["go"],
    "Cargo.toml": ["rust"],
    "pom.xml": ["java"],
    "build.gradle": ["java"],
    "build.gradle.kts": ["java", "kotlin"],
    "Gemfile": ["ruby"],
    "pubspec.yaml": ["dart"],
    "mix.exs": ["elixir"],
    "Package.swift": ["swift"],
    "composer.json": ["php"],
}

_WALK_EXCLUDE: frozenset[str] = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        "vendor",
        ".git",
        "__pycache__",
        "build",
        "dist",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "target",
        ".gradle",
        "Pods",
        ".dart_tool",
        ".build",
    }
)

_CSHARP_EXTENSIONS: tuple[str, ...] = (".csproj", ".sln")

_IDE_DIR_MAP: dict[str, str] = {
    ".vscode": "vscode",
    ".idea": "jetbrains",
}


def _walk_markers(root: Path) -> tuple[set[str], set[str]]:
    """Single-pass recursive walk. Returns (stack_names, ide_names).

    Uses ``os.walk(followlinks=False)`` to avoid symlink loops.
    JS/TS detection is per-directory: tsconfig.json suppresses package.json
    within the same directory, but different subdirectories are independent.
    """
    stacks: set[str] = set()
    ides: set[str] = set()

    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # Prune excluded directories in-place
        dirnames[:] = [d for d in dirnames if d not in _WALK_EXCLUDE]

        # Check filenames against _FILE_MARKERS
        for fname in filenames:
            if fname in _FILE_MARKERS:
                stacks.update(_FILE_MARKERS[fname])
            if fname.endswith(_CSHARP_EXTENSIONS):
                stacks.add("csharp")

        # IDE markers: directory name
        dir_name = Path(dirpath).name
        ide = _IDE_DIR_MAP.get(dir_name)
        if ide:
            ides.add(ide)

        # JS/TS per-directory detection
        fset = set(filenames)
        if "tsconfig.json" in fset:
            stacks.add("typescript")
        elif "package.json" in fset:
            stacks.add("javascript")

    return stacks, ides


def detect_stacks(root: Path) -> list[str]:
    """Recursively scan *root* and return stacks in popularity order."""
    stacks, _ides = _walk_markers(root)
    return _order_by_popularity(stacks, _STACK_POPULARITY)


# ---------------------------------------------------------------------------
# AI provider detection (root-level only by design)
# ---------------------------------------------------------------------------


def detect_ai_providers(root: Path) -> list[str]:
    """Detect AI coding assistants configured in *root*.

    Root-level only — ``.claude/``, ``.github/``, and ``.gemini/`` are project-root markers.
    """
    providers: list[str] = []

    if (root / ".claude").is_dir():
        providers.append("claude-code")

    if (root / ".gemini").is_dir() or (root / "GEMINI.md").is_file():
        providers.append("gemini-cli")

    copilot_instructions = (root / ".github" / "copilot-instructions.md").is_file()
    copilot_skills = (root / ".github" / "skills").is_dir()
    if copilot_instructions or copilot_skills:
        providers.append("github-copilot")

    codex_instruction_file = (root / "AGENTS.md").is_file()
    codex_tree = (root / ".codex").is_dir()
    if codex_instruction_file or codex_tree:
        providers.append("codex")

    return sorted(providers)


# ---------------------------------------------------------------------------
# IDE detection
# ---------------------------------------------------------------------------


def detect_ides(root: Path) -> list[str]:
    """Recursively scan *root* for IDE config directories, popularity-ordered."""
    _stacks, ides = _walk_markers(root)
    return _order_by_popularity(ides, _IDE_POPULARITY)


# ---------------------------------------------------------------------------
# VCS detection
# ---------------------------------------------------------------------------


def detect_vcs(root: Path) -> str:
    """Detect the VCS provider by delegating to ``detect_from_remote``.

    Returns ``""`` (empty string) when detection fails. The empty value
    signals the wizard to show no pre-selection.
    ``detect_from_remote()`` in ``vcs/factory.py`` is NOT modified — it
    still returns ``"github"`` as its own fallback. This wrapper intercepts
    exceptions to return ``""`` instead.
    """
    try:
        return detect_from_remote(root)
    except Exception:
        logger.debug("VCS detection failed, returning empty", exc_info=True)
        return ""


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


def detect_all(root: Path) -> DetectionResult:
    """Run all detection functions and return an aggregated result.

    Uses a single walker pass for stacks + IDEs to avoid double traversal.
    AI provider detection remains root-level only.
    """
    raw_stacks, raw_ides = _walk_markers(root)
    return DetectionResult(
        stacks=_order_by_popularity(raw_stacks, _STACK_POPULARITY),
        providers=detect_ai_providers(root),
        ides=_order_by_popularity(raw_ides, _IDE_POPULARITY),
        vcs=detect_vcs(root),
    )
