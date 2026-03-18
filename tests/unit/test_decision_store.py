"""Tests for decision-store operations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()


def _setup_decision_store(root: Path, entries: list[dict] | None = None) -> Path:
    """Create a decision-store.json with optional entries."""
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    store_path = state_dir / "decision-store.json"

    data = {"schema_version": "1.1", "decisions": entries or []}
    store_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return store_path


def test_decision_list_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Decision list with empty store."""
    # Arrange
    _setup_decision_store(tmp_path)
    monkeypatch.chdir(tmp_path)
    app = create_app()

    # Act
    result = runner.invoke(app, ["decision", "list"])

    # Assert
    assert result.exit_code == 0


def test_decision_list_with_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Decision list shows entries with camelCase schema."""
    # Arrange
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    store = state_dir / "decision-store.json"
    store.write_text(
        json.dumps(
            {
                "schemaVersion": "1.1",
                "decisions": [
                    {
                        "id": "DEC-001",
                        "title": "Test decision",
                        "status": "active",
                        "criticality": "medium",
                        "created_at": "2026-03-12",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    app = create_app()

    # Act
    result = runner.invoke(app, ["decision", "list"])

    # Assert
    assert result.exit_code == 0


def test_decision_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Decision record adds a new entry."""
    # Arrange
    _setup_decision_store(tmp_path)
    monkeypatch.chdir(tmp_path)
    app = create_app()

    # Act
    result = runner.invoke(
        app,
        [
            "decision",
            "record",
            "DEC-TEST",
            "--context",
            "Test context",
            "--decision",
            "Test decision",
            "--category",
            "architecture-decision",
        ],
    )

    # Assert
    assert result.exit_code == 0


def test_decision_expire_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Decision expire-check reports expired decisions."""
    # Arrange
    entries = [
        {
            "id": "DEC-OLD",
            "title": "Expired decision",
            "status": "active",
            "criticality": "medium",
            "created_at": "2025-01-01",
            "expires_at": "2025-06-01",
        }
    ]
    _setup_decision_store(tmp_path, entries)
    monkeypatch.chdir(tmp_path)
    app = create_app()

    # Act
    result = runner.invoke(app, ["decision", "expire-check"])

    # Assert
    assert result.exit_code == 0


def test_decision_store_schema_valid() -> None:
    """The actual decision-store.json in the repo is valid JSON with expected schema."""
    # Arrange
    store_path = (
        Path(__file__).resolve().parents[2] / ".ai-engineering" / "state" / "decision-store.json"
    )
    if not store_path.exists():
        pytest.skip("decision-store.json not found in repo")

    # Act
    data = json.loads(store_path.read_text(encoding="utf-8"))

    # Assert
    assert "schemaVersion" in data
    assert "decisions" in data
    assert isinstance(data["decisions"], list)
    for entry in data["decisions"]:
        assert "id" in entry
        assert "title" in entry
        assert "status" in entry
