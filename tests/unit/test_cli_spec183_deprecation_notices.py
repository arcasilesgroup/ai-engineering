"""spec-183 D-183-04: non-blocking stderr deprecation notices.

Covers the reusable helper (stderr-only, JSON-suppressed, one line) and the
wiring (each of the 9 low-signal commands calls it with the right label).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.cli_output import set_json_mode
from ai_engineering.cli_ui import render_deprecation_notice

_CMD = Path(__file__).resolve().parents[2] / "src" / "ai_engineering" / "cli_commands"


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


def test_notice_goes_to_stderr_not_stdout(capsys: pytest.CaptureFixture) -> None:
    render_deprecation_notice("ai-eng foo", "/ai-bar")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "deprecated" in captured.err
    assert "ai-eng foo" in captured.err
    assert "/ai-bar" in captured.err


def test_notice_is_one_line() -> None:
    import contextlib
    import io

    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        render_deprecation_notice("ai-eng foo")
    assert buf.getvalue().strip().count("\n") == 0


def test_notice_suppressed_in_json_mode(capsys: pytest.CaptureFixture) -> None:
    set_json_mode(True)
    render_deprecation_notice("ai-eng foo", "/ai-bar")
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""


# (module, expected command label) for every wired call-site.
_WIRING = [
    ("commit.py", "ai-eng commit"),
    ("status.py", "ai-eng status"),
    ("verify_cmd.py", "ai-eng verify"),
    ("ownership_cmd.py", "ai-eng ownership import"),
    ("issue.py", "ai-eng issue sync"),
    ("spec_cmd.py", "ai-eng spec show"),
    ("pr.py", "ai-eng pr"),
    ("maintenance.py", "ai-eng maintenance pr"),
    ("maintenance.py", "ai-eng maintenance reset-events"),
]


@pytest.mark.parametrize(("module", "label"), _WIRING)
def test_command_is_wired(module: str, label: str) -> None:
    text = (_CMD / module).read_text(encoding="utf-8")
    assert f'render_deprecation_notice("{label}"' in text
