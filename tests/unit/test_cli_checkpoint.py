"""Unit tests for ai_engineering.cli_commands.checkpoint module.

Tests the checkpoint save and checkpoint load CLI commands using the
Typer CLI runner with temporary state files.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()


class TestCheckpointSave:
    """Tests for `ai-eng checkpoint save`."""

    def test_save_defaults(self, tmp_path: Path) -> None:
        """Save with default (empty) options creates the checkpoint file."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "save"])
        assert result.exit_code == 0
        assert "Checkpoint saved" in result.output

        cp_path = tmp_path / ".ai-engineering" / "state" / "session-checkpoint.json"
        assert cp_path.exists()
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        assert data["spec_id"] == ""
        assert data["current_task"] == ""
        assert data["progress"] == ""

    def test_save_with_all_options(self, tmp_path: Path) -> None:
        """Save with all options populates the checkpoint fields."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "checkpoint",
                    "save",
                    "--spec-id",
                    "spec-031",
                    "--current-task",
                    "3.2",
                    "--progress",
                    "17/24",
                    "--reasoning",
                    "Refactoring agent layout",
                    "--blocked-on",
                    "Missing dependency",
                ],
            )
        assert result.exit_code == 0
        assert "spec=spec-031" in result.output
        assert "task=3.2" in result.output
        assert "progress=17/24" in result.output

        cp_path = tmp_path / ".ai-engineering" / "state" / "session-checkpoint.json"
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        assert data["spec_id"] == "spec-031"
        assert data["current_task"] == "3.2"
        assert data["progress"] == "17/24"
        assert data["last_reasoning"] == "Refactoring agent layout"
        assert data["blocked_on"] == "Missing dependency"
        assert "timestamp" in data

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Save creates the state directory if it doesn't exist."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        # state/ dir does not exist yet
        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "save"])
        assert result.exit_code == 0
        cp_path = tmp_path / ".ai-engineering" / "state" / "session-checkpoint.json"
        assert cp_path.exists()

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        """Save overwrites an existing checkpoint file."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        cp_path = state_dir / "session-checkpoint.json"
        cp_path.write_text(json.dumps({"spec_id": "old"}), encoding="utf-8")

        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "save", "--spec-id", "new-spec"])
        assert result.exit_code == 0
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        assert data["spec_id"] == "new-spec"

    def test_save_blocked_on_none_by_default(self, tmp_path: Path) -> None:
        """When --blocked-on is not given, blocked_on is null."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "save"])
        assert result.exit_code == 0
        cp_path = tmp_path / ".ai-engineering" / "state" / "session-checkpoint.json"
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        assert data["blocked_on"] is None

    def test_save_emits_session_event(self, tmp_path: Path) -> None:
        """checkpoint_save emits session_metric event after saving."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with (
            patch(
                "ai_engineering.cli_commands.checkpoint._project_root",
                return_value=tmp_path,
            ),
            patch(
                "ai_engineering.cli_commands.checkpoint.emit_session_event",
            ) as mock_emit,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["checkpoint", "save", "--spec-id", "040", "--current-task", "5.1"],
            )
        assert result.exit_code == 0
        mock_emit.assert_called_once_with(
            tmp_path,
            checkpoint_saved=True,
            tokens_used=0,
            decisions_reused=0,
            skills_loaded=["040"],
        )

    def test_save_emission_failure_doesnt_break(self, tmp_path: Path) -> None:
        """If emission fails, checkpoint save still succeeds (fail-open)."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with (
            patch(
                "ai_engineering.cli_commands.checkpoint._project_root",
                return_value=tmp_path,
            ),
            patch(
                "ai_engineering.cli_commands.checkpoint.emit_session_event",
                side_effect=RuntimeError("boom"),
            ),
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "save", "--spec-id", "040"])
        assert result.exit_code == 0  # Fail-open


class TestCheckpointLoad:
    """Tests for `ai-eng checkpoint load`."""

    def test_no_checkpoint_file(self, tmp_path: Path) -> None:
        """When no checkpoint file exists, report starting fresh."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "load"])
        assert result.exit_code == 0
        assert "No checkpoint found" in result.output

    def test_load_valid_checkpoint(self, tmp_path: Path) -> None:
        """Load a valid checkpoint and display all fields."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        checkpoint = {
            "spec_id": "spec-031",
            "current_task": "3.2",
            "progress": "17/24",
            "last_reasoning": "Refactoring agent layout",
            "blocked_on": "Missing dependency",
            "timestamp": "2026-03-04T12:00:00Z",
        }
        (state_dir / "session-checkpoint.json").write_text(
            json.dumps(checkpoint, indent=2), encoding="utf-8"
        )

        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "load"])
        assert result.exit_code == 0
        assert "# Session Checkpoint" in result.output
        assert "spec-031" in result.output
        assert "3.2" in result.output
        assert "17/24" in result.output
        assert "Refactoring agent layout" in result.output
        assert "Missing dependency" in result.output
        assert "2026-03-04T12:00:00Z" in result.output

    def test_load_corrupted_json(self, tmp_path: Path) -> None:
        """Corrupted checkpoint JSON produces exit code 1."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "session-checkpoint.json").write_text("THIS IS NOT JSON", encoding="utf-8")

        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "load"])
        assert result.exit_code != 0

    def test_load_missing_fields_use_defaults(self, tmp_path: Path) -> None:
        """Checkpoint with missing fields shows default values."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "session-checkpoint.json").write_text(json.dumps({}), encoding="utf-8")

        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "load"])
        assert result.exit_code == 0
        assert "Spec: none" in result.output
        assert "Task: none" in result.output
        assert "Progress: unknown" in result.output

    def test_save_with_agent_creates_namespaced_section(self, tmp_path: Path) -> None:
        """Save with --agent stores entry under agents.<name> and top-level."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "checkpoint",
                    "save",
                    "--agent",
                    "build",
                    "--spec-id",
                    "051",
                    "--current-task",
                    "3.1",
                ],
            )
        assert result.exit_code == 0

        cp_path = tmp_path / ".ai-engineering" / "state" / "session-checkpoint.json"
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        # Agent-namespaced data
        assert "agents" in data
        assert "build" in data["agents"]
        assert data["agents"]["build"]["spec_id"] == "051"
        assert data["agents"]["build"]["current_task"] == "3.1"
        # Backward compat: top-level also updated
        assert data["spec_id"] == "051"

    def test_save_multiple_agents_preserves_each(self, tmp_path: Path) -> None:
        """Saving for agent A then agent B preserves both."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            runner.invoke(
                app,
                ["checkpoint", "save", "--agent", "build", "--current-task", "1.0"],
            )
            runner.invoke(
                app,
                ["checkpoint", "save", "--agent", "verify", "--current-task", "2.0"],
            )

        cp_path = tmp_path / ".ai-engineering" / "state" / "session-checkpoint.json"
        data = json.loads(cp_path.read_text(encoding="utf-8"))
        assert data["agents"]["build"]["current_task"] == "1.0"
        assert data["agents"]["verify"]["current_task"] == "2.0"

    def test_load_with_agent_returns_namespaced_data(self, tmp_path: Path) -> None:
        """Load with --agent returns that agent's checkpoint data."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "session-checkpoint.json").write_text(
            json.dumps(
                {
                    "spec_id": "top-level",
                    "current_task": "0.0",
                    "progress": "",
                    "last_reasoning": "",
                    "blocked_on": None,
                    "timestamp": "2026-03-15T00:00:00Z",
                    "agents": {
                        "build": {
                            "spec_id": "051",
                            "current_task": "3.1",
                            "progress": "5/10",
                            "last_reasoning": "building",
                            "blocked_on": None,
                            "timestamp": "2026-03-15T00:00:00Z",
                        }
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "load", "--agent", "build"])
        assert result.exit_code == 0
        assert "Agent: build" in result.output
        assert "051" in result.output
        assert "3.1" in result.output

    def test_load_without_agent_lists_all_agents(self, tmp_path: Path) -> None:
        """Load without --agent shows all agent checkpoints."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "session-checkpoint.json").write_text(
            json.dumps(
                {
                    "spec_id": "051",
                    "current_task": "0.0",
                    "progress": "",
                    "last_reasoning": "",
                    "blocked_on": None,
                    "timestamp": "2026-03-15T00:00:00Z",
                    "agents": {
                        "build": {"current_task": "3.1", "progress": "5/10"},
                        "verify": {"current_task": "4.2", "progress": "2/8"},
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["checkpoint", "load"])
        assert result.exit_code == 0
        assert "Agent Checkpoints" in result.output
        assert "build:" in result.output
        assert "verify:" in result.output

    def test_save_then_load_roundtrip(self, tmp_path: Path) -> None:
        """Save followed by load produces consistent output."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.checkpoint._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            save_result = runner.invoke(
                app,
                [
                    "checkpoint",
                    "save",
                    "--spec-id",
                    "spec-099",
                    "--current-task",
                    "1.1",
                    "--progress",
                    "5/10",
                ],
            )
            assert save_result.exit_code == 0

            load_result = runner.invoke(app, ["checkpoint", "load"])
        assert load_result.exit_code == 0
        assert "spec-099" in load_result.output
        assert "1.1" in load_result.output
        assert "5/10" in load_result.output
