"""Unit tests for commands/workflows.py helper functions."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.commands.workflows import (
    StepResult,
    WorkflowResult,
    _check_unpushed_decision,
    _run_command,
    run_commit_workflow,
)

pytestmark = pytest.mark.unit


class TestRunCommand:
    """Tests for _run_command subprocess wrapper."""

    def test_success(self, tmp_path: Path) -> None:
        proc = MagicMock(returncode=0, stdout="ok", stderr="")
        with patch("ai_engineering.commands.workflows.subprocess.run", return_value=proc):
            passed, output = _run_command(["echo", "hi"], tmp_path)
        assert passed is True
        assert "ok" in output

    def test_failure(self, tmp_path: Path) -> None:
        proc = MagicMock(returncode=1, stdout="", stderr="error")
        with patch("ai_engineering.commands.workflows.subprocess.run", return_value=proc):
            passed, _output = _run_command(["false"], tmp_path)
        assert passed is False

    def test_command_not_found(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.commands.workflows.subprocess.run",
            side_effect=FileNotFoundError("not found"),
        ):
            passed, output = _run_command(["nonexistent"], tmp_path)
        assert passed is False
        assert "Command not found" in output

    def test_timeout(self, tmp_path: Path) -> None:
        with patch(
            "ai_engineering.commands.workflows.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="test", timeout=30),
        ):
            passed, output = _run_command(["slow"], tmp_path, timeout=30)
        assert passed is False
        assert "Timeout" in output


class TestCheckUnpushedDecision:
    """Tests for _check_unpushed_decision."""

    def test_no_store_file_returns_none(self, tmp_path: Path) -> None:
        result = _check_unpushed_decision(tmp_path, "feature/x")
        assert result is None

    def test_empty_store_returns_none(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        store_path = state_dir / "decision-store.json"
        store_path.write_text(json.dumps({"schema_version": "1.1", "decisions": []}))
        result = _check_unpushed_decision(tmp_path, "feature/x")
        assert result is None

    def test_matching_decision_returned(self, tmp_path: Path) -> None:
        from ai_engineering.state.decision_logic import compute_context_hash

        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        store_path = state_dir / "decision-store.json"
        context = "unpushed-branch-pr:feature/test"
        context_hash = compute_context_hash(context)
        store_data = {
            "schema_version": "1.1",
            "decisions": [
                {
                    "id": "d-001",
                    "context": context,
                    "contextHash": context_hash,
                    "decision": "defer-pr",
                    "decidedAt": "2025-01-01T00:00:00Z",
                    "spec": "test-spec",
                }
            ],
        }
        store_path.write_text(json.dumps(store_data))
        result = _check_unpushed_decision(tmp_path, "feature/test")
        assert result == "defer-pr"

    def test_corrupt_store_returns_none(self, tmp_path: Path) -> None:
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        store_path = state_dir / "decision-store.json"
        store_path.write_text("not json")
        result = _check_unpushed_decision(tmp_path, "feature/x")
        assert result is None


class TestWorkflowResult:
    """Tests for WorkflowResult dataclass."""

    def test_passed_all_steps(self) -> None:
        wr = WorkflowResult(
            workflow="commit",
            steps=[StepResult(name="a", passed=True), StepResult(name="b", passed=True)],
        )
        assert wr.passed is True
        assert wr.failed_steps == []

    def test_failed_step(self) -> None:
        wr = WorkflowResult(
            workflow="commit",
            steps=[StepResult(name="a", passed=True), StepResult(name="b", passed=False)],
        )
        assert wr.passed is False
        assert wr.failed_steps == ["b"]

    def test_skipped_step_counts_as_passed(self) -> None:
        wr = WorkflowResult(
            workflow="commit",
            steps=[
                StepResult(name="a", passed=True),
                StepResult(name="b", passed=False, skipped=True),
            ],
        )
        assert wr.passed is True


class TestGitleaksSubcommand:
    """Verify the gitleaks invocation uses 'protect' not 'detect'."""

    def test_gitleaks_uses_protect_subcommand(self, tmp_path: Path) -> None:
        """run_commit_workflow must call gitleaks with 'protect', not 'detect'."""
        calls_made: list[list[str]] = []

        def fake_run(
            cmd: list[str],
            cwd: Path,
            timeout: int = 60,
        ) -> tuple[bool, str]:
            calls_made.append(cmd)
            # Fail on the gitleaks step so we can inspect and short-circuit
            if cmd[0] == "gitleaks":
                return False, "simulated-gitleaks-output"
            return True, ""

        with (
            patch("ai_engineering.commands.workflows._run_command", side_effect=fake_run),
            patch(
                "ai_engineering.commands.workflows._check_branch_protection",
                return_value=StepResult(name="branch-protection", passed=True),
            ),
        ):
            run_commit_workflow(tmp_path, "test commit message")

        gitleaks_calls = [c for c in calls_made if c and c[0] == "gitleaks"]
        assert gitleaks_calls, "Expected at least one gitleaks invocation"
        gitleaks_cmd = gitleaks_calls[0]
        assert gitleaks_cmd[1] == "protect", (
            f"gitleaks must use 'protect' subcommand, got '{gitleaks_cmd[1]}'"
        )
        assert "--staged" in gitleaks_cmd, "gitleaks must include --staged flag"
        assert "detect" not in gitleaks_cmd, "'detect' must not appear in gitleaks command"
