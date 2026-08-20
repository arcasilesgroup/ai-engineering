"""How the chain is read, and every way that read can be refused.

`audit._chain_bytes` carried 50 surviving mutants. It is the read underneath every claim
this product makes about its own past: the chain is the hash-linked record of what
happened, kept outside the clone, and everything `audit verify` says is a statement about
these bytes.

So the read is paranoid in a specific direction. It is not guarding against a corrupted
file — a corrupted file fails the hash check further down and says so. It is guarding
against reading a *different* file than the one it checked, or the same file at two
different moments, either of which produces a verdict about something that was never there.

Hence the shape: `lstat` before, `O_NOFOLLOW` on the open, `fstat` after, and the device
and inode compared across all three. And the size and modification time compared again
after the last chunk, because a file replaced between the first byte and the last is a file
this function read half of.

Every refusal returns a problem string rather than raising. Callers treat a raise as a
crash and a problem string as an answer, and "the chain cannot be read" is an answer.
"""

from __future__ import annotations

import os
from pathlib import Path

from ai_engineering import audit


def test_an_ordinary_chain_file_is_read_whole(tmp_path: Path):
    """The clean control. Without it every refusal below is satisfied by a function that
    refuses everything, which is the passing test this repository exists to refuse."""

    here = tmp_path / "chain.jsonl"
    here.write_bytes(b'{"seq":1}\n{"seq":2}\n')

    assert audit._chain_bytes(here) == (b'{"seq":1}\n{"seq":2}\n', "")


def test_a_chain_larger_than_one_read_is_still_read_whole(tmp_path: Path):
    """The loop reads in 64k chunks and stops on an empty one. Stopping after the first
    chunk would give a verdict about the beginning of somebody's history."""

    here = tmp_path / "chain.jsonl"
    payload = b"x" * (65_536 * 2 + 17)
    here.write_bytes(payload)

    assert audit._chain_bytes(here) == (payload, "")


def test_an_empty_chain_is_empty_bytes_and_not_a_problem(tmp_path: Path):
    """A repository whose chain exists and holds nothing has a chain. Reporting that as
    unreadable would make a fresh install look damaged."""

    here = tmp_path / "chain.jsonl"
    here.write_bytes(b"")

    assert audit._chain_bytes(here) == (b"", "")


def test_a_chain_that_is_not_there_says_missing_and_not_unreadable(tmp_path: Path):
    """Two different answers for two different situations. No chain means nothing has been
    recorded on this machine for this repository; unreadable means something is there and
    cannot be trusted, and only the second is a reason to stop."""

    _, problem = audit._chain_bytes(tmp_path / "never-written.jsonl")

    assert problem.startswith("CHAIN_MISSING")


def test_a_directory_where_the_chain_belongs_is_unreadable(tmp_path: Path):
    """Checked before the open rather than after, so the failure names the situation instead
    of arriving as whatever errno the platform picks for reading a directory."""

    here = tmp_path / "chain.jsonl"
    here.mkdir()

    _, problem = audit._chain_bytes(here)

    assert problem.startswith("CHAIN_UNREADABLE")


def test_a_named_pipe_where_the_chain_belongs_is_unreadable(tmp_path: Path):
    """It is not a regular file, and opening one to read blocks until somebody writes. A
    verify that hangs is worse than one that refuses, because nobody can tell it apart from
    a slow one."""

    pipe = tmp_path / "chain.jsonl"
    os.mkfifo(pipe)

    _, problem = audit._chain_bytes(pipe)

    assert problem.startswith("CHAIN_UNREADABLE")


def test_a_symbolic_link_is_refused_by_the_open_itself(tmp_path: Path):
    """`O_NOFOLLOW` on the open rather than a check before it. A check leaves a window
    between deciding and opening, and this is the file whose whole job is to be the same
    file it was a moment ago."""

    real = tmp_path / "real.jsonl"
    real.write_bytes(b'{"seq":1}\n')
    link = tmp_path / "chain.jsonl"
    link.symlink_to(real)

    _, problem = audit._chain_bytes(link)

    assert problem.startswith("CHAIN_UNREADABLE")


def test_a_file_replaced_between_the_first_byte_and_the_last_is_refused(
    tmp_path: Path, monkeypatch
):
    """The case the size and time comparison exists for. Half of one chain and half of
    another reads as a chain, hashes as a broken one, and reports a break that never
    happened at a link that was never written."""

    here = tmp_path / "chain.jsonl"
    here.write_bytes(b'{"seq":1}\n')
    real_fstat = os.fstat
    calls = {"n": 0}

    def shifting(descriptor: int):
        info = real_fstat(descriptor)
        calls["n"] += 1
        if calls["n"] >= 2:
            # The last `fstat`, after the read: a different size from the first.
            return os.stat_result(tuple(info)[:6] + (info.st_size + 1,) + tuple(info)[7:])
        return info

    monkeypatch.setattr(os, "fstat", shifting)

    _, problem = audit._chain_bytes(here)

    assert problem.startswith("CHAIN_UNREADABLE")


def test_a_close_that_fails_is_reported_rather_than_swallowed(tmp_path: Path, monkeypatch):
    """The bytes were read and the descriptor could not be released. On a network mount that
    is how a read succeeds against a file that was already gone, so the answer is that the
    chain could not be read safely rather than a verdict over what came back."""

    here = tmp_path / "chain.jsonl"
    here.write_bytes(b'{"seq":1}\n')
    real_close = os.close

    def refusing(descriptor: int) -> None:
        real_close(descriptor)
        raise OSError(5, "input/output error")

    monkeypatch.setattr(os, "close", refusing)

    raw, problem = audit._chain_bytes(here)

    assert raw == b""
    assert "could not be closed safely" in problem
