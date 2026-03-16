"""Unit tests for ai_engineering.cli_commands.workflow module.

Tests the workflow commit, pr, and pr-only CLI commands using the
Typer CLI runner with mocked workflow functions to avoid actual git
operations.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.commands.workflows import StepResult, WorkflowResult

pytestmark = pytest.mark.unit

runner = CliRunner()


def _ok_result(workflow: str) -> WorkflowResult:
    """Build a minimal passing WorkflowResult."""
    return WorkflowResult(
        workflow=workflow,
        steps=[StepResult(name="stage", passed=True)],
    )


def _fail_result(workflow: str) -> WorkflowResult:
    """Build a minimal failing WorkflowResult."""
    return WorkflowResult(
        workflow=workflow,
        steps=[
            StepResult(name="stage", passed=True),
            StepResult(name="lint", passed=False, output="lint errors"),
        ],
    )


class TestWorkflowCommit:
    """Tests for `ai-eng workflow commit`."""

    @patch("ai_engineering.cli_commands.workflow.run_commit_workflow")
    @patch("ai_engineering.cli_commands.workflow.resolve_project_root")
    def test_commit_default_push(self, mock_root, mock_commit, tmp_path):
        """workflow commit calls run_commit_workflow with push=True by default."""
        # Arrange
        mock_root.return_value = tmp_path
        mock_commit.return_value = _ok_result("commit")
        app = create_app()

        # Act
        result = runner.invoke(app, ["workflow", "commit", "test message"])

        # Assert
        assert result.exit_code == 0
        mock_commit.assert_called_once_with(tmp_path, "test message", push=True)

    @patch("ai_engineering.cli_commands.workflow.run_commit_workflow")
    @patch("ai_engineering.cli_commands.workflow.resolve_project_root")
    def test_commit_only_skips_push(self, mock_root, mock_commit, tmp_path):
        """workflow commit --only calls run_commit_workflow with push=False."""
        # Arrange
        mock_root.return_value = tmp_path
        mock_commit.return_value = _ok_result("commit")
        app = create_app()

        # Act
        result = runner.invoke(app, ["workflow", "commit", "test message", "--only"])

        # Assert
        assert result.exit_code == 0
        mock_commit.assert_called_once_with(tmp_path, "test message", push=False)

    @patch("ai_engineering.cli_commands.workflow.run_commit_workflow")
    @patch("ai_engineering.cli_commands.workflow.resolve_project_root")
    def test_commit_failure_exits_nonzero(self, mock_root, mock_commit, tmp_path):
        """workflow commit exits with code 1 when the workflow fails."""
        # Arrange
        mock_root.return_value = tmp_path
        mock_commit.return_value = _fail_result("commit")
        app = create_app()

        # Act
        result = runner.invoke(app, ["workflow", "commit", "test message"])

        # Assert
        assert result.exit_code == 1

    @patch("ai_engineering.cli_commands.workflow.run_commit_workflow")
    @patch("ai_engineering.cli_commands.workflow.resolve_project_root")
    def test_commit_output_shows_steps(self, mock_root, mock_commit, tmp_path):
        """workflow commit renders step names in output."""
        # Arrange
        mock_root.return_value = tmp_path
        mock_commit.return_value = _ok_result("commit")
        app = create_app()

        # Act
        result = runner.invoke(app, ["workflow", "commit", "test message"])

        # Assert
        assert result.exit_code == 0
        assert "commit" in result.output.lower()


class TestWorkflowPr:
    """Tests for `ai-eng workflow pr`."""

    @patch("ai_engineering.cli_commands.workflow.run_pr_workflow")
    @patch("ai_engineering.cli_commands.workflow.resolve_project_root")
    def test_pr_calls_run_pr_workflow(self, mock_root, mock_pr, tmp_path):
        """workflow pr calls run_pr_workflow with the provided message."""
        # Arrange
        mock_root.return_value = tmp_path
        mock_pr.return_value = _ok_result("pr")
        app = create_app()

        # Act
        result = runner.invoke(app, ["workflow", "pr", "pr message"])

        # Assert
        assert result.exit_code == 0
        mock_pr.assert_called_once_with(tmp_path, "pr message")

    @patch("ai_engineering.cli_commands.workflow.run_pr_workflow")
    @patch("ai_engineering.cli_commands.workflow.resolve_project_root")
    def test_pr_failure_exits_nonzero(self, mock_root, mock_pr, tmp_path):
        """workflow pr exits with code 1 when the workflow fails."""
        # Arrange
        mock_root.return_value = tmp_path
        mock_pr.return_value = _fail_result("pr")
        app = create_app()

        # Act
        result = runner.invoke(app, ["workflow", "pr", "pr message"])

        # Assert
        assert result.exit_code == 1


class TestWorkflowPrOnly:
    """Tests for `ai-eng workflow pr-only`."""

    @patch("ai_engineering.cli_commands.workflow.run_pr_only_workflow")
    @patch("ai_engineering.cli_commands.workflow.resolve_project_root")
    def test_pr_only_calls_run_pr_only_workflow(self, mock_root, mock_pr_only, tmp_path):
        """workflow pr-only calls run_pr_only_workflow with project root."""
        # Arrange
        mock_root.return_value = tmp_path
        mock_pr_only.return_value = _ok_result("pr-only")
        app = create_app()

        # Act
        result = runner.invoke(app, ["workflow", "pr-only"])

        # Assert
        assert result.exit_code == 0
        mock_pr_only.assert_called_once_with(tmp_path)

    @patch("ai_engineering.cli_commands.workflow.run_pr_only_workflow")
    @patch("ai_engineering.cli_commands.workflow.resolve_project_root")
    def test_pr_only_failure_exits_nonzero(self, mock_root, mock_pr_only, tmp_path):
        """workflow pr-only exits with code 1 when the workflow fails."""
        # Arrange
        mock_root.return_value = tmp_path
        mock_pr_only.return_value = _fail_result("pr-only")
        app = create_app()

        # Act
        result = runner.invoke(app, ["workflow", "pr-only"])

        # Assert
        assert result.exit_code == 1

    @patch("ai_engineering.cli_commands.workflow.run_pr_only_workflow")
    @patch("ai_engineering.cli_commands.workflow.resolve_project_root")
    def test_pr_only_no_args_required(self, mock_root, mock_pr_only, tmp_path):
        """workflow pr-only requires no positional arguments."""
        # Arrange
        mock_root.return_value = tmp_path
        mock_pr_only.return_value = _ok_result("pr-only")
        app = create_app()

        # Act
        result = runner.invoke(app, ["workflow", "pr-only"])

        # Assert
        assert result.exit_code == 0
