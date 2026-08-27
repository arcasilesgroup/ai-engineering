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


WHOLE = {
    "--what": "block H needs written authority",
    "--why": "the header requires two digests and neither was named",
    "--action": "apruebo 019 en cbba04d9",
}


@pytest.mark.parametrize("omitted", sorted(WHOLE))
def test_a_stop_missing_any_of_the_three_is_refused_and_says_which(repo, capsys, omitted):
    """Three required at the command line, and the refusal has to name the one that is
    missing. A run that can say it stopped but not what would unstick it has recorded a
    complaint, and the section this feeds refuses complaints.

    The exit code is asserted rather than just `SystemExit`, because `SystemExit(0)` is a
    successful exit and would satisfy a bare `raises`.
    """

    argv = ["blocked"]
    for flag, value in WHOLE.items():
        if flag != omitted:
            argv += [flag, value]

    with pytest.raises(SystemExit) as leaving:
        report.main(argv)

    assert leaving.value.code == 2, leaving.value.code
    assert omitted in capsys.readouterr().err
    assert not (repo / blocked.LEDGER).exists(), "a refused call must not leave half a row"


@pytest.mark.parametrize("useless", ["", "   ", "TODO", "ask the owner", "decide this"])
def test_a_flag_that_says_nothing_is_refused_at_the_boundary(repo, useless):
    """`required=True` checks presence, and presence is not content. Both of these were
    present and produced a PASS over a row the collector then refused — a result claimed
    that the code did not observe, arriving through the one field that exists to stop it."""

    with pytest.raises(SystemExit) as leaving:
        report.main(["blocked", *sum(([k, v] for k, v in WHOLE.items()), []), "--action", useless])

    assert leaving.value.code == 2
    assert not (repo / blocked.LEDGER).exists()


def test_an_emoji_in_the_reason_does_not_brick_the_ledger(repo):
    """The first serialiser reached for `json.dumps`, which is close enough to TOML to be
    tempting and wrong in one place: with the default `ensure_ascii` an emoji becomes a
    surrogate pair, `tomllib` refuses an escaped surrogate, and one halt made every later
    read raise and every later write refuse — permanently, with no recovery but hand-editing
    a governed file."""

    ran = report.main(
        [
            "blocked",
            "--what",
            "block H needs written authority",
            "--why",
            'nobody named the digests \U0001f6ab and the tab\tand the "quote" stayed',
            "--action",
            "apruebo 019 en cbba04d9",
        ]
    )
    assert ran.outcome == "PASS", ran

    rows, dropped = blocked.stops(repo)
    assert len(rows) == 1
    assert dropped == []
    assert "\U0001f6ab" in rows[0].why
    assert "\t" in rows[0].why
    assert '"quote"' in rows[0].why


def test_an_unrelated_halt_does_not_delete_a_row_the_reader_only_dropped(repo):
    """`record` rewrites the whole file. Built from the parsed rows it would delete every row
    the reader had refused, so an unrelated halt would destroy the half-written record that
    the drop list existed to make visible."""

    (repo / "docs" / "blocked.toml").write_text(
        '[[stop]]\nid = "half-written"\nwhat = "something"\nsince = "2026-08-01"\n'
        'why = "a reason"\naction = "TODO"\n',
        encoding="utf-8",
    )

    report.main(
        ["blocked", "--what", "an unrelated gate", "--why", "a reason", "--action", "run this"]
    )

    kept = (repo / "docs" / "blocked.toml").read_text(encoding="utf-8")
    assert "half-written" in kept, "an unrelated write must not delete a dropped row"
    rows, dropped = blocked.stops(repo)
    assert [row.what for row in rows] == ["an unrelated gate"]
    assert dropped == ["half-written"]


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
