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
    assert "gitHooks" in payload["toolingReadiness"]
