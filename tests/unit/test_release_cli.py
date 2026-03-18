"""Unit tests for the release CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.release.orchestrator import PhaseResult, ReleaseResult

pytestmark = pytest.mark.unit

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
