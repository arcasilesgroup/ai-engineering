"""What `uninstall` is allowed to delete from somebody's machine, and what it leaves.

`_owned`, `_skills_owned` and `_removed` carried 44 surviving mutants between them. They
answer two questions about every row in the install receipt, and the questions are not the
same one asked twice.

*Owned* decides whether this tool may delete a thing. The receipt says we wrote it, and the
receipt can be stale, hand-edited, or describing a file somebody has since replaced with
their own — so ownership is re-established from the disk before anything is removed. The
direction of failure is not symmetric: refusing to remove something of ours leaves a file
behind and somebody notices, while removing something of theirs destroys work.

*Removed* decides, afterwards, whether it actually went. Its answers are deliberately
generous about things that were never there — a path that does not exist is removed, by any
reading — because an uninstall that reports failure for what it found already gone sends a
person hunting for a file nobody has.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering import paths, uninstall


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """A laptop of this test's own: every ~ and the framework folder land in tmp_path."""

    fake = tmp_path / "home"
    (fake / ".ai-engineering" / "skills").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake))
    monkeypatch.setenv("USERPROFILE", str(fake))
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(fake / ".ai-engineering"))
    return fake


def _skill_root(tmp_path: Path, *names: str) -> Path:
    root = tmp_path / "surface-skills"
    root.mkdir(parents=True, exist_ok=True)
    for name in names:
        (root / name).mkdir(exist_ok=True)
    return root


def test_a_skills_root_that_is_a_link_is_never_ours(tmp_path: Path, machine):
    """Whatever it points at. A link where a directory belongs is somebody's own
    arrangement, and following it to delete what is on the other end is the one mistake this
    verb cannot make."""

    real = tmp_path / "elsewhere"
    real.mkdir()
    link = tmp_path / "linked-skills"
    link.symlink_to(real)

    assert uninstall._skills_owned(link, "wheel") is False


def test_a_file_where_a_skills_root_belongs_is_never_ours(tmp_path: Path, machine):
    here = tmp_path / "not-a-directory"
    here.write_text("x", encoding="utf-8")

    assert uninstall._skills_owned(here, "wheel") is False


def test_a_skills_root_that_does_not_exist_yet_is_ours_to_remove(tmp_path: Path, machine):
    """Absence is not a reason to refuse. The loop below has nothing to disagree about, and
    reporting somebody else's ownership of a directory that is not there would leave the
    receipt row unresolvable forever."""

    assert uninstall._skills_owned(tmp_path / "never-made", "wheel") is True


def test_a_way_of_installing_nobody_defined_is_never_ours(tmp_path: Path, machine):
    """The `else` branch, and it fails closed. A receipt row whose `how` this version does
    not recognise was written by something else, and the safe reading of something else is
    that it is not ours to delete."""

    root = _skill_root(tmp_path, "ai-plan")

    assert uninstall._skills_owned(root, "teleport") is False


def test_a_link_pointing_at_our_store_is_ours_and_one_pointing_elsewhere_is_not(
    tmp_path: Path, machine
):
    """The whole of the symlink case. Ownership is what it points at, resolved, because a
    name is not evidence — anybody may create a directory called `ai-plan`."""

    store = paths.home() / "skills"
    names = uninstall._expected_skill_names()
    assert names, "no skills are installed here, so this case would prove nothing"
    name = sorted(names)[0]
    (store / name).mkdir(parents=True, exist_ok=True)

    root = tmp_path / "linked"
    root.mkdir()
    (root / name).symlink_to(store / name)
    assert uninstall._skills_owned(root, "symlink") is True

    (root / name).unlink()
    (root / name).symlink_to(tmp_path / "somewhere-else")
    assert uninstall._skills_owned(root, "symlink") is False


def test_a_copy_that_is_not_byte_identical_to_the_source_is_not_ours(tmp_path: Path, machine):
    """This is the Windows case, where linking copies, and it is where the receipt alone is
    not enough. A copy somebody has edited is their file now, whatever the receipt says."""

    names = uninstall._expected_skill_names()
    assert names, "no skills are installed here, so this case would prove nothing"
    name = sorted(names)[0]

    root = tmp_path / "copied"
    (root / name).mkdir(parents=True)
    (root / name / "SKILL.md").write_text("somebody edited this\n", encoding="utf-8")

    assert uninstall._skills_owned(root, "copy") is False


def test_a_guard_entry_that_is_already_gone_counts_as_removed(tmp_path: Path):
    """Generous on purpose. An uninstall reporting failure for a file it found already gone
    sends a person hunting for something nobody has."""

    row = {"kind": "guard", "path": str(tmp_path / "never-written.json"), "how": "json_claude"}

    assert uninstall._removed(row, None) is True


def test_a_settings_file_still_carrying_our_signature_is_not_removed(tmp_path: Path):
    """The check is for our entry rather than for the file, because these are files other
    tools own and we only ever added a line to them."""

    settings = tmp_path / "settings.json"
    settings.write_text(f'{{"hooks": "{uninstall.wiring.SIGNATURE}"}}', encoding="utf-8")
    row = {"kind": "guard", "path": str(settings), "how": "json_claude"}

    assert uninstall._removed(row, None) is False

    settings.write_text('{"hooks": "somebody elses"}', encoding="utf-8")
    assert uninstall._removed(row, None) is True


def test_a_settings_file_that_cannot_be_read_is_not_reported_as_removed(tmp_path: Path):
    """Undecidable resolves to *not removed* here, which is the honest direction: claiming a
    guard is gone when nobody could look is the false green, in the verb whose whole output
    is a list of what went."""

    settings = tmp_path / "settings.json"
    settings.write_bytes(b"\xff\xfe not text")
    row = {"kind": "guard", "path": str(settings), "how": "json_claude"}

    assert uninstall._removed(row, None) is False


def test_the_opencode_plugin_is_never_reported_removed_by_reading_it(tmp_path: Path):
    """Its own branch, because the plugin is a whole file we wrote rather than a line added
    to somebody else's — so the signature test that works for the JSON surfaces would answer
    about the wrong thing."""

    plugin = tmp_path / "plugin.ts"
    plugin.write_text("// anything at all\n", encoding="utf-8")
    row = {"kind": "guard", "path": str(plugin), "how": "ts_opencode"}

    assert uninstall._removed(row, None) is False


def test_a_skills_row_is_removed_only_when_none_of_ours_is_left(tmp_path: Path, machine):
    names = uninstall._expected_skill_names()
    assert names, "no skills are installed here, so this case would prove nothing"
    name = sorted(names)[0]

    root = tmp_path / "surface"
    root.mkdir()
    row = {"kind": "skills", "path": str(root), "how": "wheel"}
    assert uninstall._removed(row, None) is True

    (root / name).mkdir()
    assert uninstall._removed(row, None) is False
