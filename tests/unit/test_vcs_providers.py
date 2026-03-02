"""Unit tests for VCS provider implementations."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.vcs.azure_devops import AzureDevOpsProvider
from ai_engineering.vcs.github import GitHubProvider
from ai_engineering.vcs.protocol import CreateTagContext, PipelineStatusContext, VcsContext

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


class TestGitHubReleaseMethods:
    """Tests for GitHubProvider.create_tag/get_pipeline_status."""

    def test_create_tag_success(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=0, stdout="{}", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.create_tag(
                CreateTagContext(
                    project_root=ctx.project_root,
                    tag_name="v0.2.0",
                    commit_sha="abc123",
                )
            )
        assert result.success is True

    def test_get_pipeline_status_filters_head_sha(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        runs = [
            {"headSha": "abc", "status": "completed", "conclusion": "success", "url": "u1"},
            {"headSha": "zzz", "status": "completed", "conclusion": "failure", "url": "u2"},
        ]
        proc = MagicMock(returncode=0, stdout=json.dumps(runs), stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.get_pipeline_status(
                PipelineStatusContext(project_root=ctx.project_root, head_sha="abc")
            )
        assert result.success is True
        parsed = json.loads(result.output)
        assert len(parsed) == 1
        assert parsed[0]["headSha"] == "abc"


class TestAzureReleaseMethods:
    """Tests for AzureDevOpsProvider.create_tag/get_pipeline_status."""

    def test_create_tag_success(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="{}", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.create_tag(
                CreateTagContext(
                    project_root=ctx.project_root,
                    tag_name="v0.2.0",
                    commit_sha="abc123",
                )
            )
        assert result.success is True

    def test_get_pipeline_status_filters_source_version(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        runs = [
            {"sourceVersion": "abc", "status": "completed", "result": "succeeded"},
            {"sourceVersion": "zzz", "status": "completed", "result": "failed"},
        ]
        proc = MagicMock(returncode=0, stdout=json.dumps(runs), stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.get_pipeline_status(
                PipelineStatusContext(project_root=ctx.project_root, head_sha="abc")
            )
        assert result.success is True
        parsed = json.loads(result.output)
        assert len(parsed) == 1
        assert parsed[0]["sourceVersion"] == "abc"
