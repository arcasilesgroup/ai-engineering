"""Unit tests for cli_ui module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.cli_ui import (
    BRAND_TEAL,
    THEME,
    _is_no_color,
    file_count,
    get_console,
    get_stdout_console,
    header,
    info,
    kv,
    print_stdout,
    render_update_tree,
    result_header,
    show_logo,
    status_line,
    success,
    suggest_next,
    warning,
)
from ai_engineering.updater.service import FileChange


class TestNoColorDetection:
    """Tests for NO_COLOR / TERM=dumb detection."""

    def test_no_color_env_var(self) -> None:
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert _is_no_color() is True

    def test_term_dumb(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "NO_COLOR"}
        env["TERM"] = "dumb"
        with patch.dict(os.environ, env, clear=True):
            assert _is_no_color() is True

    def test_normal_env(self) -> None:
        env = {k: v for k, v in os.environ.items() if k not in ("NO_COLOR", "TERM")}
        with patch.dict(os.environ, env, clear=True):
            assert _is_no_color() is False


class TestConsoleCreation:
    """Tests for console factory functions."""

    def test_get_console_returns_console(self) -> None:
        get_console.cache_clear()
        con = get_console()
        # Console writes to stderr
        assert con.file is not None

    def test_get_stdout_console_returns_console(self) -> None:
        con = get_stdout_console()
        assert con is not None


class TestTheme:
    """Tests for the brand theme."""

    def test_brand_teal_is_hex(self) -> None:
        assert BRAND_TEAL.startswith("#")

    def test_theme_has_required_keys(self) -> None:
        required = {"brand", "success", "warning", "error", "info", "muted", "key"}
        assert required.issubset(set(THEME))


class TestLogoOutput:
    """Tests for the logo display."""

    def test_logo_noop_on_non_tty(self) -> None:
        get_console.cache_clear()
        # In test environment, console is not a TTY, so show_logo should be a no-op
        show_logo()  # Should not raise


class TestMessageHelpers:
    """Tests for success/warning/error/info helpers."""

    def test_success_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        success("done")
        err = capsys.readouterr().err

        # Assert
        assert "done" in err

    def test_warning_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        warning("caution")
        err = capsys.readouterr().err

        # Assert
        assert "caution" in err

    def test_info_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        info("note")
        err = capsys.readouterr().err

        # Assert
        assert "note" in err

    def test_kv_writes_pair(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        kv("Name", "value")
        err = capsys.readouterr().err

        # Assert
        assert "Name" in err
        assert "value" in err

    def test_status_line_ok(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        status_line("ok", "ruff", "passed")
        err = capsys.readouterr().err

        # Assert
        assert "ruff" in err
        assert "passed" in err

    def test_result_header_pass(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        result_header("Doctor", "PASS", "/tmp/test")
        err = capsys.readouterr().err

        # Assert
        assert "Doctor" in err
        assert "PASS" in err

    def test_result_header_fail(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        result_header("Doctor", "FAIL")
        err = capsys.readouterr().err

        # Assert
        assert "FAIL" in err

    def test_suggest_next_lists_steps(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        suggest_next(
            [
                ("ai-eng doctor", "Run health diagnostics"),
                ("ai-eng setup", "Configure platforms"),
            ]
        )
        err = capsys.readouterr().err

        # Assert
        assert "ai-eng doctor" in err
        assert "Run health diagnostics" in err
        assert "ai-eng setup" in err

    def test_file_count_formats(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        file_count("Governance", 42)
        err = capsys.readouterr().err

        # Assert
        assert "42 files" in err

    def test_header_prints_rule(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        header("Section")
        err = capsys.readouterr().err

        # Assert
        assert "Section" in err


class TestSafePrintFallback:
    """Tests for _safe_print ImportError fallback."""

    def test_safe_print_falls_back_on_import_error(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Arrange
        from ai_engineering.cli_ui import _safe_print

        get_console.cache_clear()

        # Act
        with patch.object(get_console(), "print", side_effect=ImportError("fake")):
            _safe_print("[bold]hello[/bold]")
        err = capsys.readouterr().err

        # Assert
        assert "hello" in err
        # Markup should be stripped
        assert "[bold]" not in err

    def test_safe_print_strips_nested_markup(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        from ai_engineering.cli_ui import _safe_print

        get_console.cache_clear()

        # Act
        with patch.object(get_console(), "print", side_effect=ModuleNotFoundError("fake")):
            _safe_print("[success]done[/success]")
        err = capsys.readouterr().err

        # Assert
        assert "done" in err
        assert "[success]" not in err


class TestShowLogoTty:
    """Tests for show_logo on TTY-like console."""

    def test_show_logo_prints_on_tty(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()
        con = get_console()

        # Act
        with patch.object(type(con), "is_terminal", new_callable=lambda: property(lambda s: True)):
            show_logo()
        err = capsys.readouterr().err

        # Assert
        assert "ai" in err or "engineering" in err


class TestUpdateTreeRendering:
    def test_render_update_tree_groups_and_nests_paths(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        get_console.cache_clear()
        changes = [
            FileChange(
                path=Path("/repo/src/ai_engineering/core.py"),
                action="update",
                reason_code="template-drift",
                explanation="Framework update available.",
                recommended_action="Apply the update.",
            ),
            FileChange(
                path=Path("/repo/.ai-engineering/contexts/team/lessons.md"),
                action="skip-denied",
                reason_code="team-managed-update-protected",
                explanation="Protected by ownership.",
                recommended_action="No action required.",
            ),
        ]

        render_update_tree(changes, root=Path("/repo"), dry_run=True)
        err = capsys.readouterr().err

        assert "Available" in err
        assert "Protected" in err
        assert "src" in err
        assert "ai_engineering" in err
        assert "core.py" in err
        assert "Reason: template-drift" in err
        assert "Next: Apply the update." in err
        assert "lessons.md" in err

    def test_render_update_tree_handles_relative_paths(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        get_console.cache_clear()
        changes = [
            FileChange(
                path=Path("docs/README.md"),
                action="skip-unchanged",
                reason_code="already-current",
                explanation="Up to date.",
            )
        ]

        render_update_tree(changes, root=Path("/repo"), dry_run=True)
        err = capsys.readouterr().err

        assert "Unchanged" in err
        assert "docs" in err
        assert "README.md" in err
        assert "Reason: already-current" in err

    def test_show_logo_handles_import_error(self) -> None:
        get_console.cache_clear()
        con = get_console()
        with (
            patch.object(type(con), "is_terminal", new_callable=lambda: property(lambda s: True)),
            patch.object(con, "print", side_effect=ImportError("fake")),
        ):
            show_logo()  # Should not raise


class TestHeaderFallback:
    """Tests for header() ImportError fallback."""

    def test_header_fallback_on_import_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        get_console.cache_clear()

        # Act
        with patch.object(get_console(), "print", side_effect=ImportError("fake")):
            header("MySection")
        err = capsys.readouterr().err

        # Assert
        assert "MySection" in err


class TestErrorHelper:
    """Tests for the error() helper."""

    def test_error_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        from ai_engineering.cli_ui import error

        get_console.cache_clear()

        # Act
        error("something broke")
        err = capsys.readouterr().err

        # Assert
        assert "something broke" in err


class TestPrintStdout:
    """Tests for stdout data output."""

    def test_print_stdout_goes_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_stdout("data line")
        out = capsys.readouterr().out
        assert "data line" in out
