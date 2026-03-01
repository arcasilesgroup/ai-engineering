"""Unit tests for cli_ui module."""

from __future__ import annotations

import os
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
    result_header,
    show_logo,
    status_line,
    success,
    suggest_next,
    warning,
)

pytestmark = pytest.mark.unit


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
        get_console.cache_clear()
        success("done")
        err = capsys.readouterr().err
        assert "done" in err

    def test_warning_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        get_console.cache_clear()
        warning("caution")
        err = capsys.readouterr().err
        assert "caution" in err

    def test_info_writes_to_stderr(self, capsys: pytest.CaptureFixture[str]) -> None:
        get_console.cache_clear()
        info("note")
        err = capsys.readouterr().err
        assert "note" in err

    def test_kv_writes_pair(self, capsys: pytest.CaptureFixture[str]) -> None:
        get_console.cache_clear()
        kv("Name", "value")
        err = capsys.readouterr().err
        assert "Name" in err
        assert "value" in err

    def test_status_line_ok(self, capsys: pytest.CaptureFixture[str]) -> None:
        get_console.cache_clear()
        status_line("ok", "ruff", "passed")
        err = capsys.readouterr().err
        assert "ruff" in err
        assert "passed" in err

    def test_result_header_pass(self, capsys: pytest.CaptureFixture[str]) -> None:
        get_console.cache_clear()
        result_header("Doctor", "PASS", "/tmp/test")
        err = capsys.readouterr().err
        assert "Doctor" in err
        assert "PASS" in err

    def test_result_header_fail(self, capsys: pytest.CaptureFixture[str]) -> None:
        get_console.cache_clear()
        result_header("Doctor", "FAIL")
        err = capsys.readouterr().err
        assert "FAIL" in err

    def test_suggest_next_lists_steps(self, capsys: pytest.CaptureFixture[str]) -> None:
        get_console.cache_clear()
        suggest_next(
            [
                ("ai-eng doctor", "Run health diagnostics"),
                ("ai-eng setup", "Configure platforms"),
            ]
        )
        err = capsys.readouterr().err
        assert "ai-eng doctor" in err
        assert "Run health diagnostics" in err
        assert "ai-eng setup" in err

    def test_file_count_formats(self, capsys: pytest.CaptureFixture[str]) -> None:
        get_console.cache_clear()
        file_count("Governance", 42)
        err = capsys.readouterr().err
        assert "42 files" in err

    def test_header_prints_rule(self, capsys: pytest.CaptureFixture[str]) -> None:
        get_console.cache_clear()
        header("Section")
        err = capsys.readouterr().err
        assert "Section" in err


class TestPrintStdout:
    """Tests for stdout data output."""

    def test_print_stdout_goes_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        print_stdout("data line")
        out = capsys.readouterr().out
        assert "data line" in out
