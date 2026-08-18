"""The three argument types that guard a risk acceptance, and the five fields it demands.

`accept.main` carried 107 surviving mutants — the largest pool behind any single function
left in the tree. Most of it is argument handling, which is the part of a program that runs
before anything is decided and therefore the part a suite driven by valid inputs never
reaches.

What it guards is worth the care. A risk acceptance is the one record in this product that
makes a red thing green: a signed statement that somebody accountable looked at a finding
and accepted it until a date. Every field of it is therefore mandatory in the same breath —
an owner, an expiry, a reason and actual local evidence — because a record missing any one
of them is a record that says a risk was accepted and cannot say by whom, until when, why,
or on what basis.

`--expired` is the exception and the only one, because listing what has run out asks for
nothing and accepts nothing.
"""

from __future__ import annotations

import argparse

import pytest

from ai_engineering import accept


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="whitespace only"),
        pytest.param(" leading", id="leading space"),
        pytest.param("trailing ", id="trailing space"),
        pytest.param("two\nlines", id="a newline"),
        pytest.param("a\ttab", id="a tab"),
        pytest.param("bell\x07", id="a control character"),
    ],
)
def test_a_required_value_is_one_explicit_value(value: str):
    """Surrounding space is refused rather than stripped, because a value somebody typed
    with a space and a value they meant are two different strings and only they know which
    was intended. A newline is refused for a harder reason: these fields are written into a
    record, and one that carries a newline writes its own line into it."""

    with pytest.raises(argparse.ArgumentTypeError):
        accept._required("owner")(value)


def test_an_ordinary_value_survives_byte_for_byte():
    assert accept._required("owner")("repository maintainer") == "repository maintainer"


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("2026-13-01", id="a month that does not exist"),
        pytest.param("2026-02-30", id="a day that does not exist"),
        pytest.param("2026-2-3", id="unpadded"),
        pytest.param("26-02-03", id="a two-digit year"),
        pytest.param("2026-02-03T00:00:00", id="a timestamp"),
        pytest.param("tomorrow", id="a word"),
        pytest.param("", id="empty"),
    ],
)
def test_an_expiry_has_to_be_one_exact_iso_date(value: str):
    """Round-tripped rather than pattern-matched. `2026-2-3` parses and is not the string
    that was typed, and a register sorted by a date that is not the date sorts fine and
    expires the wrong things."""

    with pytest.raises(argparse.ArgumentTypeError):
        accept._date(value)


def test_a_real_date_is_returned_unchanged():
    assert accept._date("2026-11-14") == "2026-11-14"


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="empty"),
        pytest.param("/etc/passwd", id="absolute"),
        pytest.param("../outside.md", id="upwards"),
        pytest.param("specs/../../outside.md", id="upwards in the middle"),
        pytest.param("specs//spec.md", id="an empty segment"),
        pytest.param("specs/./spec.md", id="a dot segment"),
        pytest.param("specs\\spec.md", id="a backslash"),
        pytest.param("specs/spec.md\x00", id="a null byte"),
    ],
)
def test_evidence_is_a_repository_relative_path_and_nothing_else(value: str):
    """The evidence path is read and digested, so a path that leaves the repository puts
    somebody else's file into a record this repository signs."""

    with pytest.raises(argparse.ArgumentTypeError):
        accept._evidence_path(value)


def test_an_ordinary_evidence_path_survives():
    assert accept._evidence_path("specs/010-x/spec.md") == "specs/010-x/spec.md"


def test_every_field_of_an_acceptance_is_required_together(capsys):
    """Not one at a time. A record missing any one of them says a risk was accepted and
    cannot say by whom, until when, why, or on what basis — and four of those five are
    exactly what makes it a record rather than a note."""

    for missing in ("--finding", "--expires", "--by", "--justification", "--evidence"):
        argv = [
            "--finding",
            "R-010-01",
            "--expires",
            "2026-11-14",
            "--by",
            "maintainer",
            "--justification",
            "the API promises nothing here",
            "--evidence",
            "specs/010-x/spec.md",
        ]
        index = argv.index(missing)
        del argv[index : index + 2]

        with pytest.raises(SystemExit):
            accept.main(argv)

        assert "all required" in capsys.readouterr().err


def test_listing_what_has_expired_asks_for_nothing_and_accepts_nothing(capsys, monkeypatch):
    """The one exception to the rule above, and the reason it is safe: `--expired` reads the
    register and writes nothing, so there is no record for the missing fields to be missing
    from."""

    monkeypatch.setattr(accept.paths, "repo_root", lambda: None)

    assert accept.main(["--expired"]).outcome == "INCOMPLETE"
    assert "not inside a repository" in capsys.readouterr().out


def test_a_register_that_cannot_be_read_is_undecidable_and_not_an_empty_list(
    tmp_path, capsys, monkeypatch
):
    """The failure that matters most here. An unreadable record block read as "nothing is
    expired" is a register reporting a clean bill of health it never established — which is
    the exact shape this product exists to refuse, in the verb that exists to record risk."""

    monkeypatch.setattr(accept.paths, "repo_root", lambda: tmp_path)

    def unreadable(_root):
        raise ValueError("the block at byte 40 holds a container where a value belongs")

    monkeypatch.setattr(accept, "expired", unreadable)

    assert accept.main(["--expired"]).outcome == "INCOMPLETE"
    printed = capsys.readouterr().out
    assert "UNDECIDABLE" in printed
    assert "is not a pass" in printed
