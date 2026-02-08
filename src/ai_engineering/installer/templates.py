"""Template synchronization for installer bootstrap."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.paths import template_root


TEMPLATE_MAPPINGS: tuple[tuple[str, str], ...] = (
    (
        ".ai-engineering/standards/framework/quality/core.md",
        ".ai-engineering/standards/framework/quality/core.md",
    ),
    (
        ".ai-engineering/standards/framework/quality/python.md",
        ".ai-engineering/standards/framework/quality/python.md",
    ),
    (
        ".ai-engineering/standards/framework/quality/sonarlint.md",
        ".ai-engineering/standards/framework/quality/sonarlint.md",
    ),
    (
        ".ai-engineering/skills/utils/platform-detection.md",
        ".ai-engineering/skills/utils/platform-detection.md",
    ),
    (
        ".ai-engineering/skills/utils/git-helpers.md",
        ".ai-engineering/skills/utils/git-helpers.md",
    ),
    (
        ".ai-engineering/skills/validation/install-readiness.md",
        ".ai-engineering/skills/validation/install-readiness.md",
    ),
    (
        "project/CLAUDE.md",
        "CLAUDE.md",
    ),
    (
        "project/codex.md",
        "codex.md",
    ),
    (
        "project/copilot-instructions.md",
        ".github/copilot-instructions.md",
    ),
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
