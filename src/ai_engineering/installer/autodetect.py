"""Auto-detection of project stacks, AI providers, IDEs, and VCS.

Scans a project root directory for known marker files and directories
to determine the technology stacks, AI provider configurations, IDE
integrations, and version control system in use.

Functions:
    detect_stacks     -- language/framework markers -> sorted stack list
    detect_ai_providers -- AI tool config markers -> sorted provider list
    detect_ides       -- IDE config directories -> sorted IDE list
    detect_vcs        -- delegate to vcs.factory -> provider string
    detect_all        -- aggregate all detections into DetectionResult
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.vcs.factory import detect_from_remote

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    """Aggregated auto-detection result for a project root."""

    stacks: list[str]
    providers: list[str]
    ides: list[str]
    vcs: str


# ---------------------------------------------------------------------------
# Stack detection
# ---------------------------------------------------------------------------

# Mapping: marker filename -> stack name(s).
# For glob-based markers (*.csproj, *.sln), see _GLOB_MARKERS below.
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

# Root-level glob patterns -> stack name.
_GLOB_MARKERS: dict[str, str] = {
    "*.csproj": "csharp",
    "*.sln": "csharp",
}


def detect_stacks(root: Path) -> list[str]:
    """Scan *root* for file markers and return a sorted list of stack names.

    Special rules:
    - ``package.json`` without ``tsconfig.json`` -> ``"javascript"``
    - ``tsconfig.json`` (with or without ``package.json``) -> ``"typescript"``
    - ``build.gradle.kts`` produces both ``"java"`` and ``"kotlin"``
    - ``*.csproj`` / ``*.sln`` use root-level glob (not recursive)
    """
    stacks: set[str] = set()

    # Fixed-name markers
    for filename, names in _FILE_MARKERS.items():
        if (root / filename).exists():
            stacks.update(names)

    # Glob markers (root-level only)
    for pattern, name in _GLOB_MARKERS.items():
        if any(root.glob(pattern)):
            stacks.add(name)

    # JavaScript / TypeScript special handling
    has_package_json = (root / "package.json").is_file()
    has_tsconfig = (root / "tsconfig.json").is_file()

    if has_tsconfig:
        stacks.add("typescript")
    elif has_package_json:
        stacks.add("javascript")

    return sorted(stacks)


# ---------------------------------------------------------------------------
# AI provider detection
# ---------------------------------------------------------------------------


def detect_ai_providers(root: Path) -> list[str]:
    """Detect AI coding assistants configured in *root*.

    Markers:
    - ``.claude/`` directory -> ``"claude_code"``
    - ``.github/copilot-instructions.md`` or ``.github/prompts/`` -> ``"github_copilot"``

    The ``.agents/`` directory is explicitly ignored (ambiguous provider).
    """
    providers: list[str] = []

    if (root / ".claude").is_dir():
        providers.append("claude_code")

    copilot_instructions = (root / ".github" / "copilot-instructions.md").is_file()
    copilot_prompts = (root / ".github" / "prompts").is_dir()
    if copilot_instructions or copilot_prompts:
        providers.append("github_copilot")

    return sorted(providers)


# ---------------------------------------------------------------------------
# IDE detection
# ---------------------------------------------------------------------------


def detect_ides(root: Path) -> list[str]:
    """Detect IDE configuration directories in *root*.

    Markers:
    - ``.vscode/`` -> ``"vscode"``
    - ``.idea/`` -> ``"jetbrains"``
    """
    ides: list[str] = []

    if (root / ".vscode").is_dir():
        ides.append("vscode")

    if (root / ".idea").is_dir():
        ides.append("jetbrains")

    return sorted(ides)


# ---------------------------------------------------------------------------
# VCS detection
# ---------------------------------------------------------------------------


def detect_vcs(root: Path) -> str:
    """Detect the VCS provider by delegating to ``detect_from_remote``.

    Returns ``"github"`` as fallback when detection raises any exception
    (e.g. git not installed, not a git repository).
    """
    try:
        return detect_from_remote(root)
    except Exception:
        logger.debug("VCS detection failed, falling back to github", exc_info=True)
        return "github"


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


def detect_all(root: Path) -> DetectionResult:
    """Run all detection functions and return an aggregated result."""
    return DetectionResult(
        stacks=detect_stacks(root),
        providers=detect_ai_providers(root),
        ides=detect_ides(root),
        vcs=detect_vcs(root),
    )
