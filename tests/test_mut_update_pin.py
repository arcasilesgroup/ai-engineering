"""Reading the pin: the file that says which version governs a repository.

`update._read_pin` carried 30 surviving mutants and `_publish_pin` another 50. Between them
they read `.ai/config.toml` — the pin, the one file that says which version of this
framework governs a repository — and replace it.

The read is written the way `audit._chain_bytes` is, and for the same reason. It is not
guarding against a corrupted pin; a corrupted pin fails to parse further down and says so.
It guards against reading a *different* file than the one it checked, or the same file at
two different moments, either of which produces an update decision about something that was
never there.

So: `O_NOFOLLOW` on the open, a second `stat` on the name compared to the `fstat` on the
descriptor, one hard link only, a byte bound, and after the read the identity, size and
*both* timestamps compared again. The change time as well as the modification time, because
a replacement that preserves mtime still changes ctime, and preserving both takes more than
an editor.

Every failure is `Undecidable` rather than a wrong answer, because an update that cannot
tell which version governs this repository has one safe move and it is to stop.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from ai_engineering import update


def _home(tmp_path: Path, body: bytes = b'version = "1.0.0"\n') -> int:
    home = tmp_path / ".ai"
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.toml").write_bytes(body)
    return os.open(home, os.O_RDONLY | os.O_DIRECTORY)


def test_an_ordinary_pin_is_read_whole(tmp_path: Path):
    """The clean control. Without it every refusal below is satisfied by a function that
    refuses everything, which is the passing test this repository exists to refuse."""

    home_fd = _home(tmp_path)
    try:
        details, body = update._read_pin(home_fd)
    finally:
        os.close(home_fd)

    assert body == b'version = "1.0.0"\n'
    assert details.st_size == len(body)


def test_a_pin_larger_than_one_read_is_still_read_whole(tmp_path: Path):
    """The loop reads in 64k chunks and stops on an empty one. Stopping after the first
    would decide which version governs a repository from the beginning of the file."""

    payload = b"# " + b"x" * 70_000 + b'\nversion = "1.0.0"\n'
    home_fd = _home(tmp_path, payload)
    try:
        _, body = update._read_pin(home_fd)
    finally:
        os.close(home_fd)

    assert body == payload


def test_a_pin_that_is_not_there_is_undecidable(tmp_path: Path):
    home = tmp_path / ".ai"
    home.mkdir(parents=True)
    home_fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(update.Undecidable):
            update._read_pin(home_fd)
    finally:
        os.close(home_fd)


def test_a_pin_that_is_a_symbolic_link_is_refused_by_the_open_itself(tmp_path: Path):
    """`O_NOFOLLOW` rather than a check before the open. A check leaves a window between
    deciding and opening, and this is the file whose whole job is to be the same file it was
    a moment ago."""

    home = tmp_path / ".ai"
    home.mkdir(parents=True)
    real = tmp_path / "elsewhere.toml"
    real.write_bytes(b'version = "9.9.9"\n')
    (home / "config.toml").symlink_to(real)
    home_fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(update.Undecidable):
            update._read_pin(home_fd)
    finally:
        os.close(home_fd)


def test_a_pin_with_a_second_hard_link_is_refused(tmp_path: Path):
    """A second name for the same file is a second way to change what governs this
    repository, with nothing at this path to show for it."""

    home_fd = _home(tmp_path)
    (tmp_path / "second.toml").hardlink_to(tmp_path / ".ai" / "config.toml")
    try:
        with pytest.raises(update.Undecidable):
            update._read_pin(home_fd)
    finally:
        os.close(home_fd)


def test_a_directory_where_the_pin_belongs_is_refused(tmp_path: Path):
    home = tmp_path / ".ai"
    (home / "config.toml").mkdir(parents=True)
    home_fd = os.open(home, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(update.Undecidable):
            update._read_pin(home_fd)
    finally:
        os.close(home_fd)


def test_a_pin_over_its_byte_bound_is_refused(tmp_path: Path):
    """The bound is the point. A pin that reads whatever it is pointed at is a pin somebody
    can make take as long as they like, in the verb that runs before an upgrade."""

    home_fd = _home(tmp_path, b"x" * (update._MAX_PIN_BYTES + 1))
    try:
        with pytest.raises(update.Undecidable):
            update._read_pin(home_fd)
    finally:
        os.close(home_fd)


def test_a_pin_replaced_between_the_first_byte_and_the_last_is_refused(tmp_path: Path, monkeypatch):
    """The case the second `fstat` exists for. Half of one pin and half of another parses
    as a pin, and the version it reports is one nobody wrote."""

    home_fd = _home(tmp_path)
    real = os.fstat
    seen = {"n": 0}

    def shifting(descriptor: int):
        info = real(descriptor)
        seen["n"] += 1
        if seen["n"] >= 2:
            return os.stat_result(tuple(info)[:8] + (info.st_mtime + 1,) + tuple(info)[9:])
        return info

    monkeypatch.setattr(os, "fstat", shifting)
    try:
        with pytest.raises(update.Undecidable):
            update._read_pin(home_fd)
    finally:
        os.close(home_fd)


def test_a_pin_touched_without_its_bytes_changing_is_still_refused(tmp_path: Path, monkeypatch):
    """The change time, not only the modification time. `chmod` moves ctime and leaves mtime
    and the bytes alone — so a check comparing only mtime would let through exactly the
    substitution this guards against, where a file is replaced by one whose timestamps were
    restored.

    The interference is staged during the read rather than around it, because what the two
    `fstat` calls bracket is the read itself."""

    pin = tmp_path / ".ai" / "config.toml"
    home_fd = _home(tmp_path)
    real_read = os.read
    touched = {"done": False}

    def reading(descriptor: int, size: int) -> bytes:
        chunk = real_read(descriptor, size)
        if not touched["done"]:
            touched["done"] = True
            pin.chmod(0o640)
        return chunk

    monkeypatch.setattr(os, "read", reading)
    try:
        with pytest.raises(update.Undecidable):
            update._read_pin(home_fd)
    finally:
        os.close(home_fd)

    assert touched["done"], "the interference never happened, so this proved nothing"
