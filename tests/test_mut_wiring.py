"""What the writers actually write, where every file class actually is, and what doctor
actually prints.

These three files have no interesting arithmetic in them. What they have is names: a JSON
key, a config key, a filename, a line of a report. Every one of those names is read by
something outside this process — a coding agent's settings loader, git, a person deciding
whether they are protected — so a key spelled `HOOKS` instead of `hooks`, a timeout of
5001 instead of 5000, or a coverage line that says `advises` instead of `ADVISES` is a
silent failure on a real machine. The assertions here are exact for that reason.

Every test builds its own machine under tmp_path. Nothing may read or write the real
HOME, and nothing may touch this checkout.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from ai_engineering import __version__, doctor, outcome, paths, wiring

emit = paths.load("_emit")


@pytest.fixture
def machine(tmp_path, monkeypatch):
    """A laptop of this test's own: every ~ and the framework folder land in tmp_path."""
    fake = tmp_path / "home"
    (fake / ".ai-engineering" / "cache").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(fake))
    monkeypatch.setenv("USERPROFILE", str(fake))
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(fake / ".ai-engineering"))
    return fake


def undecidable(why: str):
    def fn(root):
        raise doctor.Undecidable(why)

    return fn


# ------------------------------------------------------------------ what gets written


def test_the_claude_entry_is_one_row_per_event_and_names_the_event_it_is_for(machine, tmp_path):
    """Claude Code reads this file by key. A row filed under the wrong event name, or a
    row that tells the dispatcher the wrong event, is a guard that never sees the call."""
    path = tmp_path / "settings.json"
    assert wiring.json_claude(path) == "merged"
    assert json.loads(path.read_text()) == {
        "hooks": {
            event: [
                {
                    "matcher": "*",
                    "hooks": [{"type": "command", "command": wiring.command(event)}],
                }
            ]
            for event in wiring.EVENTS
        }
    }


def test_the_cursor_entry_is_fail_closed_and_covers_both_of_the_hooks_cursor_offers(
    machine, tmp_path
):
    """Cursor fails open unless failClosed is set, and it names its two hooks in camel
    case. Either one spelled differently is a guard that advises and never denies."""
    path = tmp_path / "hooks.json"
    assert wiring.json_cursor(path) == "failClosed: true"
    ran = wiring.command("PreToolUse")
    assert json.loads(path.read_text()) == {
        "version": 1,
        "failClosed": True,
        "hooks": {
            "beforeShellExecution": [{"command": ran}],
            "beforeReadFile": [{"command": ran}],
        },
    }


def test_the_cursor_writer_keeps_the_rows_it_did_not_write_and_replaces_the_ones_it_did(
    machine, tmp_path
):
    """Cursor's hooks file belongs to whoever else is using it too. Ours is filtered out by
    name and put back; everything else stays where it was. Reading the wrong key here
    silently deletes somebody else's hook and duplicates ours on the next install."""
    path = tmp_path / "hooks.json"
    theirs = {"command": "somebody else's hook"}
    path.write_text(
        json.dumps({"hooks": {"beforeShellExecution": [theirs]}}),
        encoding="utf-8",
    )
    ran = wiring.command("PreToolUse")
    wiring.json_cursor(path)
    wiring.json_cursor(path)
    hooks = json.loads(path.read_text())["hooks"]
    assert hooks["beforeShellExecution"] == [theirs, {"command": ran}]
    assert hooks["beforeReadFile"] == [{"command": ran}]


def test_the_cursor_writer_keeps_a_schema_version_the_file_already_declared(machine, tmp_path):
    """Version 1 is the default for a file that has none. Overwriting a version Cursor
    itself wrote would be us deciding the schema of somebody else's file."""
    path = tmp_path / "hooks.json"
    path.write_text(json.dumps({"version": 3}), encoding="utf-8")
    wiring.json_cursor(path)
    assert json.loads(path.read_text())["version"] == 3


def test_the_copilot_file_holds_exactly_one_pretooluse_command_and_nothing_else(machine, tmp_path):
    """Copilot merges its own file with five other sources, so what we write is the whole
    of our contribution. Its event key is camel case and ours alone."""
    path = tmp_path / "hooks" / "ai-eng.json"
    assert wiring.json_copilot(path) == "own file"
    assert json.loads(path.read_text()) == {
        "hooks": {"preToolUse": [{"type": "command", "command": wiring.command("PreToolUse")}]}
    }


def test_the_codex_handler_is_appended_whole_after_a_stranger_and_never_written_twice(
    machine, tmp_path
):
    """Codex keys its trust hash on the handler's contents and its position. Changing a
    field, or inserting above somebody else's group, silently invalidates their trust —
    and a second copy of our own group is a blocking guard firing twice."""
    path = tmp_path / "hooks.json"
    stranger = {"hooks": [{"command": "somebody else's hook"}]}
    path.write_text(json.dumps({"hooks": {"PreToolUse": [stranger]}}), encoding="utf-8")

    assert wiring.json_codex(path) == "appended, position 2 of 2"
    groups = json.loads(path.read_text())["hooks"]["PreToolUse"]
    assert groups[0] == stranger
    assert groups[1] == {
        "hooks": [
            {
                "type": "command",
                "command": wiring.command("PreToolUse"),
                "timeout": 5,
                "statusMessage": "ai-engineering guards",
                "async": False,
            }
        ]
    }
    assert wiring.json_codex(path) == "already present at position 2 of 2"


def test_write_json_creates_the_folders_above_it_and_writes_two_space_indent(tmp_path):
    """A settings file nobody has created yet has no folder either. The indent is not
    decoration: these files are read and edited by people, and a one-line blob is a file
    somebody reformats by hand and then cannot diff."""
    path = tmp_path / "a" / "b" / "c.json"
    wiring.write_json(path, {"one": 1, "two": {"three": 3}})
    assert path.read_text() == '{\n  "one": 1,\n  "two": {\n    "three": 3\n  }\n}\n'


def test_the_opencode_plugin_is_the_shipped_source_with_this_machine_filled_in(machine, tmp_path):
    """The plugin is a template with three holes: the interpreter, the dispatcher and the
    heartbeat file doctor reads to tell a loaded plugin from a silently dropped one. A
    hole filled with the wrong path is a plugin that reports nothing forever."""
    path = tmp_path / "plugins" / "nested" / "ai-engineering.ts"
    assert wiring.ts_opencode(path) == "plugin written"
    want = (paths.surfaces() / "opencode.ts").read_text(encoding="utf-8")
    for token, value in (
        ('"__PYTHON__"', sys.executable),
        ('"__CHAIN__"', str(paths.hooks() / "chain.py")),
        ('"__BEAT__"', str(paths.home() / "cache" / "opencode-heartbeat")),
    ):
        want = want.replace(token, json.dumps(value))
    assert path.read_text(encoding="utf-8") == want
    assert wiring.ts_opencode(path) == "plugin written"


def test_a_windows_interpreter_path_is_escaped_rather_than_pasted(machine, tmp_path, monkeypatch):
    """Every path on the machine that runs this suite is POSIX, so pasting one straight
    into a TypeScript string and escaping it first produce byte-identical files — the test
    above passes either way and agreed with the defect for as long as it existed. A Windows
    path tells them apart: `C:\\Users\\me` pasted raw yields `\\U`, an invalid escape, and the
    plugin fails to parse. To the operator that reads as OpenCode quietly running without a
    guard, which is the exact failure this whole surface exists to prevent."""

    monkeypatch.setattr(sys, "executable", r"C:\Users\me\python.exe")
    path = tmp_path / "ai-engineering.ts"
    assert wiring.ts_opencode(path) == "plugin written"
    assert r'"C:\\Users\\me\\python.exe"' in path.read_text(encoding="utf-8")


# ------------------------------------------------------------------ who gets written to


def test_asking_for_one_surface_by_name_returns_that_one_and_keeps_looking_past_the_rest(
    machine,
):
    """`init --only cursor` must wire Cursor and nothing else. Cursor is not the first row
    of the table, so a filter that stops at the first row it does not want finds nothing."""
    for folder in (".claude", ".cursor", ".codex"):
        (machine / folder).mkdir()
    assert [surface["id"] for surface in wiring.detect(only=["cursor"])] == ["cursor"]
    assert {surface["id"] for surface in wiring.detect()} == {
        "claude-code",
        "cursor",
        "codex-cli",
    }


def test_a_surface_with_no_writer_is_named_and_the_surfaces_after_it_are_still_wired(
    machine, tmp_path
):
    """Zed and pi need no file written, which is a result to report, not a reason to stop
    halfway down the table."""
    settings = str(tmp_path / "hooks.json")
    surfaces = [
        {"name": "Zed", "writer": "none", "settings": ""},
        {"name": "Cursor", "writer": "json_cursor", "settings": settings},
    ]
    assert wiring.install_guards(surfaces) == [
        ("Zed", "", "no wiring needed"),
        ("Cursor", settings, "failClosed: true"),
    ]


# ------------------------------------------------------------------ skills on disk


def test_link_repoints_a_symlink_whose_target_has_been_deleted(tmp_path):
    """A skill root left dangling by an uninstall is the normal state of a reinstall. It
    has to be pointed back at the wheel, not crashed over."""
    source = tmp_path / "wheel" / "ai-fake"
    source.mkdir(parents=True)
    target = tmp_path / "roots" / "ai-fake"
    target.parent.mkdir()
    target.symlink_to(tmp_path / "deleted-long-ago")

    assert wiring.link(source, target) == "symlink"
    assert target.resolve() == source.resolve()


def test_link_copies_the_whole_tree_where_the_platform_refuses_to_make_a_symlink(
    tmp_path, monkeypatch
):
    """Windows drops symlink creation without developer mode. Copying is the plan there,
    not an embarrassed plan B, and a copy that lands an empty folder is the exact failure
    a competing product shipped."""
    source = tmp_path / "wheel" / "ai-fake"
    (source / "inner").mkdir(parents=True)
    (source / "inner" / "SKILL.md").write_text("the skill", encoding="utf-8")

    def refuse(self, *args, **kwargs):
        raise NotImplementedError("this platform has no symlinks")

    monkeypatch.setattr(Path, "symlink_to", refuse)
    target = tmp_path / "roots" / "ai-fake"
    assert wiring.link(source, target) == "copy"
    assert (target / "inner" / "SKILL.md").read_text(encoding="utf-8") == "the skill"


def test_the_skills_receipt_names_the_home_root_and_every_surface_root_it_placed(
    machine, tmp_path, monkeypatch
):
    """The receipt is how uninstall knows what is ours and how doctor knows a skill root
    stopped resolving. A row with the wrong kind is a row neither of them acts on."""
    wheel = tmp_path / "wheel-skills"
    (wheel / "ai-fake").mkdir(parents=True)
    (wheel / "ai-fake" / "SKILL.md").write_text("the skill", encoding="utf-8")
    monkeypatch.setattr(paths, "skills", lambda: wheel)

    rows = wiring.install_skills()
    real = paths.home() / "skills"
    assert rows[0] == {"path": str(real), "kind": "skills", "how": "wheel"}
    assert (real / "ai-fake" / "SKILL.md").read_text(encoding="utf-8") == "the skill"
    roots = sorted({s["skills"] for s in wiring.table()["surface"] if s.get("skills")})
    assert rows[1:] == [
        {"path": str(wiring.expand(root)), "kind": "link", "how": "symlink"} for root in roots
    ]


def test_with_no_skills_to_place_the_receipt_says_none_rather_than_claiming_a_link(
    machine, tmp_path, monkeypatch
):
    """ "none" is the honest answer when nothing was placed. Claiming "symlink" would make
    doctor's assertion 13 look for a link that was never created."""
    empty = tmp_path / "no-skills"
    empty.mkdir()
    monkeypatch.setattr(paths, "skills", lambda: empty)
    rows = wiring.install_skills()
    assert [row["how"] for row in rows[1:]] == ["none"] * len(rows[1:])
    assert rows[1:]


# ------------------------------------------------------------------ the receipt and git


def test_the_receipt_is_machine_json_and_names_this_interpreter_and_these_guards(machine):
    """update rewrites every entry from these two values when the interpreter moves, and
    doctor's assertion 12 compares the guards path as text. Both are useless if either is
    absent or null."""
    assert wiring.receipt_path().name == "machine.json"
    wiring.record([])
    data = json.loads(wiring.receipt_path().read_text())
    assert re.fullmatch(r"[0-9a-f]{12}", data["machine_id"])
    assert data["version"] == __version__
    assert data["python"] == sys.executable
    assert data["hooks"] == str(paths.hooks())


def test_forgetting_a_row_leaves_every_other_row_and_the_head_fields(machine):
    """The way out this record never had. Spec 005 refused per-surface uninstall because of
    its absence, and then `uninstall` removed eight things and the next `init` read the log
    and called the machine ready."""
    rows = [
        {"path": "/roots/a/skills", "kind": "link", "how": "symlink"},
        {"path": "/roots/b/settings.json", "kind": "guard", "how": "json_claude"},
        {"path": "/repo/justfile", "kind": "project", "how": "written"},
    ]
    wiring.record(rows)
    wiring.forget(rows[:2])
    data = json.loads(wiring.receipt_path().read_text())
    assert data["wrote"] == rows[2:], "forget took the wrong rows"
    assert data["machine_id"]
    assert data["version"] == __version__, "forget ate the head fields"


def test_forgetting_matches_on_the_same_key_record_deduplicates_by(machine):
    """One path can hold two kinds — a skills root is both the store and a link target — so
    a retraction keyed on the path alone would take a row nobody asked it to."""
    store = {"path": "/home/skills", "kind": "skills", "how": "wheel"}
    linked = {"path": "/home/skills", "kind": "link", "how": "symlink"}
    wiring.record([store, linked])
    wiring.forget([{**linked, "how": "whatever the caller happened to have"}])
    assert json.loads(wiring.receipt_path().read_text())["wrote"] == [store]


def test_forgetting_a_row_that_was_never_there_is_not_an_error(machine):
    """`uninstall` calls this for what it removed, and a surface that was gone before it
    started is a row it removed nothing for. The caller is saying "this is gone"."""
    kept = {"path": "/roots/a/skills", "kind": "link", "how": "symlink"}
    wiring.record([kept])
    wiring.forget([{"path": "/roots/never", "kind": "guard", "how": "json_claude"}])
    assert json.loads(wiring.receipt_path().read_text())["wrote"] == [kept]


def test_a_receipt_nobody_can_parse_is_never_written_over(machine):
    """The one that loses data rather than lying about it. `record` reads, appends and
    writes; while `read_json` answered {} to a file it could not parse, one interrupted
    write made every row vanish on the next `init` — including the project rows, which are
    the only thing telling `uninstall` which justfile in somebody's repository is ours.

    Measured before this fix: three rows in, one truncation, one row out."""
    real = [
        {"path": "/repo/justfile", "kind": "project", "how": "written"},
        {"path": "/repo/CLAUDE.md", "kind": "project", "how": "written"},
    ]
    wiring.record(real)
    body = wiring.receipt_path().read_text()
    wiring.receipt_path().write_text(body[: len(body) // 2])

    with pytest.raises(wiring.Unreadable, match="machine.json"):
        wiring.receipt()
    with pytest.raises(wiring.Unreadable):
        wiring.record([{"path": "/x", "kind": "guard", "how": "json_claude"}])
    assert wiring.receipt_path().read_text() == body[: len(body) // 2], (
        "record wrote over a receipt it could not read"
    )


def test_a_receipt_that_was_never_written_is_empty_rather_than_undecidable(machine):
    """Absent and unreadable are different answers, and only one of them is a refusal:
    every first run on every machine reads a receipt that is not there."""
    assert not wiring.receipt_path().exists()
    assert wiring.receipt() == {}


def test_a_broken_receipt_stops_one_assertion_and_not_the_diagnosis(machine, capsys):
    """A doctor that dies on one unreadable file tells you nothing about the other
    nineteen. Undecidable is the answer it already has for this.

    A surface has to be installed for assertion 13 to get as far as the receipt: with none,
    it stops at its own Undecidable one line earlier and the record is never opened."""
    (machine / ".claude" / "skills").mkdir(parents=True)
    wiring.record([{"path": "/roots/ai-fake", "kind": "link", "how": "symlink"}])
    wiring.receipt_path().write_text("{ not json")
    doctor.main([])
    text = capsys.readouterr().out
    assert "could not evaluate" in text
    assert "machine.json is not readable as JSON" in text
    assert "Every symlink resolves" in text


def test_the_telemetry_half_never_writes_over_a_receipt_it_could_not_read(machine):
    """The second route to the same loss, and the one that could fire from a guard. It
    caught bare Exception around a read and answered by saving `{"wrote": []}` over the
    file — from the half of the tree whose decorator is named for failing open and never
    opining. A session-local id costs nothing; the file is a person's to look at."""
    emit = paths.load("_emit")
    wiring.record([{"path": "/repo/justfile", "kind": "project", "how": "written"}])
    wiring.receipt_path().write_text("{ torn")
    assert re.fullmatch(r"[0-9a-f]{12}", emit.machine_id())
    assert wiring.receipt_path().read_text() == "{ torn", "telemetry wrote over the record"


def test_a_receipt_that_is_absent_is_the_one_case_telemetry_may_create(machine):
    """The other half: a first run has no receipt and the machine still needs an id."""
    emit = paths.load("_emit")
    assert not wiring.receipt_path().exists()
    mid = emit.machine_id()
    assert json.loads(wiring.receipt_path().read_text()) == {
        "machine_id": mid,
        "created": json.loads(wiring.receipt_path().read_text())["created"],
        "wrote": [],
    }


def test_every_verb_stops_on_a_file_it_cannot_parse_and_names_it(machine, capsys, monkeypatch):
    """One branch in `cli.main`, because every verb that writes reads first. Without it the
    refusal reaches a person as a traceback, which reads as a crash rather than as a file
    they have to look at."""
    from ai_engineering import cli

    wiring.record([{"path": "/repo/justfile", "kind": "project", "how": "written"}])
    wiring.receipt_path().write_text("{ torn")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    assert cli.main(["uninstall", "-y"]) == 1
    text = capsys.readouterr().out
    assert "install receipt is missing, partial, corrupt or ambiguous" in text
    assert "Nothing removed." in text
    assert wiring.receipt_path().read_text() == "{ torn"


def test_a_later_run_keeps_the_rows_it_did_not_touch_and_replaces_the_ones_it_did(machine):
    """The receipt answers "did we write this file". Losing a row makes uninstall walk
    past something of ours; duplicating one makes doctor report the same broken root
    twice."""
    linked = {"path": "/roots/ai-fake", "kind": "link", "how": "symlink"}
    placed = {"path": "/home/skills", "kind": "skills", "how": "wheel"}
    wiring.record([linked])
    wiring.record([placed])
    wiring.record([{**linked, "how": "copy"}])
    wrote = json.loads(wiring.receipt_path().read_text())["wrote"]
    assert wrote == [placed, {**linked, "how": "copy"}]


def test_the_machine_id_is_written_once_and_every_later_run_keeps_it(machine):
    """Deleting it is how a person says "treat this as a new machine". A run that rewrote
    it on its own would make every install look like a first install."""
    wiring.record([])
    first = json.loads(wiring.receipt_path().read_text())["machine_id"]
    wiring.record([])
    assert json.loads(wiring.receipt_path().read_text())["machine_id"] == first


def test_wire_git_sets_three_keys_git_itself_can_read_back_out_of_this_repository(
    machine, tmp_path
):
    """`command -v ai-eng` proves a binary exists, never that it is this one, so pre-push
    reads ai.eng to find the CLI that installed it. A key under the wrong name is a hook
    that refuses every push."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)

    assert wiring.wire_git(root) == str(paths.git_hooks())
    for key, want in (
        ("core.hooksPath", str(paths.git_hooks())),
        ("ai.managed", "true"),
        ("ai.eng", f"{sys.executable} -m ai_engineering.cli"),
    ):
        got = subprocess.run(
            ["git", "-C", str(root), "config", "--local", "--get", key],
            capture_output=True,
            text=True,
        )
        assert got.stdout.strip() == want, key


def test_a_git_config_that_failed_stops_the_install_instead_of_reporting_a_hooks_path(
    tmp_path,
):
    """Outside a repository every one of these writes fails. Without check=True the
    installer swallows all three and still returns the path it never wrote."""
    not_a_repo = tmp_path / "plain-folder"
    not_a_repo.mkdir()
    with pytest.raises(subprocess.CalledProcessError):
        wiring.wire_git(not_a_repo)


# ------------------------------------------------------------------ where things live


def test_every_file_class_is_spelled_the_way_the_wheel_ships_it():
    """These names are written verbatim into other people's settings files and compared as
    text by doctor. A case-different spelling opens the right file on a Mac and vanishes
    on a Linux runner."""
    assert paths.hooks().name == "hooks"
    assert paths.git_hooks().name == "git-hooks"
    assert paths.policy("surfaces.toml").parent.name == "policy"
    assert paths.surfaces().name == "surfaces"
    assert paths.skills().name == "skills"
    assert paths.skills().parent.name in ("ai_engineering", ".agents")
    assert sorted(p.name for p in paths.skills().glob("ai-*"))


def test_load_puts_the_guard_directory_first_on_the_path_and_only_ever_once(monkeypatch):
    """The guards are imported by file, not by name, and their directory goes to the front
    so a same-named module in site-packages cannot shadow one. Re-inserting it on every
    call would grow sys.path for the life of the process."""
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != str(paths.hooks())])
    monkeypatch.delitem(sys.modules, "_otlp", raising=False)

    module = paths.load("_otlp")
    assert sys.path[0] == str(paths.hooks())
    assert module.__name__ == "_otlp"
    assert Path(module.__file__) == paths.hooks() / "_otlp.py"
    assert callable(module.probe)
    assert sys.modules["_otlp"] is module

    monkeypatch.delitem(sys.modules, "_otlp", raising=False)
    paths.load("_otlp")
    assert sys.path.count(str(paths.hooks())) == 1


# ------------------------------------------------------------------ the coverage line


def test_the_coverage_line_says_exactly_what_each_surface_does_on_this_machine(
    machine, tmp_path, monkeypatch
):
    """This is the honesty layer, and the whole product is the claim that it never reads
    green for something nobody proved. Installed-but-inert and installed-but-unrun are
    different sentences on purpose, and both of them are not BLOCKS.

    A surface added to the table has to be added here by hand. That is the point: a new
    row silently inheriting somebody else's wording is the failure this line prevents.

    The four surfaces below are wired, and until spec 008 they were not: this made the
    directories and nothing else, and every word here came out of the vendor's folder
    existing plus a static flag in the table. The verdicts are unchanged and now they cost
    an entry in a settings file, which is what they were always claiming to mean."""
    monkeypatch.chdir(tmp_path)
    for folder in (".claude", ".codex", ".cursor", ".pi", ".config/opencode"):
        (machine / folder).mkdir(parents=True)
    for surface in wiring.table()["surface"]:
        if surface["writer"] != "none" and surface["id"] in {
            "claude-code",
            "opencode",
            "codex-cli",
            "cursor",
        }:
            wiring.WRITERS[surface["writer"]](wiring.expand(surface["settings"]))
    root = tmp_path / "repo"
    (root / ".ai").mkdir(parents=True)
    (root / ".ai" / "config.toml").write_text(
        '[framework]\nversion = "0.0.0-not-this-wheel"\n', encoding="utf-8"
    )

    want = [
        # UNPROVEN, and it is the point of the wave: the word is earned from an
        # enforcement receipt now, and this repository has never written one.
        ("T2", "claude-code", "UNPROVEN", "installed and wired, but no denial has ever run here"),
        (
            "T2",
            "opencode",
            "INERT",
            "the plugin never reported loading; a malformed one is dropped in silence",
        ),
        (
            "T2",
            "codex-cli",
            "INERT",
            "installed and unapproved — type /hooks in Codex to approve it",
        ),
        ("T2", "cursor", "UNPROVEN", "installed and wired, but no denial has ever run here"),
        ("T2", "copilot-cli", "UNPROVEN", "not installed here, so nothing about it is proven"),
        ("T2", "vscode-copilot", "UNPROVEN", "not installed here, so nothing about it is proven"),
        ("T3", "pi", "ADVISES", "reads the skills; it cannot deny a call"),
        ("T3", "zed", "UNPROVEN", "not installed here, so nothing about it is proven"),
    ]
    assert doctor.coverage(root) == [
        f"  PIN  wheel {__version__} = pinned 0.0.0-not-this-wheel  MISMATCH",
        *[f"  {tier:<4} {name:<16} {word:<9} {why}" for tier, name, word, why in want],
        # Written out and not `*doctor.OPEN`: spread from the module, both sides of this
        # comparison move together and the sentence can be emptied with the suite green.
        "  OPEN  --no-verify from your own shell walks past every row above, and so does",
        "        anything that never asks a surface. Only a required check on the server",
        "        (T0) stops those, and nothing on this machine can give you one.",
        "  OPEN  self_protect matches shell commands as text: `cd hooks && rm x`,",
        "        `xargs rm`, `env rm`, `patch` and a relative path all get through.",
    ]


@pytest.mark.parametrize("word", ["BLOCKS", "INERT", "UNPROVEN", "ADVISES", "T2", "T3"])
def test_every_word_a_coverage_row_prints_is_defined_on_the_screen_that_prints_it(word):
    """What "no entiendo nada" meant. Every one of these is exact and none of them was
    defined anywhere the person running the command would see, so eight rows of it read as
    noise. A word that can reach a row and not the legend is a word nobody can look up at
    the moment they need to."""
    assert word in doctor.COLOURS or word.startswith("T"), f"{word} has no colour"
    assert any(f"  {word} " in line or f"· {word} " in line for line in doctor.LEGEND), word


def test_the_pin_line_reads_ok_only_when_this_wheel_is_the_one_the_repository_pinned(
    machine, tmp_path, monkeypatch
):
    """A repository that pins nothing is not a repository that pins us. The em dash is
    what "nothing is pinned here" looks like, and it is never OK."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "repo"
    (root / ".ai").mkdir(parents=True)
    pin = root / ".ai" / "config.toml"
    pin.write_text(f'[framework]\nversion = "{__version__}"\n', encoding="utf-8")
    assert doctor.coverage(root)[0] == f"  PIN  wheel {__version__} = pinned {__version__}  OK"

    pin.unlink()
    assert doctor.coverage(root)[0] == f"  PIN  wheel {__version__} = pinned —  MISMATCH"


# ------------------------------------------------------------------ the report itself


def test_doctor_names_itself_and_explains_both_of_its_flags_when_asked(capsys, monkeypatch):
    """The help text is the only place a person learns that --ci runs a subset. A flag
    with no sentence beside it is a flag nobody uses, and --ci unused means CI runs the
    checks that cannot pass there and somebody switches doctor off. The sentence has to
    start where the flag's column ends: anything printed in front of it is not help."""
    monkeypatch.setenv("COLUMNS", "200")
    with pytest.raises(SystemExit) as bad:
        doctor.main(["--not-a-flag"])
    assert bad.value.code == 2
    assert "usage: ai-eng doctor" in capsys.readouterr().err

    with pytest.raises(SystemExit) as asked:
        doctor.main(["--help"])
    assert asked.value.code == 0
    out = capsys.readouterr().out
    assert re.search(r"--ci +only the checks a runner can answer\n", out)
    assert re.search(r"--paths +print where every file class lives\n", out)


def test_paths_prints_the_record_of_the_repository_doctor_actually_found(
    machine, tmp_path, monkeypatch, capsys
):
    """The record is per repository. Printing the one for "no repository" while standing
    inside a repository sends somebody to read an empty file and conclude nothing ran."""
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    result = doctor.main(["--paths"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    out = capsys.readouterr().out
    assert f"  record        {emit.chain_path(root)}" in out
    assert str(emit.chain_path(None)) not in out


def test_the_report_prints_one_line_per_state_and_hands_every_check_the_repository(
    monkeypatch, capsys
):
    """Three states, counted separately, each named in the output. A check that could not
    run must never land in the passed count, a family heading must appear once above its
    checks, and every check has to be handed the repository doctor found rather than
    nothing."""
    here = Path("/somewhere/a-repository")
    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [
            (1, "The pin", "first", True, lambda root: None),
            (2, "The pin", "second", True, lambda root: f"root is {root}"),
            (3, "The record", "third", True, undecidable("nothing was ever written")),
            (4, "The record", "fourth", True, undecidable("nothing was ever written")),
            (5, "The outside", "fifth", True, lambda root: "the server said no"),
        ],
    )
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: [f"  surfaces for {root}"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: here)

    result = doctor.main([])
    assert type(result) is outcome.Execution and result.outcome == "FAIL"
    assert [fact.status for fact in result.checks[:5]] == [
        "INCOMPLETE",
        "INCOMPLETE",
        "PASS",
        "FAIL",
        "FAIL",
    ]
    out = capsys.readouterr().out
    assert out.count("\nThe pin\n") == 1
    assert out.count("\nThe record\n") == 1
    assert out.count("\nThe outside\n") == 1
    assert "   1  ok       first" in out
    assert f"   2  FAIL     second\n      root is {here}" in out
    assert "   3  ?        third\n      could not evaluate: nothing was ever written" in out
    assert "   4  ?        fourth" in out
    assert "   5  FAIL     fifth\n      the server said no" in out
    assert "\nCoverage — where a call can actually be stopped, and where it cannot\n" in out
    assert f"  surfaces for {here}" in out
    # Every failure gets one line or the other, never neither: number 2 is in FIXES and
    # number 5 is not, and the verdict counts the two of them into different columns.
    assert f"      fix: {doctor.FIXES[2]}" in out
    assert out.count("      you: a person does this one") == 1
    assert "FAILED" in out
    assert "fixable now     1   ai-eng doctor --fix" in out
    assert "needs a person  1   assertion 5" in out
    assert "1 passed · 2 failed · 2 not evaluated" in out
    # The verdict is last, and it is last on purpose: the sentence that used to end this
    # report was one unframed line under eight rows of coverage, and it was read as a ninth.
    assert out.rstrip().endswith("╯")
    assert "Not evaluated — 2 of 5 could not be answered here" in out
    assert "  None of these is a pass. Not evaluated is never green." in out


def test_ci_leaves_the_local_only_checks_unrun_and_still_runs_everything_else(monkeypatch, capsys):
    """A skip is counted as not evaluated, never as a pass, and it does not end the run.
    Both skipped checks below return a failure, so if either one ran the exit code is 1."""
    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [
            (1, "The wiring", "needs a working copy", False, lambda root: "it ran anyway"),
            (2, "The wiring", "needs one too", False, lambda root: "it ran anyway"),
            (3, "The wiring", "a runner can answer this", True, lambda root: None),
        ],
    )
    monkeypatch.setattr(doctor, "coverage", lambda root, **_: ["  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)

    result = doctor.main(["--ci"])
    assert type(result) is outcome.Execution and result.outcome == "INCOMPLETE"
    assert [fact.status for fact in result.checks[:3]] == ["SKIPPED", "SKIPPED", "PASS"]
    out = capsys.readouterr().out
    assert "   1  SKIPPED  needs a working copy — needs a real working copy" in out
    assert "   3  ok       a runner can answer this" in out
    assert "1 passed · 0 failed · 2 not evaluated" in out


def test_only_the_git_hook_assertion_is_one_a_runner_cannot_answer():
    """--ci exists so a runner skips the checks it genuinely cannot answer. If checks
    defaulted to local-only, --ci would quietly measure almost nothing and still be
    green."""
    assert [number for number, _, _, in_ci, _ in doctor.CHECKS if not in_ci] == [11]


def test_a_torn_line_in_the_middle_of_the_record_does_not_hide_the_lines_after_it(
    machine, tmp_path, monkeypatch
):
    """A crash mid-append leaves half a line behind. Every check that reads the record —
    the hash chain, the signal ratio, double decisions — would then judge a prefix of it
    and report on evidence that stops at the tear."""
    monkeypatch.chdir(tmp_path)
    path = emit.chain_path(None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"seq": 1}\n{"seq": half-written\n{"seq": 2}\n', encoding="utf-8")
    assert [event["seq"] for event in doctor.events(None)] == [1, 2]


def test_a_suite_that_never_ran_here_is_named_as_unevaluated_rather_than_passed(machine):
    """No result file is not a green result file. The sentence is the whole value of the
    third state: it tells the reader what to do about it."""
    with pytest.raises(doctor.Undecidable) as why:
        doctor.suite_result()
    assert str(why.value) == "the adversarial suite has never written a result here"


def test_a_router_is_generated_hashed_and_recorded_for_the_surface_that_declares_a_root(
    machine, tmp_path, monkeypatch
):
    """EP-014, EP-017, EP-205, EP-212. Spec 011 asks for generated `/ai-*` routers with a
    receipt, a hash, a doctor check and an uninstall path — and nothing generated a router at
    all. Four properties, and the receipt with the digest in it is what makes this an install
    rather than a file drop: without it, nothing downstream can tell a router nobody touched
    from one somebody rewrote, and `uninstall` would delete either.

    Generated, so the router carries the skill's own description: a router that restated any
    of the skill body would be the second normative layer EP-071 forbids, kept in step by
    hand."""

    commands = tmp_path / "commands"
    surface = {"id": "invented", "commands": str(commands), "skills": ""}

    written = wiring.install_routers([surface])

    assert written, "no router was written for a surface that declares a command root"
    for row in written:
        assert row["kind"] == "router"
        target = Path(row["path"])
        assert target.is_file()
        assert target.parent == commands
        marker, _, digest = row["how"].partition(" ")
        assert marker == "generated" and len(digest) == 64
        body = target.read_text(encoding="utf-8")
        assert hashlib.sha256(body.encode("utf-8")).hexdigest() == digest
        # The router names its skill and forwards the request, and nothing else.
        assert f"Use the `{target.stem}` skill" in body
        assert "$ARGUMENTS" in body

    names = {Path(row["path"]).stem for row in written}
    assert names == {skill.name for skill in paths.skills().glob("ai-*")}


def test_a_surface_with_no_command_root_gets_no_router_and_no_invented_path(machine, tmp_path):
    """Seven of the eight surfaces declare no command root, and the installer writes nothing
    for them rather than guessing. A router in a directory whose convention we invented lands
    where a person does not expect it, does nothing, and has to be found by hand — which is
    worse than the absence, and the absence is what `doctor` reports."""

    assert wiring.install_routers([{"id": "invented", "commands": "", "skills": ""}]) == []
    assert wiring.install_routers([{"id": "invented", "skills": ""}]) == []


def test_uninstall_removes_a_router_it_wrote_and_leaves_one_somebody_edited(machine, tmp_path):
    """The half that makes a hash worth recording. A generated router is ours only while it
    is still the bytes we generated: a file somebody edited is theirs now — they wanted
    something we did not write — and removing it would be this installer deciding that its
    own version of a person's file is the real one.

    Both directions in one fixture, because the interesting failure is the asymmetric one:
    a rule that removes everything and a rule that removes nothing both look tidy in a test
    that only asserts one case."""

    from ai_engineering import uninstall

    commands = tmp_path / "commands"
    written = wiring.install_routers([{"id": "invented", "commands": str(commands), "skills": ""}])
    ours, theirs = written[0], written[1]

    edited = Path(theirs["path"])
    edited.write_text("I wanted something else here\n", encoding="utf-8")

    assert uninstall._owned(ours, None) is True
    assert uninstall._owned(theirs, None) is False
    # And gone already is the state uninstall was trying to reach, not a refusal.
    Path(ours["path"]).unlink()
    assert uninstall._owned(ours, None) is True


def test_a_receipt_row_naming_a_router_outside_a_declared_command_root_is_refused(machine):
    """`canonical` is a closed allow-list of what this installer may remove, and it derives
    the path rather than trusting the row. Without that, a receipt saying `router` over an
    arbitrary path turns uninstall into an unlink of anything on the machine."""

    from ai_engineering import uninstall

    real = wiring.expand("~/.claude/commands") / "ai-spec.md"
    digest = "0" * 64
    assert uninstall.canonical(
        {"path": str(real), "kind": "router", "how": f"generated {digest}"}, None
    ) == {"path": str(real), "kind": "router", "how": f"generated {digest}"}

    for row in (
        {"path": "/etc/passwd", "kind": "router", "how": f"generated {digest}"},
        {"path": str(real), "kind": "router", "how": "generated not-a-digest"},
        {"path": str(real), "kind": "router", "how": "copied " + digest},
        {
            "path": str(real.parent / "not-a-skill.md"),
            "kind": "router",
            "how": f"generated {digest}",
        },
    ):
        assert uninstall.canonical(row, None) is None, row


# ── the five functions that carried 79 of the surviving mutants ─────────────────────
#
# `_described`, `install_routers`, `wire_git`, `linked` and `wired`. What they have in
# common is that each answers a question about the machine, and each has one answer that
# looks like a smaller version of the truth: a description that is really a fold marker, a
# link count that is really a row count, an anchor that names an interpreter which cannot
# run the thing it is anchored to. None of those show up as a crash.


@pytest.mark.parametrize(
    ("frontmatter", "expected"),
    [
        pytest.param("description: on one line\n", "on one line", id="inline"),
        pytest.param(
            "description: >-\n  folded over\n  two lines\n",
            "folded over two lines",
            id="folded with >-",
        ),
        pytest.param("description: >\n  folded\n", "folded", id="folded with >"),
        pytest.param("description: |\n  literal\n", "literal", id="literal with |"),
        pytest.param("description: |-\n  literal\n", "literal", id="literal with |-"),
    ],
)
def test_a_router_takes_the_skill_s_own_words_however_the_skill_folds_them(
    tmp_path, frontmatter, expected
):
    """Five ways YAML lets somebody write the same sentence. Reading only the first line
    answers `>-` for four of them, and a router that describes `/ai-plan` as ">-" is a
    router that tells a person nothing the command they typed had not already told them."""

    skill = tmp_path / "ai-thing"
    skill.mkdir()
    (skill / "SKILL.md").write_text(f"---\nname: ai-thing\n{frontmatter}---\n\n# body\n")

    assert wiring._described(skill) == expected


def test_a_skill_with_no_description_at_all_is_described_by_its_own_name(tmp_path):
    """Not an empty string. A router whose description is blank renders a heading with
    nothing under it, and the surface that loads it shows an empty row rather than a
    missing one — which is the harder of the two to notice."""

    skill = tmp_path / "ai-bare"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: ai-bare\n---\n\n# body\n")

    assert wiring._described(skill) == "ai-bare"


def test_a_fold_marker_with_nothing_indented_under_it_falls_back_to_the_name(tmp_path):
    skill = tmp_path / "ai-empty"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: ai-empty\ndescription: >-\nlicense: x\n---\n")

    assert wiring._described(skill) == "ai-empty"


def test_a_surface_with_no_commands_root_gets_no_router_rather_than_a_guessed_one(
    tmp_path, machine
):
    """Writing into a directory whose convention was guessed is worse than not writing: the
    file lands somewhere nobody looks, does nothing, and has to be found by hand later."""

    with_root = {"name": "A", "commands": str(tmp_path / "cmds"), "writer": "none"}
    without = {"name": "B", "writer": "none"}

    written = wiring.install_routers([with_root, without])

    assert {row["path"] for row in written}
    assert all(str(tmp_path / "cmds") in row["path"] for row in written)


def test_every_router_records_the_digest_of_exactly_what_was_written(tmp_path, machine):
    """`how` is what lets `doctor` tell a router nobody touched from one somebody edited,
    and what lets `uninstall` refuse to delete a file that is no longer ours. A digest of
    anything other than the bytes on disk makes both of those answer about a different
    file."""

    written = wiring.install_routers([{"name": "A", "commands": str(tmp_path / "c")}])

    assert written
    for row in written:
        body = Path(row["path"]).read_bytes()
        assert row["kind"] == "router"
        assert row["how"] == f"generated {hashlib.sha256(body).hexdigest()}"


def test_the_git_anchor_is_not_written_when_the_cli_it_would_name_cannot_answer(
    tmp_path, monkeypatch
):
    """The state this machine was actually found in: an editable install whose `.pth` points
    at a deleted worktree. The interpreter is alive, `ai_engineering.cli` is not, and an
    anchor written from that names something that looks configured and answers nothing."""

    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    monkeypatch.setattr(
        wiring,
        "cli_answers",
        lambda *a, **k: subprocess.CompletedProcess([], 1, stdout="", stderr="No module named x"),
    )

    with pytest.raises(wiring.Unreadable) as refused:
        wiring.wire_git(root)

    assert "--version" in str(refused.value)
    written = subprocess.run(
        ["git", "-C", str(root), "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert written.stdout.strip() == "", "the anchor was written after the proof failed"


def test_an_answer_that_is_not_ours_is_refused_even_with_a_zero_exit(tmp_path, monkeypatch):
    """`command -v ai-eng` proves a binary exists and never that it is this one. An older
    install on the PATH exits zero and has no `accept` verb, and pre-push then refused every
    push in the repository it had just been installed into."""

    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    monkeypatch.setattr(
        wiring,
        "cli_answers",
        lambda *a, **k: subprocess.CompletedProcess(
            [], 0, stdout="somebody-elses-tool 9.9\n", stderr=""
        ),
    )

    with pytest.raises(wiring.Unreadable):
        wiring.wire_git(root)


def test_a_cli_that_cannot_be_executed_at_all_is_a_refusal_and_not_a_traceback(
    tmp_path, monkeypatch
):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)

    def explode(*args, **kwargs):
        raise OSError(2, "no such file")

    monkeypatch.setattr(wiring, "cli_answers", explode)

    with pytest.raises(wiring.Unreadable) as refused:
        wiring.wire_git(root)
    assert "FileNotFoundError" in str(refused.value)


def test_a_settings_file_that_is_there_and_unreadable_does_not_read_as_absent(
    tmp_path, monkeypatch
):
    """`wired` decides from the file rather than from the receipt, on purpose. Bytes that
    are not valid UTF-8 are replaced rather than raising, because a settings file another
    tool wrote in some other encoding is still a file whose contents can be searched for
    our signature — and answering "not wired" for it would offer to wire it again."""

    settings = tmp_path / "settings.json"
    settings.write_bytes(b'{"hooks": "\xff\xfe"}')
    monkeypatch.setattr(
        wiring,
        "detect",
        lambda only=None: [{"name": "S", "writer": "json_claude", "settings": str(settings)}],
    )

    on, off = wiring.wired()

    assert (on, [row["name"] for row in off]) == ([], ["S"])


def test_five_surfaces_sharing_one_skills_root_are_one_link_and_not_five(
    tmp_path, machine, monkeypatch
):
    """The same wrong number arriving from the other side. Walking the table row by row
    reports five links over one directory, and `already()` printed exactly that."""

    store = machine / ".ai-engineering" / "skills"
    store.mkdir(parents=True, exist_ok=True)
    (store / "ai-thing").mkdir()
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "ai-thing").symlink_to(store / "ai-thing")
    monkeypatch.setattr(wiring, "table", lambda: {"surface": [{"skills": str(shared)}] * 5})

    assert wiring.linked() == [shared]


def test_a_directory_of_ours_counts_only_when_the_receipt_says_we_put_it_there(
    tmp_path, machine, monkeypatch
):
    """The Windows case, where linking copies. A directory named `ai-something` sitting in
    a skills root is not evidence on its own — anybody may write one — so the one question
    the disk genuinely cannot answer is asked of the receipt instead."""

    root = tmp_path / "copied"
    (root / "ai-thing").mkdir(parents=True)
    monkeypatch.setattr(wiring, "table", lambda: {"surface": [{"skills": str(root)}]})

    monkeypatch.setattr(wiring, "receipt", lambda: {"wrote": []})
    assert wiring.linked() == []

    monkeypatch.setattr(wiring, "receipt", lambda: {"wrote": [{"path": str(root), "how": "copy"}]})
    assert wiring.linked() == [root]


def test_a_router_is_recorded_by_the_bytes_that_landed_not_the_ones_we_meant(tmp_path, monkeypatch):
    """`uninstall` reads the file back with `read_bytes` and removes it only when the digest
    still matches. The writer used to hash the string it was about to write.

    On Windows `write_text` translates `\\n` to `\\r\\n`, so the two were never the same
    bytes: every generated router looked edited by a stranger from the first second, and the
    uninstaller — correctly, given what it was told — refused to remove any of them. A
    Windows user could not uninstall cleanly.

    Hashing the file cannot desync from the file, so this asserts the property rather than
    the platform: whatever landed is what the receipt says landed. It fails on Linux too if
    the writer goes back to hashing the string, because a translating writer is simulated
    here rather than waited for."""

    real = Path.write_text

    def translating(self, data, *args, **kwargs):
        """What `write_text` does on Windows, done here so the property is testable."""
        return self.write_bytes(data.replace("\n", "\r\n").encode("utf-8"))

    monkeypatch.setattr(Path, "write_text", translating)
    landed = tmp_path / "ai-thing.md"
    body = "one\ntwo\n"
    landed.write_text(body, encoding="utf-8")
    monkeypatch.setattr(Path, "write_text", real)

    of_the_string = hashlib.sha256(body.encode("utf-8")).hexdigest()
    of_the_file = hashlib.sha256(landed.read_bytes()).hexdigest()
    assert of_the_string != of_the_file, "the simulation is not simulating anything"

    # And the receipt a real placement writes is the second of those two.
    source = Path(wiring.__file__).read_text(encoding="utf-8")
    assert "hashlib.sha256(target.read_bytes()).hexdigest()" in source
    assert 'hashlib.sha256(body.encode("utf-8")).hexdigest()' not in source
