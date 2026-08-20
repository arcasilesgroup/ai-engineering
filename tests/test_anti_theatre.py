"""What `RAN` has to mean, as tests that fail.

This file used to be the edge cases of `PARTIAL` — the compromise that let a scoped
mutation run stand for the whole tree against a nightly receipt. The mutation lane it
served is gone: its floor of 89 was never once met, its rows named no security guard, and
the whole-tree run it was pacing took 121 minutes against a job capped at 30, so it was
reported as `cancelled` on every commit for weeks. `PARTIAL` went with it.

What survives is the original contract, which never needed a receipt: a gate proves it ran
by printing a count it could only print by having read the files, a count of zero is not a
pass, and a gate that was deleted prints no line at all — so the names are listed rather
than inferred from what happens to be present.
"""

from __future__ import annotations

from pathlib import Path

import anti_theatre
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _log(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_a_count_a_tool_printed_is_the_whole_contract(tmp_path):
    assert anti_theatre.main(_log(tmp_path / "check.log", "RAN lint=41\n"), ROOT, ("lint",)) == 0


def test_zero_is_not_a_pass(tmp_path):
    """It ran, and it ran over nothing. That is the shape a replaced tool leaves behind."""

    with pytest.raises(SystemExit):
        anti_theatre.main(_log(tmp_path / "check.log", "RAN lint=0\n"), ROOT, ("lint",))


def test_a_deleted_gate_prints_no_line_at_all(tmp_path):
    """Reading only the lines that are present cannot tell a gate that ran from a gate that
    was removed: both say nothing about the missing one. Naming them is what closes it."""

    log = _log(tmp_path / "check.log", "RAN lint=41\n")

    with pytest.raises(SystemExit):
        anti_theatre.main(log, ROOT, ("lint", "tests"))


def test_a_log_with_no_ran_lines_is_a_green_nobody_earned(tmp_path):
    with pytest.raises(SystemExit):
        anti_theatre.main(_log(tmp_path / "check.log", "all good\n"), ROOT, ("lint",))
