"""Every way the chain can be unreadable, and what each one is called.

The chain is this framework's tamper-evident record: every guard decision, every command, in
one append-only file whose links are sealed. `audit.read` is the only way anything reads it,
and nothing tested it — not directly and not through a fixture. Measured before this file
existed: eighty-one surviving mutants in `read` and fifty-five in `_chain_bytes`, which is
almost every line of both.

The distinction those two functions exist to keep is the one this whole product is named
after. A chain that is empty, a chain that is not UTF-8, a line repeating a JSON key, a line
cut mid-write — none of them is a chain with nothing wrong in it, and every one of them would
look like exactly that to a reader which returned an empty list and said nothing.

So each is its own case, and each asserts the *name* it is given rather than only that
something was refused. The name is what a person reads, and the difference between
"the chain contains no evidence to audit" and "the chain is not UTF-8 JSON Lines" is the
difference between a fresh install and a corrupted one.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from ai_engineering import audit


@pytest.fixture
def chain(tmp_path, monkeypatch):
    """A chain file this reader will find, wherever the emitter would have put it."""

    where = tmp_path / "events.jsonl"
    monkeypatch.setattr(
        audit.paths, "load", lambda name: SimpleNamespace(chain_path=lambda root: where)
    )
    return where


def link(name: str = "a-command", **extra) -> str:
    body = {"ts": "2026-08-17T00:00:00Z", "cls": "command", "name": name, "hash": "0" * 8}
    body.update(extra)
    return json.dumps(body)


def test_a_chain_with_links_in_it_is_read_in_order(chain):
    """The success path, and the only property everything else rests on: the events come back
    in the order they were appended, because a chain read out of order is a chain whose seals
    cannot be checked."""

    chain.write_text("\n".join(link(f"command-{n}") for n in range(3)) + "\n", encoding="utf-8")

    events = audit.read(None)

    assert [event["name"] for event in events] == ["command-0", "command-1", "command-2"]
    assert events.problem == ""


def test_an_empty_chain_says_it_is_empty_and_not_that_it_is_intact(chain):
    """A repository that has never run a guard has nothing to audit, and that is a different
    fact from a chain that was read and found sound. A reader answering with an empty list and
    no problem would let `audit verify` report an intact chain over no evidence at all."""

    chain.write_text("", encoding="utf-8")
    assert audit.read(None).problem.startswith("CHAIN_EMPTY")

    chain.write_text("\n  \n\n", encoding="utf-8")
    assert audit.read(None).problem.startswith("CHAIN_EMPTY"), "whitespace was read as evidence"


def test_a_chain_that_is_not_utf_8_is_named_as_unreadable(chain):
    """Bytes that do not decode are not links that happen to be missing. The name says which,
    because a person seeing "unreadable" checks the file and a person seeing "empty" does
    not."""

    chain.write_bytes(b'{"ts": "2026", "cls": "command", "name": "\xff\xfe"}\n')

    read = audit.read(None)

    assert read.problem.startswith("CHAIN_UNREADABLE")
    assert "not UTF-8" in read.problem
    assert list(read) == []


def test_a_chain_whose_location_cannot_be_derived_is_unreadable_and_not_empty(monkeypatch):
    """The emitter is loaded by path and may not be there at all — an installation half
    removed, a machine whose home moved. That is unreadable, and it must not read as a
    repository that has simply never emitted anything."""

    def missing(name):
        raise ImportError(name)

    monkeypatch.setattr(audit.paths, "load", missing)

    read = audit.read(None)

    assert read.problem.startswith("CHAIN_UNREADABLE")
    assert "location cannot be derived" in read.problem
    assert list(read) == []


def test_a_line_repeating_a_json_key_is_ambiguous_and_the_link_says_so(chain):
    """Two values under one key is a line whose meaning depends on which parser reads it, and
    a record whose meaning depends on the reader is not a record. It is kept in the list — the
    links around it still have to be walked — and marked INCOMPLETE by name and line number."""

    chain.write_text(
        link("first")
        + "\n"
        + '{"ts": "2026", "cls": "command", "name": "a", "name": "b", "hash": ""}\n'
        + link("third")
        + "\n",
        encoding="utf-8",
    )

    events = audit.read(None)

    assert len(events) == 3, "an ambiguous line was dropped instead of reported"
    assert events[1]["_audit_kind"] == "INCOMPLETE"
    assert "CHAIN_AMBIGUOUS" in events[1]["_audit_problem"]
    assert "line 2" in events[1]["_audit_problem"]
    assert events[0]["name"] == "first" and events[2]["name"] == "third"


def test_a_line_that_is_not_one_json_object_is_reported_in_place(chain):
    """Three shapes that are not a link — a fragment, a list, and a bare number — and each is
    kept in place with its line number. Dropping them would renumber every link after it,
    which is the one thing an audit of a numbered chain must never do."""

    chain.write_text(
        link("first") + "\n" + '{"half of a line\n' + "[1, 2, 3]\n" + "7\n" + link("last") + "\n",
        encoding="utf-8",
    )

    events = audit.read(None)

    assert len(events) == 5
    assert events[0]["name"] == "first" and events[4]["name"] == "last"
    for index, number in ((1, 2), (2, 3), (3, 4)):
        assert events[index]["_audit_problem"] == (
            f"link {number}: the line is not one JSON object"
        )


def test_a_non_finite_number_is_refused_rather_than_read_as_a_value(chain):
    """`NaN` and `Infinity` are not JSON, and Python's parser accepts them unless told not to.
    A chain carrying one is a chain some readers accept and others reject, which is the same
    defect as a repeated key wearing a different hat."""

    chain.write_text(
        '{"ts": "2026", "cls": "command", "name": "a", "hash": "", "depth": NaN}\n',
        encoding="utf-8",
    )

    events = audit.read(None)

    assert len(events) == 1
    assert events[0]["_audit_problem"] == "link 1: the line is not one JSON object"


def test_a_final_line_with_no_newline_is_reported_as_a_write_that_was_cut(chain):
    """A hook killed mid-append leaves a line with no terminator. The link itself may parse
    perfectly — it is the missing newline that says the write did not finish — so this is
    reported as an extra finding rather than by rejecting the line."""

    chain.write_text(link("first") + "\n" + link("cut"), encoding="utf-8")

    events = audit.read(None)

    assert len(events) == 3, "a cut write was walked as if it had finished"
    assert events[2]["_audit_problem"] == (
        "link 2: the line is not terminated — a write was cut here"
    )

    # And a chain whose last line was already unreadable is not reported twice for the same
    # byte: the missing terminator is the same fact as the broken line.
    chain.write_text(link("first") + "\n" + '{"half', encoding="utf-8")
    again = audit.read(None)
    assert len(again) == 2, "one cut line produced two findings"


def test_the_chain_file_itself_must_be_one_regular_file_nobody_swapped(tmp_path, chain):
    """`_chain_bytes` is the same hardened shape as the other readers in this tree, and for the
    same reason: the bytes it returns are the evidence. A symlink is the cheapest way to make
    an audit read somebody else's file and call it this machine's history."""

    real = tmp_path / "real.jsonl"
    real.write_text(link("elsewhere") + "\n", encoding="utf-8")

    pointed = tmp_path / "pointed.jsonl"
    pointed.symlink_to(real)
    raw, problem = audit._chain_bytes(pointed)
    assert problem, "a symlinked chain was read as this machine's own"
    assert raw == b""

    folder = tmp_path / "folder.jsonl"
    folder.mkdir()
    _, problem = audit._chain_bytes(folder)
    assert problem, "a directory was read as a chain"

    _, problem = audit._chain_bytes(tmp_path / "absent.jsonl")
    assert problem, "an absent chain was read as an empty one"

    # The ordinary case still works, or the checks above prove only that everything fails.
    raw, problem = audit._chain_bytes(real)
    assert problem == "" and b"elsewhere" in raw


def test_a_chain_that_changes_while_it_is_read_is_refused(tmp_path, monkeypatch):
    """The identity and timestamp comparisons across the read, which no arrangement of files
    can trigger from outside. A chain replaced between the open and the last stat is one this
    reader would return the wrong history for — and the wrong history is the whole attack."""

    where = tmp_path / "events.jsonl"
    where.write_text(link("first") + "\n", encoding="utf-8")
    real = os.fstat
    calls = {"n": 0}

    class Moved:
        def __init__(self, base):
            self._base = base

        def __getattr__(self, name):
            if name == "st_mtime_ns":
                return 1
            return getattr(self._base, name)

    def fstat(fd):
        calls["n"] += 1
        details = real(fd)
        return details if calls["n"] == 1 else Moved(details)

    monkeypatch.setattr(audit.os, "fstat", fstat)

    raw, problem = audit._chain_bytes(where)

    assert problem, "a chain that moved under the reader was returned anyway"
    assert raw == b""
