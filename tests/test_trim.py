"""Tests for spec 033 / B-033-1: the deterministic context trimmer.

Keeps head and tail of a tool's output, marks the elided middle, never elides a line
containing a failure marker, and is deterministic — same input, same trimmed output
(make-claude-code-last-longer's measured fix: trim before the context reads it).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import trim  # noqa: E402


def _long_output(lines: int, *, failure_at: int | None = None) -> str:
    out = [f"line {i}" for i in range(1, lines + 1)]
    if failure_at is not None:
        out[failure_at - 1] = "ERROR: the one failure marker"
    return "\n".join(out) + "\n"


def test_trim_keeps_head_and_tail_and_marks_the_elision():
    text = _long_output(200)
    out = trim.trim_output(text, max_lines=80)
    assert out.count("\n") + 1 <= 80
    assert "line 1" in out  # head kept
    assert "line 200" in out  # tail kept
    assert "elided" in out  # the middle is marked


def test_trim_never_elides_a_failure_line():
    text = _long_output(200, failure_at=100)  # in the would-be-elided middle
    out = trim.trim_output(text, max_lines=80)
    assert "ERROR: the one failure marker" in out


def test_trim_is_deterministic():
    text = _long_output(150)
    assert trim.trim_output(text, max_lines=80) == trim.trim_output(text, max_lines=80)


def test_short_output_is_untouched():
    text = "one\ntwo\nthree\n"
    assert trim.trim_output(text, max_lines=80) == text