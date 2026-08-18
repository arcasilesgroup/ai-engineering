"""What `init` refuses to write into, and why absence is not one of the reasons.

`_safe_path` and `_global_paths_safe` carried 134 surviving mutants between them. They run
before `init` writes anything into somebody's home directory, and the question they answer
is narrow and consequential: *is this path the thing it says it is, or is it a way to make
this installer write somewhere else?*

The direction of failure is not symmetric, and both directions have hurt. Passing a path
that is an alias means an installer with a person's own permissions follows it and writes
outside everything it was scoped to. Refusing one that is fine means `init` prints
INCOMPLETE with no surface table, no reason and no cure — which happened, twice, on every
second run of the only verb that installs a guard. Both comments in the source are
apologies for the second kind, so the cases for it are here beside the cases for the first.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from ai_engineering import init


def test_a_path_that_is_not_there_is_safe_because_absence_is_not_an_alias(tmp_path: Path):
    """The one that has to come first. `init` creates what it needs, so almost every path it
    checks does not exist yet, and a check that refused absence would refuse every fresh
    machine."""

    assert init._safe_path(tmp_path / "not-yet") is True
    assert init._safe_path(tmp_path / "not-yet", "directory") is True
    assert init._safe_path(tmp_path / "not-yet", "file") is True


def test_an_ordinary_directory_and_an_ordinary_file_are_safe(tmp_path: Path):
    here = tmp_path / "file.json"
    here.write_text("{}", encoding="utf-8")

    assert init._safe_path(tmp_path, "directory") is True
    assert init._safe_path(here, "file") is True


def test_a_symbolic_link_is_refused_whatever_it_points_at(tmp_path: Path):
    """The whole reason this exists. A link in a settings path is a way to make an installer
    running with somebody's own permissions write outside everything it was scoped to."""

    real = tmp_path / "real.json"
    real.write_text("{}", encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(real)

    assert init._safe_path(link, "file") is False


def test_a_path_whose_ancestor_is_a_link_is_refused_before_it_is_touched(tmp_path: Path):
    """`resolve()` compared against the lexical path catches this: the leaf may be perfectly
    ordinary and still sit under a directory that redirects the whole subtree."""

    real = tmp_path / "real"
    real.mkdir()
    (real / "settings.json").write_text("{}", encoding="utf-8")
    (tmp_path / "alias").symlink_to(real)

    assert init._safe_path(tmp_path / "alias" / "settings.json", "file") is False


def test_a_relative_walk_is_resolved_before_anything_is_decided(tmp_path: Path):
    """`~/.claude/../../etc/x` is a settings path in no meaningful sense, and it reads as one
    until the dots are taken out."""

    here = tmp_path / "a" / "b"
    here.mkdir(parents=True)

    assert init._safe_path(Path(f"{here}/../b"), "directory") is True


def test_the_kind_is_checked_in_both_directions(tmp_path: Path):
    """A directory where a settings file belongs, and a file where a skills root belongs,
    are both ways for a write to land somewhere nobody meant."""

    here = tmp_path / "thing"
    here.write_text("{}", encoding="utf-8")

    assert init._safe_path(here, "directory") is False
    assert init._safe_path(tmp_path, "file") is False


def test_a_path_with_no_kind_asked_for_accepts_either(tmp_path: Path):
    here = tmp_path / "thing"
    here.write_text("{}", encoding="utf-8")

    assert init._safe_path(here) is True
    assert init._safe_path(tmp_path) is True


def test_something_that_is_neither_a_file_nor_a_directory_is_refused_when_no_kind_is_named(
    tmp_path: Path,
):
    """A named pipe is not a settings file and is not a skills root, and reading one blocks
    forever. With a kind named it fails the kind check. With none named it used to be
    called safe, while the line above the function says it rejects special files — so the
    sentence was stronger than the code. Every caller passes a kind, so nothing in the
    product changes; the sentence is now true."""

    pipe = tmp_path / "pipe"
    os.mkfifo(pipe)

    assert init._safe_path(pipe) is False


def test_a_file_nobody_can_read_is_refused_rather_than_opened(tmp_path: Path):
    """The permission bits are checked before the open. Refusing here gives `init` something
    to say; letting the open raise gives it a traceback."""

    here = tmp_path / "settings.json"
    here.write_text("{}", encoding="utf-8")
    here.chmod(0)
    try:
        assert init._safe_path(here, "file") is False
    finally:
        here.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_a_directory_that_cannot_be_entered_is_refused(tmp_path: Path):
    """Readable and searchable are different bits. A directory that can be listed and not
    entered fails every write into it, one path at a time, with no explanation."""

    here = tmp_path / "closed"
    here.mkdir()
    here.chmod(stat.S_IRUSR)
    try:
        assert init._safe_path(here, "directory") is False
    finally:
        here.chmod(stat.S_IRWXU)


def test_a_file_that_cannot_actually_be_opened_is_refused(tmp_path: Path, monkeypatch):
    """The bits say readable and the open still fails — a stale network mount, a file being
    replaced underneath. The single byte read is what turns a promise into an observation."""

    here = tmp_path / "settings.json"
    here.write_text("{}", encoding="utf-8")

    def refuse(*_args, **_kwargs):
        raise OSError(5, "input/output error")

    monkeypatch.setattr(Path, "open", refuse)

    assert init._safe_path(here, "file") is False
