"""Unit tests for platform detection.

Tests use ``tmp_path`` to create various repo layouts and verify
that ``detect_platforms`` returns the correct platforms.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.credentials.models import PlatformKind
from ai_engineering.platforms.detector import detect_platforms


class TestDetectPlatforms:
    """Tests for detect_platforms()."""

    def test_empty_repo_returns_nothing(self, tmp_path: Path) -> None:
        assert detect_platforms(tmp_path) == []

    def test_github_directory_detected(self, tmp_path: Path) -> None:
        (tmp_path / ".github").mkdir()
        result = detect_platforms(tmp_path)
        assert PlatformKind.GITHUB in result

    def test_azure_pipelines_yml_detected(self, tmp_path: Path) -> None:
        (tmp_path / "azure-pipelines.yml").touch()
        result = detect_platforms(tmp_path)
        assert PlatformKind.AZURE_DEVOPS in result

    def test_azuredevops_directory_detected(self, tmp_path: Path) -> None:
        (tmp_path / ".azuredevops").mkdir()
        result = detect_platforms(tmp_path)
        assert PlatformKind.AZURE_DEVOPS in result

    def test_sonar_properties_detected(self, tmp_path: Path) -> None:
        (tmp_path / "sonar-project.properties").touch()
        result = detect_platforms(tmp_path)
        assert PlatformKind.SONAR in result

    def test_multiple_platforms_detected(self, tmp_path: Path) -> None:
        (tmp_path / ".github").mkdir()
        (tmp_path / "azure-pipelines.yml").touch()
        (tmp_path / "sonar-project.properties").touch()
        result = detect_platforms(tmp_path)
        assert len(result) == 3
        assert PlatformKind.GITHUB in result
        assert PlatformKind.AZURE_DEVOPS in result
        assert PlatformKind.SONAR in result

    def test_azure_devops_only_counts_once(self, tmp_path: Path) -> None:
        """Both azure-pipelines.yml and .azuredevops/ → single detection."""
        (tmp_path / "azure-pipelines.yml").touch()
        (tmp_path / ".azuredevops").mkdir()
        result = detect_platforms(tmp_path)
        azdo_count = sum(1 for p in result if p == PlatformKind.AZURE_DEVOPS)
        assert azdo_count == 1

    def test_github_only(self, tmp_path: Path) -> None:
        (tmp_path / ".github").mkdir()
        result = detect_platforms(tmp_path)
        assert result == [PlatformKind.GITHUB]

    def test_sonar_only(self, tmp_path: Path) -> None:
        (tmp_path / "sonar-project.properties").touch()
        result = detect_platforms(tmp_path)
        assert result == [PlatformKind.SONAR]

    def test_nonexistent_root_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent root path raises no error, returns empty."""
        missing = tmp_path / "does-not-exist"
        result = detect_platforms(missing)
        assert result == []
