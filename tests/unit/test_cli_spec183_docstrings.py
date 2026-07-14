"""spec-183 Goal 3: confirmed docstring/help-text bug fixes.

Behavior is unchanged; these assert the corrected user-facing text so the
stale strings cannot silently return.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from ai_engineering.cli_commands import gate
from ai_engineering.cli_commands.core import doctor_cmd
from ai_engineering.cli_factory import create_app

runner = CliRunner()

_SRC = Path(__file__).resolve().parents[2] / "src" / "ai_engineering" / "cli_commands"


def test_setup_success_strings_no_phantom_table() -> None:
    text = (_SRC / "setup.py").read_text(encoding="utf-8")
    assert "install_state table" not in text
    assert "state.db singleton row" not in text


def test_doctor_check_help_drops_state_db() -> None:
    result = runner.invoke(create_app(), ["doctor", "--help"])
    assert result.exit_code == 0
    assert "state-db" not in result.output
    assert "state-db" not in (doctor_cmd.__doc__ or "")


def test_doctor_check_state_db_rejected() -> None:
    # Behavior unchanged: the dispatcher supports only 'hot-path'.
    result = runner.invoke(create_app(), ["doctor", "--check", "state-db"])
    assert result.exit_code != 0


def test_cleanup_reset_help_is_accurate() -> None:
    result = runner.invoke(create_app(), ["cleanup", "branches", "--help"])
    assert result.exit_code == 0
    assert "Force re-sync to remote state" not in result.output
    assert "alias of --untracked" in result.output


def test_gate_pre_push_docstring_discloses_scope() -> None:
    doc = gate.gate_pre_push.__doc__ or ""
    assert "Article VII" in doc
    assert "expiring-soon" in doc


def test_gate_risk_check_strict_discloses_expiring_soon() -> None:
    doc = gate.gate_risk_check.__doc__ or ""
    assert "expiring-soon" in doc
