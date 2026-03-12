"""Tests for governance CLI commands."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()


def _setup_governance(root: Path) -> None:
    """Create minimal governance structure for testing."""
    ai_eng = root / ".ai-engineering"
    ai_eng.mkdir(parents=True, exist_ok=True)

    # GOVERNANCE_SOURCE.md
    source = ai_eng / "GOVERNANCE_SOURCE.md"
    source.write_text(
        "# Governance Source\n\n"
        "## Session Start Protocol\n\n"
        "Read _active.md and decision-store.json.\n"
        "Verify ruff, gitleaks, pytest, ty.\n\n"
        "## Absolute Prohibitions\n\n"
        "NEVER use --no-verify.\n\n"
        "## Skills\n\n"
        "35 skills.\n\n"
        "## Agents\n\n"
        "7 agents.\n\n"
        "## Quick Reference\n\n"
        "Quality: coverage 80%.\n",
        encoding="utf-8",
    )

    # CLAUDE.md with matching content
    claude_md = root / "CLAUDE.md"
    claude_md.write_text(
        "# CLAUDE.md\n\n"
        "## Session Start Protocol\n\n"
        "Read _active.md and decision-store.json.\n"
        "Verify ruff, gitleaks, pytest, ty.\n\n"
        "## Absolute Prohibitions\n\n"
        "NEVER use --no-verify.\n\n"
        "## Skills\n\n"
        "35 skills.\n\n"
        "## Agents\n\n"
        "7 agents.\n\n"
        "## Quick Reference\n\n"
        "Quality: coverage 80%.\n",
        encoding="utf-8",
    )


def test_governance_diff_no_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Governance diff exits 1 when GOVERNANCE_SOURCE.md is missing."""
    (tmp_path / ".ai-engineering").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["governance", "diff"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_governance_diff_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Governance diff reports OK when IDE files match source."""
    _setup_governance(tmp_path)
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["governance", "diff"])
    assert "OK" in result.output
    assert "CLAUDE.md" in result.output


def test_governance_diff_detects_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Governance diff detects missing key phrases in IDE files."""
    _setup_governance(tmp_path)
    # Create a minimal GEMINI.md missing prohibitions
    gemini = tmp_path / "GEMINI.md"
    gemini.write_text("# GEMINI.md\n\nMinimal content.\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["governance", "diff"])
    assert "DRIFT" in result.output
    assert "GEMINI.md" in result.output


def test_governance_sync_validates_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Governance sync validates source has all required sections."""
    _setup_governance(tmp_path)
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["governance", "sync"])
    assert "Governance source validation" in result.output
    assert "OK" in result.output


def test_governance_sync_no_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Governance sync exits 1 when source is missing."""
    (tmp_path / ".ai-engineering").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["governance", "sync"])
    assert result.exit_code == 1
