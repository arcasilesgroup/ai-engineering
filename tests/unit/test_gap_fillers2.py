"""Additional targeted tests for remaining uncovered branches."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer

from ai_engineering.cli_commands import stack_ide
from ai_engineering.cli_factory import _version_lifecycle_callback
from ai_engineering.commands import workflows
from ai_engineering.detector import readiness
from ai_engineering.git import operations as git_ops
from ai_engineering.hooks import manager as hooks_manager
from ai_engineering.installer import operations as installer_ops
from ai_engineering.paths import ai_engineering_dir, state_dir
from ai_engineering.pipeline import injector
from ai_engineering.validator import service as validator
from ai_engineering.version import checker as version_checker


def test_stack_list_and_ide_list_error_paths(tmp_path: Path) -> None:
    with (
        patch(
            "ai_engineering.cli_commands.stack_ide.list_status",
            side_effect=stack_ide.InstallerError("x"),
        ),
        pytest.raises(typer.Exit),
    ):
        stack_ide.stack_list(target=tmp_path)
    with (
        patch(
            "ai_engineering.cli_commands.stack_ide.list_status",
            side_effect=stack_ide.InstallerError("x"),
        ),
        pytest.raises(typer.Exit),
    ):
        stack_ide.ide_list(target=tmp_path)


def test_cli_factory_callback_no_subcommand() -> None:
    _version_lifecycle_callback(SimpleNamespace(invoked_subcommand=None))


def test_workflows_remaining_failure_paths(tmp_path: Path) -> None:
    with patch(
        "ai_engineering.commands.workflows._run_command", return_value=(False, "stage fail")
    ):
        wf = workflows.run_commit_workflow(tmp_path, "msg")
    assert wf.passed is False

    seq = iter([(True, "ok"), (False, "format fail")])
    with patch(
        "ai_engineering.commands.workflows._run_command", side_effect=lambda *a, **k: next(seq)
    ):
        wf2 = workflows.run_commit_workflow(tmp_path, "msg")
    assert "format" in wf2.failed_steps

    def _mock_commit_failure(cmd: list[str], cwd: Path, **kwargs: object) -> tuple[bool, str]:
        if cmd[:2] == ["git", "commit"]:
            return False, "commit fail"
        return True, "ok"

    with patch("ai_engineering.commands.workflows._run_command", side_effect=_mock_commit_failure):
        wf3 = workflows.run_commit_workflow(tmp_path, "msg")
    assert "commit" in wf3.failed_steps

    with (
        patch(
            "ai_engineering.commands.workflows.run_commit_workflow",
            return_value=workflows.WorkflowResult("commit", [workflows.StepResult("x", True)]),
        ),
        patch("ai_engineering.commands.workflows._run_pre_push_checks", return_value=[]),
        patch(
            "ai_engineering.commands.workflows._create_pr",
            return_value=workflows.StepResult(name="create-pr", passed=False),
        ),
    ):
        wf4 = workflows.run_pr_workflow(tmp_path, "msg")
    assert wf4.passed is False

    with (
        patch("ai_engineering.commands.workflows.is_branch_pushed", return_value=True),
        patch(
            "ai_engineering.commands.workflows._create_pr",
            return_value=workflows.StepResult(name="create-pr", passed=False),
        ),
    ):
        wf5 = workflows.run_pr_only_workflow(tmp_path)
    assert wf5.passed is False

    store_dir = tmp_path / ".ai-engineering" / "state"
    store_dir.mkdir(parents=True, exist_ok=True)
    (store_dir / "decision-store.json").write_text("{}", encoding="utf-8")
    decision = SimpleNamespace(decision="defer-pr")
    store = SimpleNamespace(find_by_context_hash=lambda _h: decision)
    with (
        patch("ai_engineering.commands.workflows.read_json_model", return_value=store),
        patch("ai_engineering.state.decision_logic.compute_context_hash", return_value="h"),
    ):
        val = workflows._check_unpushed_decision(tmp_path, "feature/x")
    assert val == "defer-pr"


def test_detector_git_paths_hooks_installer_misc(tmp_path: Path) -> None:
    with patch(
        "ai_engineering.detector.readiness.subprocess.run",
        side_effect=subprocess.TimeoutExpired("x", 1),
    ):
        assert readiness._get_version("ruff") is None

    with (
        patch("ai_engineering.detector.readiness.shutil.which", return_value="/bin/uv"),
        patch(
            "ai_engineering.detector.readiness.subprocess.run",
            side_effect=[subprocess.CalledProcessError(1, "uv"), FileNotFoundError()],
        ),
    ):
        assert readiness._try_install("ruff") is False

    with patch("ai_engineering.git.operations.subprocess.run", side_effect=FileNotFoundError):
        ok, _ = git_ops.run_git(["status"], tmp_path)
    assert ok is False

    assert ai_engineering_dir(tmp_path) == tmp_path / ".ai-engineering"
    assert state_dir(tmp_path) == tmp_path / ".ai-engineering" / "state"

    hook = tmp_path / "hook"
    hook.write_text("x", encoding="utf-8")
    with patch.object(Path, "read_text", side_effect=UnicodeDecodeError("utf-8", b"x", 0, 1, "e")):
        assert hooks_manager.is_managed_hook(hook) is False
    with patch.object(Path, "chmod", side_effect=OSError):
        hooks_manager._make_executable(hook)

    with patch("ai_engineering.installer.operations.TEMPLATES_ROOT", tmp_path):
        assert installer_ops.get_available_stacks() == []
    with pytest.raises(installer_ops.InstallerError):
        installer_ops._load_manifest(tmp_path / "missing.json")


def test_injector_version_validator_private_paths(tmp_path: Path) -> None:
    with patch.object(injector, "_TEMPLATES_DIR", tmp_path):
        assert "Risk Governance Gate" in injector.generate_github_step()
        assert "Risk Governance Gate" in injector.generate_azure_task()

    reg = SimpleNamespace(
        versions=[SimpleNamespace(version="1.0.0"), SimpleNamespace(version="bad")]
    )
    assert version_checker.find_latest_version(reg) == "1.0.0"

    assert validator._as_string_list([1]) is None
    report = validator.IntegrityReport()
    validator._check_counter_accuracy(tmp_path, report)
    report2 = validator.IntegrityReport()
    validator._check_manifest_coherence(tmp_path, report2)
