"""Additional coverage for CLI command modules."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer

from ai_engineering.cli_commands import core, gate, maintenance, stack_ide, validate, vcs
from ai_engineering.policy.gates import GateCheckResult, GateHook, GateResult
from ai_engineering.skills.service import SkillStatus, SyncResult
from ai_engineering.state.defaults import default_install_manifest
from ai_engineering.state.io import write_json_model


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
    out = capsys.readouterr().out
    assert "line-1" in out
    assert "line-5" in out
    assert "line-6" not in out


def test_gate_risk_check_no_store_prints_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gate.gate_risk_check(target=tmp_path)
    assert "No decision store found" in capsys.readouterr().out


def test_gate_risk_check_expired_exits(tmp_path: Path) -> None:
    ds = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    ds.parent.mkdir(parents=True, exist_ok=True)
    ds.write_text("{}", encoding="utf-8")
    expired = [SimpleNamespace(id="R-1", expires_at=datetime(2026, 1, 1, tzinfo=UTC))]
    with (
        patch("ai_engineering.cli_commands.gate.read_json_model", return_value=object()),
        patch("ai_engineering.cli_commands.gate.list_expired_decisions", return_value=expired),
        patch("ai_engineering.cli_commands.gate.list_expiring_soon", return_value=[]),
        pytest.raises(typer.Exit),
    ):
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


def test_maintenance_pipeline_compliance_with_suggest(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    report = SimpleNamespace(
        to_markdown=lambda: "report",
        results=[SimpleNamespace(compliant=False, pipeline=".github/workflows/ci.yml")],
    )
    with (
        patch("ai_engineering.cli_commands.maintenance.scan_all_pipelines", return_value=report),
        patch("ai_engineering.cli_commands.maintenance.suggest_injection", return_value="inject"),
    ):
        maintenance.maintenance_pipeline_compliance(target=tmp_path, suggest=True)
    out = capsys.readouterr().out
    assert "report" in out
    assert "inject" in out


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
    manifest_path = tmp_path / ".ai-engineering" / "state" / "install-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_model(manifest_path, default_install_manifest(vcs_provider="github"))

    provider = SimpleNamespace(provider_name=lambda: "github", is_available=lambda: True)
    with patch("ai_engineering.cli_commands.vcs.get_provider", return_value=provider):
        vcs.vcs_status(target=tmp_path)
    out = capsys.readouterr().out
    assert "Primary provider" in out

    vcs.vcs_set_primary("azure_devops", target=tmp_path)
    updated = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert updated["providers"]["primary"] == "azure_devops"


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
    assert json.loads(capsys.readouterr().out)["applied"] == 1

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
    empty_manifest = SimpleNamespace(installed_stacks=[], installed_ides=[])
    with patch("ai_engineering.cli_commands.stack_ide.list_status", return_value=empty_manifest):
        stack_ide.stack_list(target=tmp_path)
        stack_ide.ide_list(target=tmp_path)
    out = capsys.readouterr().out
    assert "(no stacks configured)" in out
    assert "(no IDEs configured)" in out

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
        patch("ai_engineering.cli_commands.gate.read_json_model", return_value=object()),
        patch("ai_engineering.cli_commands.gate.list_expired_decisions", return_value=[]),
        patch("ai_engineering.cli_commands.gate.list_expiring_soon", return_value=expiring),
        pytest.raises(typer.Exit),
    ):
        gate.gate_risk_check(target=tmp_path, strict=True)
    assert "expiring soon" in capsys.readouterr().out


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
        patch("ai_engineering.cli_commands.maintenance.read_json_model", return_value=store),
        patch(
            "ai_engineering.cli_commands.maintenance.list_expired_decisions", return_value=expired
        ),
        patch("ai_engineering.cli_commands.maintenance.list_expiring_soon", return_value=expiring),
    ):
        maintenance.maintenance_risk_status(target=tmp_path)
    out = capsys.readouterr().out
    assert "Expiring Soon" in out
    assert "Expired" in out


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
    assert "Content Integrity [PASS]" in capsys.readouterr().out


def test_skills_cli_branches(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from ai_engineering.cli_commands import skills as skills_cmd

    with patch("ai_engineering.cli_commands.skills.list_sources", return_value=[]):
        skills_cmd.skill_list(target=tmp_path)

    src = SimpleNamespace(url="https://x", trusted=False)
    with patch("ai_engineering.cli_commands.skills.list_sources", return_value=[src]):
        skills_cmd.skill_list(target=tmp_path)

    sync = SyncResult(fetched=["a"], cached=["b"], failed=["c"], untrusted=["d"])
    with patch("ai_engineering.cli_commands.skills.sync_sources", return_value=sync):
        skills_cmd.skill_sync(target=tmp_path)

    with (
        patch("ai_engineering.cli_commands.skills.add_source", side_effect=ValueError("dup")),
        pytest.raises(typer.Exit),
    ):
        skills_cmd.skill_add("https://x", target=tmp_path)

    with (
        patch(
            "ai_engineering.cli_commands.skills.remove_source", side_effect=ValueError("missing")
        ),
        pytest.raises(typer.Exit),
    ):
        skills_cmd.skill_remove("https://x", target=tmp_path)

    statuses = [
        SkillStatus(
            name="s",
            file_path=".ai-engineering/skills/dev/s.md",
            eligible=False,
            missing_bins=["bin"],
            missing_any_bins=["a", "b"],
            missing_env=["ENV"],
            missing_config=["cfg.path"],
            missing_os=["linux"],
            errors=["e"],
        )
    ]
    with patch("ai_engineering.cli_commands.skills.list_local_skill_status", return_value=statuses):
        skills_cmd.skill_status(target=tmp_path, all_skills=True)
    out = capsys.readouterr().out
    assert "missing bins" in out
    assert "Summary:" in out
