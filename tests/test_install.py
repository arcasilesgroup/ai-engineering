"""The five verbs that write into somebody else's machine, pinned.

Everything here runs against tmp_path with HOME and AI_ENGINEERING_HOME redirected, so a
test that reaches for the real home finds an empty one instead of the operator's.

The rule these tests exist to hold: an entry we write must point at a path that is there,
must be recognisable as ours, and must survive being written a second time. An entry that
saves fine and fires nothing is the failure this product sells a cure for.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering import __version__, init, outcome, paths, skeletons, uninstall, update, wiring


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Every path with a ~ in it, and the framework's own folder, land inside tmp_path."""
    fake = tmp_path / "home"
    fake.mkdir()
    monkeypatch.setenv("HOME", str(fake))
    monkeypatch.setenv("USERPROFILE", str(fake))
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(fake / ".ai-engineering"))
    return fake


@pytest.fixture
def repo(tmp_path, home):
    root = tmp_path / "repo"
    root.mkdir()
    for args in (
        ("init", "-b", "main"),
        ("config", "user.email", "t@example.invalid"),
        ("config", "user.name", "test"),
    ):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    return root


def git_get(root: Path, key: str) -> str:
    got = subprocess.run(
        ["git", "-C", str(root), "config", "--local", "--get", key], capture_output=True, text=True
    )
    return got.stdout.strip()


def surface_row(surface_id: str, kind: str = "guard", how: str | None = None) -> tuple[Path, dict]:
    """A receipt row in the exact shape the real installer records, plus its disk path."""
    surface = next(row for row in wiring.table()["surface"] if row["id"] == surface_id)
    field = "settings" if kind == "guard" else "skills"
    raw = surface[field]
    recorded = raw if kind == "guard" else str(wiring.expand(raw))
    return wiring.expand(raw), {
        "path": recorded,
        "kind": kind,
        "how": surface["writer"] if how is None else how,
    }


def leaves(node) -> list[str]:
    if isinstance(node, dict):
        return [item for value in node.values() for item in leaves(value)]
    if isinstance(node, list):
        return [item for value in node for item in leaves(value)]
    return [node] if isinstance(node, str) else []


def absolute_paths(blob: str) -> list[Path]:
    """Every absolute path a written file names, read out of the JSON values where it is JSON
    and out of the source where it is the TypeScript plugin."""
    with contextlib.suppress(ValueError):
        blob = " ".join(leaves(json.loads(blob)))
    return [Path(item) for item in re.findall(r'"([^"]+)"', blob) if Path(item).is_absolute()]


@pytest.mark.parametrize("writer", sorted(wiring.WRITERS))
def test_every_writer_points_at_a_live_dispatcher_and_never_writes_a_tilde(writer, home, tmp_path):
    """A ~ in a settings value saves without complaint and fires nothing, because no surface
    expands one; a dispatcher path that is not on disk is an entry that silently never runs."""
    target = tmp_path / "surface" / f"{writer}.conf"
    wiring.WRITERS[writer](target)
    blob = target.read_text(encoding="utf-8")

    # By what ours() answers, not by the literal string it happens to look for. Asserting
    # MARK is in the text asserts an implementation, and that implementation was wrong: the
    # only place MARK appeared was the install path, so this assertion passed on a machine
    # whose checkout is spelled ai-engineering and would have failed on every other one.
    assert wiring.ours(blob), f"{writer} wrote an entry nothing recognises as ours"
    assert "~" not in blob, f"{writer} wrote a tilde, which saves fine and fires nothing"
    assert "__" not in blob, f"{writer} left a placeholder unreplaced"
    assert sys.executable in blob, f"{writer} did not name the interpreter it was installed by"
    chains = [path for path in absolute_paths(blob) if path.name == "chain.py"]
    assert chains, f"{writer} wrote no path to the dispatcher"
    for chain in chains:
        assert chain.exists(), f"{writer} points at {chain}, which is not there"


@pytest.mark.parametrize("writer", ["json_claude", "json_cursor", "json_codex", "json_copilot"])
def test_installing_twice_leaves_one_entry(writer, home, tmp_path):
    """`init` is meant to be safe to run a thousand times. A writer that appends instead of
    replacing gives the user a settings file with one dispatcher call per install."""
    target = tmp_path / "surface.json"
    wiring.WRITERS[writer](target)
    once = target.read_text(encoding="utf-8")
    wiring.WRITERS[writer](target)
    twice = target.read_text(encoding="utf-8")
    assert twice.count("chain.py") == once.count("chain.py"), (
        f"{writer} added a second entry on the second install"
    )


def test_installing_twice_leaves_one_entry_when_no_path_spells_the_mark(
    home, tmp_path, monkeypatch
):
    """The same install run twice from a venv that has no 'ai-engineering' in its path."""
    monkeypatch.setattr(sys, "executable", "/opt/venv/bin/python3")
    monkeypatch.setattr(paths, "hooks", lambda: Path("/opt/venv/lib/ai_engineering/hooks"))
    target = tmp_path / "settings.json"
    wiring.json_claude(target)
    wiring.json_claude(target)
    assert target.read_text(encoding="utf-8").count("chain.py") == 4


@pytest.mark.parametrize(
    "writer,keeps",
    [("json_claude", True), ("json_cursor", True), ("json_codex", True), ("json_copilot", False)],
)
def test_a_foreign_settings_file_keeps_the_keys_that_are_not_ours(writer, keeps, home, tmp_path):
    """These files belong to the user and hold their own hooks. A writer that replaces the
    file instead of merging into it deletes settings we were never asked to manage — except
    the Copilot one, which is a file of ours alone, and that is pinned here too."""
    target = tmp_path / "surface.json"
    wiring.write_json(
        target, {"env": {"EDITOR": "vim"}, "hooks": {"PreToolUse": [{"n": "theirs"}]}}
    )
    wiring.WRITERS[writer](target)
    data = json.loads(target.read_text(encoding="utf-8"))
    assert (data.get("env") == {"EDITOR": "vim"}) is keeps
    assert ("theirs" in json.dumps(data)) is keeps


def test_a_settings_file_with_comments_is_left_alone_and_the_reason_is_named(home, tmp_path):
    """VS Code and Cursor write JSON with // comments and trailing commas. json.loads refuses
    it, read_json used to turn that refusal into {}, and the writer then saved a file that had
    lost everything the user had — under a line of output reading `(merged)`.

    The test that stood here pinned that loss and said in its own docstring that it did not
    bless it. It was a passing assertion that an install destroys a settings file, and nothing
    tracked it. Absent is empty; present-and-unparseable is a refusal with the file named."""
    target = tmp_path / "settings.json"
    body = '{\n  // theirs\n  "env": {"EDITOR": "vim"},\n}\n'
    target.write_text(body, encoding="utf-8")
    with pytest.raises(wiring.Unreadable, match="not readable as JSON"):
        wiring.read_json(target)
    with pytest.raises(wiring.Unreadable):
        wiring.json_claude(target)
    assert target.read_text(encoding="utf-8") == body, "the writer touched a file it cannot read"


def test_a_settings_file_that_is_not_there_is_written_from_nothing(home, tmp_path):
    """The other half of the same rule, and the reason it is not `except OSError: raise`:
    every writer's ordinary case is a surface that has no settings file yet."""
    target = tmp_path / "settings.json"
    assert wiring.read_json(target) == {}
    wiring.json_claude(target)
    assert wiring.ours(target.read_text(encoding="utf-8"))


def test_the_cursor_entry_is_written_fail_closed(home, tmp_path):
    """Cursor runs the hook and then ignores its denial unless failClosed is set. Without
    that one key the entry saves, fires, prints its refusal and lets the call through: the
    exact shape of a guard that is off while the settings file still looks wired."""
    target = tmp_path / "hooks.json"
    wiring.json_cursor(target)
    assert json.loads(target.read_text(encoding="utf-8"))["failClosed"] is True


def test_link_repoints_a_stale_symlink_and_copies_into_a_real_directory(tmp_path):
    """A skill left pointing at an old install is a skill that never changes again. link has
    to replace what is there when it points somewhere else, leave a correct link alone, and
    fall back to copying when the target is already a real directory, as it is on Windows."""
    try:
        (tmp_path / "probe").symlink_to(tmp_path)
    except (OSError, NotImplementedError):
        pytest.skip("no symlinks here, which is the machine the copy path exists for")
    source = tmp_path / "wheel" / "ai-spec"
    source.mkdir(parents=True)
    (source / "SKILL.md").write_text("new", encoding="utf-8")
    fresh = tmp_path / "fresh" / "ai-spec"
    assert wiring.link(source, fresh) == "symlink"
    assert wiring.link(source, fresh) == "symlink", "a correct link was rebuilt for nothing"
    assert fresh.resolve() == source.resolve()

    old = tmp_path / "old-install"
    old.mkdir()
    stale = tmp_path / "stale" / "ai-spec"
    stale.parent.mkdir()
    stale.symlink_to(old)
    assert wiring.link(source, stale) == "symlink"
    assert stale.resolve() == source.resolve(), "the link still points at the old install"

    real = tmp_path / "real" / "ai-spec"
    real.mkdir(parents=True)
    assert wiring.link(source, real) == "copy"
    assert (real / "SKILL.md").read_text(encoding="utf-8") == "new"


def test_a_second_machine_install_leaves_one_receipt_row_per_thing_written(home, tmp_path, capsys):
    """The install a competing product got wrong: it reported eight skills and left the
    directory empty. This runs the whole machine half twice and checks the skills are on
    disk, that every surface root holds them, and that the receipt lists each thing once —
    a receipt with duplicate rows is an uninstall that walks the same path twice."""
    (home / ".claude").mkdir()
    not_a_repo = tmp_path / "nowhere"
    not_a_repo.mkdir()
    names = sorted(path.name for path in paths.skills().glob("ai-*"))
    for _ in range(2):
        init.main(["--global", "-y", "--project", str(not_a_repo)])
    assert sorted(path.name for path in (paths.home() / "skills").glob("ai-*")) == names
    assert sorted(path.name for path in (home / ".claude" / "skills").glob("ai-*")) == names
    settings = (home / ".claude" / "settings.json").read_text(encoding="utf-8")
    assert wiring.ours(settings), "the machine half wrote an entry nothing recognises as ours"
    rows = wiring.receipt()["wrote"]
    assert len(rows) == len({(row["path"], row["kind"]) for row in rows})
    assert {"path": "~/.claude/settings.json", "kind": "guard", "how": "json_claude"} in rows


def test_a_receipt_from_an_older_version_is_installed_over_rather_than_believed(home, tmp_path):
    """When the wheel moves, every entry still names the directory the old one lived in and
    every guard is off. If `init` reads the receipt and calls the machine ready on the row
    count alone, the run that was meant to repoint them is the run that skipped them."""
    foreign = tmp_path / "foreign-settings"
    foreign.write_bytes(b"not owned\n")
    wiring.write_json(
        wiring.receipt_path(),
        {
            "wrote": [
                {"path": "x", "kind": "guard"},
                {"path": str(paths.home() / "skills"), "kind": "skills"},
                {"path": str(foreign), "kind": "guard"},
            ],
            "version": "0.0.1",
        },
    )
    not_a_repo = tmp_path / "nowhere"
    not_a_repo.mkdir()
    init.main(["-y", "--project", str(not_a_repo)])
    receipt = wiring.receipt()
    assert receipt["version"] == __version__, "a stale install reported itself ready"
    assert {"path": "x", "kind": "guard"} not in receipt["wrote"]
    assert all(
        all(isinstance(row.get(field), str) for field in ("path", "kind", "how"))
        for row in receipt["wrote"]
    )
    assert foreign.read_bytes() == b"not owned\n"
    second = init.main(["--global", "--no-project", "-y"])
    assert second.outcome == "PASS"


def test_the_overwrite_question_only_returns_what_was_actually_chosen(keyboard, monkeypatch):
    """This is the one prompt in this product that destroys a file, so what comes back out
    of it has to be exactly what went in. It is a checkbox now rather than typed numbers;
    the widget itself is stood in for, because a real one needs a real terminal and this
    suite is the matrix that runs where there is none."""
    keyboard("")
    monkeypatch.setattr(init.ui, "pick", lambda question, rows, checked: ["justfile"])
    rows = [("CLAUDE.md", 1, "one line"), ("justfile", 9, "5 recipes")]
    assert init.choose(rows, SimpleNamespace(overwrite="", yes=False)) == {"justfile"}


def test_the_overwrite_flag_answers_without_a_terminal_at_all(tmp_path):
    """The matrix runs where there is no keyboard, and every platform in it drives the
    installer with flags. That path must never construct a widget: it is the parser."""
    rows = [("CLAUDE.md", 1, "one line"), ("justfile", 9, "5 recipes")]
    picked = init.choose(rows, SimpleNamespace(overwrite="justfile", yes=False))
    assert picked == {"justfile"}


def test_uninstall_strips_our_entries_and_keeps_everyone_else_s(tmp_path):
    """Removing a tool must not remove the hooks a user wrote themselves, and a settings file
    that never held an entry of ours must come back untouched rather than rewritten."""
    theirs = {"n": "theirs"}
    mixed = tmp_path / "settings.json"
    ours = {"hooks": [{"command": '"/x/ai-engineering/hooks/chain.py" PreToolUse'}]}
    wiring.write_json(mixed, {"hooks": {"PreToolUse": [theirs, ours]}})
    assert uninstall.strip_entries(mixed) is True
    assert json.loads(mixed.read_text(encoding="utf-8")) == {"hooks": {"PreToolUse": [theirs]}}

    foreign = tmp_path / "foreign.json"
    before = '{"hooks": {"PreToolUse": [{"n": "theirs"}]}}'
    foreign.write_text(before, encoding="utf-8")
    assert uninstall.strip_entries(foreign) is False
    assert foreign.read_text(encoding="utf-8") == before


def test_overwriting_a_file_writes_the_backup_before_it_writes_the_skeleton(repo, home):
    """Overwrite is the one answer that destroys something. It has to leave the old file on
    disk under a dated name, or a mistyped answer costs work that no git history holds."""
    (repo / "justfile").write_text("mine:\n\t@echo hello\n", encoding="utf-8")
    init.main(["--no-global", "--project", str(repo), "-y", "--overwrite", "justfile"])
    assert (repo / "justfile").read_text(encoding="utf-8") == skeletons.justfile([])
    backups = list(repo.glob(".ai/backups/justfile.bak-*"))
    assert len(backups) == 1, f"overwrite left {len(backups)} backups"
    assert not list(repo.glob("justfile.bak-*")), "a backup at the root is committed by git add -A"
    assert backups[0].read_text(encoding="utf-8") == "mine:\n\t@echo hello\n"


def test_wire_git_sets_three_repository_scoped_keys_that_all_resolve(repo):
    """`command -v ai-eng` proves a binary exists and never that it is this one, so ai.eng
    records the interpreter that wrote the hooks. A key pointing at a directory or an
    interpreter that is not there is a pre-push hook that cannot run."""
    wiring.wire_git(repo)
    values = {key: git_get(repo, key) for key in ("core.hooksPath", "ai.managed", "ai.eng")}
    assert values["ai.managed"] == "true"
    assert Path(values["core.hooksPath"]).is_dir(), "core.hooksPath names no directory"
    interpreter, _, module = values["ai.eng"].partition(" ")
    assert Path(interpreter).exists(), f"ai.eng names {interpreter}, which is not there"
    assert module == "-m ai_engineering.cli"
    for key, value in values.items():
        assert "~" not in value, f"{key} holds a tilde, which git saves and never expands"


@pytest.mark.parametrize(
    "markers,expected",
    [
        ([], []),
        (["pyproject.toml"], ["python"]),
        (["package.json"], ["node"]),
        (["go.mod"], ["go"]),
        (["Cargo.toml"], ["rust"]),
        (["pom.xml"], ["java"]),
        (["Gemfile"], ["ruby"]),
        (["README.md"], []),
        (["pyproject.toml", "package.json", "go.mod"], ["go", "node", "python"]),
    ],
)
def test_stacks_names_every_marker_it_finds_and_nothing_else(markers, expected, tmp_path):
    """A stack reported that is not there sends somebody installing binaries they do not
    need; one missed leaves `just check` calling a linter nobody was told to install."""
    for name in markers:
        (tmp_path / name).write_text("", encoding="utf-8")
    assert init.stacks(tmp_path) == expected


def test_a_dry_run_writes_nothing_at_all(repo, home, capsys):
    """--dry-run is the offer to look before anything is touched. If it writes, the one
    command a cautious person runs first is the one that changed their repository."""
    init.main(["--project", str(repo), "--dry-run", "-y"])
    assert [path.name for path in repo.iterdir()] == [".git"], "a dry run wrote into the repository"
    assert not paths.home().exists(), "a dry run created the framework's own folder"
    assert git_get(repo, "core.hooksPath") == "", "a dry run rewired git"


def test_uninstall_gives_back_the_hooks_path_the_repository_had_before_us(
    repo, home, monkeypatch, keyboard
):
    """The wiring wrote core.hooksPath without ever reading what was there and uninstall
    unset it, so a repository that had its own hooks path did not get it back: the
    no-lock-in promise was a command that left the repository different from how it found
    it. The check is not a byte-identical repository — the constitution requires three
    things to survive — it is the configured value and the file list."""
    subprocess.run(
        ["git", "-C", str(repo), "config", "--", "core.hooksPath", "--their/hooks"], check=True
    )
    init.main(["--no-global", "--project", str(repo), "-y"])
    assert git_get(repo, "core.hooksPath") == str(paths.git_hooks())
    monkeypatch.chdir(repo)
    result = uninstall.main(["--project", "-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert git_get(repo, "core.hooksPath") == "--their/hooks"
    assert git_get(repo, "ai.managed") == ""


def test_setting_a_repository_up_twice_still_gives_back_what_was_there_first(
    repo, home, monkeypatch, keyboard
):
    """The `repo` row holds what `core.hooksPath` was before us, and `uninstall` restores
    from it. The second `init --project` read our own hooks directory as "before us" and
    stored that, so the verb that promises no lock-in put the repository back to the exact
    thing it was asked to remove. The first write is the one that knows."""
    subprocess.run(["git", "-C", str(repo), "config", "core.hooksPath", "their/hooks"], check=True)
    init.main(["--no-global", "--project", str(repo), "-y"])
    init.main(["--no-global", "--project", str(repo), "-y"])
    row = next(r for r in wiring.receipt()["wrote"] if r["kind"] == "repo")
    assert row["how"] == "their/hooks", "the second run overwrote what was there before us"
    monkeypatch.chdir(repo)
    result = uninstall.main(["--project", "-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert git_get(repo, "core.hooksPath") == "their/hooks"


def test_a_repository_that_had_no_hooks_path_gets_none_back(repo, home, monkeypatch, keyboard):
    """The other half of the same rule: restoring a value nobody configured would leave a
    setting behind, which is the mirror of deleting one somebody did configure."""
    init.main(["--no-global", "--project", str(repo), "-y"])
    monkeypatch.chdir(repo)
    result = uninstall.main(["--project", "-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert git_get(repo, "core.hooksPath") == ""


def test_the_two_files_the_constitution_protects_are_written_once_and_never_offered(repo, home):
    """A prompt that offers a forbidden action is a rule that only holds while somebody
    reads carefully. They stay in the create set — dropping them from that would stop them
    ever being written — and they leave the overwrite set. They are not in the receipt
    either: they are yours from the second they were written, so uninstall cannot take
    them."""
    init.main(["--no-global", "--project", str(repo), "-y"])
    for name in init.PROTECTED:
        assert (repo / name).exists(), f"{name} was never created"
        (repo / name).write_text("mine, and edited\n", encoding="utf-8")
    assert [name for name, _, _ in init.existing(repo)] == []
    init.main(["--no-global", "--project", str(repo), "--overwrite", "all", "-y"])
    for name in init.PROTECTED:
        assert (repo / name).read_text() == "mine, and edited\n"


def test_a_second_init_over_an_unchanged_repository_offers_nothing(repo, home):
    """Offering to overwrite a file with itself is a screen reporting work that would not
    happen, and every one of those makes the next screen worth less."""
    init.main(["--no-global", "--project", str(repo), "-y"])
    assert init.existing(repo) == []
    (repo / "justfile").write_text("mine:\n\t@echo hello\n", encoding="utf-8")
    assert [name for name, _, _ in init.existing(repo)] == ["justfile"]


def test_uninstall_keeps_a_justfile_the_installer_refused_to_overwrite(
    repo, home, monkeypatch, keyboard
):
    """Uninstall used to unlink four files by name from a hardcoded tuple with no record
    that we had ever written them, so a justfile the installer explicitly declined to
    overwrite — and took no backup of — was deleted by the verb whose whole pitch is that
    it is safe. It reads the receipt now, and the receipt is what init actually wrote."""
    (repo / "justfile").write_text("mine:\n\t@echo hello\n", encoding="utf-8")
    init.main(["--no-global", "--project", str(repo), "-y"])
    assert (repo / "justfile").read_text(encoding="utf-8").startswith("mine:")
    monkeypatch.chdir(repo)
    result = uninstall.main(["--project", "-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert (repo / "justfile").exists(), "uninstall deleted a file the user wrote"


def test_uninstall_removes_skills_that_were_copied_rather_than_linked(home, keyboard):
    """Uninstall a machine where the skills were copied in, which is what Windows gets.

    This was a strict xfail for as long as the link branch only unlinked symlinks: every
    skill this tool installed on Windows stayed behind, and the marker was the alarm on it."""
    root, row = surface_row("claude-code", "link", "copy")
    shutil.copytree(paths.skills() / "ai-spec", root / "ai-spec")
    wiring.record([row])
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert not (root / "ai-spec").exists(), "a copied skill survived the uninstall"


# ── the round trip ──────────────────────────────────────────────────────────────────
#
# Nothing in this suite ran `uninstall` and then asked what the next command sees. Six tests
# called `uninstall.main`; none of them read the receipt afterwards and none of them called
# `init.main`. That is how a screen reporting four guards over a machine with none of them
# shipped: every half was asserted and the seam between them was not.
#
# Each marker below names one defect and comes off in the commit that fixes it. They are
# strict, so the fix without the deletion is a failing build — which is the whole point of
# their being strict, and is how spec 005 carried the defect it was written to close.


@pytest.fixture
def wired(home):
    """A machine with the global half actually installed: two surfaces on disk, so
    `wiring.detect` finds something to write into and the receipt gets real rows."""
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()
    init.main(["--global", "--no-project", "-y"])
    assert wiring.ours((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return home


def stripped(home) -> dict:
    """What is actually on the machine, read from the machine and never from the receipt."""
    roots = [wiring.expand(s["skills"]) for s in wiring.table()["surface"] if s.get("skills")]
    return {
        "guards": sum(
            wiring.ours(path.read_text(errors="replace"))
            for path in (wiring.expand(s["settings"]) for s in wiring.table()["surface"])
            if path.is_file()
        ),
        "links": sum(len([x for x in root.glob("ai-*") if x.is_symlink()]) for root in roots),
    }


def test_the_receipt_stops_claiming_what_uninstall_removed(wired, keyboard):
    """The record of what is installed, after the verb whose whole job is to uninstall it."""
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert stripped(wired) == {"guards": 0, "links": 0}, "uninstall left the machine wired"
    kinds = {row["kind"] for row in wiring.receipt().get("wrote", [])}
    assert not kinds & {"guard", "link"}, f"the receipt still claims {sorted(kinds)}"


def test_a_machine_uninstall_stripped_is_not_reported_as_ready(wired, keyboard):
    """`ai-eng init` printed `Global ready · 4 links, 4 guards` over zero of both.

    Green from task 4, and for the smaller of the two reasons: the receipt shrinks now, so
    the log and the disk agree again. They agree because one of them was corrected, not
    because the answer is read from the machine — a receipt that goes stale for any reason
    this tool did not cause still reports ready. Task 8 owes that half, and its own test
    hands `global_ready` a full receipt over an empty disk."""
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert stripped(wired) == {"guards": 0, "links": 0}
    assert init.global_ready() is False, "a machine with no guards on it reported ready"


def test_no_surface_reads_as_blocking_without_deleting_an_unreceipted_heartbeat(
    wired, capsys, keyboard
):
    """The screen this whole spec was opened for, and the worst line on it. The coverage
    block is the product's headline claim — where a call can actually be stopped — and it
    decided each word from whether the vendor's own directory exists plus a static flag in
    policy/surfaces.toml. It never opened a settings file. So on the operator's machine,
    with zero entries anywhere, it printed `claude-code BLOCKS a denial has executed here`.

    A heartbeat without an OpenCode receipt row is not uninstall authority. It stays even
    though this run removes other, exactly receipted surfaces."""
    from ai_engineering import doctor

    beat = paths.home() / "cache" / "opencode-heartbeat"
    beat.parent.mkdir(parents=True, exist_ok=True)
    beat.touch()
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"

    rows = [line for line in doctor.coverage(None) if line.startswith("  T")]
    assert rows, "the coverage block printed no surface at all"
    assert not [line for line in rows if "BLOCKS" in line], "\n".join(rows)
    assert beat.exists(), "uninstall deleted a global cache no receipt row authorized"


def test_a_full_receipt_over_an_empty_machine_is_not_ready(wired):
    """The half task 4 could not deliver, and the reason option 1 was refused in writing.

    `uninstall` is only the loudest way a machine stops matching its receipt. A settings
    file edited by hand, a surface removed by its own installer, a home restored from a
    backup — none of them goes through this tool, and a record that only this tool can
    correct is wrong the moment any of them happens. So the receipt is left exactly as a
    completed install wrote it, and the guards are taken off the disk underneath it."""
    receipt = wiring.receipt()
    assert [row for row in receipt["wrote"] if row["kind"] == "guard"], "the fixture wired nothing"
    for surface in wiring.table()["surface"]:
        if surface.get("settings"):
            wiring.expand(surface["settings"]).unlink(missing_ok=True)

    assert wiring.receipt() == receipt, "this test is supposed to leave the record alone"
    assert init.global_ready() is False, "a full receipt outvoted an empty machine"


def test_a_plain_init_after_uninstall_rewires_rather_than_reporting_ready(wired, keyboard):
    """The install verb, told by a log that there is nothing to install. Green from task 4
    for the same reason as the test above it, and owed the same second half by task 8."""
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    init.main(["--no-project", "-y"])
    assert stripped(wired)["guards"], "a plain `ai-eng init` wired nothing back"


def test_doctor_does_not_call_a_stripped_machine_healthy(wired, keyboard):
    """The one assertion whose title is `Every symlink resolves` reported ok with none left,
    because it tested that the recorded root exists — and a skills root exists because the
    surface made it, and keeps existing because it holds skills that belong to the user."""
    from ai_engineering import doctor

    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert stripped(wired)["links"] == 0
    problem = None
    with contextlib.suppress(doctor.Undecidable):
        problem = doctor.links_resolve(None)
    assert problem is not None, "assertion 13 passed with every one of our symlinks deleted"


def test_the_count_of_links_removed_is_the_number_it_removed(home, capsys, keyboard):
    """The line reports a count, so the count is asserted rather than its presence. Every
    arithmetic mutant of it — set to one, decremented, stepped by two — is a screen that
    says a number nobody counted, which is the smallest possible version of this spec."""
    store = paths.home() / "skills"
    root = home / ".claude" / "skills"
    root.mkdir(parents=True)
    for name in ("ai-spec", "ai-plan", "ai-note"):
        (store / name).mkdir(parents=True)
        (root / name).symlink_to(store / name)
    wiring.record([{"path": str(root), "kind": "link", "how": "symlink"}])
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert f"✓ 3 skills removed from {root}" in capsys.readouterr().out
    assert not list(root.glob("ai-*"))


def test_a_copied_skill_goes_only_where_the_receipt_says_we_copied(home, keyboard):
    """`how` is the receipt answering the one question the disk cannot: a directory named
    like a skill is ours when we put it there and somebody else's otherwise. Without the row
    saying copy, a real directory in a skills root is not ours to delete."""
    store = paths.home() / "skills"
    shutil.copytree(paths.skills() / "ai-spec", store / "ai-spec")
    root = home / ".claude" / "skills"
    shutil.copytree(paths.skills() / "ai-spec", root / "ai-spec")
    wiring.record([{"path": str(root), "kind": "link", "how": "symlink"}])
    first = uninstall.main(["-y"])
    assert type(first) is outcome.Result and first.outcome == "INCOMPLETE"
    assert (root / "ai-spec").is_dir(), "a directory was removed on a row that says symlink"

    wiring.record([{"path": str(root), "kind": "link", "how": "copy"}])
    second = uninstall.main(["-y"])
    assert type(second) is outcome.Result and second.outcome == "PASS"
    assert not (root / "ai-spec").exists(), "the copy the receipt names survived"


def test_a_project_file_somebody_deleted_by_hand_is_not_an_error(repo, home, monkeypatch, keyboard):
    """`uninstall` runs over a record of what was written, and a person is free to have
    removed any of it already. Reaching for a file that is gone has to be the ordinary case,
    not a traceback in the middle of unwiring a repository."""
    init.main(["--no-global", "--project", str(repo), "-y"])
    (repo / "justfile").unlink()
    monkeypatch.chdir(repo)
    result = uninstall.main(["--project", "-y"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert git_get(repo, "core.hooksPath") == "", "the unwiring stopped at the missing file"


def test_the_link_branch_leaves_a_skill_this_install_never_wrote(home, capsys, keyboard):
    """It globbed `ai-*` in the surface's skills root and unlinked whatever came back, so a
    skill somebody else installed under that prefix went with ours — from the verb that
    exists to prove this tool takes only what it brought."""
    store = paths.home() / "skills"
    (store / "ai-spec").mkdir(parents=True)
    root = home / ".claude" / "skills"
    root.mkdir(parents=True)
    (root / "ai-spec").symlink_to(store / "ai-spec")
    # A name that is provably not one of ours, asserted rather than assumed: this fixture
    # used to plant `ai-design`, and the day `ai-design` shipped the "somebody else's skill"
    # in the test became one of ours and the test stopped testing what it says.
    theirs = root / "ai-not-one-of-ours"
    assert not (paths.skills() / theirs.name).exists()
    theirs.symlink_to(home / "somewhere-else")
    wiring.record([{"path": str(root), "kind": "link", "how": "symlink"}])

    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert not (root / "ai-spec").exists(), "ours survived"
    assert theirs.is_symlink(), "uninstall took a skill it never installed"
    assert "✓ 1 skills removed from" in capsys.readouterr().out


def test_one_ownership_mismatch_stops_the_whole_uninstall_before_the_loop(
    home, tmp_path, capsys, keyboard
):
    """The write was outside every `try` in a function whose read and parse were both
    guarded, so one settings file with the wrong permissions raised mid-loop and left every
    surface after it in the receipt's order still wired — the shape spec 003 closed for the
    OpenCode parse crash, in the one line that fix did not reach."""
    locked, locked_row = surface_row("claude-code")
    locked.parent.mkdir()
    wiring.write_json(locked, {"hooks": [{"command": wiring.command("PreToolUse")}]})
    locked.chmod(0o400)
    after, after_row = surface_row("cursor")
    wiring.write_json(after, {"hooks": [{"command": wiring.command("PreToolUse")}]})
    rows = [locked_row, after_row]
    wiring.record(rows)
    try:
        result = uninstall.main(["-y"])
        assert type(result) is outcome.Result
        assert result.outcome == "INCOMPLETE"
        assert wiring.ours(locked.read_text(encoding="utf-8"))
        assert wiring.ours(after.read_text(encoding="utf-8"))
        text = capsys.readouterr().out
        assert "no longer matches the exact bytes or entries owned" in text
        left = [row["path"] for row in wiring.receipt()["wrote"]]
        assert left == [locked_row["path"], after_row["path"]]
    finally:
        locked.chmod(0o600)


def test_a_settings_file_holding_our_entry_that_is_not_json_is_named_not_dismissed(
    home, tmp_path, capsys, keyboard
):
    """It answered "had no entry of ours" about a file that had just proved it has one —
    the same false green this spec is about, one function down."""
    target, row = surface_row("claude-code")
    target.parent.mkdir(parents=True)
    target.write_text(f'{{ // theirs\n "c": "{wiring.SIGNATURE}",\n}}\n', encoding="utf-8")
    wiring.record([row])
    before = target.read_bytes()
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert target.read_bytes() == before
    assert "no longer matches the exact bytes or entries owned" in capsys.readouterr().out


def test_uninstall_cannot_reach_a_repository_you_are_not_standing_in(
    repo, home, monkeypatch, keyboard
):
    """`"…/repo-backup/justfile".startswith("…/repo")` is True, and the line that asked it
    went straight on to unlink. Standing in one repository deleted recorded files out of
    every sibling whose name began with the same letters. Nothing on the operator's machine
    happened to pair that way; that is luck, and luck is not a control."""
    sibling = repo.parent / f"{repo.name}-backup"
    sibling.mkdir()
    theirs = sibling / "justfile"
    theirs.write_text("mine, in a repository nobody asked about\n", encoding="utf-8")
    init.main(["--no-global", "--project", str(repo), "-y"])
    wiring.record([{"path": str(theirs), "kind": "project", "how": "written"}])

    monkeypatch.chdir(repo)
    before = wiring.receipt_path().read_bytes()
    result = uninstall.main(["--project", "-y"])
    assert type(result) is outcome.Result and result.outcome == "INCOMPLETE"
    assert theirs.exists(), "uninstall deleted a file in a repository it was never pointed at"
    assert (repo / "justfile").exists(), "an ambiguous receipt still removed a valid target"
    assert wiring.receipt_path().read_bytes() == before


def test_a_tampered_receipt_blocks_every_project_mutation(repo, home, monkeypatch, keyboard):
    """The receipt is evidence of an install, not authority to delete any path somebody
    writes into it. Even inside the selected repository, only the finite files `init` can
    create are candidates; otherwise a forged project row can delete AGENTS.md, source, or
    any other file while the screen repeats the receipt's false claim that it is ours."""
    theirs = repo / "notes.txt"
    theirs.write_text("mine\n", encoding="utf-8")
    ours = repo / "justfile"
    ours.write_text("check:\n", encoding="utf-8")
    forged = {"path": str(theirs), "kind": "project", "how": "written"}
    wiring.record(
        [
            {"path": str(ours), "kind": "project", "how": "written"},
            forged,
            {"path": str(repo), "kind": "repo", "how": ""},
        ]
    )

    monkeypatch.chdir(repo)
    before = wiring.receipt_path().read_bytes()
    result = uninstall.main(["--project", "-y"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert theirs.read_text(encoding="utf-8") == "mine\n"
    assert ours.read_text(encoding="utf-8") == "check:\n"
    assert wiring.receipt_path().read_bytes() == before


@pytest.mark.parametrize(
    "kind,how,file_target",
    [
        ("guard", "ts_opencode", True),
        ("link", "copy", False),
        ("skills", "wheel", False),
    ],
)
def test_a_tampered_receipt_cannot_expand_the_machine_paths_this_install_owns(
    home, tmp_path, kind, how, file_target, keyboard
):
    """Each global row kind has one source of allowed destinations: the surface table or
    the private skills store. A forged row outside that closed set must remain recorded and
    untouched instead of turning a receipt edit into arbitrary unlink or rmtree."""
    target = tmp_path / f"not-ours-{kind}"
    owned_looking = target if file_target else target / "ai-spec"
    if file_target:
        owned_looking.write_text(wiring.SIGNATURE, encoding="utf-8")
    else:
        owned_looking.mkdir(parents=True)
        (owned_looking / "SKILL.md").write_text("mine\n", encoding="utf-8")
    row = {"path": str(target), "kind": kind, "how": how}
    wiring.record([row])

    result = uninstall.main(["-y"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert owned_looking.exists()
    assert wiring.receipt()["wrote"] == [row]


def test_a_malformed_project_path_in_the_receipt_fails_closed(home):
    row = {"path": None, "kind": "project", "how": "written"}
    assert uninstall.fate(row, Path("/repos/app")) == (
        "kept — receipt target is not one this installer can own"
    )


@pytest.mark.parametrize("before", [None, "other\nhooks", "x" * 4097])
def test_a_receipt_cannot_put_control_data_in_git_config(home, before):
    root = Path("/repos/app")
    row = {"path": str(root), "kind": "repo", "how": before}
    assert uninstall.canonical(row, root) is None


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/repos/app", True),
        ("/repos/app/justfile", True),
        ("/repos/app/.github/workflows/check.yml", True),
        ("/repos/app-backup/justfile", False),
        ("/repos/application/justfile", False),
        ("/repos/other/justfile", False),
    ],
)
def test_inside_answers_by_path_parts_and_never_by_string_prefix(path, expected):
    """The unit of the above, because the sibling that matters is the one nobody has yet."""
    assert uninstall.inside(path, Path("/repos/app")) is expected


@pytest.mark.parametrize(
    "kind, root, want",
    [
        ("guard", None, ""),
        ("link", None, ""),
        ("skills", None, ""),
        ("project", None, "kept — repository files"),
        ("repo", None, "kept — repository files"),
        ("project", Path("/repos/app"), ""),
        ("repo", Path("/repos/app"), ""),
        ("project", Path("/repos/other"), "kept — belongs to another repository"),
        ("repo", Path("/repos/other"), "kept — not this repository"),
    ],
)
def test_what_happens_to_a_row_is_decided_once_for_every_kind_there_is(home, kind, root, want):
    """The table this verb's screen and its loop both read. They used to be two answers —
    a list that printed every row and a loop with branches for two of the five kinds — and
    the whole defect was that the two could disagree. Every kind is named here, so a sixth
    one arriving with no fate lands on this test rather than on somebody's machine."""
    rows = {
        "guard": surface_row("claude-code")[1],
        "link": surface_row("claude-code", "link", "symlink")[1],
        "skills": {"path": str(paths.home() / "skills"), "kind": "skills", "how": "wheel"},
        "project": {"path": "/repos/app/justfile", "kind": "project", "how": "written"},
        "repo": {"path": "/repos/app", "kind": "repo", "how": ""},
    }
    row = rows[kind]
    got = uninstall.fate(row, root)
    assert got.startswith(want) if want else got == ""


@pytest.mark.parametrize(
    "typed, removed", [("y", True), ("Y", True), ("yes", True), ("n", False), ("", False)]
)
def test_the_consent_question_is_the_answer_typed_into_it(home, typed, removed, keyboard):
    """A consent check satisfied by the presence of a terminal rather than by the answer
    typed into it strips a machine's guards on the run somebody started in order to read
    the list. The prompt's own words are pinned because they are the question being
    answered."""
    keyboard(typed)
    settings, row = surface_row("claude-code")
    wiring.json_claude(settings)
    wiring.record([row])
    result = uninstall.main([])
    assert wiring.ours(settings.read_text(encoding="utf-8")) is not removed
    assert type(result) is outcome.Result
    assert result.outcome == ("PASS" if removed else "CANCELLED")


def test_declining_says_so_and_leaves_the_record_exactly_as_it_was(home, capsys, keyboard):
    """The other half of the same question: a run that removed nothing must not retract
    anything either, or the record starts disagreeing with the machine in the direction this
    spec spent fifteen tasks removing."""
    keyboard("n")
    settings, row = surface_row("claude-code")
    wiring.json_claude(settings)
    wiring.record([row])
    before = wiring.receipt_path().read_text(encoding="utf-8")
    result = uninstall.main([])
    assert type(result) is outcome.Result
    assert result.outcome == "CANCELLED"
    assert "  nothing removed.\n" in capsys.readouterr().out
    assert wiring.receipt_path().read_text(encoding="utf-8") == before


def test_the_repository_half_is_retracted_from_the_record_too(repo, home, monkeypatch, keyboard):
    """`--project` unwires the repository, and the rows that described it have to leave the
    record with everything else — otherwise the next `uninstall` lists files it removed an
    hour ago and offers to remove them again."""
    init.main(["--no-global", "--project", str(repo), "-y"])
    assert [r["kind"] for r in wiring.receipt()["wrote"] if r["kind"] in ("project", "repo")]
    monkeypatch.chdir(repo)
    result = uninstall.main(["--project", "-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    left = [r["kind"] for r in wiring.receipt().get("wrote", [])]
    assert not [k for k in left if k in ("project", "repo")], f"the record kept {left}"


def test_a_skills_store_that_is_already_gone_says_so_rather_than_ticking(home, capsys, keyboard):
    """A tick for work that did not happen is the smallest version of this spec's subject."""
    wiring.record([{"path": str(paths.home() / "skills"), "kind": "skills", "how": "wheel"}])
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert "→ " in capsys.readouterr().out


def test_the_whole_uninstall_screen_line_for_line(home, capsys, keyboard):
    """Every line, not a fragment of one. Specs 005 and 006 both closed on the same lesson
    and it is written down in the ceiling comment: two screens asserted by fragment, where
    every line the fragment did not name could be emptied or upper-cased with the suite
    still green. This verb's screen is the one a person reads while deciding whether to
    answer y, so it is held whole.

    One row of every kind there is, and two of them are kept — which is what makes the
    header's count, the reason on each kept row and the repository it will not enter all
    assertions rather than decoration."""
    store = paths.home() / "skills"
    shutil.copytree(paths.skills() / "ai-spec", store / "ai-spec")
    root, link_row = surface_row("claude-code", "link", "symlink")
    root.mkdir(parents=True)
    (root / "ai-spec").symlink_to(store / "ai-spec")
    settings, guard_row = surface_row("claude-code")
    wiring.json_claude(settings)
    wiring.record(
        [
            guard_row,
            link_row,
            {"path": str(store), "kind": "skills", "how": "wheel"},
            {"path": "/elsewhere/repo/justfile", "kind": "project", "how": "written"},
            {"path": "/elsewhere/repo", "kind": "repo", "how": ""},
        ]
    )
    capsys.readouterr()
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    kept = "kept — repository files; re-run with --project inside that repository"
    assert capsys.readouterr().out == (
        f"  5 things are recorded here, and 3 of them will be removed:\n"
        f"    guard    {guard_row['path']}\n"
        f"    link     {root}\n"
        f"    skills   {store}\n"
        f"    project  /elsewhere/repo/justfile  ·  {kept}\n"
        f"    repo     /elsewhere/repo  ·  {kept}\n"
        f"  Kept, always: specs/, CONSTITUTION.md, AGENTS.md, docs/adr/\n"
        f"  Not entered: /elsewhere/repo — `cd /elsewhere/repo && ai-eng uninstall --project`\n"
        f"  ✓ entries removed from {guard_row['path']}\n"
        f"  ✓ 1 skills removed from {root}\n"
        f"  ✓ skills removed from {store}\n"
        f"\n"
        f"  The record is still at {paths.home() / 'state'}. Delete that folder yourself if "
        f"you want it gone: it is proof of what happened, and not ours to throw away.\n"
    )


def test_every_row_it_lists_gets_a_line_saying_what_happened_to_it(home, capsys, keyboard):
    """It printed thirty-two rows under "every one is listed here", asked "Remove them?",
    and ran a loop with branches for two kinds. Nineteen project rows, four repo rows and one
    skills row fell through with no tick, no "kept", and no line at all — consent taken for
    work that was never going to happen."""
    settings, guard_row = surface_row("claude-code")
    _, link_row = surface_row("claude-code", "link", "symlink")
    wiring.json_claude(settings)
    rows = [
        guard_row,
        link_row,
        {"path": str(paths.home() / "skills"), "kind": "skills", "how": "wheel"},
        {"path": "/elsewhere/repo/justfile", "kind": "project", "how": "written"},
        {"path": "/elsewhere/repo", "kind": "repo", "how": ""},
    ]
    wiring.record(rows)
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    text = capsys.readouterr().out
    assert "5 things are recorded here, and 3 of them will be removed" in text
    for row in rows:
        assert row["path"] in text, f"{row['kind']} row was never printed"
    assert "/elsewhere/repo/justfile  ·  kept — repository files" in text
    assert (
        "Not entered: /elsewhere/repo — `cd /elsewhere/repo && ai-eng uninstall --project`" in text
    )
    kept = {row["kind"] for row in wiring.receipt()["wrote"]}
    assert kept == {"project", "repo"}, f"the receipt kept {sorted(kept)}"


def test_the_skills_store_is_removed_rather_than_listed_and_left(home, capsys, keyboard):
    """Eight skills survived every uninstall, and `init` counted them off the disk on the
    next run and reported a ready machine. They are ours, under our own folder, and nothing
    else reads them."""
    store = paths.home() / "skills"
    shutil.copytree(paths.skills() / "ai-spec", store / "ai-spec")
    (store / "yours").mkdir()
    wiring.record([{"path": str(store), "kind": "skills", "how": "wheel"}])
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result and result.outcome == "PASS"
    assert not (store / "ai-spec").exists(), "the skills store survived"
    assert (store / "yours").exists(), "uninstall removed something that is not ours"
    assert "✓ skills removed from" in capsys.readouterr().out


def test_a_receipt_with_nothing_this_run_can_remove_asks_no_question(home, capsys, keyboard):
    """The consent question counted rows it had no branch for, so a machine whose global half
    was already gone still asked whether to remove twenty-four things and then removed none.
    The typed answer here is `n`: reaching the question at all fails this test."""
    keyboard("n")
    wiring.record(
        [
            {"path": "/elsewhere/repo/justfile", "kind": "project", "how": "written"},
            {"path": "/elsewhere/repo", "kind": "repo", "how": ""},
        ]
    )
    result = uninstall.main([])
    assert type(result) is outcome.Result
    assert result.outcome == "READY", "it asked about rows it was never going to touch"
    assert "Nothing to remove." in capsys.readouterr().out


def test_uninstall_removes_nothing_until_somebody_types_yes(home, keyboard):
    """Without -y the question is the whole safety. A consent check satisfied by the mere
    presence of a terminal rather than by the answer typed into it strips a machine's guards
    on the run somebody started to read the list."""
    keyboard("n")
    settings, row = surface_row("claude-code")
    wiring.json_claude(settings)
    wiring.record([row])
    before = settings.read_text(encoding="utf-8")
    result = uninstall.main([])
    assert type(result) is outcome.Result
    assert result.outcome == "CANCELLED"
    assert settings.read_text(encoding="utf-8") == before, "it removed the entry anyway"


def test_uninstall_removes_the_opencode_plugin_and_keeps_going(home, capsys, keyboard):
    """The installer records the OpenCode plugin as a guard row, so uninstall used to send
    it to the routine that strips JSON entries. That routine found the signature inside the
    TypeScript, handed the TypeScript to a JSON parser and raised — uncaught, and mid-loop,
    so every surface listed after it was left wired by the verb whose whole pitch is that
    governance can be removed cleanly. The plugin is a file we wrote whole, so it is
    removed rather than edited, and the settings file after it in the receipt is still
    unwired."""
    plugin, plugin_row = surface_row("opencode")
    wiring.ts_opencode(plugin)
    settings, settings_row = surface_row("claude-code")
    wiring.json_claude(settings)
    wiring.record([plugin_row, settings_row])
    result = uninstall.main(["-y"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert not plugin.exists()
    remaining = json.loads(settings.read_text(encoding="utf-8"))
    assert wiring.SIGNATURE not in json.dumps(remaining)
    assert all(rows == [] for rows in remaining["hooks"].values())
    assert "plugin removed" in capsys.readouterr().out


def test_a_settings_file_that_is_not_json_is_left_alone_and_reported(tmp_path):
    """Anything the stripper cannot parse is not something it knows how to edit, and the
    file stays exactly as it is. What changed is the answer it gives about it.

    This used to return False, and the reason written here was that raising ends the whole
    uninstall part-way through — which was true while `main` had no per-row catch, and is
    the better half of that trade no longer being on offer. False reaches the screen as
    "had no entry of ours", about a file that contains our entry; the loop now names it,
    keeps its row in the receipt because the entry really is still there, and carries on to
    every surface after it."""
    odd = tmp_path / "hooks.yaml"
    body = "command: /x/hooks/chain.py PreToolUse\n"
    odd.write_text(body, encoding="utf-8")
    with pytest.raises(wiring.Unreadable, match="holds our entry"):
        uninstall.strip_entries(odd)
    assert odd.read_text(encoding="utf-8") == body


@pytest.fixture
def pinned_repo(repo):
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text(
        skeletons.CONFIG_TOML.format(version=__version__), encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "pin"], check=True, capture_output=True)
    return repo


def test_update_migrations_are_strictly_forward_ordered_and_contiguous() -> None:
    upgrade = update.migrations("0.13", "1.0")

    assert [step.parent.name + "/" + step.name for step in upgrade] == ["0.13..1.0/unvendor.py"]
    assert update.migrations("0.13.7", "1.0") == upgrade
    assert update.migrations("1.0", "1.0.0") == []
    with pytest.raises(update.Undecidable, match="downgrade"):
        update.migrations("1.0", "0.13")


def test_update_rejects_a_gap_in_the_shipped_migration_chain(tmp_path, monkeypatch) -> None:
    folder = tmp_path / "migrations"
    for name in ("0.13..0.14", "0.14..1.0"):
        step = folder / name / "step.py"
        step.parent.mkdir(parents=True)
        step.write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(update.paths, "shipped", lambda name: folder)

    assert [step.parent.name for step in update.migrations("0.13", "1.0")] == [
        "0.13..0.14",
        "0.14..1.0",
    ]
    (folder / "0.14..1.0").rename(folder / "0.15..1.0")
    with pytest.raises(update.Undecidable, match="not contiguous"):
        update.migrations("0.13", "1.0")


def test_update_blocks_a_downgrade_before_requesting_consent(
    pinned_repo, keyboard, monkeypatch, capsys
):
    pin = pinned_repo / ".ai" / "config.toml"
    before = pin.read_bytes()
    keyboard("y")
    monkeypatch.chdir(pinned_repo)
    monkeypatch.setattr(
        "builtins.input", lambda _: pytest.fail("a downgrade must stop before consent")
    )

    result = update.main(["--to", "0.13"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert pin.read_bytes() == before
    assert "downgrade" in capsys.readouterr().out


def test_update_rejects_an_aliased_pin_home_without_touching_its_target(
    repo, tmp_path, keyboard, monkeypatch
):
    external = tmp_path / "foreign-ai-home"
    external.mkdir()
    external_pin = external / "config.toml"
    external_pin.write_text(skeletons.CONFIG_TOML.format(version=__version__), encoding="utf-8")
    before = external_pin.read_bytes()
    (repo / ".ai").symlink_to(external, target_is_directory=True)
    keyboard("y")
    monkeypatch.chdir(repo)

    result = update.main(["--to", "9.9.9"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert external_pin.read_bytes() == before


def test_update_preserves_a_valid_pin_edit_made_while_consent_is_requested(
    pinned_repo, keyboard, monkeypatch
):
    pin = pinned_repo / ".ai" / "config.toml"
    monkeypatch.chdir(pinned_repo)

    def edit_then_consent(_: str) -> str:
        with pin.open("a", encoding="utf-8") as stream:
            stream.write('\n[user]\nnote = "keep this concurrent edit"\n')
        return "y"

    keyboard("y")
    monkeypatch.setattr("builtins.input", edit_then_consent)

    result = update.main(["--to", "9.9.9"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    body = pin.read_text(encoding="utf-8")
    assert 'version = "1.0.0"' in body
    assert 'note = "keep this concurrent edit"' in body


def test_update_rejects_a_same_bytes_pin_replacement_after_consent_snapshot(
    pinned_repo, keyboard, monkeypatch
):
    pin = pinned_repo / ".ai" / "config.toml"
    before = pin.read_bytes()
    monkeypatch.chdir(pinned_repo)

    def replace_then_consent(_: str) -> str:
        replacement = pin.with_name("replacement.toml")
        replacement.write_bytes(before)
        replacement.replace(pin)
        return "y"

    keyboard("y")
    monkeypatch.setattr("builtins.input", replace_then_consent)

    result = update.main(["--to", "9.9.9"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert pin.read_bytes() == before


def test_update_atomic_pin_publish_never_exposes_a_partial_temp_write(
    pinned_repo, keyboard, monkeypatch
):
    pin = pinned_repo / ".ai" / "config.toml"
    before = pin.read_bytes()
    keyboard("y")
    monkeypatch.chdir(pinned_repo)

    def partial_write(descriptor: int, body: bytes) -> None:
        update.os.write(descriptor, body[:12])
        raise OSError("simulated short publish")

    monkeypatch.setattr(update, "_write_all", partial_write)

    result = update.main(["--to", "9.9.9"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert pin.read_bytes() == before
    assert list(pin.parent.glob(".config.toml.ai-eng-*")) == []


def test_update_names_the_nontransactional_risk_after_an_opaque_script_starts(
    pinned_repo, keyboard, monkeypatch, capsys
):
    pin = pinned_repo / ".ai" / "config.toml"
    before = pin.read_bytes()
    touched = pinned_repo / "opaque-side-effect"
    keyboard("y")
    monkeypatch.chdir(pinned_repo)
    monkeypatch.setattr(update, "migrations", lambda pinned, target: [Path("opaque.py")])
    real_run = update.subprocess.run

    def fail_after_effect(command, **kwargs):
        if command[:2] == [sys.executable, "opaque.py"]:
            touched.write_text("migration started\n", encoding="utf-8")
            raise subprocess.CalledProcessError(1, command)
        return real_run(command, **kwargs)

    monkeypatch.setattr(update.subprocess, "run", fail_after_effect)

    result = update.main(["--to", "9.9.9"])

    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert pin.read_bytes() == before
    assert touched.read_text(encoding="utf-8") == "migration started\n"
    rendered = capsys.readouterr().out
    assert "Migration scripts already ran and are not transactional" in rendered
    assert "Update wrote nothing" not in rendered


def test_update_never_runs_without_a_person_at_the_keyboard(pinned_repo, monkeypatch, capsys):
    """A change of governance is never silent. With no terminal — CI, a cron job, a wrapper
    script — update must refuse and leave the pin exactly as it found it."""
    monkeypatch.chdir(pinned_repo)
    pin = pinned_repo / ".ai" / "config.toml"
    before = pin.read_text(encoding="utf-8")
    result = update.main(["--to", "9.9.9"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert pin.read_text(encoding="utf-8") == before
    assert "decision" in capsys.readouterr().out


@pytest.mark.parametrize("flags", [[], ["--force"]])
def test_update_refuses_while_a_framework_owned_file_has_uncommitted_changes(
    flags, pinned_repo, monkeypatch, capsys
):
    """The files update rewrites are the ones a user edits. Running over an uncommitted edit
    destroys work with no diff to recover it from, so it stops before the question is asked —
    and --force, which people reach for expecting the opposite, only prints what it would
    have discarded. A --force that actually overwrote would be a silent loss of somebody's
    afternoon."""
    monkeypatch.chdir(pinned_repo)
    (pinned_repo / "justfile").write_text("mine:\n", encoding="utf-8")
    result = update.main(flags)
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert "REFUSED" in capsys.readouterr().out
    assert (pinned_repo / "justfile").read_text(encoding="utf-8") == "mine:\n"


@pytest.mark.parametrize(
    "setup,message", [("none", "not inside a repository"), ("git", "not set up")]
)
def test_update_stops_where_there_is_nothing_pinned_to_update(
    setup, message, tmp_path, repo, monkeypatch, capsys
):
    """Run from a directory that is no repository, or one that was never set up, update has to
    say so and stop. Reading a pin that is not there is where a half-applied migration starts."""
    monkeypatch.chdir(repo if setup == "git" else tmp_path)
    result = update.main([])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    assert message in capsys.readouterr().out


@pytest.fixture
def keyboard(monkeypatch):
    """A terminal with somebody at it, and whatever they typed."""

    class Terminal:
        def isatty(self):
            return True

    monkeypatch.setattr(sys, "stdin", Terminal())
    return lambda typed: monkeypatch.setattr("builtins.input", lambda *_: typed)


@pytest.mark.parametrize(
    "typed,runs", [("", False), ("n", False), ("yes please", False), ("Y ", True)]
)
def test_update_runs_only_on_an_answer_that_is_exactly_yes(
    typed, runs, pinned_repo, keyboard, monkeypatch
):
    """Enter is not consent. Anything but a typed y leaves the pin alone, because the prompt
    that decides which rules govern a repository must not be answerable by leaning on the
    keyboard."""
    keyboard(typed)
    monkeypatch.chdir(pinned_repo)
    pin = pinned_repo / ".ai" / "config.toml"
    result = update.main(["--to", "9.9.9"])
    assert type(result) is outcome.Result
    assert result.outcome == ("PASS" if runs else "CANCELLED")
    assert ('version = "9.9.9"' in pin.read_text(encoding="utf-8")) is runs


def test_update_leaves_a_surface_this_machine_declined(pinned_repo, home, keyboard, monkeypatch):
    """Decline Cursor at `init`, run `ai-eng update` a week later, and it was wired — with
    `failClosed: true`, which is the key that makes Cursor deny rather than advise — by a
    verb somebody ran to move a version number, with no receipt row behind it. `uninstall`
    then listed what `init` had written, took the consent, and left Cursor running."""
    keyboard("y")
    monkeypatch.chdir(pinned_repo)
    (home / ".cursor").mkdir()
    (home / ".claude").mkdir(exist_ok=True)
    wiring.json_claude(home / ".claude" / "settings.json")
    wiring.record([{"path": "~/.claude/settings.json", "kind": "guard", "how": "json_claude"}])

    result = update.main(["--to", "9.9.9"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert not (home / ".cursor" / "hooks.json").exists(), "update wired a declined surface"


def test_update_records_the_entries_it_writes_so_uninstall_can_find_them(
    pinned_repo, home, keyboard, monkeypatch
):
    """An entry nothing recorded is an entry `uninstall` cannot see. update rewrote them and
    never called `record`, so the receipt under-reported for exactly as long as the log was
    also the thing `init` read to decide whether this machine was wired."""
    keyboard("y")
    monkeypatch.chdir(pinned_repo)
    wiring.json_claude(home / ".claude" / "settings.json")
    wiring.record([{"path": "~/.claude/settings.json", "kind": "guard", "how": "json_claude"}])
    wiring.forget([{"path": "~/.claude/settings.json", "kind": "guard"}])
    wiring.record([{"path": "~/.claude/settings.json", "kind": "guard", "how": "json_claude"}])

    result = update.main(["--to", "9.9.9"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    rows = [r for r in wiring.receipt()["wrote"] if r["kind"] == "guard"]
    assert [r["path"] for r in rows] == ["~/.claude/settings.json"]
    assert rows[0]["how"] == "json_claude", "the row update wrote does not say how"


def test_update_rewrites_a_stale_entry_and_leaves_an_append_only_surface_alone(
    pinned_repo, home, keyboard, monkeypatch, capsys
):
    """When the interpreter moves, every entry still names the old one and every guard is off
    while the settings file still looks wired. update rewrites them — except Codex, whose
    trust is a hash of the whole handler and its position, where a rewrite would silently turn
    the entry off instead of on.

    Both surfaces are recorded first, because `update` rewires what this machine chose rather
    than everything installed on it. Walking `detect()` meant declining Cursor at `init` and
    updating a week later wired it, failClosed, from a verb somebody ran to move a version
    number."""
    keyboard("y")
    monkeypatch.chdir(pinned_repo)
    wiring.record(
        [
            {"path": "~/.claude/settings.json", "kind": "guard", "how": "json_claude"},
            {"path": "~/.codex/hooks.json", "kind": "guard", "how": "json_codex"},
        ]
    )
    stale = '"/gone/python" "/gone/ai-engineering/hooks/chain.py" PreToolUse'
    claude = home / ".claude" / "settings.json"
    wiring.write_json(
        claude,
        {"hooks": {"PreToolUse": [{"matcher": "*", "hooks": [{"command": stale}]}]}},
    )
    codex = home / ".codex" / "hooks.json"
    # Spelled the way a wheel installs it, so nothing here is recognisable as ours: what has
    # to leave this file alone is the append_only rule, not json_codex recognising itself.
    unknown = '"/gone/python" "/gone/ai_engineering/hooks/chain.py" PreToolUse'
    wiring.write_json(codex, {"hooks": {"PreToolUse": [{"hooks": [{"command": unknown}]}]}})
    frozen = codex.read_text(encoding="utf-8")

    result = update.main(["--to", "9.9.9"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    written = claude.read_text(encoding="utf-8")
    assert "/gone/" not in written, "the stale entry survived; the guard is still not running"
    assert sys.executable in written
    assert written.count("chain.py") == len(wiring.EVENTS)
    assert codex.read_text(encoding="utf-8") == frozen, "Codex was rewritten and lost its trust"
    assert 'version = "9.9.9"' in (pinned_repo / ".ai" / "config.toml").read_text(encoding="utf-8")


@pytest.mark.parametrize("stacks", [[], ["python"], sorted(skeletons.RECIPES)])
def test_the_shipped_check_recipe_runs_every_recipe_that_ships_with_it(home, stacks):
    """`just check` is the whole contract with CI. A recipe missing from that line never runs
    and reports nothing; a name on it that is no recipe makes `just check` fail for everyone.

    Driven over no stack, one, and every stack there is a row for, because the recipe bodies
    are filled in now and a body that lands at the wrong indentation is a new recipe as far
    as `just` is concerned — which is how a filled-in file could ship having quietly dropped
    `security` off the check line."""
    written = skeletons.justfile(stacks)
    defined = set(re.findall(r"^([a-z]+):", written, re.M))
    called = set(re.search(r"^check:(.*)$", written, re.M).group(1).split())
    assert called == defined - {"check"}, f"check runs {sorted(called)}, ships {sorted(defined)}"
    assert "{" not in written, "an unrendered placeholder shipped in the justfile"
    for stack in stacks:
        for command in skeletons.RECIPES[stack]:
            assert f"\n    {command}\n" in written, command


def test_a_stack_with_no_row_here_keeps_its_todo_and_says_nothing_about_itself():
    """The promise in the docstring, driven. A name we cannot fill in has to leave the file
    exactly as an empty repository gets it — no header claiming it was filled in for a
    language, and no recipe body invented for one."""
    written = skeletons.justfile(["cobol"])
    assert written == skeletons.justfile([])
    assert written.startswith(
        "# What `check` means here. CI never learns a language: it runs `just check`.\n\nwired:"
    )
    # And it is skipped rather than stopped on: a repository with a marker we cannot name
    # beside one we can has to get the recipes for the one we can, whatever order they
    # arrive in. `stacks()` sorts them, so alphabetical order is the order this happens in.
    assert skeletons.justfile(["cobol", "python"]) == skeletons.justfile(["python"])
    assert "ruff check ." in skeletons.justfile(["cobol", "python"])


def test_the_python_recipes_are_the_commands_this_project_would_actually_run():
    """One stack written out, because the test above reads its expectations from the same
    table the code reads: swap two rows there and both sides move together. This one says
    what `lint`, `test` and `build` mean in Python, in the order the recipes are filled, so
    a table whose columns drift lands `pytest` under `lint` and is caught here.

    Python and not all seven: the point is that the order is pinned somewhere, and seven
    copies of that are seven things to update for one fact."""
    assert skeletons.RECIPES["python"] == ("ruff check .", "pytest -q", "uv build")
    assert list(skeletons.TODOS) == ["lint", "test", "build"]
    written = skeletons.justfile(["python"])
    assert "\nlint:\n    ruff check .\n" in written
    assert "\ntest:\n    pytest -q\n" in written
    assert "\nbuild:\n    uv build\n" in written


def test_the_config_template_renders_to_toml_carrying_the_version(home):
    """The pin is the audit trail of which version governs a repository. A template that will
    not parse, or that ships the placeholder as text, leaves every reader of it guessing."""
    rendered = skeletons.CONFIG_TOML.format(version="9.9.9")
    parsed = tomllib.loads(rendered)
    assert parsed["framework"]["version"] == "9.9.9"
    assert "{" not in rendered, "an unrendered placeholder shipped in the pin"
    assert set(parsed["guards"]) == {
        "loop_window",
        "loop_repeats",
        "loop_failures",
        "design_budget",
    }


def test_the_ci_snippet_keeps_its_actions_expression(home):
    """The copy-and-paste workflow init prints at the end of a project install."""
    assert "${{ env.PIN }}" in skeletons.CHECK_YML.format(version="9.9.9")


@pytest.mark.skipif(
    bool(os.environ.get("AI_ENG_REAL_SRC")),
    reason=(
        "the mutation sandbox has no environment in which a child can import the product, "
        "and this test's whole subject is that the real command runs before the anchor is "
        "written. Standing that command in for would leave the test asserting itself. It "
        "runs in every other suite, including CI's, and it is skipped here rather than "
        "hollowed out — a dead mutation gate cost more than this one test's reach."
    ),
)
def test_wire_git_executes_the_configured_module_before_persisting_it(
    repo, monkeypatch, real_anchor
):
    """The anchor is proved to run before it is written down.

    This machine was found with an editable install whose `.pth` pointed at a deleted
    worktree: a live interpreter, a dead `ai_engineering.cli`, and a persisted anchor that
    looked configured and answered nothing. Every hook that resolves the CLI through it then
    failed on a repository somebody had just installed into — and `doctor` said the anchor
    was set, because it was.

    So the command runs first, and a failure writes none of the three keys. Not one of them:
    a half-written anchor is the same lie with fewer fields.
    """

    keys = ("core.hooksPath", "ai.managed", "ai.eng")

    def configured() -> dict[str, str]:
        found = {}
        for key in keys:
            answer = subprocess.run(
                ["git", "-C", str(repo), "config", "--get", key],
                capture_output=True,
                text=True,
                check=False,
            )
            if answer.returncode == 0:
                found[key] = answer.stdout.strip()
        return found

    assert configured() == {}

    # The exact command, and nothing else, before any key is written.
    ran: list[list[str]] = []
    real = wiring.subprocess.run

    def watch(argv, *args, **kwargs):
        ran.append(list(argv))
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(wiring.subprocess, "run", watch)
    wiring.wire_git(repo)
    assert ran[0] == [sys.executable, "-m", "ai_engineering.cli", "--version"]
    assert configured()["ai.eng"] == f"{sys.executable} -m ai_engineering.cli"
    monkeypatch.undo()

    # And every way that command can fail to answer leaves the anchor untouched.
    for failure in (
        SimpleNamespace(returncode=1, stdout="ai-engineering 1.0.0"),
        SimpleNamespace(returncode=0, stdout=""),
        SimpleNamespace(returncode=0, stdout="some other tool 9.9"),
    ):
        fresh = repo.parent / f"fresh-{failure.returncode}-{len(failure.stdout)}"
        subprocess.run(["git", "init", "-b", "main", str(fresh)], check=True, capture_output=True)
        monkeypatch.setattr(wiring.subprocess, "run", lambda *a, _r=failure, **k: _r)
        with pytest.raises(wiring.Unreadable):
            wiring.wire_git(fresh)
        monkeypatch.undo()
        for key in keys:
            answer = subprocess.run(
                ["git", "-C", str(fresh), "config", "--get", key],
                capture_output=True,
                text=True,
                check=False,
            )
            assert answer.returncode != 0, key

    # The same plant as doctor's, against the writer — which runs with no `cwd=` at all,
    # so what it would have picked up is the installer's own shell directory.
    planted = repo.parent / "planted"
    (planted / "ai_engineering").mkdir(parents=True)
    marker = planted / "the-plant-ran"
    (planted / "ai_engineering" / "__init__.py").write_text("", encoding="utf-8")
    (planted / "ai_engineering" / "cli.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('executed', encoding='utf-8')\n"
        "print('ai-engineering 9.9.9')\n",
        encoding="utf-8",
    )
    standing = repo.parent / "standing"
    subprocess.run(["git", "init", "-b", "main", str(standing)], check=True, capture_output=True)
    monkeypatch.chdir(planted)
    wiring.wire_git(standing)
    monkeypatch.undo()
    assert not marker.exists(), "the directory the installer stood in executed its own code"

    # A timeout is a failure too, and it is the one a hung interpreter produces.
    def hangs(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="python", timeout=30)

    hung = repo.parent / "hung"
    subprocess.run(["git", "init", "-b", "main", str(hung)], check=True, capture_output=True)
    monkeypatch.setattr(wiring.subprocess, "run", hangs)
    with pytest.raises(wiring.Unreadable):
        wiring.wire_git(hung)
    monkeypatch.undo()
    assert (
        subprocess.run(
            ["git", "-C", str(hung), "config", "--get", "ai.eng"],
            capture_output=True,
            check=False,
        ).returncode
        != 0
    )


def test_the_wheel_carries_every_policy_file_the_product_opens(tmp_path):
    """The release's own wheel check is eight paths written by hand, and nothing keeps that
    list in step with what the product actually reads.

    Two policy files landed today. Neither is in that list, so if packaging ever stopped
    shipping `policy/accessibility.toml`, `ai-eng doctor`'s assertion 26 would report "cannot
    be read here" on every installed machine and the release that shipped it would have said
    nothing — a check whose list is a snapshot of the day it was written.

    So the list is derived instead of typed: every `paths.policy("...")` call site in the
    product, read out of the source, plus the adapters directory that `chain.py` globs. A
    file added to the tree and opened by the product is in this list the moment the call
    exists, which is the only version of this check that cannot go stale.
    """
    import ast
    import subprocess
    import sys
    import zipfile

    root = Path(__file__).resolve().parents[1]

    # Parsed, not matched. The first version of this used a regular expression and read the
    # sentence `paths.policy("...")` out of a comment written the same hour — reporting a
    # file called `...` as missing from the wheel. A tool that cannot tell a call from prose
    # about a call is the same defect this test exists to catch, one level up.
    opened = set()
    for source in [*(root / "src").rglob("*.py"), *(root / "hooks").rglob("*.py")]:
        try:
            tree = ast.parse(source.read_text("utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            called = node.func
            name = called.attr if isinstance(called, ast.Attribute) else getattr(called, "id", "")
            first = node.args[0]
            if (
                name == "policy"
                and isinstance(first, ast.Constant)
                and isinstance(first.value, str)
            ):
                opened.add(first.value)

    assert "accessibility.toml" in opened, "the reader this test was written for is gone"
    assert len(opened) >= 9, f"only {len(opened)} policy files are opened, which is too few"

    built = subprocess.run(
        [sys.executable, "-m", "uv", "build", "--out-dir", str(tmp_path)],
        capture_output=True,
        text=True,
        cwd=root,
        timeout=600,
        check=False,
    )
    if built.returncode != 0:
        built = subprocess.run(
            ["uv", "build", "--out-dir", str(tmp_path)],
            capture_output=True,
            text=True,
            cwd=root,
            timeout=600,
            check=False,
        )
    assert built.returncode == 0, built.stderr[-1500:]

    wheel = sorted(tmp_path.glob("*.whl"))[-1]
    names = set(zipfile.ZipFile(wheel).namelist())

    missing = sorted(one for one in opened if f"ai_engineering/policy/{one}" not in names)
    assert not missing, (
        f"the product opens {missing} and the wheel does not carry them, so every check "
        "that reads one is undecidable on an installed machine"
    )

    # And the adapters, which are globbed as a directory rather than named one at a time —
    # an adapter is added by dropping a file in, and the wheel has to carry that shape too.
    assert any(one.startswith("ai_engineering/policy/adapters/") for one in names)
