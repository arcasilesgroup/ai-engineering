"""Unit tests for centralized CLI error handling.

Verifies that path-related OS errors produce clean user-facing messages
instead of raw Python tracebacks (spec-013 finding F1).
"""

from __future__ import annotations

from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()


class TestCleanErrorMessages:
    """Commands that receive a non-existent path emit a clean error."""

    def test_install_nonexistent_path(self) -> None:
        app = create_app()
        result = runner.invoke(app, ["install", "/nonexistent/path"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Error" in result.output

    def test_doctor_nonexistent_path(self) -> None:
        app = create_app()
        result = runner.invoke(app, ["doctor", "/nonexistent/path"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Error" in result.output

    def test_update_nonexistent_path(self) -> None:
        app = create_app()
        result = runner.invoke(app, ["update", "/nonexistent/path"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Error" in result.output

    def test_stack_list_nonexistent_path(self) -> None:
        app = create_app()
        result = runner.invoke(app, ["stack", "list", "--target", "/nonexistent/path"])
        assert result.exit_code != 0
        assert "Traceback" not in result.output
        assert "Error" in result.output

    def test_error_message_includes_path(self) -> None:
        app = create_app()
        result = runner.invoke(app, ["install", "/nonexistent/path"])
        assert "/nonexistent/path" in result.output
