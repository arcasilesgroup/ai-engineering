"""Unit tests for VCS provider implementations."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.vcs.azure_devops import AzureDevOpsProvider
from ai_engineering.vcs.github import GitHubProvider
from ai_engineering.vcs.protocol import VcsContext

pytestmark = pytest.mark.unit


@pytest.fixture
def ctx(tmp_path: Path) -> VcsContext:
    return VcsContext(project_root=tmp_path, branch="feature/test", target_branch="main")


# ── Azure DevOps ──────────────────────────────────────────────────


class TestAzureDevOpsCheckAuth:
    """Tests for AzureDevOpsProvider.check_auth."""

    def test_check_auth_success(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout='{"id": "abc"}', stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.check_auth(ctx)
        assert result.success is True

    def test_check_auth_failure(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=1, stdout="", stderr="not logged in")
        with patch("subprocess.run", return_value=proc):
            result = provider.check_auth(ctx)
        assert result.success is False


class TestAzureDevOpsBranchPolicy:
    """Tests for AzureDevOpsProvider.apply_branch_policy."""

    def test_apply_branch_policy_success(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="[]", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.apply_branch_policy(
                ctx, branch="main", required_checks=["ci", "lint"]
            )
        assert result.success is True
        assert "ci,lint" in result.output

    def test_apply_branch_policy_failure(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=1, stdout="", stderr="unauthorized")
        with patch("subprocess.run", return_value=proc):
            result = provider.apply_branch_policy(ctx, branch="main", required_checks=["ci"])
        assert result.success is False


class TestAzureDevOpsPostPrReview:
    """Tests for AzureDevOpsProvider.post_pr_review."""

    def test_post_pr_review_success(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        # First call: list PRs; Second call: post comment
        pr_list_json = json.dumps([{"pullRequestId": 42}])
        calls = iter(
            [
                MagicMock(returncode=0, stdout=pr_list_json, stderr=""),
                MagicMock(returncode=0, stdout="{}", stderr=""),
            ]
        )
        with patch("subprocess.run", side_effect=lambda *a, **kw: next(calls)):
            result = provider.post_pr_review(ctx, body="review comment")
        assert result.success is True

    def test_post_pr_review_no_active_pr(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="[]", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.post_pr_review(ctx, body="review")
        assert result.success is False
        assert "No active PR" in result.output

    def test_post_pr_review_list_failure(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=1, stdout="", stderr="error")
        with patch("subprocess.run", return_value=proc):
            result = provider.post_pr_review(ctx, body="review")
        assert result.success is False

    def test_post_pr_review_bad_json(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="not-json", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.post_pr_review(ctx, body="review")
        assert result.success is False
        assert "parse" in result.output.lower()


# ── GitHub ────────────────────────────────────────────────────────


class TestGitHubPostPrReview:
    """Tests for GitHubProvider.post_pr_review."""

    def test_post_pr_review_success(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=0, stdout="Comment posted", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.post_pr_review(ctx, body="great PR")
        assert result.success is True

    def test_post_pr_review_failure(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=1, stdout="", stderr="not found")
        with patch("subprocess.run", return_value=proc):
            result = provider.post_pr_review(ctx, body="review")
        assert result.success is False
