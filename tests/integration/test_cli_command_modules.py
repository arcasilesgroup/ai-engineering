"""Additional coverage for CLI command modules."""

from __future__ import annotations

import json
import uuid
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
    stack_ide,
    validate,
    vcs,
)
from ai_engineering.cli_output import set_json_mode
from ai_engineering.policy.gates import GateCheckResult, GateHook, GateResult
from ai_engineering.state.defaults import default_install_state
from ai_engineering.state.models import GateFindingsDocument
from ai_engineering.state.service import save_install_state
from ai_engineering.updater.service import FileChange, UpdateResult


@pytest.fixture(autouse=True)
def _reset_json_mode() -> None:
    set_json_mode(False)
    yield
    set_json_mode(False)


def _pass_gate_result(hook: GateHook = GateHook.PRE_COMMIT) -> GateResult:
    return GateResult(hook=hook, checks=[GateCheckResult(name="ok", passed=True, output="ok")])


def _gate_document(*, severity: str | None = None) -> GateFindingsDocument:
    findings = []
    if severity is not None:
        findings.append(
            {
                "check": "pytest-smoke",
                "rule_id": "PYTEST-001",
                "file": "tests/example.py",
                "line": 1,
                "column": 1,
                "severity": severity,
                "message": f"example {severity} finding",
                "auto_fixable": False,
                "auto_fix_command": None,
            }
        )
    return GateFindingsDocument.model_validate(
        {
            "schema": "ai-engineering/gate-findings/v1",
            "session_id": str(uuid.uuid4()),
            "produced_by": "ai-commit",
            "produced_at": datetime.now(UTC).isoformat(),
            "branch": "feature/test",
            "commit_sha": "0" * 40,
            "findings": findings,
            "auto_fixed": [],
            "cache_hits": [],
            "cache_misses": [],
            "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
        }
    )


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
    ai_eng_dir = tmp_path / ".ai-engineering"
    state_dir = ai_eng_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    save_install_state(state_dir, default_install_state())

    manifest_yml = ai_eng_dir / "manifest.yml"
    manifest_yml.write_text(
        "providers:\n  vcs: github\n  stacks:\n    - python\n", encoding="utf-8"
    )

    provider = SimpleNamespace(provider_name=lambda: "github", is_available=lambda: True)
    with patch("ai_engineering.cli_commands.vcs.get_provider", return_value=provider):
        vcs.vcs_status(target=tmp_path)
    captured = capsys.readouterr()
    assert "Primary provider" in captured.err

    vcs.vcs_set_primary("azure_devops", target=tmp_path)
    import yaml

    updated = yaml.safe_load(manifest_yml.read_text(encoding="utf-8"))
    assert updated["providers"]["vcs"] == "azure_devops"


def test_vcs_set_primary_invalid_provider_exits(tmp_path: Path) -> None:
    with pytest.raises(typer.Exit):
        vcs.vcs_set_primary("bad", target=tmp_path)


def test_core_update_json_and_doctor_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fake_result = UpdateResult(
        dry_run=True,
        changes=[
            FileChange(
                path=Path("a"),
                action="update",
                diff="x\n" * 50,
                reason_code="template-drift",
                explanation="Template update available.",
                recommended_action="Apply the update.",
            )
        ],
    )
    with patch("ai_engineering.cli_commands.core.update", return_value=fake_result):
        core.update_cmd(target=tmp_path, output_json=True)
    data = json.loads(capsys.readouterr().out)
    # JSON envelope wraps result under "result" key
    assert data["result"]["applied"] == 1
    assert data["result"]["changes"][0]["reason_code"] == "template-drift"

    report = SimpleNamespace(
        passed=False,
        installed=True,
        summary={"fail": 1},
        phases=[
            SimpleNamespace(
                name="detect",
                status=SimpleNamespace(value="fail"),
                checks=[
                    SimpleNamespace(status=SimpleNamespace(value="fail"), name="x", message="bad")
                ],
            )
        ],
        runtime=[],
        has_warnings=False,
    )
    with (
        patch("ai_engineering.cli_commands.core.diagnose", return_value=report),
        pytest.raises(typer.Exit),
    ):
        core.doctor_cmd(target=tmp_path)


def test_core_doctor_json_suggests_fix_only_for_fixable_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = SimpleNamespace(
        passed=False,
        installed=True,
        summary={"warn": 1},
        phases=[
            SimpleNamespace(
                name="hooks",
                status=SimpleNamespace(value="warn"),
                checks=[
                    SimpleNamespace(
                        status=SimpleNamespace(value="warn"),
                        name="hooks-runtime",
                        message="runtime launcher missing",
                        fixable=True,
                    )
                ],
            )
        ],
        runtime=[],
        has_warnings=True,
        to_dict=lambda: {"passed": False, "summary": {"warn": 1}},
    )
    with (
        patch("ai_engineering.cli_commands.core.diagnose", return_value=report),
        pytest.raises(typer.Exit),
    ):
        core.doctor_cmd(target=tmp_path, output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert data["next_actions"] == [
        {
            "command": "ai-eng doctor --fix",
            "description": "Attempt automatic repairs for fixable issues",
            "params": None,
        }
    ]


def test_core_doctor_json_omits_fix_when_follow_up_is_manual(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = SimpleNamespace(
        passed=False,
        installed=True,
        summary={"fail": 1},
        phases=[
            SimpleNamespace(
                name="runtime",
                status=SimpleNamespace(value="fail"),
                checks=[
                    SimpleNamespace(
                        status=SimpleNamespace(value="fail"),
                        name="hooks-runtime",
                        message="framework runtime not discoverable",
                        fixable=False,
                    )
                ],
            )
        ],
        runtime=[],
        has_warnings=False,
        to_dict=lambda: {"passed": False, "summary": {"fail": 1}},
    )
    with (
        patch("ai_engineering.cli_commands.core.diagnose", return_value=report),
        pytest.raises(typer.Exit),
    ):
        core.doctor_cmd(target=tmp_path, output_json=True)
    data = json.loads(capsys.readouterr().out)
    assert data["next_actions"] == []


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
    fake_result = UpdateResult(
        dry_run=True,
        changes=[
            FileChange(
                path=Path("f"),
                action="update",
                diff=diff_text,
                reason_code="template-drift",
                explanation="Template update available.",
                recommended_action="Apply the update.",
            )
        ],
    )
    with patch("ai_engineering.cli_commands.core.update", return_value=fake_result):
        core.update_cmd(target=tmp_path, show_diff=True)
    assert "more lines" in capsys.readouterr().out


def test_core_update_interactive_preview_then_apply(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    preview = UpdateResult(
        dry_run=True,
        changes=[
            FileChange(
                path=Path("f"),
                action="update",
                diff=None,
                reason_code="template-drift",
                explanation="Template update available.",
                recommended_action="Apply the update.",
            ),
            FileChange(
                path=Path("team.md"),
                action="skip-denied",
                reason_code="team-managed-update-protected",
                explanation=(
                    "This is a team-managed path, so ai-eng update intentionally "
                    "leaves it unchanged and will not have it replaced. No action "
                    "is required."
                ),
            ),
        ],
    )
    applied = UpdateResult(
        dry_run=False,
        changes=[
            FileChange(
                path=Path("f"),
                action="update",
                diff=None,
                reason_code="template-drift",
                explanation=(
                    "This installed file differs from the current bundled framework template."
                ),
                recommended_action=(
                    "Apply the update to replace it with the latest framework-managed version."
                ),
            )
        ],
    )

    with (
        patch.object(core.sys.stdin, "isatty", return_value=True),
        patch(
            "ai_engineering.cli_commands.core.update", side_effect=[preview, applied]
        ) as mock_update,
        patch("ai_engineering.cli_commands.core.typer.confirm", return_value=True) as mock_confirm,
    ):
        core.update_cmd(target=tmp_path)

    captured = capsys.readouterr()
    # Preview header on stdout
    assert "Update [PREVIEW]" in captured.out
    # Applied header on stdout
    assert "Update [APPLIED]" in captured.out

    # Preview: unified tree with inline state labels (no bucket headers)
    assert "Available  1" in captured.err
    assert "Protected  1" in captured.err
    assert "f" in captured.err
    assert "updated" in captured.err
    assert "team.md" in captured.err
    assert "protected" in captured.err

    # Post-apply: compact one-liner summary on stdout (not a full tree)
    assert "Done. 0 created, 1 updated, 0 removed" in captured.out

    assert mock_update.call_count == 2
    mock_confirm.assert_called_once()


def test_core_update_interactive_decline_keeps_preview_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    preview = UpdateResult(
        dry_run=True,
        changes=[
            FileChange(
                path=Path("f"),
                action="update",
                diff=None,
                reason_code="template-drift",
                explanation="Template update available.",
                recommended_action="Apply the update.",
            )
        ],
    )

    with (
        patch.object(core.sys.stdin, "isatty", return_value=True),
        patch("ai_engineering.cli_commands.core.update", return_value=preview) as mock_update,
        patch("ai_engineering.cli_commands.core.typer.confirm", return_value=False) as mock_confirm,
    ):
        core.update_cmd(target=tmp_path)

    captured = capsys.readouterr()
    # Preview header on stdout
    assert "Update [PREVIEW]" in captured.out
    # Decline warning on stderr
    assert "Preview only. No changes were applied." in captured.err

    # Preview: unified tree with inline state labels (no bucket headers)
    assert "Available  1" in captured.err
    assert "f" in captured.err
    assert "updated" in captured.err

    # No post-apply output (user declined)
    assert "Update [APPLIED]" not in captured.out

    assert mock_update.call_count == 1
    mock_confirm.assert_called_once()


def test_core_update_non_tty_apply_skips_prompt(tmp_path: Path) -> None:
    applied = UpdateResult(
        dry_run=False,
        changes=[
            FileChange(
                path=Path("f"),
                action="update",
                diff=None,
                reason_code="template-drift",
                explanation=(
                    "This installed file differs from the current bundled framework template."
                ),
                recommended_action=(
                    "Apply the update to replace it with the latest framework-managed version."
                ),
            )
        ],
    )

    with (
        patch.object(core.sys.stdin, "isatty", return_value=False),
        patch("ai_engineering.cli_commands.core.update", return_value=applied) as mock_update,
        patch("ai_engineering.cli_commands.core.typer.confirm") as mock_confirm,
    ):
        core.update_cmd(target=tmp_path, apply=True)

    mock_confirm.assert_not_called()
    mock_update.assert_called_once_with(tmp_path, dry_run=False)


# -- Post-apply output tests (spec-095, Phase 2) ----------------------------------


def test_update_post_apply_success_oneliner(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """After a successful apply (no failures), output is a summary one-liner, not a tree."""
    preview = UpdateResult(
        dry_run=True,
        changes=[
            FileChange(
                path=Path("CLAUDE.md"),
                action="create",
                reason_code="new-file",
                explanation="New governance file.",
            ),
            FileChange(
                path=Path("AGENTS.md"),
                action="create",
                reason_code="new-file",
                explanation="New governance file.",
            ),
            FileChange(
                path=Path(".ai-engineering/manifest.yml"),
                action="update",
                reason_code="template-drift",
                explanation="Template update available.",
            ),
        ],
    )
    applied = UpdateResult(
        dry_run=False,
        changes=[
            FileChange(
                path=Path("CLAUDE.md"),
                action="create",
                reason_code="new-file",
                explanation="New governance file.",
            ),
            FileChange(
                path=Path("AGENTS.md"),
                action="create",
                reason_code="new-file",
                explanation="New governance file.",
            ),
            FileChange(
                path=Path(".ai-engineering/manifest.yml"),
                action="update",
                reason_code="template-drift",
                explanation="Template update available.",
            ),
        ],
    )

    with (
        patch.object(core.sys.stdin, "isatty", return_value=True),
        patch("ai_engineering.cli_commands.core.update", side_effect=[preview, applied]),
        patch("ai_engineering.cli_commands.core.typer.confirm", return_value=True),
    ):
        core.update_cmd(target=tmp_path)

    captured = capsys.readouterr()
    combined = captured.out + captured.err

    # Post-apply output MUST be a compact one-liner summary
    assert "Done. 2 created, 1 updated, 0 removed" in combined

    # Post-apply output MUST NOT render the full applied tree.
    # Tree output (├── / └──) goes to stderr.  Both the preview tree and the
    # applied tree are rendered there.  The preview has 3 visible changes so
    # it produces 3 tree lines.  If the implementation also renders the applied
    # tree, we get 3 more (6 total).  With the spec change we expect only 3.
    err_lines = captured.err.strip().split("\n")
    tree_line_count = sum(
        1 for line in err_lines if "\u251c\u2500\u2500" in line or "\u2514\u2500\u2500" in line
    )
    preview_change_count = len(preview.changes)  # 3 non-unchanged files in preview
    assert tree_line_count == preview_change_count, (
        f"Expected {preview_change_count} tree lines (preview only), "
        f"got {tree_line_count} (current code renders applied tree too)"
    )


def test_update_post_apply_failures_show_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """After an apply with failures, the tree shows ONLY failed files."""
    # Use file names unique to each result so assertions are unambiguous
    # across the stdout/stderr split.
    preview = UpdateResult(
        dry_run=True,
        changes=[
            FileChange(
                path=Path("preview-a.md"),
                action="update",
                reason_code="template-drift",
                explanation="Template update available.",
            ),
            FileChange(
                path=Path("preview-b.md"),
                action="update",
                reason_code="template-drift",
                explanation="Template update available.",
            ),
        ],
    )
    # Simulate partial failure: one succeeds, one fails.
    applied = UpdateResult(
        dry_run=False,
        changes=[
            FileChange(
                path=Path("success-file.md"),
                action="update",
                reason_code="template-drift",
                explanation="Applied successfully.",
            ),
            FileChange(
                path=Path("failed-file.md"),
                action="error",  # triggers outcome() -> "failed"
                reason_code="write-error",
                explanation="Permission denied.",
            ),
        ],
    )

    with (
        patch.object(core.sys.stdin, "isatty", return_value=True),
        patch("ai_engineering.cli_commands.core.update", side_effect=[preview, applied]),
        patch("ai_engineering.cli_commands.core.typer.confirm", return_value=True),
    ):
        core.update_cmd(target=tmp_path)

    captured = capsys.readouterr()

    # The failed file MUST appear in the post-apply output.
    # "failed-file.md" is unique to the applied result, so its presence in
    # stderr confirms the post-apply rendering includes it.
    assert "failed-file.md" in captured.err, "Failed file should appear in post-apply output"

    # The successfully applied file MUST NOT appear in the post-apply tree.
    # "success-file.md" is unique to the applied result -- if it appears in
    # stderr, the current code is rendering the full applied tree (wrong).
    assert "success-file.md" not in captured.err, (
        "Successfully applied file should not appear in the post-apply failure tree"
    )


def test_update_post_apply_preview_still_shows_full_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The preview (before confirmation) still shows the full unified tree."""
    preview = UpdateResult(
        dry_run=True,
        changes=[
            FileChange(
                path=Path("CLAUDE.md"),
                action="create",
                reason_code="new-file",
                explanation="New governance file.",
            ),
            FileChange(
                path=Path("AGENTS.md"),
                action="update",
                reason_code="template-drift",
                explanation="Template update available.",
            ),
            FileChange(
                path=Path("team.md"),
                action="skip-denied",
                reason_code="team-managed-update-protected",
                explanation="Team-managed path.",
            ),
        ],
    )
    applied = UpdateResult(
        dry_run=False,
        changes=[
            FileChange(
                path=Path("CLAUDE.md"),
                action="create",
                reason_code="new-file",
                explanation="New governance file.",
            ),
            FileChange(
                path=Path("AGENTS.md"),
                action="update",
                reason_code="template-drift",
                explanation="Template update available.",
            ),
        ],
    )

    with (
        patch.object(core.sys.stdin, "isatty", return_value=True),
        patch("ai_engineering.cli_commands.core.update", side_effect=[preview, applied]),
        patch("ai_engineering.cli_commands.core.typer.confirm", return_value=True),
    ):
        core.update_cmd(target=tmp_path)

    captured = capsys.readouterr()

    # Tree output goes to stderr; both preview and applied trees are there.
    # The preview tree MUST contain ALL non-unchanged files including protected.
    # The protected file "team.md" is ONLY in the preview (not applied), so its
    # presence in stderr confirms the preview tree renders the full unified set.
    assert "CLAUDE.md" in captured.err, "Preview tree must include the new file"
    assert "AGENTS.md" in captured.err, "Preview tree must include the updated file"
    assert "team.md" in captured.err, "Preview tree must include the protected file"

    # Verify the preview header appeared in stdout
    assert "Update [PREVIEW]" in captured.out, "Preview header must be rendered"
    assert "Update [APPLIED]" in captured.out, "Applied header must also be rendered"

    # The kv summary for the preview must show Available and Protected counts.
    # "Protected  1" in stderr confirms the preview section rendered ownership info.
    assert "Protected  1" in captured.err, "Preview must report protected file count in summary"


def test_gate_pre_push_and_risk_expiring_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with patch(
        "ai_engineering.cli_commands.gate.run_orchestrator_gate",
        return_value=_gate_document(),
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


def test_gate_all_combined_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch(
            "ai_engineering.cli_commands.gate.run_orchestrator_gate",
            return_value=_gate_document(),
        ),
    ):
        gate.gate_all(target=tmp_path)
    captured = capsys.readouterr()
    assert "Gate All" in captured.err
    assert "PASS" in captured.err


def test_gate_all_any_fail_exits(tmp_path: Path) -> None:
    with (
        patch(
            "ai_engineering.cli_commands.gate.run_orchestrator_gate",
            return_value=_gate_document(severity="medium"),
        ),
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
