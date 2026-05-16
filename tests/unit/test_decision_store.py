"""Tests for the canonical state.db ``decisions`` table CLI surface."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.state.state_db import upsert_decision_rows_raw

runner = CliRunner()


def test_decision_list_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """List against an uninitialised project root reports empty."""
    (tmp_path / ".ai-engineering").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(create_app(), ["decision", "list"])

    assert result.exit_code == 0
    assert "empty" in result.output.lower()


def test_decision_list_with_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A seeded decision appears in the listing."""
    upsert_decision_rows_raw(
        tmp_path,
        [
            {
                "decision_id": "DEC-001",
                "spec_id": "spec-200",
                "status": "active",
                "title": "Seeded decision",
                "context": "test fixture",
            }
        ],
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(create_app(), ["decision", "list"])

    assert result.exit_code == 0
    assert "DEC-001" in result.output
    assert "spec-200" in result.output


def test_decision_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`decision record` writes to the canonical table."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        create_app(),
        [
            "decision",
            "record",
            "DEC-TEST",
            "--context",
            "Test context",
            "--decision",
            "Test decision",
            "--spec",
            "spec-034",
        ],
    )

    assert result.exit_code == 0
    assert "Recorded" in result.output


def test_decision_expire_check_with_no_decisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`expire-check` returns a no-decisions message on an empty store."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(create_app(), ["decision", "expire-check"])

    assert result.exit_code == 0
    assert "no active decisions" in result.output.lower()


def test_decision_record_with_expires(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`decision record --expires` persists the expiry timestamp."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        create_app(),
        [
            "decision",
            "record",
            "DEC-EXP",
            "--context",
            "ctx",
            "--decision",
            "dec",
            "--expires",
            "2026-12-31",
        ],
    )

    assert result.exit_code == 0
    from ai_engineering.state.state_db import list_decisions

    rows = list_decisions(tmp_path)
    assert any(r["decision_id"] == "DEC-EXP" and r["expires_at"] for r in rows)
