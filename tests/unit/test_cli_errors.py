"""Unit tests for centralized CLI error handling.

Verifies that path-related OS errors produce clean user-facing messages
instead of raw Python tracebacks (spec-013 finding F1).
"""

from __future__ import annotations

from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()


class TestCleanErrorMessages:
    """Commands that receive a non-existent path emit a clean error."""

    def test_install_nonexistent_path(self) -> None:
        # Arrange
        app = create_app()

        # Act
        result = runner.invoke(app, ["install", "/nonexistent/path"])

        # Assert
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Error" in result.output

    def test_doctor_nonexistent_path(self) -> None:
        # Arrange
        app = create_app()

        # Act
        result = runner.invoke(app, ["doctor", "/nonexistent/path"])

        # Assert
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Error" in result.output

    def test_update_nonexistent_path(self) -> None:
        # Arrange
        app = create_app()

        # Act
        result = runner.invoke(app, ["update", "/nonexistent/path"])

        # Assert
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Error" in result.output

    def test_stack_list_nonexistent_path(self) -> None:
        # Arrange
        app = create_app()

        # Act
        result = runner.invoke(app, ["stack", "list", "--target", "/nonexistent/path"])

        # Assert
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Error" in result.output

    def test_yaml_error_produces_clean_message(self) -> None:
        app = create_app()

        with patch(
            "ai_engineering.cli_commands.core.diagnose",
            side_effect=yaml.YAMLError("invalid YAML in manifest"),
        ):
            result = runner.invoke(app, ["doctor", "."])

        assert result.exit_code != 0
        assert "Traceback" not in result.output

    def test_error_message_includes_path(self) -> None:
        # Arrange
        app = create_app()

        # Act
        result = runner.invoke(app, ["install", "/nonexistent/path"])

        # Assert
        # On Windows the path is resolved with backslashes (e.g. D:\nonexistent\path)
        assert "nonexistent" in result.output
