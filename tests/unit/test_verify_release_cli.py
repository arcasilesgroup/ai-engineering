"""Unit tests for ``ai-eng verify --release``."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.release.readiness import ReleaseReadinessReport

runner = CliRunner()
_READINESS_TARGET = "ai_engineering.cli_commands.verify_cmd.verify_release_readiness"


def _report(
    tmp_path: Path,
    verdict: str,
    *,
    conditions: list[str] | None = None,
) -> ReleaseReadinessReport:
    return ReleaseReadinessReport(
        version="0.5.0",
        verdict=verdict,
        conditions=conditions or [],
        dimensions={"security": {"status": "PASS", "summary": "clean"}},
        artifact_path=str(tmp_path / "release-readiness.json"),
    )


def test_verify_release_human_outputs_go(tmp_path: Path) -> None:
    app = create_app()
    with (
        patch("ai_engineering.cli_commands.verify_cmd.resolve_project_root", return_value=tmp_path),
        patch(_READINESS_TARGET, return_value=_report(tmp_path, "GO")),
    ):
        result = runner.invoke(app, ["verify", "--release", "0.5.0"])

    assert result.exit_code == 0
    assert "GO" in result.output


def test_verify_release_human_outputs_conditional_go(tmp_path: Path) -> None:
    app = create_app()
    report = _report(tmp_path, "CONDITIONAL GO", conditions=["accepted via D-143-09"])
    with (
        patch("ai_engineering.cli_commands.verify_cmd.resolve_project_root", return_value=tmp_path),
        patch(_READINESS_TARGET, return_value=report),
    ):
        result = runner.invoke(app, ["verify", "--release", "0.5.0"])

    assert result.exit_code == 0
    assert "CONDITIONAL GO" in result.output
    assert "D-143-09" in result.output


def test_verify_release_no_go_exits_nonzero(tmp_path: Path) -> None:
    app = create_app()
    with (
        patch("ai_engineering.cli_commands.verify_cmd.resolve_project_root", return_value=tmp_path),
        patch(_READINESS_TARGET, return_value=_report(tmp_path, "NO-GO")),
    ):
        result = runner.invoke(app, ["verify", "--release", "0.5.0"])

    assert result.exit_code == 1
    assert "NO-GO" in result.output


def test_verify_release_json_includes_readiness_evidence(tmp_path: Path) -> None:
    app = create_app()
    report = _report(tmp_path, "GO")
    with (
        patch("ai_engineering.cli_commands.verify_cmd.resolve_project_root", return_value=tmp_path),
        patch(_READINESS_TARGET, return_value=report),
    ):
        result = runner.invoke(app, ["--json", "verify", "--release", "0.5.0"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["result"]["release_readiness"]["verdict"] == "GO"
    assert payload["result"]["release_readiness"]["artifact_path"].endswith(
        "release-readiness.json"
    )
