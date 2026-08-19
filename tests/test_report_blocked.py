"""The subcommand a halting run calls before it halts.

Specification 020's second repair. A run that reaches a gate it cannot pass leaves a record
first, so the stop is a fact in the tree rather than a sentence in a terminal nobody kept.
The record states the gate reached and what is missing; it never records that the missing
thing arrived.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from ai_engineering import blocked, paths, report


@pytest.fixture
def repo(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    monkeypatch.setattr(paths, "repo_root", lambda start=None: tmp_path)
    return tmp_path


def _ran(repo: Path) -> list[dict]:
    return list(tomllib.loads((repo / blocked.LEDGER).read_text(encoding="utf-8"))["stop"])


def test_a_stop_without_an_action_is_refused(repo):
    """Three of the four are required at the command line and the fourth is the reason this
    exists. A run that can say it stopped but not what would unstick it has recorded a
    complaint, and the section this feeds refuses complaints."""

    with pytest.raises(SystemExit):
        report.main(["blocked", "--what", "block H", "--why", "no authority named"])

    assert not (repo / blocked.LEDGER).exists(), "a refused call must not leave half a row"


def test_a_stop_is_recorded_and_recording_it_twice_updates_rather_than_grows(repo):
    """A build that halts twice at the same gate must not grow the ledger. The identity is
    what is waiting: the same gate reached again is the same row with a newer reason, and a
    second row would be the section counting one stop as two."""

    first = report.main(
        [
            "blocked",
            "--what",
            "block H needs written authority",
            "--why",
            "the header requires two digests and neither was named",
            "--action",
            "apruebo 019 en cbba04d9",
            "--since",
            "2026-08-19",
        ]
    )
    assert first.outcome == "PASS", first

    rows = _ran(repo)
    assert len(rows) == 1
    assert rows[0]["action"] == "apruebo 019 en cbba04d9"
    assert rows[0]["since"] == "2026-08-19"

    report.main(
        [
            "blocked",
            "--what",
            "block H needs written authority",
            "--why",
            "still nobody has named them",
            "--action",
            "apruebo 019 en cbba04d9",
        ]
    )

    rows = _ran(repo)
    assert len(rows) == 1, "the same gate reached twice is one row"
    assert rows[0]["why"] == "still nobody has named them"
    # The date of the first halt, not of the latest. "Since when" is the question the column
    # asks, and refreshing it on every retry would make a week-old block look new.
    assert rows[0]["since"] == "2026-08-19"

    shown, dropped = blocked.collect(repo)
    assert [row.kind for row in shown] == ["halt"]
    assert dropped == []


def test_a_docs_directory_nobody_can_write_reports_rather_than_raising(repo, monkeypatch):
    """This runs when a build is already failing. A recorder that throws while recording a
    stop turns a halt into a crash, and the crash is what the person would then be reading
    instead of the record."""

    import ai_engineering.report as module

    def refuse(*_args, **_kwargs):
        raise OSError("read-only file system")

    monkeypatch.setattr(module.Path, "write_text", refuse)

    ran = report.main(["blocked", "--what", "a gate", "--why", "a reason", "--action", "a literal"])

    assert ran.outcome == "INCOMPLETE", ran
