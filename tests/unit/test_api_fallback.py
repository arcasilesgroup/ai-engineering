"""Unit tests for vcs/api_fallback module."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.vcs.api_fallback import ApiFallbackProvider
from ai_engineering.vcs.protocol import (
    CreateTagContext,
    IssueContext,
    PipelineStatusContext,
    VcsContext,
)


@pytest.fixture
def provider() -> ApiFallbackProvider:
    return ApiFallbackProvider("github")


@pytest.fixture
def ctx(tmp_path: Path) -> VcsContext:
    return VcsContext(project_root=tmp_path)


class TestApiFallbackProvider:
    """Tests for all ApiFallbackProvider methods."""

    def test_create_pr_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        result = provider.create_pr(ctx)
        assert result.success is False
        assert "github" in result.output

    def test_enable_auto_complete_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        result = provider.enable_auto_complete(ctx)
        assert result.success is False
        assert "auto-complete" in result.output

    def test_find_open_pr_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        result = provider.find_open_pr(ctx)
        assert result.success is False
        assert "PR lookup" in result.output

    def test_update_pr_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        result = provider.update_pr(ctx, pr_number="1")
        assert result.success is False
        assert "PR update" in result.output

    def test_is_available_returns_true(self, provider: ApiFallbackProvider) -> None:
        assert provider.is_available() is True

    def test_provider_name_returns_name(self, provider: ApiFallbackProvider) -> None:
        assert provider.provider_name() == "github"

    def test_check_auth_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        result = provider.check_auth(ctx)
        assert result.success is False

    def test_apply_branch_policy_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        result = provider.apply_branch_policy(ctx, branch="main", required_checks=["ci"])
        assert result.success is False
        assert "branch policy" in result.output

    def test_post_pr_review_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        result = provider.post_pr_review(ctx, body="test review")
        assert result.success is False
        assert "PR review" in result.output

    def test_create_tag_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        tag_ctx = CreateTagContext(
            project_root=ctx.project_root, tag_name="v1.0.0", commit_sha="abc123"
        )
        result = provider.create_tag(tag_ctx)
        assert result.success is False
        assert "tag creation" in result.output

    def test_get_pipeline_status_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        pipe_ctx = PipelineStatusContext(project_root=ctx.project_root, head_sha="abc123")
        result = provider.get_pipeline_status(pipe_ctx)
        assert result.success is False
        assert "pipeline status" in result.output

    def test_create_issue_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        issue_ctx = IssueContext(project_root=ctx.project_root, spec_id="037")
        result = provider.create_issue(issue_ctx)
        assert result.success is False
        assert "issue creation" in result.output

    def test_find_issue_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        issue_ctx = IssueContext(project_root=ctx.project_root, spec_id="037")
        result = provider.find_issue(issue_ctx)
        assert result.success is False
        assert "issue lookup" in result.output

    def test_close_issue_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        issue_ctx = IssueContext(project_root=ctx.project_root, spec_id="037")
        result = provider.close_issue(issue_ctx, issue_id="7")
        assert result.success is False
        assert "issue close" in result.output

    def test_link_issue_to_pr_returns_failure(
        self, provider: ApiFallbackProvider, ctx: VcsContext
    ) -> None:
        issue_ctx = IssueContext(project_root=ctx.project_root, spec_id="037")
        result = provider.link_issue_to_pr(issue_ctx, issue_id="7", pr_number="12")
        assert result.success is False
        assert "issue-PR linking" in result.output
