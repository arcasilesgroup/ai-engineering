"""Integration tests for the ai-engineering CLI.

Uses Typer's CliRunner to test CLI commands end-to-end:
- install, doctor, update, version.
- stack add/remove/list, ide add/remove/list.
- gate pre-commit/commit-msg/pre-push.
- skill list/sync.
- maintenance report.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()


@pytest.fixture()
def app() -> object:
    """Create a fresh CLI app instance for each test."""
    return create_app()


@pytest.fixture()
def installed_dir(tmp_path: Path, app: object) -> Path:
    """Install framework to tmp_path via CLI and return the path."""
    result = runner.invoke(
        app,
        ["install", str(tmp_path), "--stack", "python", "--ide", "vscode"],
    )
    assert result.exit_code == 0, result.output
    return tmp_path


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersionCommand:
    """Tests for the version command."""

    def test_version_shows_version(self, app: object) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "ai-engineering" in result.output

    def test_help_shows_commands(self, app: object) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "doctor" in result.output


# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------


class TestInstallCommand:
    """Tests for the install command."""

    def test_install_creates_framework(
        self,
        tmp_path: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["install", str(tmp_path), "--stack", "python"],
        )
        assert result.exit_code == 0
        assert "Installed to:" in result.output
        assert (tmp_path / ".ai-engineering" / "state").is_dir()

    def test_install_on_existing_shows_skipped(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["install", str(installed_dir), "--stack", "python"],
        )
        assert result.exit_code == 0
        assert "already installed" in result.output


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------


class TestDoctorCommand:
    """Tests for the doctor command."""

    def test_doctor_passes_on_installed(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(app, ["doctor", str(installed_dir)])
        # May pass or fail depending on tools, but should not crash
        assert result.exit_code in (0, 1)
        assert "Doctor" in result.output

    def test_doctor_json_output(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["doctor", str(installed_dir), "--json"],
        )
        assert result.exit_code in (0, 1)
        # JSON output should be parseable
        data = json.loads(result.output)
        assert "passed" in data
        assert "checks" in data


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


class TestUpdateCommand:
    """Tests for the update command."""

    def test_update_dry_run(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(app, ["update", str(installed_dir)])
        assert result.exit_code == 0
        assert "DRY-RUN" in result.output

    def test_update_apply(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["update", str(installed_dir), "--apply"],
        )
        assert result.exit_code == 0
        assert "APPLIED" in result.output


# ---------------------------------------------------------------------------
# Stack
# ---------------------------------------------------------------------------


class TestStackCommands:
    """Tests for stack add/remove/list commands."""

    def test_stack_list(self, installed_dir: Path, app: object) -> None:
        result = runner.invoke(
            app,
            ["stack", "list", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0
        assert "python" in result.output

    def test_stack_add_and_remove(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        # Add
        result = runner.invoke(
            app,
            ["stack", "add", "node", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0
        assert "Added stack 'node'" in result.output

        # Remove
        result = runner.invoke(
            app,
            ["stack", "remove", "node", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0
        assert "Removed stack 'node'" in result.output

    def test_stack_add_duplicate_fails(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["stack", "add", "python", "--target", str(installed_dir)],
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# IDE
# ---------------------------------------------------------------------------


class TestIDECommands:
    """Tests for ide add/remove/list commands."""

    def test_ide_list(self, installed_dir: Path, app: object) -> None:
        result = runner.invoke(
            app,
            ["ide", "list", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0
        assert "vscode" in result.output

    def test_ide_add_and_remove(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["ide", "add", "jetbrains", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0

        result = runner.invoke(
            app,
            ["ide", "remove", "jetbrains", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------


class TestGateCommands:
    """Tests for gate commands."""

    def test_gate_pre_commit_runs(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        # Will likely fail if tools aren't installed, but should not crash
        result = runner.invoke(
            app,
            ["gate", "pre-commit", "--target", str(installed_dir)],
        )
        assert result.exit_code in (0, 1)
        assert "Gate" in result.output

    def test_gate_commit_msg_with_file(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        msg_file = installed_dir / "COMMIT_MSG"
        msg_file.write_text("feat: test commit message\n", encoding="utf-8")
        result = runner.invoke(
            app,
            [
                "gate",
                "commit-msg",
                str(msg_file),
                "--target",
                str(installed_dir),
            ],
        )
        assert result.exit_code in (0, 1)
        assert "Gate" in result.output


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class TestSkillCommands:
    """Tests for skill commands."""

    def test_skill_list(self, installed_dir: Path, app: object) -> None:
        result = runner.invoke(
            app,
            ["skill", "list", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0

    def test_skill_add_and_remove(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            [
                "skill",
                "add",
                "https://example.com/skill.md",
                "--target",
                str(installed_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Added source" in result.output

        result = runner.invoke(
            app,
            [
                "skill",
                "remove",
                "https://example.com/skill.md",
                "--target",
                str(installed_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Removed source" in result.output


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------


class TestMaintenanceCommands:
    """Tests for maintenance commands."""

    def test_maintenance_report(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["maintenance", "report", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0
        assert "Maintenance Report" in result.output
