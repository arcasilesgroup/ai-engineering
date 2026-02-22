"""Unit tests for the VCS provider factory."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from ai_engineering.vcs.azure_devops import AzureDevOpsProvider
from ai_engineering.vcs.factory import _detect_from_remote, get_provider
from ai_engineering.vcs.github import GitHubProvider


class TestGetProvider:
    """Tests for get_provider() dispatch."""

    def test_returns_github_by_default(self, tmp_path: Path) -> None:
        """No manifest, no remote → defaults to GitHub."""
        with patch("ai_engineering.vcs.factory.run_git", return_value=(False, "")):
            provider = get_provider(tmp_path)
        assert isinstance(provider, GitHubProvider)

    def test_reads_manifest_primary_github(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".ai-engineering" / "state"
        manifest_dir.mkdir(parents=True)
        manifest = {
            "schemaVersion": "1.1",
            "providers": {"primary": "github", "enabled": ["github"]},
        }
        (manifest_dir / "install-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        provider = get_provider(tmp_path)
        assert isinstance(provider, GitHubProvider)

    def test_reads_manifest_primary_azure(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".ai-engineering" / "state"
        manifest_dir.mkdir(parents=True)
        manifest = {
            "schemaVersion": "1.1",
            "providers": {"primary": "azure_devops", "enabled": ["azure_devops"]},
        }
        (manifest_dir / "install-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        provider = get_provider(tmp_path)
        assert isinstance(provider, AzureDevOpsProvider)

    def test_falls_back_to_remote_detection(self, tmp_path: Path) -> None:
        """Manifest exists but has unknown provider → detect from remote."""
        manifest_dir = tmp_path / ".ai-engineering" / "state"
        manifest_dir.mkdir(parents=True)
        manifest = {
            "schemaVersion": "1.1",
            "providers": {"primary": "unknown_provider", "enabled": []},
        }
        (manifest_dir / "install-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "https://dev.azure.com/org/project/_git/repo"),
        ):
            provider = get_provider(tmp_path)
        assert isinstance(provider, AzureDevOpsProvider)

    def test_corrupt_manifest_falls_back(self, tmp_path: Path) -> None:
        manifest_dir = tmp_path / ".ai-engineering" / "state"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "install-manifest.json").write_text("not json", encoding="utf-8")
        with patch("ai_engineering.vcs.factory.run_git", return_value=(False, "")):
            provider = get_provider(tmp_path)
        assert isinstance(provider, GitHubProvider)


class TestDetectFromRemote:
    """Tests for _detect_from_remote()."""

    def test_github_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "https://github.com/org/repo.git"),
        ):
            assert _detect_from_remote(tmp_path) == "github"

    def test_azure_devops_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "https://dev.azure.com/org/project/_git/repo"),
        ):
            assert _detect_from_remote(tmp_path) == "azure_devops"

    def test_visualstudio_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "https://org.visualstudio.com/project/_git/repo"),
        ):
            assert _detect_from_remote(tmp_path) == "azure_devops"

    def test_no_remote_defaults_to_github(self, tmp_path: Path) -> None:
        with patch("ai_engineering.vcs.factory.run_git", return_value=(False, "")):
            assert _detect_from_remote(tmp_path) == "github"

    def test_ssh_github_url(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.vcs.factory.run_git",
            return_value=(True, "git@github.com:org/repo.git"),
        ):
            assert _detect_from_remote(tmp_path) == "github"
