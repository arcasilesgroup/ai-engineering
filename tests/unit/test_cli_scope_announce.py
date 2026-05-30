"""Tests for the resolved-scope announcement (spec-156 D-156-03)."""

from __future__ import annotations

import pytest

from ai_engineering import cli_ui
from ai_engineering.cli_output import set_json_mode


@pytest.fixture(autouse=True)
def _reset_json() -> None:
    set_json_mode(False)
    yield
    set_json_mode(False)


def test_announce_prints_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    cli_ui.get_console.cache_clear()
    cli_ui.announce_scope("◈ ai-engineering · acting on global install (~/)")
    err = capsys.readouterr().err
    assert "global install (~/)" in err


def test_announce_empty_message_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    cli_ui.announce_scope("")
    out = capsys.readouterr()
    assert out.err == ""
    assert out.out == ""


def test_announce_suppressed_in_json_mode(capsys: pytest.CaptureFixture[str]) -> None:
    set_json_mode(True)
    cli_ui.announce_scope("◈ ai-engineering · acting on local install (./)")
    out = capsys.readouterr()
    assert out.err == ""
    assert out.out == ""


def test_announce_never_writes_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    """Announcement is stderr-only — stdout stays clean for piping."""
    cli_ui.get_console.cache_clear()
    cli_ui.announce_scope("◈ ai-engineering · acting on local install (./)")
    assert capsys.readouterr().out == ""
