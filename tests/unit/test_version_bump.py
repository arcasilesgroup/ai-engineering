"""Unit tests for release version bump helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.release.version_bump import (
    bump_python_version,
    compare_versions,
    detect_current_version,
    validate_semver,
)

pytestmark = pytest.mark.unit


def _write_project(tmp_path: Path, version: str = "0.1.0") -> None:
    (tmp_path / "src" / "ai_engineering").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "ai-engineering"',
                f'version = "{version}"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_engineering" / "__version__.py").write_text(
        f'__version__ = "{version}"\n',
        encoding="utf-8",
    )


def test_validate_semver() -> None:
    assert validate_semver("0.2.0")
    assert validate_semver("1.0.0-rc.1")
    assert validate_semver("2.0.0-beta.1+build.123")
    assert not validate_semver("v0.2.0")
    assert not validate_semver("0.2")
    assert not validate_semver("abc")


def test_compare_versions_handles_prerelease() -> None:
    assert compare_versions("0.1.0", "0.2.0") == -1
    assert compare_versions("0.2.0", "0.2.0") == 0
    assert compare_versions("0.3.0", "0.2.0") == 1
    assert compare_versions("1.0.0-rc.1", "1.0.0") == -1
    assert compare_versions("1.0.0", "1.0.0-rc.1") == 1


def test_detect_current_version(tmp_path: Path) -> None:
    _write_project(tmp_path, "0.1.0")
    assert detect_current_version(tmp_path) == "0.1.0"


def test_bump_python_version_updates_pyproject_and_version_file(tmp_path: Path) -> None:
    # Arrange
    _write_project(tmp_path, "0.1.0")

    # Act
    result = bump_python_version(tmp_path, "0.2.0")

    # Assert
    assert result.old_version == "0.1.0"
    assert result.new_version == "0.2.0"
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8").find('version = "0.2.0"') >= 0
    assert (tmp_path / "src" / "ai_engineering" / "__version__.py").read_text(
        encoding="utf-8"
    ).find('__version__ = "0.2.0"') >= 0


def test_bump_python_version_rejects_invalid_semver(tmp_path: Path) -> None:
    _write_project(tmp_path, "0.1.0")
    with pytest.raises(ValueError):
        bump_python_version(tmp_path, "v0.2.0")


def test_compare_versions_numeric_and_alpha_prerelease_ordering() -> None:
    assert compare_versions("1.0.0-rc.2", "1.0.0-rc.10") == -1
    assert compare_versions("1.0.0-rc.1", "1.0.0-rc.alpha") == -1
    assert compare_versions("1.0.0-rc.alpha", "1.0.0-rc.1") == 1


def test_compare_versions_rejects_invalid_input() -> None:
    with pytest.raises(ValueError):
        compare_versions("bad", "1.0.0")


def test_detect_current_version_raises_when_missing(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    with pytest.raises(ValueError):
        detect_current_version(tmp_path)


def test_bump_python_version_raises_when_pyproject_version_line_missing(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / "src" / "ai_engineering").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "src" / "ai_engineering" / "__version__.py").write_text(
        '__version__ = "0.1.0"\n',
        encoding="utf-8",
    )

    # Act & Assert
    with pytest.raises(ValueError):
        bump_python_version(tmp_path, "0.2.0")


def test_bump_python_version_raises_when_version_file_missing(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='x'\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        bump_python_version(tmp_path, "0.2.0")


def test_bump_python_version_raises_when_version_assignment_missing(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / "src" / "ai_engineering").mkdir(parents=True)
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='x'\nversion = \"0.1.0\"\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_engineering" / "__version__.py").write_text(
        "VERSION = '0.1.0'\n",
        encoding="utf-8",
    )

    # Act & Assert
    with pytest.raises(ValueError):
        bump_python_version(tmp_path, "0.2.0")
