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
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering import __version__, init, paths, skeletons, uninstall, update, wiring


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


def test_a_settings_file_with_comments_reads_as_empty_and_is_then_replaced(home, tmp_path):
    """VS Code and Cursor write JSON with // comments and trailing commas. json.loads refuses
    it, read_json turns that refusal into {}, and the writer then saves a file that has lost
    everything the user had. This pins the loss; it does not bless it."""
    target = tmp_path / "settings.json"
    target.write_text('{\n  // theirs\n  "env": {"EDITOR": "vim"},\n}\n', encoding="utf-8")
    assert wiring.read_json(target) == {}
    wiring.json_claude(target)
    assert "EDITOR" not in target.read_text(encoding="utf-8")


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
    wiring.write_json(
        wiring.receipt_path(), {"wrote": [{"path": "x", "kind": "guard"}], "version": "0.0.1"}
    )
    not_a_repo = tmp_path / "nowhere"
    not_a_repo.mkdir()
    init.main(["-y", "--project", str(not_a_repo)])
    assert wiring.receipt()["version"] == __version__, "a stale install reported itself ready"


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
    backups = list(repo.glob("justfile.bak-*"))
    assert len(backups) == 1, f"overwrite left {len(backups)} backups"
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


@pytest.mark.xfail(
    reason="uninstall unlinks justfile and CLAUDE.md unconditionally, from a list that is not "
    "the receipt. init explicitly declined to overwrite this justfile and wrote no backup of "
    "it, so uninstall deletes a file the installer never created and cannot restore.",
    strict=True,
)
def test_uninstall_keeps_a_justfile_the_installer_refused_to_overwrite(repo, home, monkeypatch):
    """Install into a repository that already has a justfile, keep it, then uninstall."""
    (repo / "justfile").write_text("mine:\n\t@echo hello\n", encoding="utf-8")
    init.main(["--no-global", "--project", str(repo), "-y"])
    assert (repo / "justfile").read_text(encoding="utf-8").startswith("mine:")
    monkeypatch.chdir(repo)
    uninstall.main(["--project", "-y"])
    assert (repo / "justfile").exists(), "uninstall deleted a file the user wrote"


@pytest.mark.xfail(
    reason="wiring.link copies where symlinks are unavailable and records how: 'copy', but "
    "uninstall only unlinks symlinks, so on Windows every skill it installed stays behind.",
    strict=True,
)
def test_uninstall_removes_skills_that_were_copied_rather_than_linked(home):
    """Uninstall a machine where the skills were copied in, which is what Windows gets."""
    root = home / "skills"
    (root / "ai-spec").mkdir(parents=True)
    (root / "ai-spec" / "SKILL.md").write_text("copied", encoding="utf-8")
    wiring.write_json(
        wiring.receipt_path(), {"wrote": [{"path": str(root), "kind": "link", "how": "copy"}]}
    )
    uninstall.main(["-y"])
    assert not (root / "ai-spec").exists(), "a copied skill survived the uninstall"


def test_uninstall_removes_nothing_until_somebody_types_yes(home, tmp_path, keyboard):
    """Without -y the question is the whole safety. A consent check satisfied by the mere
    presence of a terminal rather than by the answer typed into it strips a machine's guards
    on the run somebody started to read the list."""
    keyboard("n")
    settings = tmp_path / "settings.json"
    wiring.write_json(settings, {"hooks": [{"command": wiring.command("PreToolUse")}]})
    wiring.write_json(
        wiring.receipt_path(),
        {"wrote": [{"path": str(settings), "kind": "guard", "how": "json_claude"}]},
    )
    before = settings.read_text(encoding="utf-8")
    assert uninstall.main([]) == 1
    assert settings.read_text(encoding="utf-8") == before, "it removed the entry anyway"


@pytest.mark.xfail(
    reason="init records the OpenCode plugin as kind 'guard', and strip_entries json.loads "
    "every guard file whose text holds the mark. That file is TypeScript, and it holds the "
    "mark because 'denied by ai-engineering' is its denial message, so uninstall raises "
    "JSONDecodeError on any machine with OpenCode — after it has already removed the skills.",
    strict=True,
)
def test_uninstall_survives_the_opencode_plugin_it_installed(home, tmp_path):
    """Uninstall a machine whose receipt lists the one entry that is not JSON."""
    plugin = tmp_path / "ai-engineering.ts"
    wiring.ts_opencode(plugin)
    wiring.write_json(
        wiring.receipt_path(),
        {"wrote": [{"path": str(plugin), "kind": "guard", "how": "ts_opencode"}]},
    )
    assert uninstall.main(["-y"]) == 0


@pytest.fixture
def pinned_repo(repo):
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text(
        skeletons.CONFIG_TOML.format(version=__version__), encoding="utf-8"
    )
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "pin"], check=True, capture_output=True)
    return repo


def test_update_never_runs_without_a_person_at_the_keyboard(pinned_repo, monkeypatch, capsys):
    """A change of governance is never silent. With no terminal — CI, a cron job, a wrapper
    script — update must refuse and leave the pin exactly as it found it."""
    monkeypatch.chdir(pinned_repo)
    pin = pinned_repo / ".ai" / "config.toml"
    before = pin.read_text(encoding="utf-8")
    assert update.main(["--to", "9.9.9"]) == 1
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
    assert update.main(flags) == 1
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
    assert update.main([]) == 1
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
    assert update.main(["--to", "9.9.9"]) == (0 if runs else 1)
    assert ('version = "9.9.9"' in pin.read_text(encoding="utf-8")) is runs


def test_update_rewrites_a_stale_entry_and_leaves_an_append_only_surface_alone(
    pinned_repo, home, keyboard, monkeypatch, capsys
):
    """When the interpreter moves, every entry still names the old one and every guard is off
    while the settings file still looks wired. update rewrites them — except Codex, whose
    trust is a hash of the whole handler and its position, where a rewrite would silently turn
    the entry off instead of on."""
    keyboard("y")
    monkeypatch.chdir(pinned_repo)
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
    wiring.write_json(codex, {"hooks": {"PreToolUse": [{"handlers": [{"command": unknown}]}]}})
    frozen = codex.read_text(encoding="utf-8")

    assert update.main(["--to", "9.9.9"]) == 0
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
