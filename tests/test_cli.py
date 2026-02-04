"""Basic tests for ai-engineering package."""

import pytest
from click.testing import CliRunner

from ai_engineering import __version__
from ai_engineering.cli import main


def test_version():
    """Test version is set."""
    assert __version__ == "1.0.0"


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "AI Engineering Framework" in result.output


def test_cli_version():
    """Test CLI version command."""
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_help():
    """Test init command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--help"])
    assert result.exit_code == 0
    assert "--name" in result.output
    assert "--stack" in result.output


def test_sync_help():
    """Test sync command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["sync", "--help"])
    assert result.exit_code == 0
    assert "github" in result.output
    assert "claude" in result.output


def test_validate_help():
    """Test validate command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--help"])
    assert result.exit_code == 0
    assert "--fix" in result.output


def test_update_help():
    """Test update command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["update", "--help"])
    assert result.exit_code == 0
    assert "--check" in result.output
