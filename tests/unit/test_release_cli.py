"""Unit tests for the release CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.release.orchestrator import PhaseResult, ReleaseResult

runner = CliRunner()


def test_release_cli_success_human(tmp_path: Path) -> None:
    app = create_app()
    payload = ReleaseResult(
        success=True,
        phases=[
            PhaseResult(phase="validate", success=True, output="ok"),
            PhaseResult(phase="prepare", success=True, output="pyproject.toml"),
        ],
        version="0.2.0",
        tag_name="v0.2.0",
        pr_url="https://example/pr/1",
        release_url="https://example/release/v0.2.0",
    )
    with (
        patch("ai_engineering.cli_commands.release.resolve_project_root", return_value=tmp_path),
        patch("ai_engineering.cli_commands.release.get_provider"),
        patch("ai_engineering.cli_commands.release.execute_release", return_value=payload),
    ):
        result = runner.invoke(app, ["release", "0.2.0"])

    assert result.exit_code == 0
    assert "Release v0.2.0" in result.output
    assert "https://example/release/v0.2.0" in result.output


def test_release_cli_success_json(tmp_path: Path) -> None:
    app = create_app()
    payload = ReleaseResult(
        success=True,
        phases=[PhaseResult(phase="validate", success=True, output="ok")],
        version="0.2.0",
        tag_name="v0.2.0",
        pr_url="",
        release_url="",
    )
    with (
        patch("ai_engineering.cli_commands.release.resolve_project_root", return_value=tmp_path),
        patch("ai_engineering.cli_commands.release.get_provider"),
        patch("ai_engineering.cli_commands.release.execute_release", return_value=payload),
    ):
        result = runner.invoke(app, ["--json", "release", "v0.2.0"])

    assert result.exit_code == 0
    assert '"ok": true' in result.output
    assert '"version": "0.2.0"' in result.output


def test_release_cli_json_exposes_dry_run_readiness_and_packet_fields(
    tmp_path: Path,
) -> None:
    app = create_app()
    payload = ReleaseResult(
        success=True,
        phases=[PhaseResult(phase="plan", success=True, output="dry-run", skipped=True)],
        version="0.2.0",
        tag_name="v0.2.0",
        dry_run_plan={"target_version": "0.2.0", "readiness_gate": "planned readiness gate"},
        readiness={"verdict": "CONDITIONAL GO", "conditions": ["accepted via D-143-09"]},
        release_packet_url="https://example/releases/download/v0.2.0/release-packet.json",
        release_packet_ref="release-packet.json",
    )
    with (
        patch("ai_engineering.cli_commands.release.resolve_project_root", return_value=tmp_path),
        patch("ai_engineering.cli_commands.release.get_provider"),
        patch("ai_engineering.cli_commands.release.execute_release", return_value=payload),
    ):
        result = runner.invoke(app, ["--json", "release", "v0.2.0", "--dry-run"])

    assert result.exit_code == 0
    envelope = json.loads(result.stdout)
    release = envelope["result"]
    assert release["dry_run_plan"]["target_version"] == "0.2.0"
    assert release["readiness"]["verdict"] == "CONDITIONAL GO"
    assert release["release_packet_url"].endswith("release-packet.json")
    assert release["release_packet_ref"] == "release-packet.json"


def test_release_cli_human_dry_run_lists_plan_without_publish_claim(
    tmp_path: Path,
) -> None:
    app = create_app()
    payload = ReleaseResult(
        success=True,
        phases=[PhaseResult(phase="plan", success=True, output="dry-run", skipped=True)],
        version="0.2.0",
        tag_name="v0.2.0",
        dry_run_plan={
            "old_version": "0.1.0",
            "target_version": "0.2.0",
            "release_branch": "release/v0.2.0",
            "readiness_gate": "ai-eng verify --release 0.2.0",
            "release_packet_outputs": "release-packet.json",
        },
    )
    with (
        patch("ai_engineering.cli_commands.release.resolve_project_root", return_value=tmp_path),
        patch("ai_engineering.cli_commands.release.get_provider"),
        patch("ai_engineering.cli_commands.release.execute_release", return_value=payload),
    ):
        result = runner.invoke(app, ["release", "0.2.0", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry-run plan" in result.output
    assert "ai-eng verify --release 0.2.0" in result.output
    assert "Release v0.2.0 completed" not in result.output


def test_release_cli_failure_exits_nonzero(tmp_path: Path) -> None:
    app = create_app()
    payload = ReleaseResult(
        success=False,
        phases=[PhaseResult(phase="validate", success=False, output="bad")],
        version="0.2.0",
        tag_name="v0.2.0",
        errors=["validation failed"],
    )
    with (
        patch("ai_engineering.cli_commands.release.resolve_project_root", return_value=tmp_path),
        patch("ai_engineering.cli_commands.release.get_provider"),
        patch("ai_engineering.cli_commands.release.execute_release", return_value=payload),
    ):
        result = runner.invoke(app, ["release", "0.2.0"])

    assert result.exit_code == 1
    assert "validation failed" in result.output
