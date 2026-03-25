"""Additional coverage for CLI command modules."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer

from ai_engineering.cli_commands import (
    core,
    gate,
    maintenance,
    review,
    stack_ide,
    validate,
    vcs,
)
from ai_engineering.policy.gates import GateCheckResult, GateHook, GateResult
from ai_engineering.state.defaults import default_install_state
from ai_engineering.state.service import save_install_state

pytestmark = pytest.mark.integration


def _pass_gate_result(hook: GateHook = GateHook.PRE_COMMIT) -> GateResult:
    return GateResult(hook=hook, checks=[GateCheckResult(name="ok", passed=True, output="ok")])


def test_gate_print_failure_shows_first_five_lines(capsys: pytest.CaptureFixture[str]) -> None:
    result = GateResult(
        hook=GateHook.PRE_PUSH,
        checks=[
            GateCheckResult(
                name="bad",
                passed=False,
                output="\n".join([f"line-{n}" for n in range(1, 7)]),
            )
        ],
    )
    with pytest.raises(typer.Exit):
        gate._print_gate_result(result)
    captured = capsys.readouterr()
    # info() writes to stderr via Rich Console
    assert "line-1" in captured.err
    assert "line-5" in captured.err
    assert "line-6" not in captured.err


def test_gate_print_scope_diagnostic_even_when_passed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = GateResult(
        hook=GateHook.PRE_PUSH,
        checks=[
            GateCheckResult(
                name="test-scope",
                passed=True,
                output="mode=shadow\nresolved_mode=selective\ntest_count=1",
            )
        ],
    )
    gate._print_gate_result(result)
    captured = capsys.readouterr()
    assert "mode=shadow" in captured.err
    assert "resolved_mode=selective" in captured.err


def test_gate_risk_check_no_store_prints_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gate.gate_risk_check(target=tmp_path)
    assert "No decision store found" in capsys.readouterr().err


def test_gate_risk_check_expired_exits(tmp_path: Path) -> None:
    ds = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    ds.parent.mkdir(parents=True, exist_ok=True)
    ds.write_text("{}", encoding="utf-8")
    expired = [SimpleNamespace(id="R-1", expires_at=datetime(2026, 1, 1, tzinfo=UTC))]
    with (
        patch("ai_engineering.cli_commands.gate.StateService") as mock_svc,
        patch("ai_engineering.cli_commands.gate.list_expired_decisions", return_value=expired),
        patch("ai_engineering.cli_commands.gate.list_expiring_soon", return_value=[]),
        pytest.raises(typer.Exit),
    ):
        mock_svc.return_value.load_decisions.return_value = object()
        gate.gate_risk_check(target=tmp_path)


def test_maintenance_pr_success_and_failure(tmp_path: Path) -> None:
    with (
        patch(
            "ai_engineering.cli_commands.maintenance.generate_report",
            return_value=SimpleNamespace(),
        ),
        patch("ai_engineering.cli_commands.maintenance.create_maintenance_pr", return_value=True),
    ):
        maintenance.maintenance_pr(target=tmp_path)

    with (
        patch(
            "ai_engineering.cli_commands.maintenance.generate_report",
            return_value=SimpleNamespace(),
        ),
        patch("ai_engineering.cli_commands.maintenance.create_maintenance_pr", return_value=False),
        pytest.raises(typer.Exit),
    ):
        maintenance.maintenance_pr(target=tmp_path)


def test_maintenance_branch_cleanup_fail_exits(tmp_path: Path) -> None:
    result = SimpleNamespace(success=False, to_markdown=lambda: "cleanup")
    with (
        patch("ai_engineering.cli_commands.maintenance.run_branch_cleanup", return_value=result),
        pytest.raises(typer.Exit),
    ):
        maintenance.maintenance_branch_cleanup(target=tmp_path)


def test_validate_unknown_category_exits(tmp_path: Path) -> None:
    with pytest.raises(typer.Exit):
        validate.validate_cmd(target=tmp_path, category="nope")


def test_validate_json_and_failure_exit(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    fake_report = SimpleNamespace(
        passed=False,
        to_dict=lambda: {"passed": False},
        by_category=lambda: {},
        category_passed=lambda _cat: False,
    )
    with (
        patch(
            "ai_engineering.cli_commands.validate.validate_content_integrity",
            return_value=fake_report,
        ),
        pytest.raises(typer.Exit),
    ):
        validate.validate_cmd(target=tmp_path, output_json=True)
    assert json.loads(capsys.readouterr().out)["passed"] is False


def test_vcs_status_and_set_primary(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import shutil

    from ai_engineering.installer.templates import get_ai_engineering_template_root

    ai_eng_dir = tmp_path / ".ai-engineering"
    ai_eng_dir.mkdir(parents=True, exist_ok=True)
    state_dir = ai_eng_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    save_install_state(state_dir, default_install_state())
    # Copy template manifest.yml so vcs_set_primary can update it
    shutil.copy2(get_ai_engineering_template_root() / "manifest.yml", ai_eng_dir / "manifest.yml")

    provider = SimpleNamespace(provider_name=lambda: "github", is_available=lambda: True)
    with patch("ai_engineering.cli_commands.vcs.get_provider", return_value=provider):
        vcs.vcs_status(target=tmp_path)
    captured = capsys.readouterr()
    # kv() writes to stderr via Rich Console
    assert "Primary provider" in captured.err

    vcs.vcs_set_primary("azure_devops", target=tmp_path)
    import yaml

    manifest_yml = tmp_path / ".ai-engineering" / "manifest.yml"
    updated = yaml.safe_load(manifest_yml.read_text(encoding="utf-8"))
    assert updated["providers"]["vcs"] == "azure_devops"


def test_vcs_set_primary_invalid_provider_exits(tmp_path: Path) -> None:
    with pytest.raises(typer.Exit):
        vcs.vcs_set_primary("bad", target=tmp_path)


def test_core_update_json_and_doctor_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_result = SimpleNamespace(
        dry_run=True,
        applied_count=1,
        denied_count=0,
        changes=[SimpleNamespace(path=Path("a"), action="update", diff="x\n" * 50)],
    )
    with patch("ai_engineering.cli_commands.core.update", return_value=fake_result):
        core.update_cmd(target=tmp_path, output_json=True)
    data = json.loads(capsys.readouterr().out)
    # JSON envelope wraps result under "result" key
    assert data["result"]["applied"] == 1

    report = SimpleNamespace(
        passed=False,
        summary={"fail": 1},
        checks=[SimpleNamespace(status=SimpleNamespace(value="fail"), name="x", message="bad")],
    )
    with (
        patch("ai_engineering.cli_commands.core.diagnose", return_value=report),
        pytest.raises(typer.Exit),
    ):
        core.doctor_cmd(target=tmp_path)


def test_stack_and_ide_empty_lists_and_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    empty_manifest = SimpleNamespace(providers=SimpleNamespace(stacks=[], ides=[]))
    with patch("ai_engineering.cli_commands.stack_ide.list_status", return_value=empty_manifest):
        stack_ide.stack_list(target=tmp_path)
        stack_ide.ide_list(target=tmp_path)
    captured = capsys.readouterr()
    # info() writes to stderr via Rich Console
    assert "No stacks configured" in captured.err
    assert "No IDEs configured" in captured.err

    with (
        patch(
            "ai_engineering.cli_commands.stack_ide.add_stack",
            side_effect=stack_ide.InstallerError("x"),
        ),
        pytest.raises(typer.Exit),
    ):
        stack_ide.stack_add("python", target=tmp_path)


def test_core_update_diff_truncation(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    diff_text = "\n".join([f"line-{i}" for i in range(200)])
    fake_result = SimpleNamespace(
        dry_run=True,
        applied_count=1,
        denied_count=0,
        changes=[SimpleNamespace(path=Path("f"), action="update", diff=diff_text)],
    )
    with patch("ai_engineering.cli_commands.core.update", return_value=fake_result):
        core.update_cmd(target=tmp_path, show_diff=True)
    assert "more lines" in capsys.readouterr().out


def test_gate_pre_push_and_risk_expiring_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch(
        "ai_engineering.cli_commands.gate.run_gate",
        return_value=_pass_gate_result(GateHook.PRE_PUSH),
    ):
        gate.gate_pre_push(target=tmp_path)

    ds = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    ds.parent.mkdir(parents=True, exist_ok=True)
    ds.write_text("{}", encoding="utf-8")
    expiring = [SimpleNamespace(id="R-2", expires_at=datetime(2026, 1, 1, tzinfo=UTC))]
    with (
        patch("ai_engineering.cli_commands.gate.StateService") as mock_svc,
        patch("ai_engineering.cli_commands.gate.list_expired_decisions", return_value=[]),
        patch("ai_engineering.cli_commands.gate.list_expiring_soon", return_value=expiring),
        pytest.raises(typer.Exit),
    ):
        mock_svc.return_value.load_decisions.return_value = object()
        gate.gate_risk_check(target=tmp_path, strict=True)
    assert "expiring soon" in capsys.readouterr().err


def test_maintenance_risk_status_branches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ds = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    ds.parent.mkdir(parents=True, exist_ok=True)
    ds.write_text("{}", encoding="utf-8")
    expiring = [SimpleNamespace(id="R-1", expires_at=datetime(2026, 1, 1, tzinfo=UTC), context="x")]
    expired = [SimpleNamespace(id="R-2", expires_at=datetime(2025, 1, 1, tzinfo=UTC), context="y")]
    store = SimpleNamespace(risk_decisions=lambda: [expiring[0], expired[0]])
    with (
        patch("ai_engineering.cli_commands.maintenance.StateService") as mock_svc,
        patch(
            "ai_engineering.cli_commands.maintenance.list_expired_decisions", return_value=expired
        ),
        patch("ai_engineering.cli_commands.maintenance.list_expiring_soon", return_value=expiring),
    ):
        mock_svc.return_value.load_decisions.return_value = store
        maintenance.maintenance_risk_status(target=tmp_path)
    captured = capsys.readouterr()
    assert "Expiring Soon" in captured.err
    assert "Expired" in captured.err


def test_validate_text_output_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    check = SimpleNamespace(
        status=SimpleNamespace(value="ok"),
        name="n",
        message="m",
        file_path="p",
    )
    fake_report = SimpleNamespace(
        passed=True,
        by_category=lambda: {cat: [check] for cat in validate.IntegrityCategory},
        category_passed=lambda _cat: True,
    )
    with patch(
        "ai_engineering.cli_commands.validate.validate_content_integrity", return_value=fake_report
    ):
        validate.validate_cmd(target=tmp_path)
    captured = capsys.readouterr()
    # result_header writes to stderr via Rich Console
    assert "Validate" in captured.err
    assert "PASS" in captured.err


def test_skills_cli_branches(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from ai_engineering.cli_commands import skills

    # skill_status with no skills
    with (
        patch("ai_engineering.cli_commands.skills.resolve_project_root", return_value=tmp_path),
        patch("ai_engineering.cli_commands.skills.list_local_skill_status", return_value=[]),
    ):
        skills.skill_status(target=tmp_path)
    captured = capsys.readouterr()
    assert "No local skills" in captured.err


def test_review_pr_strict_failure_exits(tmp_path: Path) -> None:
    provider = SimpleNamespace(
        post_pr_review=lambda _ctx, body: SimpleNamespace(success=False, output="boom")
    )
    with (
        patch("ai_engineering.cli_commands.review.get_provider", return_value=provider),
        pytest.raises(typer.Exit),
    ):
        review.review_pr(target=tmp_path, strict=True)


def test_review_pr_blocks_on_high_findings(tmp_path: Path) -> None:
    findings = tmp_path / "findings.json"
    findings.write_text(
        json.dumps({"findings": [{"severity": "high"}, {"severity": "low"}]}),
        encoding="utf-8",
    )
    provider = SimpleNamespace(
        post_pr_review=lambda _ctx, body: SimpleNamespace(success=True, output="ok")
    )
    with (
        patch("ai_engineering.cli_commands.review.get_provider", return_value=provider),
        pytest.raises(typer.Exit),
    ):
        review.review_pr(target=tmp_path, findings_json=findings)


def test_gate_all_combined_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch(
            "ai_engineering.cli_commands.gate.run_gate",
            return_value=_pass_gate_result(GateHook.PRE_COMMIT),
        ),
    ):
        gate.gate_all(target=tmp_path)
    captured = capsys.readouterr()
    assert "Gate All" in captured.err
    assert "PASS" in captured.err


def test_gate_all_any_fail_exits(tmp_path: Path) -> None:
    fail_result = GateResult(
        hook=GateHook.PRE_COMMIT,
        checks=[GateCheckResult(name="bad", passed=False, output="err")],
    )
    with (
        patch("ai_engineering.cli_commands.gate.run_gate", return_value=fail_result),
        pytest.raises(typer.Exit),
    ):
        gate.gate_all(target=tmp_path)


def test_maintenance_all_combined_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = SimpleNamespace(to_markdown=lambda: "report-md", to_dict=lambda: {})
    repo = SimpleNamespace(to_markdown=lambda: "repo-md", to_dict=lambda: {})
    spec = SimpleNamespace(to_markdown=lambda: "spec-md", success=True, to_dict=lambda: {})
    with (
        patch("ai_engineering.cli_commands.maintenance.generate_report", return_value=report),
        patch(
            "ai_engineering.cli_commands.maintenance._collect_risk_status",
            return_value={"active": 0, "expired": 0, "expiring_soon": 0},
        ),
        patch("ai_engineering.cli_commands.maintenance.run_repo_status", return_value=repo),
        patch("ai_engineering.cli_commands.maintenance.run_spec_reset", return_value=spec),
    ):
        maintenance.maintenance_all(target=tmp_path)
    captured = capsys.readouterr()
    assert "report-md" in captured.out
    assert "Maintenance" in captured.err
