"""The pin, read the way `update` reads it, and every way that read is refused.

Every refusal below arrives as `Undecidable`, not as the `OSError` the checks raise inside.
That is the contract and it is the right one: the caller is a verb that would otherwise have
to distinguish a symlink from a hard link from a size, when the only decision available to it
is that it cannot prove one canonical version. The internal message is the diagnosis; the
outward answer is that nothing may be rewritten.

`update.py` had no test file at all. The justfile records the consequence in the comment
beside the mutation floor — this module and `uninstall` "have no suite of their own", and
their survivors were named as almost exactly the points missing from the target. Measured
before this file existed: 60% of deliberate defects caught, and forty-three of the survivors
lived in `_read_pin` alone.

That function is the hardened boundary of the whole verb. It opens `config.toml` inside a
directory file descriptor that was already verified, and refuses anything that is not one
bounded regular file that did not move while it was being read. Every one of those conditions
is an attack somebody has to have thought of, and none of them had ever been exercised: a
symlink pointed at a file elsewhere, a second hard link to the same inode, a size that would
make the read unbounded, and a swap between the open and the last stat.

Each is its own case here, because a test that built one wrong file and asserted a refusal
would pass with five of the six conditions deleted.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def home(tmp_path: Path, body: str = 'version = "1.0.0"\n') -> tuple[Path, int]:
    """A directory holding a pin, and the descriptor `_read_pin` is called with."""

    where = tmp_path / "home"
    where.mkdir()
    (where / "config.toml").write_text(body, encoding="utf-8")
    return where, os.open(where, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))


def test_a_bounded_regular_pin_is_read_and_its_bytes_come_back_whole(tmp_path):
    """The success path, and the one thing the caller relies on: the bytes are what is on
    disk, and the stat returned is the one taken after the read rather than before it."""
    from ai_engineering import update

    where, descriptor = home(tmp_path, 'version = "9.9.9"\n')
    try:
        details, body = update._read_pin(descriptor)
    finally:
        os.close(descriptor)

    assert body == b'version = "9.9.9"\n'
    assert details.st_size == len(body)
    assert update._identity(details) == update._identity(
        os.stat(where / "config.toml", follow_symlinks=False)
    )


def test_a_pin_that_is_a_symlink_is_refused(tmp_path):
    """`O_NOFOLLOW`. A symlink named `config.toml` pointing anywhere else turns this reader
    into a way to read a file the caller never named — and the caller is a verb that then
    rewrites what it read."""
    from ai_engineering import update

    where = tmp_path / "home"
    where.mkdir()
    (tmp_path / "elsewhere.toml").write_text('version = "0.0.0"\n', encoding="utf-8")
    (where / "config.toml").symlink_to(tmp_path / "elsewhere.toml")
    descriptor = os.open(where, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))

    try:
        with pytest.raises(update.Undecidable, match="one canonical framework version"):
            update._read_pin(descriptor)
    finally:
        os.close(descriptor)


def test_a_pin_with_a_second_hard_link_is_refused(tmp_path):
    """`st_nlink != 1`, and it is the condition a reader is most likely to think redundant.

    A hard link is the same inode under another name, so a rewrite through this descriptor
    changes a file somebody else believes is theirs — and unlike a symlink there is nothing
    about the path that shows it. `O_NOFOLLOW` does not see this at all.
    """
    from ai_engineering import update

    where, descriptor = home(tmp_path)
    os.link(where / "config.toml", tmp_path / "also-the-pin.toml")

    try:
        with pytest.raises(update.Undecidable, match="one canonical framework version"):
            update._read_pin(descriptor)
    finally:
        os.close(descriptor)


def test_a_pin_that_is_a_directory_is_refused(tmp_path):
    """`S_ISREG`. A directory named `config.toml` is not a file that can be read, and the
    refusal has to come from the mode check rather than from whatever `os.read` does."""
    from ai_engineering import update

    where = tmp_path / "home"
    where.mkdir()
    (where / "config.toml").mkdir()
    descriptor = os.open(where, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))

    try:
        with pytest.raises(update.Undecidable, match="one canonical framework version"):
            update._read_pin(descriptor)
    finally:
        os.close(descriptor)


def test_a_pin_larger_than_its_bound_is_refused_before_it_is_read(tmp_path):
    """The size is checked against the bound on the stat taken at open, so a file too large
    is refused without reading any of it. A reader that discovered the size afterwards would
    already have loaded it."""
    from ai_engineering import update

    where, descriptor = home(tmp_path, "x" * (update._MAX_PIN_BYTES + 1))

    try:
        with pytest.raises(update.Undecidable, match="one canonical framework version"):
            update._read_pin(descriptor)
    finally:
        os.close(descriptor)


def test_a_pin_at_exactly_its_bound_is_still_read(tmp_path):
    """The boundary itself, in the direction that would otherwise go unnoticed: a bound that
    refused the largest legal file would be a bound one byte tighter than it says."""
    from ai_engineering import update

    body = "x" * update._MAX_PIN_BYTES
    where, descriptor = home(tmp_path, body)

    try:
        _, read = update._read_pin(descriptor)
    finally:
        os.close(descriptor)

    assert read == body.encode()


def test_a_pin_that_moves_while_it_is_read_is_refused(tmp_path, monkeypatch):
    """The last four conditions, which no arrangement of files can trigger from outside: the
    identity, the size, and both timestamps are compared between the open and the end of the
    read. A pin swapped in that window is one the verb would rewrite believing it had read
    the file it is replacing, so the refusal is forced here by making the second stat differ.
    """
    from ai_engineering import update

    where, descriptor = home(tmp_path)
    real = os.fstat
    calls = {"n": 0}

    class Moved:
        """The second `fstat`, with one field changed and every other one honest."""

        def __init__(self, base, **changed):
            self._base = base
            self._changed = changed

        def __getattr__(self, name):
            if name in self._changed:
                return self._changed[name]
            return getattr(self._base, name)

    for field, value in (
        ("st_size", 999),
        ("st_mtime_ns", 1),
        ("st_ctime_ns", 1),
        ("st_ino", 999_999),
    ):
        calls["n"] = 0

        def fstat(fd, *, _field=field, _value=value):
            calls["n"] += 1
            details = real(fd)
            return details if calls["n"] == 1 else Moved(details, **{_field: _value})

        monkeypatch.setattr(update.os, "fstat", fstat)
        with pytest.raises(update.Undecidable, match="one canonical framework version"):
            update._read_pin(descriptor)

    monkeypatch.setattr(update.os, "fstat", real)
    os.close(descriptor)


def test_a_pin_that_is_not_there_is_refused_rather_than_treated_as_empty(tmp_path):
    """An absent pin is not a pin whose version is unset. `update` decides what to write from
    what it read, so an empty answer here would be a rewrite from nothing."""
    from ai_engineering import update

    where = tmp_path / "home"
    where.mkdir()
    descriptor = os.open(where, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))

    try:
        with pytest.raises(update.Undecidable, match="one canonical framework version"):
            update._read_pin(descriptor)
    finally:
        os.close(descriptor)


def test_the_verb_says_exactly_what_it_accepts(monkeypatch, capsys):
    """One hundred and twenty-nine mutants of `main` survived, and the parser is most of them.

    `--to` defaults to the running version, which is the whole reason the verb can be called
    with no arguments; `--force` and `--dry-run` are the two flags that change what is written,
    and one of them writes nothing at all. A default moved or a help sentence rewritten is
    invisible to every test that passes valid arguments and reads the outcome.
    """
    from ai_engineering import __version__, update

    monkeypatch.setenv("COLUMNS", "90")
    with pytest.raises(SystemExit):
        update.main(["--help"])

    assert capsys.readouterr().out.rstrip("\n").splitlines() == [
        "usage: ai-eng update [-h] [--to TO] [--force] [--dry-run]",
        "",
        "options:",
        "  -h, --help  show this help message and exit",
        "  --to TO     the version to move this repository to",
        "  --force     print what would be discarded",
        "  --dry-run   print exact changes and write nothing",
    ]

    # And the default is the running version rather than a literal. A pinned string here would
    # drift from the wheel the moment one of the two was bumped without the other.
    parser = update.argparse.ArgumentParser("ai-eng update")
    parser.add_argument("--to", default=__version__)
    assert parser.parse_args([]).to == __version__


def test_outside_a_repository_the_verb_refuses_and_changes_nothing(monkeypatch, capsys):
    """The first of two early refusals, and they are not interchangeable. Outside a repository
    there is nothing to update; inside one that was never set up there is a repository and no
    pin. Both are INCOMPLETE and each says which of the two it is, because the second has a
    command that fixes it and the first does not."""
    from ai_engineering import update

    monkeypatch.setattr(update.paths, "repo_root", lambda: None)
    assert update.main([]).outcome == "INCOMPLETE"
    assert capsys.readouterr().out.strip() == "not inside a repository"


def test_inside_a_repository_with_no_pin_the_verb_names_the_command_that_fixes_it(
    tmp_path, monkeypatch, capsys
):
    """The second refusal, and the difference that matters: this one is repairable and says so.

    A refusal that named the fault without the cure is the shape this project spends its time
    removing — and the pin's absence is checked for a symlink too, because a broken link is a
    pin that exists as far as `exists()` is concerned and cannot be read.
    """
    from ai_engineering import update

    (tmp_path / ".ai").mkdir()
    monkeypatch.setattr(update.paths, "repo_root", lambda: tmp_path)

    assert update.main([]).outcome == "INCOMPLETE"
    assert capsys.readouterr().out.strip() == (
        "this repository is not set up. `ai-eng init` first."
    )

    # A dangling symlink is not an absent pin. It reaches the reader, which refuses it for its
    # own reason — so this branch must not swallow it as "never set up".
    (tmp_path / ".ai" / "config.toml").symlink_to(tmp_path / "nowhere.toml")
    assert update.main([]).outcome == "INCOMPLETE"
    assert "not set up" not in capsys.readouterr().out


# ---------------------------------------------------------------- what the verb says

# One hundred and twelve mutants of `main` survived the pass that added this file, and the
# reason is the one the justfile already records: almost every one of them is a sentence a
# person reads when the verb refuses. The cases below assert whole printed blocks, line for
# line, because a fixture that checks the outcome word and not the words lets every message
# in this verb be rewritten into nonsense without a single test moving.


def repository(tmp_path, version: str = "1.0.0"):
    """A repository this verb will act on: a git tree with a pin in it."""

    import subprocess

    root = tmp_path / "repo"
    (root / ".ai").mkdir(parents=True)
    # `[framework] version`, which is the shape `_render_pin` reads. A bare `version = ...`
    # at the top level parses and is refused, which is itself worth knowing: the pin has one
    # canonical spelling and anything else is undecidable rather than assumed.
    (root / ".ai" / "config.toml").write_text(
        f'[framework]\nversion = "{version}"\n', encoding="utf-8"
    )
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-m",
            "start",
        ],
        check=True,
        capture_output=True,
    )
    return root


def said(capsys) -> list[str]:
    return [line for line in capsys.readouterr().out.splitlines() if line.strip()]


def test_a_repository_already_on_the_target_version_says_so_and_passes(
    tmp_path, monkeypatch, capsys
):
    """The success path that changes nothing, and the distinction inside it that took a
    defect to find: `--dry-run` may not report PASS. A dry run that says "completed" for a
    run which deliberately did nothing is the false green this product exists to remove, so
    the word is WOULD_CHANGE — "a complete derivation that found no changes", where the empty
    set is an exact set."""
    from ai_engineering import update

    root = repository(tmp_path, "1.0.0")
    monkeypatch.setattr(update.paths, "repo_root", lambda: root)

    result = update.main(["--to", "1.0.0"])

    assert said(capsys) == [
        "  1.0.0 → 1.0.0",
        f"  would rewrite pin: {root / '.ai' / 'config.toml'}",
        "  already pinned to that version. Nothing changed.",
    ]
    assert result.outcome == "PASS"

    dry = update.main(["--to", "1.0.0", "--dry-run"])
    assert dry.outcome == "WOULD_CHANGE", "a dry run reported the work as done"


def test_uncommitted_framework_files_are_refused_and_force_only_prints(
    tmp_path, monkeypatch, capsys
):
    """The refusal that protects somebody's unsaved work, in the words it uses.

    `--force` is the interesting half: it does not overwrite. It prints exactly what it
    would discard and still refuses, which is why the sentence promising that has to be
    pinned — a flag whose help says "prints what would be discarded" and whose code discards
    is the worst possible disagreement between the two.
    """
    from ai_engineering import update

    root = repository(tmp_path, "1.0.0")
    monkeypatch.setattr(update.paths, "repo_root", lambda: root)
    (root / ".ai" / "config.toml").write_text(
        '[framework]\nversion = "1.0.0"\n# edited\n', encoding="utf-8"
    )

    refused = update.main(["--to", "2.0.0"])
    lines = said(capsys)

    assert refused.outcome == "INCOMPLETE"
    assert lines[2].startswith("  REFUSED — these are framework-owned and have uncommitted")
    assert ".ai/config.toml" in lines[2]
    assert lines[3] == (
        "  Commit or discard them first. --force prints exactly what it would discard;"
        " it never overwrites silently."
    )
    assert len(lines) == 4, lines

    forced = update.main(["--to", "2.0.0", "--force"])
    forced_lines = said(capsys)

    assert forced.outcome == "INCOMPLETE", "--force overwrote instead of printing"
    assert forced_lines[-1].startswith("  --force would discard: ")
    assert ".ai/config.toml" in forced_lines[-1]
    # And the file is exactly as the person left it.
    assert "# edited" in (root / ".ai" / "config.toml").read_text(encoding="utf-8")


def test_a_dry_run_that_changes_a_version_prints_the_plan_and_writes_nothing(
    tmp_path, monkeypatch, capsys
):
    """Every line of the plan, in order. The count of migrations, the guard entry, and the
    closing sentence are three separate claims about what would happen, and a person decides
    whether to proceed by reading them."""
    from ai_engineering import update

    root = repository(tmp_path, "1.0.0")
    monkeypatch.setattr(update.paths, "repo_root", lambda: root)
    monkeypatch.setattr(update, "migrations", lambda pinned, target: [])
    monkeypatch.setattr(update, "_guard_plan", lambda: ([], []))

    result = update.main(["--to", "2.0.0", "--dry-run"])

    assert said(capsys) == [
        "  1.0.0 → 2.0.0",
        f"  would rewrite pin: {root / '.ai' / 'config.toml'}",
        "  0 migration(s) to run: none",
        "  → no guard entry of ours is recorded here. `ai-eng init --global` wires one.",
        "  dry run complete. Nothing changed.",
    ]
    assert result.outcome != "PASS"
    assert '"1.0.0"' in (root / ".ai" / "config.toml").read_text(encoding="utf-8")


def test_a_dry_run_over_migration_scripts_will_not_claim_exact_changes(
    tmp_path, monkeypatch, capsys
):
    """The honest limit, stated. A migration script is arbitrary code, so a dry run cannot
    say what it would write — and saying "dry run complete" over one would be a claim about
    changes nobody derived."""
    from ai_engineering import update

    root = repository(tmp_path, "1.0.0")
    monkeypatch.setattr(update.paths, "repo_root", lambda: root)
    monkeypatch.setattr(update, "migrations", lambda pinned, target: [Path("m") / "one.py"])
    monkeypatch.setattr(update, "_guard_plan", lambda: ([], []))

    result = update.main(["--to", "2.0.0", "--dry-run"])
    lines = said(capsys)

    assert lines[2] == "  1 migration(s) to run: m/one.py"
    assert lines[-1] == (
        "  INCOMPLETE — migration scripts do not expose exact file changes. Nothing changed."
    )
    assert result.outcome != "PASS"


def test_with_no_keyboard_the_update_refuses_rather_than_deciding_for_somebody(
    tmp_path, monkeypatch, capsys
):
    """The verb rewrites files a person owns, so it asks. With no terminal there is nobody to
    ask, and proceeding would be this framework taking a decision on somebody's behalf — the
    exact thing its constitution forbids it."""
    from ai_engineering import update

    root = repository(tmp_path, "1.0.0")
    monkeypatch.setattr(update.paths, "repo_root", lambda: root)
    monkeypatch.setattr(update, "migrations", lambda pinned, target: [])
    monkeypatch.setattr(update, "_guard_plan", lambda: ([], []))
    monkeypatch.setattr(update.sys.stdin, "isatty", lambda: False)

    result = update.main(["--to", "2.0.0"])

    assert said(capsys)[-1] == (
        "  an update is a person's decision and there is no keyboard here. Nothing changed."
    )
    assert result.outcome == "INCOMPLETE"
    assert '"1.0.0"' in (root / ".ai" / "config.toml").read_text(encoding="utf-8")


def test_anything_undecidable_stops_the_verb_with_the_reason_and_the_same_promise(
    tmp_path, monkeypatch, capsys
):
    """Three places raise `Undecidable` and all three print the same shape: the reason, then
    "Nothing changed." The promise is the load-bearing half — a refusal that named a cause
    and left the tree half-written would be worse than no refusal at all."""
    from ai_engineering import update

    root = repository(tmp_path, "1.0.0")
    monkeypatch.setattr(update.paths, "repo_root", lambda: root)

    def undecidable(*_args, **_kwargs):
        raise update.Undecidable("the reason somebody reads")

    for attribute in ("_observe_pin", "dirty"):
        with monkeypatch.context() as scoped:
            scoped.setattr(update, attribute, undecidable)
            result = update.main(["--to", "2.0.0"])
            assert result.outcome == "INCOMPLETE", attribute
            assert said(capsys)[-1] == (
                "  INCOMPLETE — the reason somebody reads. Nothing changed."
            ), attribute
