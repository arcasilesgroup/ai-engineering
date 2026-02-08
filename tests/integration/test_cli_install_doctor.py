"""Integration tests for install and doctor CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ai_engineering.cli import app


runner = CliRunner()


def test_install_creates_required_state_files(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()

    result = runner.invoke(app, ["install"])

    assert result.exit_code == 0
    state_root = temp_repo / ".ai-engineering" / "state"
    assert (state_root / "install-manifest.json").exists()
    assert (state_root / "ownership-map.json").exists()
    assert (state_root / "sources.lock.json").exists()
    assert (state_root / "decision-store.json").exists()
    assert (state_root / "audit-log.ndjson").exists()

    hooks_root = temp_repo / ".git" / "hooks"
    for hook in ("pre-commit", "commit-msg", "pre-push"):
        hook_path = hooks_root / hook
        assert hook_path.exists()
        assert "ai-engineering managed hook" in hook_path.read_text(encoding="utf-8")


def test_doctor_json_reports_expected_sections(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    result = runner.invoke(app, ["doctor", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "repo" in payload
    assert "stateFiles" in payload
    assert "toolingReadiness" in payload
    assert "branchPolicy" in payload
    assert "gitHooks" in payload["toolingReadiness"]


def test_gate_list_json_reports_stages(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    result = runner.invoke(app, ["gate", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "protectedBranches" in payload
    assert "stages" in payload
    assert "pre-commit" in payload["stages"]


def test_skill_list_json_after_install(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    result = runner.invoke(app, ["skill", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "sources" in payload
    assert len(payload["sources"]) >= 1


def test_maintenance_report_command_creates_report(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0
    (temp_repo / ".ai-engineering" / "context" / "delivery" / "planning.md").write_text(
        "# Planning\n", encoding="utf-8"
    )

    result = runner.invoke(app, ["maintenance", "report"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["reportPath"]


def test_maintenance_pr_command_requires_approved_payload(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0
    payload_path = temp_repo / ".ai-engineering" / "state" / "maintenance_pr_payload.json"
    payload_path.write_text(
        '{"approved": false, "title": "x", "body": "y", "base": "main", "head": "feature/x"}\n',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["maintenance", "pr"])

    assert result.exit_code == 1
    assert "not approved" in result.stdout
