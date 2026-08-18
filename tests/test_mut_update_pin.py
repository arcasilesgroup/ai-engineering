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


# --- _guard_plan: which recorded guards this update may rewrite ----------------------
#
# 26 more survivors. `update` rewrites guard entries in other tools' settings files, and
# this decides which ones it is allowed to touch. Ownership narrows that set; it never
# widens it, and the comment in the source says why in one line worth repeating: ownership
# does not grant permission and is never proof that an update ran or succeeded.
#
# Everything it cannot establish is `Undecidable` rather than an empty plan. An empty plan
# means there is nothing to rewrite, which is a claim; a receipt nobody can parse is not a
# claim at all, and rewriting nothing on the strength of one would leave a machine half
# upgraded with a green line under it.


def _planned(monkeypatch, receipt, surfaces):
    monkeypatch.setattr(update.wiring, "receipt", lambda: receipt)
    monkeypatch.setattr(update.wiring, "detect", lambda: surfaces)
    return update._guard_plan()


def test_only_surfaces_the_receipt_records_as_ours_are_in_the_plan(tmp_path, monkeypatch):
    """A settings file this tool never wrote to is somebody else's file, whatever else is
    true about it."""

    ours = tmp_path / "ours.json"
    ours.write_text("{}", encoding="utf-8")
    theirs = tmp_path / "theirs.json"
    theirs.write_text("{}", encoding="utf-8")

    found, rewritten = _planned(
        monkeypatch,
        {"wrote": [{"path": str(ours), "kind": "guard", "how": "json_claude"}]},
        [
            {"settings": str(ours), "writer": "json_claude"},
            {"settings": str(theirs), "writer": "json_claude"},
        ],
    )

    assert [one["settings"] for one in found] == [str(ours)]
    assert [one["settings"] for one in rewritten] == [str(ours)]


def test_a_receipt_row_of_another_kind_does_not_put_a_surface_in_the_plan(tmp_path, monkeypatch):
    """`kind == "guard"` and nothing else. A skills row naming the same path would otherwise
    authorise a rewrite of a file recorded for a different reason entirely."""

    here = tmp_path / "settings.json"
    here.write_text("{}", encoding="utf-8")

    found, _ = _planned(
        monkeypatch,
        {"wrote": [{"path": str(here), "kind": "skills", "how": "wheel"}]},
        [{"settings": str(here), "writer": "json_claude"}],
    )

    assert found == []


def test_an_append_only_surface_is_found_and_never_rewritten(tmp_path, monkeypatch):
    """Two lists for two different questions. `found` is what we are recorded as owning;
    `rewritten` is the subset this update may replace — and an append-only surface keys its
    trust to the position of our entry, so rewriting it invalidates somebody else's."""

    here = tmp_path / "settings.json"
    here.write_text("{}", encoding="utf-8")

    found, rewritten = _planned(
        monkeypatch,
        {"wrote": [{"path": str(here), "kind": "guard", "how": "json_codex"}]},
        [{"settings": str(here), "writer": "json_codex", "append_only": True}],
    )

    assert [one["settings"] for one in found] == [str(here)]
    assert rewritten == []


@pytest.mark.parametrize(
    "receipt",
    [
        pytest.param([], id="not an object"),
        pytest.param({"wrote": {}}, id="rows are not a list"),
        pytest.param({"wrote": ["a string"]}, id="a row is not an object"),
        pytest.param({"wrote": [{"path": "x", "kind": "guard"}]}, id="a row has no how"),
        pytest.param(
            {"wrote": [{"path": 7, "kind": "guard", "how": "x"}]}, id="a path is a number"
        ),
    ],
)
def test_a_receipt_that_is_not_canonical_is_undecidable_rather_than_an_empty_plan(
    receipt, monkeypatch
):
    """An empty plan means there is nothing to rewrite, which is a claim. A receipt nobody
    can parse is not a claim at all, and rewriting nothing on the strength of one leaves a
    machine half upgraded with a green line under it."""

    monkeypatch.setattr(update.wiring, "detect", lambda: [])

    with pytest.raises(update.Undecidable):
        _planned(monkeypatch, receipt, [])


def test_a_recorded_target_that_is_a_link_is_undecidable(tmp_path, monkeypatch):
    """Before anything is written. A link where a settings file belongs would make this
    update rewrite whatever is on the other end, with the person's own permissions."""

    real = tmp_path / "real.json"
    real.write_text("{}", encoding="utf-8")
    link = tmp_path / "settings.json"
    link.symlink_to(real)

    with pytest.raises(update.Undecidable):
        _planned(
            monkeypatch,
            {"wrote": [{"path": str(link), "kind": "guard", "how": "json_claude"}]},
            [{"settings": str(link), "writer": "json_claude"}],
        )


def test_a_recorded_target_that_cannot_be_parsed_is_undecidable(tmp_path, monkeypatch):
    """The file is read here, before the plan is returned, precisely so that the failure
    happens before anything is rewritten rather than in the middle of it."""

    here = tmp_path / "settings.json"
    here.write_text("{ not json", encoding="utf-8")

    with pytest.raises(update.Undecidable):
        _planned(
            monkeypatch,
            {"wrote": [{"path": str(here), "kind": "guard", "how": "json_claude"}]},
            [{"settings": str(here), "writer": "json_claude"}],
        )


def test_a_recorded_target_that_is_not_there_yet_is_still_planned(tmp_path, monkeypatch):
    """Absence is not a reason to refuse. A surface whose settings file a person deleted is
    exactly the machine an update should repair."""

    missing = tmp_path / "gone.json"

    found, rewritten = _planned(
        monkeypatch,
        {"wrote": [{"path": str(missing), "kind": "guard", "how": "json_claude"}]},
        [{"settings": str(missing), "writer": "json_claude"}],
    )

    assert [one["settings"] for one in rewritten] == [str(missing)]
