"""More focused tests for remaining uncovered branches."""

from __future__ import annotations

import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai_engineering.doctor import service as doctor
from ai_engineering.hooks import manager as hooks_manager
from ai_engineering.maintenance import report as maint_report
from ai_engineering.pipeline import compliance
from ai_engineering.policy import gates
from ai_engineering.skills import service as skills_service
from ai_engineering.updater import service as updater
from ai_engineering.validator import service as validator
from ai_engineering.version import checker as version_checker


def test_doctor_remaining_branches(tmp_path: Path) -> None:
    report = doctor.DoctorReport()
    with patch("ai_engineering.doctor.service._get_current_branch", return_value="feature/x"):
        doctor._check_branch_policy(tmp_path, report)
    assert any(c.status == doctor.CheckStatus.OK for c in report.checks)

    report2 = doctor.DoctorReport()
    version = SimpleNamespace(
        status="supported", is_current=False, is_deprecated=False, is_eol=False, message="old"
    )
    with patch("ai_engineering.version.checker.check_version", return_value=version):
        doctor._check_version(report2)
    assert any(c.status == doctor.CheckStatus.WARN for c in report2.checks)

    with patch("ai_engineering.doctor.service.subprocess.run", return_value=SimpleNamespace()):
        assert doctor._try_install_tool("ruff") is True

    proc = SimpleNamespace(stdout="feature/test\n")
    with patch("ai_engineering.doctor.service.subprocess.run", return_value=proc):
        assert doctor._get_current_branch(tmp_path) == "feature/test"


def test_hooks_hash_loader_and_recorder_error_paths(tmp_path: Path) -> None:
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "install-manifest.json").write_text("{}", encoding="utf-8")
    with patch("ai_engineering.state.io.read_json_model", side_effect=ValueError("bad")):
        assert hooks_manager._load_expected_hook_hashes(tmp_path) == {}
        hooks_manager._record_hook_hashes(tmp_path)


def test_pipeline_compliance_remaining_lines(tmp_path: Path) -> None:
    report = compliance.ComplianceReport(
        results=[
            compliance.PipelineComplianceResult(
                pipeline=compliance.PipelineFile(
                    path=Path(".github/workflows/ci.yaml"),
                    pipeline_type=compliance.PipelineType.GITHUB_ACTIONS,
                ),
                checks=[
                    compliance.ComplianceCheck(
                        name="risk-gate-present", passed=False, detail="missing"
                    )
                ],
            )
        ]
    )
    md = report.to_markdown()
    assert "| Pipeline | Type | Compliant | Issues |" in md

    az_yaml = tmp_path / ".azure-pipelines" / "build.yaml"
    az_yaml.parent.mkdir(parents=True, exist_ok=True)
    az_yaml.write_text("steps:\n- script: echo hi\n", encoding="utf-8")
    detected = compliance.detect_pipelines(tmp_path)
    assert any(p.path.name == "build.yaml" for p in detected)


def test_gates_remaining_paths(tmp_path: Path) -> None:
    result = gates.GateResult(hook=gates.GateHook.COMMIT_MSG)
    msg_file = tmp_path / "msg.txt"
    msg_file.write_text("feat: x\n", encoding="utf-8")
    with patch.object(Path, "read_text", side_effect=OSError("x")):
        gates._run_commit_msg_checks(msg_file, result)
    assert result.checks[-1].passed is False

    with patch.object(Path, "write_text", side_effect=OSError("x")):
        gates._inject_gate_trailer(tmp_path / "msg2.txt")

    assert gates._validate_commit_message("")
    assert gates._validate_commit_message("\n")


def test_skills_service_remaining_paths(tmp_path: Path) -> None:
    skill = tmp_path / ".ai-engineering" / "skills" / "dev" / "s.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(
        "---\nname: s\nversion: 1.0.0\ncategory: dev\nrequires: {bins: [ruff]}\n---\n",
        encoding="utf-8",
    )
    with patch("ai_engineering.skills.service.shutil.which", return_value="/bin/ruff"):
        statuses = skills_service.list_local_skill_status(tmp_path)
    assert statuses[0].eligible is True

    with patch(
        "ai_engineering.skills.service.urllib.request.urlopen",
        side_effect=urllib.error.URLError("x"),
    ):
        assert skills_service._fetch_url("https://x") is None


def test_updater_report_validator_version_edges(tmp_path: Path) -> None:
    # updater rollback path
    ai = tmp_path / ".ai-engineering" / "state"
    ai.mkdir(parents=True, exist_ok=True)
    (ai / "ownership-map.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".ai-engineering").mkdir(exist_ok=True)
    with (
        patch("ai_engineering.updater.service._evaluate_governance_files", return_value=[]),
        patch("ai_engineering.updater.service._evaluate_project_files", return_value=[]),
    ):
        res = updater.update(tmp_path, dry_run=False)
    assert res.applied_count == 0

    # maintenance report warning branches
    (tmp_path / ".ai-engineering" / "state" / "install-manifest.json").unlink(missing_ok=True)
    rep = maint_report.generate_report(tmp_path)
    assert isinstance(rep.warnings, list)

    # validator claude mirror direct call branches
    report = validator.IntegrityReport()
    (tmp_path / ".claude" / "commands" / "a.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "commands" / "a.md").write_text("x", encoding="utf-8")
    validator._check_claude_commands_mirror(tmp_path, report)

    # version checker else-message branch
    registry = SimpleNamespace(
        versions=[
            SimpleNamespace(
                version="1.0.0", status=SimpleNamespace(value="supported"), deprecated_reason=None
            )
        ]
    )
    entry = SimpleNamespace(
        version="1.0.0", status=SimpleNamespace(value="supported"), deprecated_reason=None
    )
    with (
        patch("ai_engineering.version.checker.find_version_entry", return_value=entry),
        patch("ai_engineering.version.checker.find_latest_version", return_value=None),
    ):
        result = version_checker.check_version("1.0.0", registry=registry)
    assert "supported" in result.message
