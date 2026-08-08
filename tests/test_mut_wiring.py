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

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from ai_engineering import __version__, doctor, paths, wiring

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
    stranger = {"handlers": [{"command": "somebody else's hook"}]}
    path.write_text(json.dumps({"hooks": {"PreToolUse": [stranger]}}), encoding="utf-8")

    assert wiring.json_codex(path) == "appended, position 2 of 2"
    groups = json.loads(path.read_text())["hooks"]["PreToolUse"]
    assert groups[0] == stranger
    assert groups[1] == {
        "handlers": [
            {
                "type": "command",
                "command": wiring.command("PreToolUse"),
                "timeout_ms": 5000,
                "status_message": "ai-engineering guards",
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
        ("__PYTHON__", sys.executable),
        ("__CHAIN__", str(paths.hooks() / "chain.py")),
        ("__BEAT__", str(paths.home() / "cache" / "opencode-heartbeat")),
    ):
        want = want.replace(token, value)
    assert path.read_text(encoding="utf-8") == want
    assert wiring.ts_opencode(path) == "plugin written"


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
    row silently inheriting somebody else's wording is the failure this line prevents."""
    monkeypatch.chdir(tmp_path)
    for folder in (".claude", ".codex", ".cursor", ".pi", ".config/opencode"):
        (machine / folder).mkdir(parents=True)
    root = tmp_path / "repo"
    (root / ".ai").mkdir(parents=True)
    (root / ".ai" / "config.toml").write_text(
        '[framework]\nversion = "0.0.0-not-this-wheel"\n', encoding="utf-8"
    )

    want = [
        ("T2", "claude-code", "denial executed here BLOCKS"),
        ("T2", "opencode", "plugin not loaded    INERT"),
        ("T2", "codex-cli", "hook present         INERT — run /hooks"),
        ("T2", "cursor", "documented, unrun    UNPROVEN"),
        ("T2", "copilot-cli", "not installed        UNPROVEN"),
        ("T2", "vscode-copilot", "not installed        UNPROVEN"),
        ("T3", "pi", "instructions only    ADVISES"),
        ("T3", "zed", "not installed        UNPROVEN"),
    ]
    assert doctor.coverage(root) == [
        f"  PIN  wheel {__version__} = pinned 0.0.0-not-this-wheel  MISMATCH",
        *[f"  {tier:<4} {surface:<16} {state}" for tier, surface, state in want],
        "  Bypasses that work today: --no-verify from your own shell. T1 is not T0.",
    ]


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

    assert doctor.main(["--paths"]) == 0
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
    monkeypatch.setattr(doctor, "coverage", lambda root: [f"  surfaces for {root}"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: here)

    assert doctor.main([]) == 1
    out = capsys.readouterr().out
    assert out.count("\nThe pin\n") == 1
    assert out.count("\nThe record\n") == 1
    assert out.count("\nThe outside\n") == 1
    assert "   1  ok       first" in out
    assert f"   2  FAIL     second\n      root is {here}" in out
    assert "   3  ?        third\n      could not evaluate: nothing was ever written" in out
    assert "   4  ?        fourth" in out
    assert "   5  FAIL     fifth\n      the server said no" in out
    assert "\nCoverage — what actually blocks, by surface\n" in out
    assert f"  surfaces for {here}" in out
    assert "1 passed · 2 failed · 2 not evaluated" in out
    assert out.endswith("\nNot evaluated is never green. Each one names why above.\n")


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
    monkeypatch.setattr(doctor, "coverage", lambda root: ["  stubbed"])
    monkeypatch.setattr(paths, "repo_root", lambda start=None: None)

    assert doctor.main(["--ci"]) == 0
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
