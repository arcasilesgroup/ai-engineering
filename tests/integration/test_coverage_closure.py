"""Target uncovered branches to move toward full coverage."""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import typer

from ai_engineering.cli_commands import gate, maintenance, skills, stack_ide, validate, vcs
from ai_engineering.doctor import service as doctor
from ai_engineering.maintenance import branch_cleanup
from ai_engineering.policy import gates
from ai_engineering.skills import service as skills_service
from ai_engineering.validator import service as validator

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _reset_json_mode() -> None:
    """Ensure JSON mode is off so tests expecting human output are not affected by state leakage."""
    from ai_engineering.cli_output import set_json_mode

    set_json_mode(False)


def test_stack_ide_remaining_exception_paths(tmp_path: Path) -> None:
    with (
        patch(
            "ai_engineering.cli_commands.stack_ide.remove_stack",
            side_effect=stack_ide.InstallerError("x"),
        ),
        pytest.raises(typer.Exit),
    ):
        stack_ide.stack_remove("python", target=tmp_path)
    with (
        patch(
            "ai_engineering.cli_commands.stack_ide.add_ide",
            side_effect=stack_ide.InstallerError("x"),
        ),
        pytest.raises(typer.Exit),
    ):
        stack_ide.ide_add("vscode", target=tmp_path)
    with (
        patch(
            "ai_engineering.cli_commands.stack_ide.remove_ide",
            side_effect=stack_ide.InstallerError("x"),
        ),
        pytest.raises(typer.Exit),
    ):
        stack_ide.ide_remove("vscode", target=tmp_path)


def test_vcs_missing_manifest_paths(tmp_path: Path) -> None:
    with pytest.raises(typer.Exit):
        vcs.vcs_status(target=tmp_path)
    with pytest.raises(typer.Exit):
        vcs.vcs_set_primary("github", target=tmp_path)


def test_validate_single_category_mapping(tmp_path: Path) -> None:
    fake = SimpleNamespace(
        passed=True,
        by_category=lambda: {},
        category_passed=lambda _c: True,
        to_dict=lambda: {"passed": True, "checks": []},
    )
    with patch(
        "ai_engineering.cli_commands.validate.validate_content_integrity", return_value=fake
    ):
        validate.validate_cmd(target=tmp_path, category="file-existence")


def test_gate_risk_all_current_message(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ds = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    ds.parent.mkdir(parents=True, exist_ok=True)
    ds.write_text("{}", encoding="utf-8")
    with (
        patch("ai_engineering.cli_commands.gate.read_json_model", return_value=object()),
        patch("ai_engineering.cli_commands.gate.list_expired_decisions", return_value=[]),
        patch("ai_engineering.cli_commands.gate.list_expiring_soon", return_value=[]),
    ):
        gate.gate_risk_check(target=tmp_path)
    assert "All risk acceptances are current" in capsys.readouterr().err


def test_maintenance_risk_status_missing_store(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    maintenance.maintenance_risk_status(target=tmp_path)
    assert "No decision store found" in capsys.readouterr().err


def test_skills_status_empty_and_all_eligible(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with patch("ai_engineering.cli_commands.skills.list_local_skill_status", return_value=[]):
        skills.skill_status(target=tmp_path)
    assert "No local skills" in capsys.readouterr().err

    statuses = [SimpleNamespace(eligible=True)]
    with patch("ai_engineering.cli_commands.skills.list_local_skill_status", return_value=statuses):
        skills.skill_status(target=tmp_path)
    captured = capsys.readouterr()
    # success() writes to stderr via Rich Console
    assert "All 1 skills are eligible" in captured.err


def test_branch_cleanup_remaining_paths(tmp_path: Path) -> None:
    result = branch_cleanup.CleanupResult(
        errors=["x"], deleted_branches=["a"], skipped_branches=["b"]
    )
    md = result.to_markdown()
    assert "### Errors" in md

    with patch("ai_engineering.maintenance.branch_cleanup.run_git", return_value=(False, "err")):
        ok, count = branch_cleanup.fetch_and_prune(tmp_path)
    assert ok is False and count == 0

    with (
        patch("ai_engineering.maintenance.branch_cleanup.current_branch", return_value="feature"),
        patch(
            "ai_engineering.maintenance.branch_cleanup.run_git",
            return_value=(False, "cannot checkout"),
        ),
    ):
        res = branch_cleanup.run_branch_cleanup(tmp_path, base_branch="main")
    assert res.success is False


def test_doctor_remaining_branches(tmp_path: Path) -> None:
    report = doctor.DoctorReport()
    with patch("ai_engineering.doctor.service._is_tool_available", return_value=False):
        doctor._check_tools(report, fix=False)
    assert any(c.status == doctor.CheckStatus.WARN for c in report.checks)

    report2 = doctor.DoctorReport()
    with (
        patch("ai_engineering.doctor.service._is_tool_available", return_value=False),
        patch("ai_engineering.doctor.service._try_install_tool", return_value=False),
    ):
        doctor._check_tools(report2, fix=True)
    assert any(c.status == doctor.CheckStatus.FAIL for c in report2.checks)

    report3 = doctor.DoctorReport()
    with patch("ai_engineering.doctor.service._get_current_branch", return_value="main"):
        doctor._check_branch_policy(tmp_path, report3)
    assert any("protected branch" in c.message for c in report3.checks)

    report4 = doctor.DoctorReport()
    version = SimpleNamespace(
        status=None, message="warn", is_current=False, is_deprecated=False, is_eol=False
    )
    with patch("ai_engineering.version.checker.check_version", return_value=version):
        doctor._check_version(report4)
    assert any(c.name == "version-lifecycle" for c in report4.checks)

    with patch("ai_engineering.doctor.service.subprocess.run", side_effect=FileNotFoundError):
        assert doctor._try_install_tool("x") is False


def test_gates_remaining_branches(tmp_path: Path) -> None:
    result = gates.GateResult(hook=gates.GateHook.PRE_PUSH)
    long_output = "x" * 700
    proc = SimpleNamespace(returncode=1, stdout=long_output, stderr="")
    with (
        patch("ai_engineering.policy.gates.shutil.which", return_value="/bin/cmd"),
        patch("ai_engineering.policy.gates.subprocess.run", return_value=proc),
    ):
        gates._run_tool_check(result, name="tool", cmd=["cmd"], cwd=tmp_path)
    assert "truncated" in result.checks[-1].output

    result2 = gates.GateResult(hook=gates.GateHook.PRE_PUSH)
    with (
        patch("ai_engineering.policy.gates.shutil.which", return_value="/bin/cmd"),
        patch(
            "ai_engineering.policy.gates.subprocess.run",
            side_effect=subprocess.TimeoutExpired("cmd", 1),
        ),
    ):
        gates._run_tool_check(result2, name="tool", cmd=["cmd"], cwd=tmp_path)
    assert "timed out" in result2.checks[-1].output

    result3 = gates.GateResult(hook=gates.GateHook.PRE_PUSH)
    with patch("ai_engineering.policy.gates.shutil.which", return_value=None):
        gates._run_tool_check(result3, name="tool", cmd=["cmd"], cwd=tmp_path, required=False)
    assert "skipped" in result3.checks[-1].output

    with patch("ai_engineering.policy.gates.read_json_model", side_effect=ValueError("bad")):
        assert gates._load_decision_store(tmp_path) is None


def test_skills_service_remaining_branches(tmp_path: Path) -> None:
    skill = tmp_path / ".ai-engineering" / "skills" / "dev" / "a.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(
        "---\nname: a\nversion: 1.0.0\ncategory: dev\nos: [linux]\n---\n", encoding="utf-8"
    )
    with patch("ai_engineering.skills.service.sys.platform", "darwin"):
        statuses = skills_service.list_local_skill_status(tmp_path)
    assert statuses[0].missing_os == ["linux"]

    bad = tmp_path / "bad.json"
    bad.write_text("[1,2]", encoding="utf-8")
    assert skills_service._safe_json_load(bad) == {}

    p = tmp_path / "front.md"
    p.write_text("---\nname: [\n---\n", encoding="utf-8")
    _, err = skills_service._load_skill_frontmatter(p)
    assert "invalid-frontmatter-yaml" in err[0]

    assert skills_service._ensure_str_list("x") == []


def test_validator_remaining_branches(tmp_path: Path) -> None:
    ai = tmp_path / ".ai-engineering"
    (ai / "skills" / "dev").mkdir(parents=True, exist_ok=True)
    (ai / "agents").mkdir(parents=True, exist_ok=True)
    # trigger cross-ref continue path for blank ref
    f = ai / "skills" / "dev" / "a.md"
    f.write_text("# a\n\n## References\n- ``\n", encoding="utf-8")
    report = validator.validate_content_integrity(
        tmp_path, categories=[validator.IntegrityCategory.CROSS_REFERENCE]
    )
    assert report.category_passed(validator.IntegrityCategory.CROSS_REFERENCE)

    # explicit frontmatter list type failure (directory-based skill layout)
    (ai / "skills" / "dev" / "bad-skill").mkdir(parents=True, exist_ok=True)
    g = ai / "skills" / "dev" / "bad-skill" / "SKILL.md"
    g.write_text("---\n- a\n---\n", encoding="utf-8")
    report2 = validator.validate_content_integrity(
        tmp_path, categories=[validator.IntegrityCategory.SKILL_FRONTMATTER]
    )
    assert report2.category_passed(validator.IntegrityCategory.SKILL_FRONTMATTER) is False
