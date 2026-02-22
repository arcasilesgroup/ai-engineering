"""Unit tests for the GitHub VCS provider."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from ai_engineering.vcs.github import GitHubProvider
from ai_engineering.vcs.protocol import VcsContext


class TestGitHubProviderAvailability:
    """Tests for GitHubProvider.is_available()."""

    def test_available_when_gh_found(self) -> None:
        provider = GitHubProvider()
        with patch("ai_engineering.vcs.github.shutil.which", return_value="/usr/bin/gh"):
            assert provider.is_available() is True

    def test_not_available_when_gh_missing(self) -> None:
        provider = GitHubProvider()
        with patch("ai_engineering.vcs.github.shutil.which", return_value=None):
            assert provider.is_available() is False


class TestGitHubProviderName:
    """Tests for GitHubProvider.provider_name()."""

    def test_returns_github(self) -> None:
        assert GitHubProvider().provider_name() == "github"


class TestGitHubCreatePr:
    """Tests for GitHubProvider.create_pr()."""

    def test_creates_pr_with_title_and_body(self, tmp_path: Path) -> None:
        ctx = VcsContext(
            project_root=tmp_path,
            title="My PR",
            body="Some description",
            branch="feat/test",
            target_branch="main",
        )
        mock_proc = subprocess.CompletedProcess(
            args=["gh"],
            returncode=0,
            stdout="https://github.com/org/repo/pull/42\n",
            stderr="",
        )
        with patch("ai_engineering.vcs.github.subprocess.run", return_value=mock_proc):
            result = GitHubProvider().create_pr(ctx)

        assert result.success is True
        assert result.url == "https://github.com/org/repo/pull/42"

    def test_creates_pr_with_fill_when_no_title(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path)
        mock_proc = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout="https://github.com/org/repo/pull/1\n", stderr=""
        )
        with patch("ai_engineering.vcs.github.subprocess.run", return_value=mock_proc) as mock_run:
            result = GitHubProvider().create_pr(ctx)

        assert result.success is True
        # --fill should be in the command
        called_cmd = mock_run.call_args[0][0]
        assert "--fill" in called_cmd

    def test_failure_returns_error(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path, title="PR")
        mock_proc = subprocess.CompletedProcess(
            args=["gh"], returncode=1, stdout="", stderr="authentication required"
        )
        with patch("ai_engineering.vcs.github.subprocess.run", return_value=mock_proc):
            result = GitHubProvider().create_pr(ctx)

        assert result.success is False
        assert "authentication required" in result.output

    def test_handles_file_not_found(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path, title="PR")
        with patch(
            "ai_engineering.vcs.github.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            result = GitHubProvider().create_pr(ctx)

        assert result.success is False
        assert "not found" in result.output

    def test_handles_timeout(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path, title="PR")
        with patch(
            "ai_engineering.vcs.github.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="gh", timeout=60),
        ):
            result = GitHubProvider().create_pr(ctx)

        assert result.success is False
        assert "timed out" in result.output


class TestGitHubAutoComplete:
    """Tests for GitHubProvider.enable_auto_complete()."""

    def test_enables_auto_merge(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path, branch="feat/test")
        mock_proc = subprocess.CompletedProcess(
            args=["gh"], returncode=0, stdout="auto-merge enabled\n", stderr=""
        )
        with patch("ai_engineering.vcs.github.subprocess.run", return_value=mock_proc) as mock_run:
            result = GitHubProvider().enable_auto_complete(ctx)

        assert result.success is True
        called_cmd = mock_run.call_args[0][0]
        assert "--auto" in called_cmd
        assert "--squash" in called_cmd
        assert "--delete-branch" in called_cmd
