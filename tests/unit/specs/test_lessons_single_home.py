"""Spec-146 sub-003: lessons have one canonical Markdown home."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.installer.phases import governance

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CANONICAL_LESSONS = PROJECT_ROOT / ".ai-engineering" / "LESSONS.md"
LEGACY_TEAM_LESSONS = PROJECT_ROOT / ".ai-engineering" / "team" / "lessons.md"
TEMPLATE_LEGACY_TEAM_LESSONS = (
    PROJECT_ROOT
    / "src"
    / "ai_engineering"
    / "templates"
    / ".ai-engineering"
    / "team"
    / "lessons.md"
)

PRESERVED_TEAM_LESSON_HEADINGS = (
    "### Autonomous orchestrators must define consolidation, not only execution",
    "### Baseline exploration must happen before DAG and wave planning",
)


def test_team_lessons_content_is_preserved_in_canonical_lessons() -> None:
    """Unique team lessons from the duplicate file remain in the canonical file."""
    text = CANONICAL_LESSONS.read_text(encoding="utf-8")

    for heading in PRESERVED_TEAM_LESSON_HEADINGS:
        assert heading in text


def test_team_lessons_duplicate_is_absent_from_repo_and_templates() -> None:
    """The repository and fresh-install templates no longer seed team/lessons.md."""
    assert not LEGACY_TEAM_LESSONS.exists()
    assert not TEMPLATE_LEGACY_TEAM_LESSONS.exists()


def test_governance_phase_migrates_legacy_team_lessons_without_recreating_duplicate() -> None:
    """Existing consumer projects migrate team/lessons.md into LESSONS.md only."""
    assert governance._MIGRATIONS == {"LESSONS.md": "team/lessons.md"}
    assert "team/" in governance._EXCLUDE_PREFIXES
