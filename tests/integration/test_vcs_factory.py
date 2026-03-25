"""Unit tests for the VCS provider factory."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.vcs.api_fallback import ApiFallbackProvider
from ai_engineering.vcs.azure_devops import AzureDevOpsProvider
from ai_engineering.vcs.factory import detect_from_remote, get_provider
from ai_engineering.vcs.github import GitHubProvider

pytestmark = pytest.mark.integration


def _setup_project(
    tmp_path: Path,
    *,
    vcs: str = "github",
    gh_mode: str = "cli",
    az_mode: str = "cli",
) -> None:
    """Create manifest.yml and install-state.json for factory tests."""
    ai_dir = tmp_path / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        f"schema_version: '2.0'\nproviders:\n  vcs: {vcs}\n  stacks:\n    - python\n"
    )
    state_dir = ai_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "schema_version": "2.0",
        "tooling": {
            "gh": {"installed": True, "authenticated": True, "mode": gh_mode},
            "az": {"installed": True, "authenticated": True, "mode": az_mode},
        },
    }
    (state_dir / "install-state.json").write_text(json.dumps(state), encoding="utf-8")


class TestGetProvider:
    """Tests for get_provider() dispatch."""

    def test_returns_github_by_default(self, tmp_path: Path) -> None:
        """No config, no remote -> defaults to GitHub."""
        with patch("ai_engineering.vcs.factory.run_git", return_value=(False, "")):
            provider = get_provider(tmp_path)
        assert isinstance(provider, GitHubProvider)

    def test_reads_config_primary_github(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, vcs="github")
        provider = get_provider(tmp_path)
        assert isinstance(provider, GitHubProvider)

    def test_reads_config_primary_azure(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, vcs="azure_devops")
        provider = get_provider(tmp_path)
        assert isinstance(provider, AzureDevOpsProvider)

    def test_api_mode_returns_fallback(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, vcs="github", gh_mode="api")
        provider = get_provider(tmp_path)
        assert isinstance(provider, ApiFallbackProvider)

    def test_falls_back_to_remote_detection(self, tmp_path: Path) -> None:
        """Config has unknown provider -> detect from remote."""
        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "manifest.yml").write_text(
            "schema_version: '2.0'\nproviders:\n  vcs: unknown_provider\n  stacks: []\n"
        )
        state_dir = ai_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text('{"schema_version":"2.0"}')
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "https://dev.azure.com/org/project/_git/repo"),
        ):
            provider = get_provider(tmp_path)
        assert isinstance(provider, AzureDevOpsProvider)

    def test_corrupt_state_falls_back(self, tmp_path: Path) -> None:
        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir(parents=True, exist_ok=True)
        (ai_dir / "manifest.yml").write_text("not: valid: yaml: [")
        state_dir = ai_dir / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "install-state.json").write_text("not json", encoding="utf-8")
        with patch("ai_engineering.vcs.factory.run_git", return_value=(False, "")):
            provider = get_provider(tmp_path)
        assert isinstance(provider, GitHubProvider)


class TestDetectFromRemote:
    """Tests for detect_from_remote()."""

    def test_github_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "https://github.com/org/repo.git"),
        ):
            assert detect_from_remote(tmp_path) == "github"

    def test_azure_devops_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "https://dev.azure.com/org/project/_git/repo"),
        ):
            assert detect_from_remote(tmp_path) == "azure_devops"

    def test_visualstudio_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "https://org.visualstudio.com/project/_git/repo"),
        ):
            assert detect_from_remote(tmp_path) == "azure_devops"

    def test_no_remote_defaults_to_github(self, tmp_path: Path) -> None:
        with patch("ai_engineering.vcs.factory.run_git", return_value=(False, "")):
            assert detect_from_remote(tmp_path) == "github"

    def test_ssh_github_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "git@github.com:org/repo.git"),
        ):
            assert detect_from_remote(tmp_path) == "github"
