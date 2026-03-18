"""Unit tests for release changelog helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.release.changelog import (
    extract_release_notes,
    promote_unreleased,
    validate_changelog,
)

pytestmark = pytest.mark.unit


def _write_changelog(path: Path, unreleased_body: str = "- item\n") -> None:
    path.write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "## [Unreleased]",
                "",
                unreleased_body.rstrip("\n"),
                "",
                "## [0.1.0] - 2026-03-01",
                "",
                "- old",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_extract_release_notes_returns_section_body(tmp_path: Path) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    _write_changelog(changelog)

    # Act
    notes = extract_release_notes(changelog, "0.1.0")

    # Assert
    assert notes is not None
    assert "- old" in notes


def test_validate_changelog_reports_duplicate_version_section(tmp_path: Path) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    _write_changelog(changelog)

    # Act
    errors = validate_changelog(changelog, "0.1.0")

    # Assert
    assert any("already contains" in err for err in errors)


def test_promote_unreleased_moves_content_and_leaves_empty_section(tmp_path: Path) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    _write_changelog(changelog, "### Added\n- release thing\n")

    # Act
    promoted = promote_unreleased(changelog, "0.2.0", "2026-03-02")

    # Assert
    assert promoted is True
    text = changelog.read_text(encoding="utf-8")
    assert "## [Unreleased]" in text
    assert "## [0.2.0] - 2026-03-02" in text
    assert "- release thing" in text


def test_promote_unreleased_returns_false_when_section_missing(tmp_path: Path) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n", encoding="utf-8")

    # Act & Assert
    assert promote_unreleased(changelog, "0.2.0", "2026-03-02") is False
