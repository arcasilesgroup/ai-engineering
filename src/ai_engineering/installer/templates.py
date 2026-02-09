"""Template synchronization for installer bootstrap."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.paths import template_root


PROJECT_TEMPLATE_MAPPINGS: tuple[tuple[str, str], ...] = (
    ("project/CLAUDE.md", "CLAUDE.md"),
    ("project/codex.md", "codex.md"),
    ("project/copilot-instructions.md", ".github/copilot-instructions.md"),
    ("project/copilot/code-generation.md", ".github/copilot/code-generation.md"),
    ("project/copilot/test-generation.md", ".github/copilot/test-generation.md"),
    ("project/copilot/code-review.md", ".github/copilot/code-review.md"),
    ("project/copilot/commit-message.md", ".github/copilot/commit-message.md"),
)

PROJECT_TEMPLATE_BY_IDE: dict[str, list[tuple[str, str]]] = {
    "claude": [("project/CLAUDE.md", "CLAUDE.md")],
    "codex": [("project/codex.md", "codex.md")],
    "copilot": [
        ("project/copilot-instructions.md", ".github/copilot-instructions.md"),
        ("project/copilot/code-generation.md", ".github/copilot/code-generation.md"),
        ("project/copilot/test-generation.md", ".github/copilot/test-generation.md"),
        ("project/copilot/code-review.md", ".github/copilot/code-review.md"),
        ("project/copilot/commit-message.md", ".github/copilot/commit-message.md"),
    ],
}


def _governance_template_mappings() -> tuple[tuple[str, str], ...]:
    source_root = template_root()
    governance_root = source_root / ".ai-engineering"
    mappings: list[tuple[str, str]] = []
    for source in sorted(governance_root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root).as_posix()
        mappings.append((relative, relative))
    return tuple(mappings)


TEMPLATE_MAPPINGS: tuple[tuple[str, str], ...] = (
    *_governance_template_mappings(),
    *PROJECT_TEMPLATE_MAPPINGS,
)


def sync_templates(repo_root: Path) -> dict[str, str]:
    """Copy bundled templates into repository when missing.

    Existing files are preserved to respect ownership and team customization.
    """

    result: dict[str, str] = {}
    source_root = template_root()

    for source_relative, destination_relative in TEMPLATE_MAPPINGS:
        source = source_root / source_relative
        destination = repo_root / destination_relative

        if not source.exists():
            result[destination_relative] = "missing-template"
            continue

        if destination.exists():
            result[destination_relative] = "exists"
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        result[destination_relative] = "created"

    return result


def available_stack_templates() -> list[str]:
    """Return available stack template names bundled with framework."""
    root = template_root() / ".ai-engineering" / "standards" / "framework" / "stacks"
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.md") if path.is_file())
