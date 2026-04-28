"""Integration tests for the ai-engineering CLI.

Uses Typer's CliRunner to test CLI commands end-to-end:
- install, doctor, update, version.
- stack add/remove/list, ide add/remove/list.
- gate pre-commit/commit-msg/pre-push.
- skill status.
- maintenance report.
"""

from __future__ import annotations

import json
import subprocess
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
def _project_dir(tmp_path: Path) -> Path:
    """Create a minimal git repo so install validation and hooks setup pass."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    return tmp_path


# Use the named ``hermetic_install_env`` fixture from conftest.py so every
# test in this module engages the spec-101 synthetic-OK simulate hooks.
# Without these env vars the install calls real network mechanisms (curl
# against GitHub releases, brew, winget) which:
#   * Fail on CI runners that lack the toolchain (gitleaks, semgrep, etc.)
#     -- producing EXIT 80 instead of EXIT 0.
#   * Make tests slow + flaky -- network reachability is not a property
#     of the framework under test.
pytestmark = pytest.mark.usefixtures("hermetic_install_env")


@pytest.fixture()
def installed_dir(_project_dir: Path, app: object) -> Path:
    """Install framework to _project_dir via CLI and return the path."""
    result = runner.invoke(
        app,
        ["install", str(_project_dir), "--stack", "python", "--ide", "vscode"],
    )
    assert result.exit_code == 0, result.output
    return _project_dir


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
        _project_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["install", str(_project_dir), "--stack", "python"],
        )
        assert result.exit_code == 0, result.output
        assert "Installed to:" in result.output
        assert (_project_dir / ".ai-engineering" / "state").is_dir()

    def test_install_output_points_to_ai_start_after_doctor(
        self,
        _project_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["install", str(_project_dir), "--stack", "python"],
        )
        assert result.exit_code == 0, result.output
        assert "/ai-start" in result.output
        assert "/ai-brainstorm" not in result.output

    def test_install_on_existing_shows_skipped(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["install", str(installed_dir), "--stack", "python", "--non-interactive"],
        )
        assert result.exit_code == 0
        # spec-101 Corr-1 (Wave 28): non-interactive mode emits one
        # ``tool:<name>:<marker>`` line per skipped tool to STDERR while
        # the JSON envelope stays on STDOUT. This preserves stdout JSON
        # purity so smoke-test ``json.load(...)`` consumers parse without
        # corruption, while ``2>&1``-merged grep assertions still see the
        # markers. Wave 27 emitted markers to stdout, which broke
        # workflows piping stdout to ``json.load``.
        data = json.loads(result.stdout)
        assert data["result"]["already_installed"] is True

        # Verify the Corr-1 markers landed on STDERR (grep-able after
        # ``2>&1`` merge) and not on STDOUT.
        assert "tool:" in result.stderr, (
            "expected at least one 'tool:<name>:<marker>' line in non-interactive "
            f"stderr; got {result.stderr!r}"
        )
        assert "tool:" not in result.stdout, (
            "tool:<name>:<marker> markers must NOT appear on stdout — JSON "
            f"consumers parse stdout. got stdout={result.stdout!r}"
        )


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
        # May pass, warn, or fail depending on tools, but should not crash
        assert result.exit_code in (0, 1, 2)
        assert "Doctor" in result.output

    def test_doctor_json_output(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["--json", "doctor", str(installed_dir)],
        )
        assert result.exit_code in (0, 1, 2)
        # JSON output should be parseable (envelope wraps result)
        data = json.loads(result.output)
        report = data["result"]
        assert "passed" in report
        assert "phases" in report


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
        assert "PREVIEW" in result.output

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

    def test_stack_remove_and_readd(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        # Remove existing
        result = runner.invoke(
            app,
            ["stack", "remove", "python", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0
        assert "Removed stack 'python'" in result.output

        # Re-add
        result = runner.invoke(
            app,
            ["stack", "add", "python", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0
        assert "Added stack 'python'" in result.output

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

    def test_stack_add_unknown_rejected(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["stack", "add", "bogus", "--target", str(installed_dir)],
        )
        assert result.exit_code == 1
        assert "Unknown stack" in result.output
        assert "python" in result.output  # shows available stacks


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

    def test_ide_add_unknown_rejected(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(
            app,
            ["ide", "add", "notepad", "--target", str(installed_dir)],
        )
        assert result.exit_code == 1
        assert "Unknown IDE" in result.output


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

    def test_skill_status(self, installed_dir: Path, app: object) -> None:
        result = runner.invoke(
            app,
            ["skill", "status", "--target", str(installed_dir)],
        )
        assert result.exit_code == 0


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


# ---------------------------------------------------------------------------
# Guide
# ---------------------------------------------------------------------------


class TestGuideCommand:
    """Tests for the guide command."""

    def test_guide_not_installed(self, tmp_path: Path, app: object) -> None:
        result = runner.invoke(app, ["guide", str(tmp_path)])
        assert result.exit_code == 1

    def test_guide_shows_text_after_install(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(app, ["guide", str(installed_dir)])
        # Guide may or may not be present depending on VCS auth stubs,
        # but command should not crash
        assert result.exit_code == 0

    def test_guide_json_output(
        self,
        installed_dir: Path,
        app: object,
    ) -> None:
        result = runner.invoke(app, ["--json", "guide", str(installed_dir)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "has_guide" in data["result"]
