"""Integration tests for install and doctor CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ai_engineering.cli import app
from ai_engineering.paths import template_root


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
    state_gitignore = state_root / ".gitignore"
    assert state_gitignore.exists()
    ignore_text = state_gitignore.read_text(encoding="utf-8")
    assert "!decision-store.json" in ignore_text
    assert "!audit-log.ndjson" not in ignore_text

    hooks_root = temp_repo / ".git" / "hooks"
    for hook in ("pre-commit", "commit-msg", "pre-push"):
        hook_path = hooks_root / hook
        assert hook_path.exists()
        assert "ai-engineering managed hook" in hook_path.read_text(encoding="utf-8")
        assert "lefthook" not in hook_path.read_text(encoding="utf-8")

    assert (
        temp_repo / ".ai-engineering" / "standards" / "framework" / "quality" / "core.md"
    ).exists()
    assert (temp_repo / ".ai-engineering" / "skills" / "utils" / "platform-detection.md").exists()
    assert (temp_repo / "CLAUDE.md").exists()
    assert (temp_repo / "codex.md").exists()
    assert (temp_repo / ".github" / "copilot-instructions.md").exists()


def test_install_preserves_existing_team_owned_files(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    team_core = temp_repo / ".ai-engineering" / "standards" / "team" / "core.md"
    team_core.parent.mkdir(parents=True, exist_ok=True)
    team_core.write_text("custom team content\n", encoding="utf-8")

    result = runner.invoke(app, ["install"])

    assert result.exit_code == 0
    assert team_core.read_text(encoding="utf-8") == "custom team content\n"


def test_install_creates_all_governance_template_files(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()

    result = runner.invoke(app, ["install"])

    assert result.exit_code == 0
    governance_templates = template_root() / ".ai-engineering"
    for template_file in governance_templates.rglob("*"):
        if not template_file.is_file():
            continue
        relative = template_file.relative_to(governance_templates)
        installed = temp_repo / ".ai-engineering" / relative
        assert installed.exists()


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


def test_install_replaces_lefthook_wrappers(temp_repo: Path) -> None:
    hooks_root = temp_repo / ".git" / "hooks"
    hooks_root.mkdir(parents=True)
    for hook in ("pre-commit", "commit-msg", "pre-push"):
        (hooks_root / hook).write_text("#!/bin/sh\nlefthook run pre-commit\n", encoding="utf-8")

    result = runner.invoke(app, ["install"])

    assert result.exit_code == 0
    for hook in ("pre-commit", "commit-msg", "pre-push"):
        content = (hooks_root / hook).read_text(encoding="utf-8")
        assert "ai-engineering managed hook" in content
        assert "lefthook" not in content


def test_doctor_fix_hooks_repairs_external_wrapper(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    hooks_root = temp_repo / ".git" / "hooks"
    hooks_root.mkdir(parents=True, exist_ok=True)
    (hooks_root / "pre-commit").write_text("#!/bin/sh\nlefthook run pre-commit\n", encoding="utf-8")
    (hooks_root / "commit-msg").write_text("#!/bin/sh\nlefthook run commit-msg\n", encoding="utf-8")
    (hooks_root / "pre-push").write_text("#!/bin/sh\nlefthook run pre-push\n", encoding="utf-8")

    result = runner.invoke(app, ["doctor", "--json", "--fix-hooks"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    hook_payload = payload["toolingReadiness"]["gitHooks"]
    assert hook_payload["installed"] is True
    assert hook_payload["managedByFramework"] is True


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


def test_update_dry_run_reports_framework_managed_changes(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    quality_core = temp_repo / ".ai-engineering" / "standards" / "framework" / "quality" / "core.md"
    quality_core.write_text("custom framework override\n", encoding="utf-8")

    result = runner.invoke(app, ["update"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    statuses = {entry["path"]: entry["status"] for entry in payload["entries"]}
    assert statuses[".ai-engineering/standards/framework/quality/core.md"] == "updated"
    assert quality_core.read_text(encoding="utf-8") == "custom framework override\n"


def test_update_apply_preserves_team_owned_content(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    team_core = temp_repo / ".ai-engineering" / "standards" / "team" / "core.md"
    team_core.parent.mkdir(parents=True, exist_ok=True)
    team_core.write_text("team custom\n", encoding="utf-8")

    result = runner.invoke(app, ["update", "--apply"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    statuses = {entry["path"]: entry["status"] for entry in payload["entries"]}
    assert statuses[".ai-engineering/standards/framework/quality/core.md"] in {
        "unchanged",
        "updated",
    }
    assert team_core.read_text(encoding="utf-8") == "team custom\n"


def test_stack_add_and_remove_updates_manifest(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    remove_result = runner.invoke(app, ["stack", "remove", "python"])
    assert remove_result.exit_code == 0
    removed_payload = json.loads(remove_result.stdout)
    assert "python" not in removed_payload["installedStacks"]

    add_result = runner.invoke(app, ["stack", "add", "python"])
    assert add_result.exit_code == 0
    add_payload = json.loads(add_result.stdout)
    assert "python" in add_payload["installedStacks"]


def test_stack_remove_preserves_custom_team_stack_file(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    team_stack = temp_repo / ".ai-engineering" / "standards" / "team" / "stacks" / "python.md"
    team_stack.write_text("custom team python stack\n", encoding="utf-8")

    remove_result = runner.invoke(app, ["stack", "remove", "python"])
    assert remove_result.exit_code == 0
    payload = json.loads(remove_result.stdout)
    assert payload["result"]["team"] == "skipped-customized"
    assert team_stack.exists()


def test_ide_add_remove_copilot_file(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    copilot_file = temp_repo / ".github" / "copilot-instructions.md"
    if copilot_file.exists():
        copilot_file.unlink()

    add_result = runner.invoke(app, ["ide", "add", "copilot"])
    assert add_result.exit_code == 0
    assert copilot_file.exists()

    remove_result = runner.invoke(app, ["ide", "remove", "copilot"])
    assert remove_result.exit_code == 0
    payload = json.loads(remove_result.stdout)
    assert payload["result"] in {"removed", "missing"}


def test_gate_risk_accept_persists_decision_and_audit(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "gate",
            "risk-accept",
            "--policy-id",
            "MANDATORY_TOOLING_ENFORCEMENT",
            "--policy-version",
            "1",
            "--decision",
            "accept-risk",
            "--rationale",
            "manual exception requested",
            "--severity",
            "high",
            "--context",
            '{"scope":"pre-push"}',
            "--path-pattern",
            "src/**",
            "--actor",
            "tester",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["policyId"] == "MANDATORY_TOOLING_ENFORCEMENT"
    assert payload["severity"] == "high"

    state_root = temp_repo / ".ai-engineering" / "state"
    store = json.loads((state_root / "decision-store.json").read_text(encoding="utf-8"))
    assert len(store["decisions"]) >= 1
    events = (state_root / "audit-log.ndjson").read_text(encoding="utf-8").splitlines()
    assert any("risk_acceptance_recorded" in event for event in events)


def test_gate_risk_check_reports_policy_change(temp_repo: Path) -> None:
    (temp_repo / ".git").mkdir()
    install_result = runner.invoke(app, ["install"])
    assert install_result.exit_code == 0

    accept_result = runner.invoke(
        app,
        [
            "gate",
            "risk-accept",
            "--policy-id",
            "NO_DIRECT_COMMIT_PROTECTED_BRANCH",
            "--policy-version",
            "1",
            "--decision",
            "defer-pr",
            "--rationale",
            "test",
            "--context",
            '{"branch":"feature/x"}',
        ],
    )
    assert accept_result.exit_code == 0

    check_result = runner.invoke(
        app,
        [
            "gate",
            "risk-check",
            "--policy-id",
            "NO_DIRECT_COMMIT_PROTECTED_BRANCH",
            "--policy-version",
            "2",
            "--severity",
            "medium",
            "--context",
            '{"branch":"feature/x"}',
        ],
    )
    assert check_result.exit_code == 0
    payload = json.loads(check_result.stdout)
    assert payload["reusable"] is False
    assert payload["reason"] == "policy_changed"
