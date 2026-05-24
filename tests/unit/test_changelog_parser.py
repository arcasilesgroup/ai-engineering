"""Unit tests for release changelog helpers."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.release.changelog import (
    extract_release_notes,
    promote_unreleased,
    validate_changelog,
)


def _write_changelog(path: Path, unreleased_body: str = "### Added\n- item\n") -> None:
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


def test_validate_changelog_reports_missing_unreleased_section(tmp_path: Path) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [0.1.0] - 2026-03-01\n\n- old\n", encoding="utf-8")

    # Act
    errors = validate_changelog(changelog, "0.2.0")

    # Assert
    assert any("Missing [Unreleased]" in err for err in errors)


def test_validate_changelog_reports_target_section_bad_date_format(tmp_path: Path) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "\n".join(
            [
                "# Changelog",
                "",
                "## [Unreleased]",
                "",
                "### Added",
                "- item",
                "",
                "## [0.2.0] - 2026/03/02",
                "",
                "### Fixed",
                "- old",
                "",
            ]
        ),
        encoding="utf-8",
    )

    # Act
    errors = validate_changelog(changelog, "0.2.0")

    # Assert
    assert any("YYYY-MM-DD" in err for err in errors)


def test_validate_changelog_reports_empty_unreleased_notes(tmp_path: Path) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-03-01\n\n- old\n",
        encoding="utf-8",
    )

    # Act
    errors = validate_changelog(changelog, "0.2.0")

    # Assert
    assert any("release notes are empty" in err for err in errors)


def test_validate_changelog_reports_missing_keep_a_changelog_subgroup(tmp_path: Path) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    _write_changelog(changelog, "- item without subgroup\n")

    # Act
    errors = validate_changelog(changelog, "0.2.0")

    # Assert
    assert any("Keep-a-Changelog subgroup" in err for err in errors)


def test_validate_changelog_requires_breaking_subgroup_for_release_path_semantics(
    tmp_path: Path,
) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    _write_changelog(
        changelog,
        "\n".join(
            [
                "### Changed",
                "- semantic-release and manual CI commit-back are removed; "
                "ai-eng release is sole authority.",
                "",
            ]
        ),
    )

    # Act
    errors = validate_changelog(changelog, "0.2.0")

    # Assert
    assert any("### BREAKING" in err for err in errors)


def test_validate_changelog_accepts_release_path_semantics_under_breaking(
    tmp_path: Path,
) -> None:
    # Arrange
    changelog = tmp_path / "CHANGELOG.md"
    _write_changelog(
        changelog,
        "\n".join(
            [
                "### BREAKING",
                "- semantic-release and manual CI commit-back are removed; "
                "ai-eng release is sole authority.",
                "",
            ]
        ),
    )

    # Act
    errors = validate_changelog(changelog, "0.2.0")

    # Assert
    assert not any("### BREAKING" in err for err in errors)


def test_validate_changelog_allows_release_path_fix_under_fixed(
    tmp_path: Path,
) -> None:
    # Arrange — a non-breaking release-path *fix* belongs under ### Fixed and
    # must not be forced into a ### BREAKING subgroup (Keep-a-Changelog).
    changelog = tmp_path / "CHANGELOG.md"
    _write_changelog(
        changelog,
        "\n".join(
            [
                "### Fixed",
                "- Release finalization now writes non-empty proof logs so "
                "release packet asset uploads do not fail on zero-byte files.",
                "",
            ]
        ),
    )

    # Act
    errors = validate_changelog(changelog, "0.2.0")

    # Assert
    assert not any("### BREAKING" in err for err in errors)


def test_validate_changelog_still_requires_breaking_when_fixed_subsection_present(
    tmp_path: Path,
) -> None:
    # Arrange — the Fixed exemption is scoped: a release-path *semantic change*
    # under ### Changed still requires a ### BREAKING entry even when a ### Fixed
    # subsection coexists.
    changelog = tmp_path / "CHANGELOG.md"
    _write_changelog(
        changelog,
        "\n".join(
            [
                "### Changed",
                "- semantic-release and manual CI commit-back are removed; "
                "ai-eng release is sole authority.",
                "",
                "### Fixed",
                "- unrelated typo fix.",
                "",
            ]
        ),
    )

    # Act
    errors = validate_changelog(changelog, "0.2.0")

    # Assert
    assert any("### BREAKING" in err for err in errors)


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
