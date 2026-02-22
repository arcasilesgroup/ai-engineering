"""Unit tests for the Azure DevOps VCS provider."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from ai_engineering.vcs.azure_devops import AzureDevOpsProvider
from ai_engineering.vcs.protocol import VcsContext


class TestAzureDevOpsAvailability:
    """Tests for AzureDevOpsProvider.is_available()."""

    def test_available_when_az_found(self) -> None:
        provider = AzureDevOpsProvider()
        with patch("ai_engineering.vcs.azure_devops.shutil.which", return_value="/usr/bin/az"):
            assert provider.is_available() is True

    def test_not_available_when_az_missing(self) -> None:
        provider = AzureDevOpsProvider()
        with patch("ai_engineering.vcs.azure_devops.shutil.which", return_value=None):
            assert provider.is_available() is False


class TestAzureDevOpsProviderName:
    """Tests for AzureDevOpsProvider.provider_name()."""

    def test_returns_azure_devops(self) -> None:
        assert AzureDevOpsProvider().provider_name() == "azure_devops"


class TestAzureDevOpsCreatePr:
    """Tests for AzureDevOpsProvider.create_pr()."""

    def test_creates_pr_with_json_output(self, tmp_path: Path) -> None:
        ctx = VcsContext(
            project_root=tmp_path,
            title="My PR",
            body="Description",
            branch="feat/test",
            target_branch="main",
        )
        pr_response = json.dumps(
            {
                "pullRequestId": 123,
                "repository": {"webUrl": "https://dev.azure.com/org/project/_git/repo"},
            }
        )
        mock_proc = subprocess.CompletedProcess(
            args=["az"], returncode=0, stdout=pr_response + "\n", stderr=""
        )
        with patch("ai_engineering.vcs.azure_devops.subprocess.run", return_value=mock_proc):
            result = AzureDevOpsProvider().create_pr(ctx)

        assert result.success is True
        assert "pullrequest/123" in result.url

    def test_creates_pr_failure(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path, title="PR", branch="feat/x")
        mock_proc = subprocess.CompletedProcess(
            args=["az"], returncode=1, stdout="", stderr="authorization error"
        )
        with patch("ai_engineering.vcs.azure_devops.subprocess.run", return_value=mock_proc):
            result = AzureDevOpsProvider().create_pr(ctx)

        assert result.success is False
        assert "authorization" in result.output

    def test_handles_file_not_found(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path, title="PR", branch="feat/x")
        with patch(
            "ai_engineering.vcs.azure_devops.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            result = AzureDevOpsProvider().create_pr(ctx)

        assert result.success is False
        assert "not found" in result.output


class TestAzureDevOpsAutoComplete:
    """Tests for AzureDevOpsProvider.enable_auto_complete()."""

    def test_enables_auto_complete(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path, branch="feat/test")

        # Mock: first call lists PRs, second call updates the PR
        list_response = json.dumps([{"pullRequestId": 42}])
        calls = [0]

        def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls[0] += 1
            if "list" in cmd:
                return subprocess.CompletedProcess(
                    args=cmd, returncode=0, stdout=list_response + "\n", stderr=""
                )
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="updated\n", stderr=""
            )

        with patch("ai_engineering.vcs.azure_devops.subprocess.run", side_effect=fake_run):
            result = AzureDevOpsProvider().enable_auto_complete(ctx)

        assert result.success is True
        assert calls[0] == 2

    def test_no_active_pr_returns_failure(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path, branch="feat/orphan")
        mock_proc = subprocess.CompletedProcess(args=["az"], returncode=0, stdout="[]\n", stderr="")
        with patch("ai_engineering.vcs.azure_devops.subprocess.run", return_value=mock_proc):
            result = AzureDevOpsProvider().enable_auto_complete(ctx)

        assert result.success is False
        assert "No active PR" in result.output

    def test_handles_timeout(self, tmp_path: Path) -> None:
        ctx = VcsContext(project_root=tmp_path, branch="feat/slow")
        with patch(
            "ai_engineering.vcs.azure_devops.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="az", timeout=60),
        ):
            result = AzureDevOpsProvider().enable_auto_complete(ctx)

        assert result.success is False
        assert "timed out" in result.output
