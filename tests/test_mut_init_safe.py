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

import pytest

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
    forever. With a kind named it fails the kind check; with none named it must still
    refuse, because the line above the function says it rejects special files — a sentence
    stronger than the code is the defect. Every caller passes a kind, so nothing in the
    product changes; the refusal makes the sentence true."""

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


# --- _receipt_state: whether the install record can be believed at all ----------------
#
# The receipt is the only thing that says what this tool put on the machine, and `init`,
# `uninstall` and `doctor` all decide from it. It is a JSON file in a person's home
# directory, so it can be edited, truncated by an interrupted write, or left behind by a
# version that wrote a different shape.
#
# The answer is `None` for every one of those, and `None` means *undecidable* rather than
# *empty*. That distinction is the whole function: an empty receipt says this tool has
# installed nothing, which is a claim, and a receipt nobody can parse says nothing at all.


def _stated(state, monkeypatch) -> object:
    monkeypatch.setattr(init.wiring, "receipt", lambda: state)
    return init._receipt_state()


def test_a_receipt_that_lists_what_was_written_is_believed(monkeypatch):
    state = {
        "version": init.__version__,
        "wrote": [{"path": "/x", "kind": "skills", "how": "wheel"}],
    }

    assert _stated(state, monkeypatch) == state


def test_a_receipt_with_no_rows_at_all_is_believed_and_says_nothing_was_written(monkeypatch):
    """Empty is a claim and an honest one: this tool has installed nothing here. Answering
    undecidable for it would make every fresh machine look damaged."""

    assert _stated({"wrote": []}, monkeypatch) == {"wrote": []}


def test_rows_that_are_not_a_list_are_undecidable(monkeypatch):
    assert _stated({"wrote": {"path": "/x"}}, monkeypatch) is None


@pytest.mark.parametrize(
    "row",
    [
        pytest.param("just a string", id="not an object"),
        pytest.param({"kind": "skills", "how": "wheel"}, id="no path"),
        pytest.param({"path": "/x", "how": "wheel"}, id="no kind"),
        pytest.param({"path": 7, "kind": "skills", "how": "wheel"}, id="a path that is a number"),
        pytest.param({"path": "/x", "kind": "skills"}, id="no how, at the current version"),
    ],
)
def test_a_row_that_is_not_a_row_makes_the_whole_receipt_undecidable(row, monkeypatch):
    """The whole receipt and not just that row. A file with one unreadable line is a file
    something interrupted, and the readable lines around it are no more trustworthy than
    the one that is missing."""

    assert _stated({"version": init.__version__, "wrote": [row]}, monkeypatch) is None


def test_a_receipt_from_an_older_version_is_not_asked_for_a_field_it_never_wrote(monkeypatch):
    """`how` arrived later. Demanding it from a receipt an older version wrote would make
    every upgrade look like corruption, and `uninstall` would then refuse to remove what
    that version installed — the worst moment to be undecidable."""

    older = {"version": "0.0.1", "wrote": [{"path": "/x", "kind": "skills"}]}

    assert _stated(older, monkeypatch) == older


def test_two_rows_claiming_the_same_path_and_kind_are_undecidable(monkeypatch):
    """Not deduplicated. Two rows for one path is a receipt that was appended to twice for
    the same write, and which of the two describes the file on disk is exactly the question
    nobody can answer from here — `uninstall` would remove it once and report it twice."""

    state = {
        "version": init.__version__,
        "wrote": [
            {"path": "/x", "kind": "skills", "how": "wheel"},
            {"path": "/x", "kind": "skills", "how": "copy"},
        ],
    }

    assert _stated(state, monkeypatch) is None


def test_the_same_path_recorded_under_two_kinds_is_not_a_duplicate(monkeypatch):
    """The identity is the pair. One path can legitimately be both a settings entry and a
    guard registration, and collapsing them to the path alone would refuse a real receipt."""

    state = {
        "version": init.__version__,
        "wrote": [
            {"path": "/x", "kind": "skills", "how": "wheel"},
            {"path": "/x", "kind": "link", "how": "copy"},
        ],
    }

    assert _stated(state, monkeypatch) == state


def test_a_receipt_that_cannot_be_read_is_undecidable_rather_than_a_traceback(monkeypatch):
    """`wiring.read_json` raises rather than answering `{}` for a file that is there and
    unparseable, and this is where that lands. Treating it as empty is how a machine's whole
    install record is silently replaced by the next `init`."""

    def unreadable():
        raise init.wiring.Unreadable("machine.json is not readable as JSON")

    monkeypatch.setattr(init.wiring, "receipt", unreadable)

    assert init._receipt_state() is None
