"""Unit tests for VCS provider implementations."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.vcs.azure_devops import AzureDevOpsProvider
from ai_engineering.vcs.github import GitHubProvider
from ai_engineering.vcs.protocol import (
    CreateTagContext,
    IssueContext,
    PipelineStatusContext,
    VcsContext,
)


@pytest.fixture
def ctx(tmp_path: Path) -> VcsContext:
    return VcsContext(project_root=tmp_path, branch="feature/test", target_branch="main")


# ── Azure DevOps ──────────────────────────────────────────────────


class TestAzureDevOpsCheckAuth:
    """Tests for AzureDevOpsProvider.check_auth."""

    def test_check_auth_success(self, ctx: VcsContext) -> None:
        # Arrange
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout='{"id": "abc"}', stderr="")

        # Act
        with patch("subprocess.run", return_value=proc):
            result = provider.check_auth(ctx)

        # Assert
        assert result.success is True

    def test_check_auth_failure(self, ctx: VcsContext) -> None:
        # Arrange
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=1, stdout="", stderr="not logged in")

        # Act
        with patch("subprocess.run", return_value=proc):
            result = provider.check_auth(ctx)

        # Assert
        assert result.success is False


class TestAzureDevOpsBranchPolicy:
    """Tests for AzureDevOpsProvider.apply_branch_policy."""

    def test_apply_branch_policy_success(self, ctx: VcsContext) -> None:
        # Arrange
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="[]", stderr="")

        # Act
        with patch("subprocess.run", return_value=proc):
            result = provider.apply_branch_policy(
                ctx, branch="main", required_checks=["ci", "lint"]
            )

        # Assert
        assert result.success is True
        assert "ci,lint" in result.output

    def test_apply_branch_policy_failure(self, ctx: VcsContext) -> None:
        # Arrange
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=1, stdout="", stderr="unauthorized")

        # Act
        with patch("subprocess.run", return_value=proc):
            result = provider.apply_branch_policy(ctx, branch="main", required_checks=["ci"])

        # Assert
        assert result.success is False


class TestAzureDevOpsPostPrReview:
    """Tests for AzureDevOpsProvider.post_pr_review."""

    def test_post_pr_review_success(self, ctx: VcsContext) -> None:
        # Arrange
        provider = AzureDevOpsProvider()
        pr_list_json = json.dumps([{"pullRequestId": 42}])
        calls = iter(
            [
                MagicMock(returncode=0, stdout=pr_list_json, stderr=""),
                MagicMock(returncode=0, stdout="{}", stderr=""),
            ]
        )

        # Act
        with patch("subprocess.run", side_effect=lambda *a, **kw: next(calls)):
            result = provider.post_pr_review(ctx, body="review comment")

        # Assert
        assert result.success is True

    def test_post_pr_review_no_active_pr(self, ctx: VcsContext) -> None:
        # Arrange
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="[]", stderr="")

        # Act
        with patch("subprocess.run", return_value=proc):
            result = provider.post_pr_review(ctx, body="review")

        # Assert
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


class TestGitHubUpsertMethods:
    """Tests for GitHubProvider.find_open_pr/update_pr."""

    def test_find_open_pr_returns_first(self, ctx: VcsContext) -> None:
        # Arrange
        provider = GitHubProvider()
        payload = json.dumps([{"number": 12, "title": "t", "body": "b", "url": "https://x/pr/12"}])
        proc = MagicMock(returncode=0, stdout=payload, stderr="")

        # Act
        with patch("subprocess.run", return_value=proc):
            result = provider.find_open_pr(ctx)

        # Assert
        assert result.success is True
        data = json.loads(result.output)
        assert data["number"] == 12

    def test_find_open_pr_cli_failure(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=1, stdout="", stderr="auth error")
        with patch("subprocess.run", return_value=proc):
            result = provider.find_open_pr(ctx)
        assert result.success is False

    def test_find_open_pr_bad_json(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=0, stdout="not-json", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.find_open_pr(ctx)
        assert result.success is False
        assert "parse" in result.output.lower()

    def test_find_open_pr_empty_list(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=0, stdout="[]", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.find_open_pr(ctx)
        assert result.success is True
        assert result.output == ""

    def test_update_pr_uses_body_file_flag(self, ctx: VcsContext) -> None:
        # Arrange
        provider = GitHubProvider()
        proc = MagicMock(returncode=0, stdout="ok", stderr="")

        # Act
        with patch("subprocess.run", return_value=proc) as run_mock:
            result = provider.update_pr(
                VcsContext(project_root=ctx.project_root, body="line1\nline2"),
                pr_number="12",
                title="same title",
            )

        # Assert
        assert result.success is True
        cmd = run_mock.call_args[0][0]
        assert "--body-file" in cmd
        assert "--title" in cmd


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
        # Arrange
        provider = GitHubProvider()
        runs = [
            {"headSha": "abc", "status": "completed", "conclusion": "success", "url": "u1"},
            {"headSha": "zzz", "status": "completed", "conclusion": "failure", "url": "u2"},
        ]
        proc = MagicMock(returncode=0, stdout=json.dumps(runs), stderr="")

        # Act
        with patch("subprocess.run", return_value=proc):
            result = provider.get_pipeline_status(
                PipelineStatusContext(project_root=ctx.project_root, head_sha="abc")
            )

        # Assert
        assert result.success is True
        parsed = json.loads(result.output)
        assert len(parsed) == 1
        assert parsed[0]["headSha"] == "abc"

    def test_get_pipeline_status_cli_failure(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=1, stdout="", stderr="error")
        with patch("subprocess.run", return_value=proc):
            result = provider.get_pipeline_status(
                PipelineStatusContext(project_root=ctx.project_root, head_sha="abc")
            )
        assert result.success is False

    def test_get_pipeline_status_bad_json(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=0, stdout="not-json", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.get_pipeline_status(
                PipelineStatusContext(project_root=ctx.project_root, head_sha="abc")
            )
        assert result.output == "not-json"


class TestGitHubResolveBodyFile:
    """Tests for GitHubProvider._resolve_body_file."""

    def test_uses_ctx_body_file_if_provided(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        body_file = Path("/tmp/test-body.md")
        new_ctx = VcsContext(project_root=ctx.project_root, body="text", body_file=body_file)
        path, cleanup = provider._resolve_body_file(new_ctx)
        assert path == body_file
        assert cleanup is False

    def test_creates_temp_file_when_no_body_file(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        new_ctx = VcsContext(project_root=ctx.project_root, body="hello world")
        path, cleanup = provider._resolve_body_file(new_ctx)
        try:
            assert cleanup is True
            assert path.exists()
            assert path.read_text(encoding="utf-8") == "hello world"
        finally:
            path.unlink(missing_ok=True)


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


# ── GitHub Issues ─────────────────────────────────────────────────


class TestGitHubIssueCreate:
    """Tests for GitHubProvider.create_issue."""

    def test_create_issue_success(self, ctx: VcsContext) -> None:
        # Arrange
        provider = GitHubProvider()
        proc = MagicMock(
            returncode=0,
            stdout="https://github.com/org/repo/issues/7\n",
            stderr="",
        )

        # Act
        with patch("subprocess.run", return_value=proc) as run_mock:
            issue_ctx = IssueContext(
                project_root=ctx.project_root,
                spec_id="037",
                title="[spec-037] Work-Item Sync",
                body="Implement sync",
            )
            result = provider.create_issue(issue_ctx)

        # Assert
        assert result.success is True
        cmd = run_mock.call_args[0][0]
        assert "gh" in cmd
        assert "--title" in cmd

    def test_create_issue_with_labels(self, ctx: VcsContext) -> None:
        # Arrange
        provider = GitHubProvider()
        proc = MagicMock(
            returncode=0,
            stdout="https://github.com/org/repo/issues/8\n",
            stderr="",
        )

        # Act
        with patch("subprocess.run", return_value=proc) as run_mock:
            issue_ctx = IssueContext(
                project_root=ctx.project_root,
                spec_id="037",
                title="Test",
                body="Body",
                labels=("spec-037", "enhancement"),
            )
            result = provider.create_issue(issue_ctx)

        # Assert
        assert result.success is True
        cmd = run_mock.call_args[0][0]
        assert cmd.count("--label") == 2


class TestGitHubIssueFindClose:
    """Tests for GitHubProvider.find_issue, close_issue, link_issue_to_pr."""

    def test_find_issue_found(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        payload = json.dumps([{"number": 7, "title": "test", "state": "OPEN"}])
        proc = MagicMock(returncode=0, stdout=payload, stderr="")
        with patch("subprocess.run", return_value=proc):
            issue_ctx = IssueContext(project_root=ctx.project_root, spec_id="037")
            result = provider.find_issue(issue_ctx)
        assert result.success is True
        assert result.output == "7"

    def test_find_issue_not_found(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=0, stdout="[]", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.find_issue(IssueContext(project_root=ctx.project_root, spec_id="999"))
        assert result.success is True
        assert result.output == ""

    def test_close_issue(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=0, stdout="Closed", stderr="")
        with patch("subprocess.run", return_value=proc) as run_mock:
            result = provider.close_issue(
                IssueContext(project_root=ctx.project_root, spec_id="037"),
                issue_id="7",
            )
        assert result.success is True
        cmd = run_mock.call_args[0][0]
        assert "close" in cmd
        assert "7" in cmd

    def test_find_issue_bad_json(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        proc = MagicMock(returncode=0, stdout="not-json", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.find_issue(IssueContext(project_root=ctx.project_root, spec_id="037"))
        assert result.success is False
        assert "parse" in result.output.lower()

    def test_link_issue_to_pr_noop(self, ctx: VcsContext) -> None:
        provider = GitHubProvider()
        result = provider.link_issue_to_pr(
            IssueContext(project_root=ctx.project_root, spec_id="037"),
            issue_id="7",
            pr_number="12",
        )
        assert result.success is True
        assert "keyword" in result.output.lower()


# ── Azure DevOps Issues ──────────────────────────────────────────


class TestAzureDevOpsIssueCreate:
    """Tests for AzureDevOpsProvider.create_issue."""

    def test_create_issue_success(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 101}),
            stderr="",
        )
        with patch("subprocess.run", return_value=proc) as run_mock:
            issue_ctx = IssueContext(
                project_root=ctx.project_root,
                spec_id="037",
                title="[spec-037] Sync",
                body="Implement",
            )
            result = provider.create_issue(issue_ctx)
        assert result.success is True
        assert result.output == "101"
        cmd = run_mock.call_args[0][0]
        assert "work-item" in cmd
        assert "create" in cmd

    def test_create_issue_custom_type(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(
            returncode=0,
            stdout=json.dumps({"id": 102}),
            stderr="",
        )
        with patch("subprocess.run", return_value=proc) as run_mock:
            issue_ctx = IssueContext(
                project_root=ctx.project_root,
                spec_id="037",
                title="Bug",
                body="Fix",
                work_item_type="Bug",
            )
            result = provider.create_issue(issue_ctx)
        assert result.success is True
        cmd = run_mock.call_args[0][0]
        assert "Bug" in cmd


class TestAzureDevOpsIssueFindClose:
    """Tests for AzureDevOpsProvider.find_issue, close_issue, link_issue_to_pr."""

    def test_find_issue_wiql_found(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        payload = json.dumps([{"id": 101}])
        proc = MagicMock(returncode=0, stdout=payload, stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.find_issue(IssueContext(project_root=ctx.project_root, spec_id="037"))
        assert result.success is True
        assert result.output == "101"

    def test_find_issue_not_found(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="[]", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.find_issue(IssueContext(project_root=ctx.project_root, spec_id="999"))
        assert result.success is True
        assert result.output == ""

    def test_close_issue(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="{}", stderr="")
        with patch("subprocess.run", return_value=proc) as run_mock:
            result = provider.close_issue(
                IssueContext(project_root=ctx.project_root, spec_id="037"),
                issue_id="101",
            )
        assert result.success is True
        cmd = run_mock.call_args[0][0]
        assert "--state" in cmd
        assert "Done" in cmd

    def test_link_issue_to_pr(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="{}", stderr="")
        with patch("subprocess.run", return_value=proc) as run_mock:
            result = provider.link_issue_to_pr(
                IssueContext(project_root=ctx.project_root, spec_id="037"),
                issue_id="101",
                pr_number="33",
            )
        assert result.success is True
        cmd = run_mock.call_args[0][0]
        assert "--work-items" in cmd
        assert "101" in cmd


class TestAzureUpsertMethods:
    """Tests for AzureDevOpsProvider.find_open_pr/update_pr."""

    def test_find_open_pr_returns_first(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        payload = json.dumps(
            [
                {
                    "pullRequestId": 33,
                    "title": "feat",
                    "description": "body",
                    "repository": {"webUrl": "https://dev.azure.com/org/p/_git/repo"},
                }
            ]
        )
        proc = MagicMock(returncode=0, stdout=payload, stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.find_open_pr(ctx)
        assert result.success is True
        data = json.loads(result.output)
        assert data["number"] == "33"

    def test_update_pr_uses_description(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="{}", stderr="")
        with patch("subprocess.run", return_value=proc) as run_mock:
            result = provider.update_pr(
                VcsContext(project_root=ctx.project_root, body="extra"),
                pr_number="33",
                title="feat",
            )
        assert result.success is True
        cmd = run_mock.call_args[0][0]
        assert "--description" in cmd
        assert "--id" in cmd


class TestAzureDevOpsErrorPaths:
    """Tests for AzureDevOps error handling paths."""

    def test_get_pipeline_status_cli_failure(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=1, stdout="", stderr="auth error")
        with patch("subprocess.run", return_value=proc):
            result = provider.get_pipeline_status(
                PipelineStatusContext(project_root=ctx.project_root, head_sha="abc")
            )
        assert result.success is False

    def test_get_pipeline_status_bad_json(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="not-json", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.get_pipeline_status(
                PipelineStatusContext(project_root=ctx.project_root, head_sha="abc")
            )
        assert result.output == "not-json"

    def test_find_issue_bad_json(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        proc = MagicMock(returncode=0, stdout="not-json", stderr="")
        with patch("subprocess.run", return_value=proc):
            result = provider.find_issue(IssueContext(project_root=ctx.project_root, spec_id="037"))
        assert result.success is False
        assert "parse" in result.output.lower()

    def test_read_body_oserror(self, ctx: VcsContext) -> None:
        provider = AzureDevOpsProvider()
        bad_file = MagicMock()
        bad_file.read_text.side_effect = OSError("denied")
        new_ctx = VcsContext(project_root=ctx.project_root, body="fallback", body_file=bad_file)
        result = provider._read_body(new_ctx)
        assert result == "fallback"
