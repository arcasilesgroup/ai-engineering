"""Unit tests for release version bump helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.release.version_bump import (
    _update_registry,
    bump_python_version,
    compare_versions,
    detect_current_version,
    validate_semver,
)


def _write_project(tmp_path: Path, version: str = "0.1.0") -> None:
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


def test_bump_python_version_updates_pyproject_only(tmp_path: Path) -> None:
    _write_project(tmp_path, "0.1.0")

    result = bump_python_version(tmp_path, "0.2.0")

    assert result.old_version == "0.1.0"
    assert result.new_version == "0.2.0"
    assert len(result.files_modified) == 1
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8").find('version = "0.2.0"') >= 0


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
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")

    with pytest.raises(ValueError):
        bump_python_version(tmp_path, "0.2.0")


def test_bump_python_version_works_without_version_file(tmp_path: Path) -> None:
    _write_project(tmp_path, "0.1.0")

    result = bump_python_version(tmp_path, "0.2.0")
    assert result.new_version == "0.2.0"
    assert len(result.files_modified) == 1


def _write_registry(tmp_path: Path, versions: list[dict[str, str]]) -> Path:
    registry_path = tmp_path / "src" / "ai_engineering" / "version" / "registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps({"schemaVersion": "1.0", "versions": versions}, indent=2) + "\n",
        encoding="utf-8",
    )
    return registry_path


def test_bump_python_version_syncs_registry(tmp_path: Path) -> None:
    _write_project(tmp_path, "0.1.0")
    _write_registry(
        tmp_path,
        [
            {"version": "0.1.0", "status": "current", "released": "2026-01-01"},
        ],
    )

    result = bump_python_version(tmp_path, "0.2.0")

    assert len(result.files_modified) == 2
    registry = json.loads(result.files_modified[1].read_text(encoding="utf-8"))
    versions = registry["versions"]
    assert versions[0]["version"] == "0.2.0"
    assert versions[0]["status"] == "current"
    assert versions[1]["version"] == "0.1.0"
    assert versions[1]["status"] == "supported"


def test_update_registry_demotes_current(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            {"version": "0.3.0", "status": "current", "released": "2026-03-01"},
            {"version": "0.2.0", "status": "supported", "released": "2026-02-01"},
        ],
    )

    _update_registry(path, "0.4.0")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["versions"][0]["version"] == "0.4.0"
    assert data["versions"][0]["status"] == "current"
    assert data["versions"][1]["version"] == "0.3.0"
    assert data["versions"][1]["status"] == "supported"
    assert data["versions"][2]["status"] == "supported"


def test_update_registry_is_idempotent(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            {"version": "0.4.0", "status": "current", "released": "2026-04-01"},
        ],
    )

    _update_registry(path, "0.4.0")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["versions"]) == 1
    assert data["versions"][0]["version"] == "0.4.0"


def test_update_registry_rejects_invalid_version_entries(tmp_path: Path) -> None:
    path = _write_registry(
        tmp_path,
        [
            {"version": "not-a-semver", "status": "current", "released": "2026-04-01"},
        ],
    )

    with pytest.raises(ValueError, match="Invalid version in version registry"):
        _update_registry(path, "0.4.0")
