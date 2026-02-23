"""Additional branch coverage for commands.workflows."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.commands import workflows
from ai_engineering.installer.service import install
from ai_engineering.policy.gates import GateCheckResult, GateHook, GateResult


@pytest.fixture()
def git_project(tmp_path: Path) -> Path:
    install(tmp_path)
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    (tmp_path / "x.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-b", "feature/x"], cwd=tmp_path, check=True)
    return tmp_path


def test_run_command_file_not_found(tmp_path: Path) -> None:
    ok, output = workflows._run_command(["definitely-not-a-binary"], tmp_path)
    assert ok is False
    assert "Command not found" in output


def test_run_command_timeout(tmp_path: Path) -> None:
    with patch(
        "ai_engineering.commands.workflows.subprocess.run",
        side_effect=subprocess.TimeoutExpired("x", 1),
    ):
        ok, output = workflows._run_command(["x"], tmp_path, timeout=1)
    assert ok is False
    assert "Timeout after 1s" in output


def test_run_command_empty_streams(tmp_path: Path) -> None:
    class Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    with patch("ai_engineering.commands.workflows.subprocess.run", return_value=Proc()):
        ok, output = workflows._run_command(["git", "status"], tmp_path)
    assert ok is True
    assert output == ""


def test_commit_workflow_push_failure_logs_and_fails(git_project: Path) -> None:
    def _mock(cmd: list[str], cwd: Path, **kwargs: object) -> tuple[bool, str]:
        if cmd[:2] == ["git", "push"]:
            return False, "push failed"
        return True, "ok"

    with patch("ai_engineering.commands.workflows._run_command", side_effect=_mock):
        result = workflows.run_commit_workflow(git_project, "feat: test", push=True)
    push_step = next(s for s in result.steps if s.name == "push")
    assert push_step.passed is False


def test_pr_workflow_stops_on_pre_push_failure(git_project: Path) -> None:
    gate = GateResult(
        hook=GateHook.PRE_PUSH,
        checks=[GateCheckResult(name="semgrep", passed=False, output="bad")],
    )
    with (
        patch("ai_engineering.commands.workflows._run_command", return_value=(True, "ok")),
        patch("ai_engineering.commands.workflows.run_gate", return_value=gate),
    ):
        result = workflows.run_pr_workflow(git_project, "feat: x")
    assert "create-pr" not in [s.name for s in result.steps]


def test_pr_only_auto_push_failure_returns(git_project: Path) -> None:
    with (
        patch("ai_engineering.commands.workflows.is_branch_pushed", return_value=False),
        patch("ai_engineering.commands.workflows._check_unpushed_decision", return_value=None),
        patch(
            "ai_engineering.commands.workflows._run_command", return_value=(False, "push failed")
        ),
    ):
        result = workflows.run_pr_only_workflow(git_project)
    assert result.passed is False
    assert "auto-push" in result.failed_steps


def test_check_unpushed_decision_exception_path(git_project: Path) -> None:
    with patch(
        "ai_engineering.commands.workflows.read_json_model", side_effect=RuntimeError("boom")
    ):
        decision = workflows._check_unpushed_decision(git_project, "feature/x")
    assert decision is None


def test_check_unpushed_decision_missing_store_returns_none(git_project: Path) -> None:
    decision = workflows._check_unpushed_decision(git_project / "not-found", "feature/x")
    assert decision is None
