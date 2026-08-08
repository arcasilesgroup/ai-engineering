"""The installer's first five minutes, pinned line by line.

`init` is the only thing a stranger runs before they trust anything else, so what it
prints is not decoration: it is the whole report of what was touched. These tests hold
the exact exit code of every path, the exact question asked before each write, and the
exact text of every line, because a message nobody asserts on is a message that can
quietly start lying.

Everything lands in tmp_path with HOME and AI_ENGINEERING_HOME redirected, so a test
that reaches for the real machine finds an empty one instead of the operator's.
"""

from __future__ import annotations

import re
import subprocess
import sys
from types import SimpleNamespace

import pytest

from ai_engineering import __version__, init, paths, skeletons, wiring


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
    subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, capture_output=True)
    return root.resolve()


@pytest.fixture
def tty(monkeypatch):
    """A stdin that says it is a terminal, so the interactive branches actually run."""
    monkeypatch.setattr(sys, "stdin", SimpleNamespace(isatty=lambda: True))


@pytest.fixture
def typed(monkeypatch):
    """Records every prompt shown and answers each one from a queue. Empty queue means
    the user pressed Enter."""
    box = SimpleNamespace(prompts=[], replies=[])

    def fake_input(prompt=""):
        box.prompts.append(prompt)
        return box.replies.pop(0) if box.replies else ""

    monkeypatch.setattr("builtins.input", fake_input)
    return box


@pytest.fixture
def no_keyboard(monkeypatch):
    """Any question asked here is the bug: these paths must decide without a human."""

    def refuse(prompt=""):
        raise AssertionError(f"asked a question it should not have asked: {prompt!r}")

    monkeypatch.setattr("builtins.input", refuse)


ROWS = [
    ("CLAUDE.md", 3, "one line: @./AGENTS.md"),
    ("justfile", 12, "5 recipes + the RAN lines"),
]


def survey(text: str) -> dict[str, str]:
    """The Global table read back: each surface's detect path mapped to the mark printed
    at the end of its row."""
    rows = {}
    for line in text.splitlines():
        words = line.split()
        paths_named = [word for word in words if word.startswith("~/")]
        if line.startswith("   ") and len(paths_named) == 1:
            rows[paths_named[0]] = " ".join(words[words.index(paths_named[0]) + 1 :])
    return rows


# ── out and banner ──────────────────────────────────────────────────────────────────


def test_out_ends_every_line_and_an_empty_call_prints_only_the_newline(capsys):
    """Catches a changed line terminator or a default that is not the empty string, both
    of which would put literal junk in front of a user."""
    init.out("hello")
    init.out()
    assert capsys.readouterr().out == "hello\n\n"


def test_the_banner_stays_out_of_logs_and_ci_transcripts(capsys):
    """Catches the banner being printed when stderr is a pipe rather than a terminal."""
    init.banner()
    assert capsys.readouterr().err == ""


def test_the_banner_names_the_product_and_this_version_on_a_terminal(monkeypatch):
    """Catches a banner that goes blank on the one screen it exists for."""
    written: list[str] = []
    monkeypatch.setattr(
        sys,
        "stderr",
        SimpleNamespace(isatty=lambda: True, write=written.append, flush=lambda: None),
    )
    init.banner()
    assert "e n g i n e e r i n g" in written[0]
    assert f"v{__version__} · AI Governance Framework" in written[0]


# ── ask ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("default", [True, False])
def test_ask_takes_the_default_under_dash_y_without_asking(default, no_keyboard):
    """Catches -y stopping to wait for a human, which hangs every script that uses it."""
    assert init.ask("Set up?", default, init.parse(["-y"])) is default


@pytest.mark.parametrize("default", [True, False])
def test_ask_takes_the_default_when_no_terminal_is_attached(default, no_keyboard):
    """Catches the terminal check being inverted, which makes a piped run block forever."""
    assert init.ask("Set up?", default, init.parse([])) is default


@pytest.mark.parametrize(
    ("reply", "default", "answer"),
    [
        ("y", False, True),
        ("Y", False, True),
        ("yes", False, True),
        ("n", True, False),
        ("N", True, False),
        ("maybe", True, False),
        ("", True, True),
        ("", False, False),
    ],
)
def test_ask_reads_the_typed_answer_and_falls_back_to_the_default_on_enter(
    reply, default, answer, tty, typed
):
    """Catches a yes that is only recognised in one case, and an Enter that stops meaning
    the safe default."""
    typed.replies.append(reply)
    assert init.ask("Set up?", default, init.parse([])) is answer


@pytest.mark.parametrize(
    ("default", "shown"),
    [(True, "◆ Set up? (Y/n) › "), (False, "◆ Set up? (y/N) › ")],
)
def test_ask_shows_which_answer_pressing_enter_gives(default, shown, tty, typed):
    """Catches the prompt losing the capital letter that tells a user what Enter does."""
    init.ask("Set up?", default, init.parse([]))
    assert typed.prompts == [shown]


# ── parse ───────────────────────────────────────────────────────────────────────────


def test_the_help_names_the_command_and_explains_every_flag(monkeypatch, capsys):
    """Catches a help screen that loses the command name, the one-line description, or
    the explanation of a flag — the only documentation reachable without a browser."""
    monkeypatch.setenv("COLUMNS", "200")
    with pytest.raises(SystemExit) as stopped:
        init.parse(["--help"])
    assert stopped.value.code == 0
    text = capsys.readouterr().out
    assert text.startswith("usage: ai-eng init ")
    assert "The only install verb: this machine, and then this repository if you say yes." in text
    for phrase in (
        "set up this machine",
        "set up this repository",
        "comma-separated surface ids; default is all found",
        "comma-separated file names, or all",
        "print the checklist, write nothing",
        "take every default",
    ):
        # Anchored to the end of its line: a help string with anything stuck on the end
        # of it is a different help string.
        assert re.search(rf"{re.escape(phrase)}$", text, re.MULTILINE), phrase


def test_every_default_is_the_one_that_writes_nothing():
    """Catches a default flipping to the destructive side, where running `ai-eng init`
    with no arguments would overwrite files nobody offered up."""
    plain = init.parse([])
    assert plain.do_global is False
    assert plain.skip_global is False
    assert plain.project is None
    assert plain.harness == ""
    assert plain.overwrite == ""
    assert plain.dry is False
    assert plain.yes is False


def test_project_without_a_value_means_the_directory_you_are_standing_in():
    """Catches `--project` with no path silently becoming "no project at all"."""
    assert init.parse(["--project"]).project == "."
    assert init.parse(["--project", "sub"]).project == "sub"


# ── global_ready ────────────────────────────────────────────────────────────────────


def test_the_machine_counts_as_ready_only_with_a_receipt_at_this_exact_version(home):
    """Catches `init` calling an old install ready, which leaves guards pointing at an
    interpreter path that has moved."""
    assert init.global_ready() is False
    entry = [{"path": "/somewhere/settings.json", "kind": "guard", "how": "json_claude"}]
    wiring.write_json(wiring.receipt_path(), {"wrote": entry, "version": __version__})
    assert init.global_ready() is True
    wiring.write_json(wiring.receipt_path(), {"wrote": entry, "version": "0.0.0"})
    assert init.global_ready() is False
    wiring.write_json(wiring.receipt_path(), {"wrote": [], "version": __version__})
    assert init.global_ready() is False


# ── global_step ─────────────────────────────────────────────────────────────────────


def test_an_already_wired_machine_gets_one_summary_line_and_no_survey(home, capsys):
    """Catches the installer walking the whole surface table again on a machine that is
    already set up, which is how a second guard entry gets written."""
    entry = [{"path": "/a", "kind": "guard"}, {"path": "/b", "kind": "link"}]
    wiring.write_json(wiring.receipt_path(), {"wrote": entry, "version": __version__})
    init.global_step(init.parse([]))
    assert capsys.readouterr().out == (
        f"  Global ready — 8 skills, 2 entries, v{__version__} ({wiring.receipt_path()})\n"
    )


def test_no_global_says_nothing_at_all_when_there_is_no_receipt(home, capsys, no_keyboard):
    """Catches --no-global falling through into the machine setup it exists to prevent."""
    init.global_step(init.parse(["--no-global"]))
    assert capsys.readouterr().out == ""


def test_the_dry_run_surveys_every_surface_marks_the_found_one_and_writes_nothing(home, capsys):
    """Catches the survey mislabelling which editors are installed, or a dry run that
    writes anyway — the two things a person reads this screen to check."""
    (home / ".claude").mkdir()
    init.global_step(init.parse(["--global", "--dry-run"]))
    text = capsys.readouterr().out
    marks = survey(text)
    assert len(marks) == len([s for s in wiring.table()["surface"] if s["detect"]])
    assert marks["~/.claude"] == "found"
    assert marks["~/.codex"] == "not installed — skipped"
    # The one row with no detect path of its own. "not installed" would be a claim, and
    # nothing here is in a position to make it.
    assert "   VS Code Copilot    —                          wired by name only\n" in text
    assert "\n◇ Global\n" in text
    assert (
        f"   Writes 8 skills into {paths.home() / 'skills'}, symlinks from the roots above,"
    ) in text
    assert "   → skipped.\n" in text
    assert not wiring.receipt_path().exists()
    assert not (home / ".claude" / "settings.json").exists()


def test_harness_narrows_the_survey_to_the_surface_ids_you_name(home, capsys):
    """Catches --harness being ignored, which wires editors the user deliberately left
    out of the list."""
    for folder in (".claude", ".codex", ".cursor"):
        (home / folder).mkdir()
    init.global_step(init.parse(["--global", "--dry-run", "--harness", "claude-code,cursor"]))
    marks = survey(capsys.readouterr().out)
    assert marks["~/.claude"] == "found"
    assert marks["~/.cursor"] == "found"
    assert marks["~/.codex"] == "not installed — skipped"


def test_the_machine_setup_asks_first_and_a_no_leaves_the_machine_untouched(
    home, tty, typed, capsys
):
    """Catches the installer writing into a machine before the person said yes."""
    (home / ".claude").mkdir()
    typed.replies.append("n")
    init.global_step(init.parse(["--global"]))
    assert typed.prompts == ["◆ Set up this machine? (Y/n) › "]
    assert "   → skipped.\n" in capsys.readouterr().out
    assert not wiring.receipt_path().exists()


def test_the_machine_setup_reports_the_skills_every_link_and_each_guard_entry(
    home, capsys, no_keyboard
):
    """Catches a report that hides half of what was written — a skipped link root, or a
    Codex entry that needs human approval being flagged as done."""
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()
    init.global_step(init.parse(["--global", "-y"]))
    text = capsys.readouterr().out
    assert f"   ✓ 8 skills   → {paths.home() / 'skills'}/ai-*/\n" in text
    found = {s["skills"] for s in wiring.detect() if s.get("skills")}
    assert found == {"~/.claude/skills", "~/.agents/skills"}
    for root in sorted(found):
        assert f"→ {wiring.expand(root)}\n" in text
    assert "   ✓ guards     → ~/.claude/settings.json (merged)\n" in text
    # The warning has to sit under the entry it is about. Under any other entry it reads
    # as a claim that a live guard is inert.
    assert (
        "   ⚠ guards     → ~/.codex/hooks.json (appended, position 1 of 1)\n"
        "     Codex will not run it until you approve it: type /hooks in Codex.\n"
        "     `doctor` reports it as INERT until then.\n"
    ) in text
    assert f"   ✓ receipt    → {wiring.receipt_path()}\n" in text


def test_only_the_surfaces_that_were_found_get_a_skills_root(home, capsys, no_keyboard):
    """Linking creates the parent of a skills root, so linking into all eight put
    ~/.config/opencode, ~/.pi and ~/.agents on a machine that had none of them — and those
    are the paths the next run's detector reads. One init made the next init find OpenCode
    on a machine that has never had OpenCode, and write a plugin there."""
    init.global_step(init.parse(["--global", "--harness", "claude-code", "-y"]))
    assert (home / ".claude" / "skills").is_dir()
    assert not (home / ".agents").exists()
    assert not (home / ".pi").exists()
    assert not (home / ".config").exists()
    assert [row["path"] for row in wiring.receipt()["wrote"] if row["kind"] == "link"] == [
        str(home / ".claude" / "skills")
    ]


# ── choose ──────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("word", ["all", "ALL", " all "])
def test_overwrite_all_takes_every_file_on_the_list_whatever_the_case(word, tty, no_keyboard):
    """Catches `--overwrite all` quietly selecting nothing, which is a user asking for a
    reset and getting silence."""
    assert init.choose(ROWS, init.parse(["--overwrite", word])) == {"CLAUDE.md", "justfile"}


def test_overwrite_splits_the_names_on_commas(tty, no_keyboard):
    """Catches the separator changing, which turns two named files into one name that
    matches nothing."""
    args = init.parse(["--overwrite", "CLAUDE.md,justfile"])
    assert init.choose(ROWS, args) == {"CLAUDE.md", "justfile"}


def test_overwrite_can_only_select_files_that_are_actually_there(tty, no_keyboard):
    """Catches a name that matches no existing file being added to the overwrite set,
    which would hand `write_offer` a file it never listed."""
    assert init.choose(ROWS, init.parse(["--overwrite", "nope.md"])) == set()


def test_dash_y_selects_nothing_and_asks_nothing_even_on_a_terminal(tty, no_keyboard):
    """Catches -y turning into a prompt, and catches it defaulting to overwrite: the
    defaults of this installer destroy nothing."""
    assert init.choose(ROWS, init.parse(["-y"])) == set()


def test_the_checklist_shows_every_file_numbered_from_one_with_what_it_would_become(
    tty, typed, capsys
):
    """Catches the numbering starting anywhere but 1, which makes the number a user types
    overwrite a different file than the one they read."""
    init.choose(ROWS, init.parse([]))
    text = capsys.readouterr().out
    assert "\n◇ 2 files already exist and are not ours\n" in text
    assert "   Type the numbers to overwrite, separated by spaces. Enter selects none.\n\n" in text
    assert "   1. CLAUDE.md" in text
    assert "   2. justfile" in text
    assert "one line: @./AGENTS.md" in text
    assert typed.prompts == ["\n◆ Overwrite which? (Enter = none) › "]


@pytest.mark.parametrize(
    ("reply", "picked"),
    [
        ("", set()),
        ("1", {"CLAUDE.md"}),
        ("2", {"justfile"}),
        ("1 2", {"CLAUDE.md", "justfile"}),
        ("0", set()),
        ("3", set()),
        ("x 1", {"CLAUDE.md"}),
    ],
)
def test_only_a_number_on_the_list_selects_a_file_and_enter_selects_none(reply, picked, tty, typed):
    """Catches an out-of-range or non-numeric answer either crashing the installer or
    wrapping round to select a file the user never pointed at."""
    typed.replies.append(reply)
    assert init.choose(ROWS, init.parse([])) == picked


@pytest.mark.parametrize(
    ("reply", "picked"),
    [
        ("1, 2", {"CLAUDE.md", "justfile"}),
        ("1,2", {"CLAUDE.md", "justfile"}),
        ("all", {"CLAUDE.md", "justfile"}),
        ("CLAUDE.md", {"CLAUDE.md"}),
    ],
)
def test_the_prompt_accepts_every_spelling_the_same_command_teaches(reply, picked, tty, typed):
    """Catches the typed reply and --overwrite drifting back into two parsers. Each of
    these four selected one file, nothing, nothing and nothing while they were: the comma
    is what `--overwrite CLAUDE.md,justfile` teaches in the same command's own help, and
    `all` is a valid spelling of the same intent five lines away."""
    typed.replies.append(reply)
    assert init.choose(ROWS, init.parse([])) == picked


def test_anything_it_could_not_use_is_named_rather_than_dropped(tty, typed, capsys):
    """Catches a selection prompt that takes half of what you typed and says nothing —
    the failure mode of a parser that filters instead of refusing."""
    typed.replies.append("1 9 nope.md")
    assert init.choose(ROWS, init.parse([])) == {"CLAUDE.md"}
    assert "   → ignored, nothing on the list matches: 9, nope.md\n" in capsys.readouterr().out


def test_an_empty_list_asks_nothing_at_all(tty, no_keyboard, capsys):
    """Catches the checklist appearing on a repository where nothing pre-existed, which
    is what asking the disk before the writes leaves behind if nobody guards the zero."""
    assert init.choose([], init.parse([])) == set()
    assert capsys.readouterr().out == ""


# ── project_step ────────────────────────────────────────────────────────────────────


def test_outside_a_git_repository_it_says_so_and_succeeds(tmp_path, home, capsys):
    """Catches a plain directory being treated as a failure, which would break `ai-eng
    init` for somebody who only wanted the machine set up."""
    plain = tmp_path / "plain"
    plain.mkdir()
    args = init.parse(["--project", str(plain)])
    assert init.project_step(args) == 0
    assert capsys.readouterr().out == (
        "\n◇ Project   not a git repository — nothing to set up here.\n"
    )


def test_with_no_project_flag_it_looks_at_the_directory_you_are_standing_in(
    repo, monkeypatch, capsys, tty, typed
):
    """Catches the current directory being replaced by a path that exists nowhere, which
    reports every repository as "not a git repository"."""
    monkeypatch.chdir(repo)
    typed.replies.append("n")
    assert init.project_step(init.parse([])) == 0
    assert f"\n◇ Project   {repo}   git repository, not set up\n" in capsys.readouterr().out


def test_a_repository_that_is_already_pinned_is_left_alone(repo, monkeypatch, capsys, no_keyboard):
    """Catches a second run rewriting a pin that is already there, and catches the path
    it reports being anything other than the file it actually looked at."""
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text("already mine\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    assert init.project_step(init.parse([])) == 0
    assert capsys.readouterr().out == (
        "  Project ready — .ai/config.toml, spec chain wired\n\n"
        "  Nothing to do. `ai-eng doctor` for the full check.\n"
    )
    assert (repo / ".ai" / "config.toml").read_text() == "already mine\n"


def test_naming_the_project_explicitly_runs_the_setup_over_an_existing_pin(repo, capsys):
    """Catches `--project` being ignored on a repository that is already set up, which is
    the only way to repair a half-written install."""
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text("stale\n", encoding="utf-8")
    assert init.project_step(init.parse(["--project", str(repo)])) == 0
    text = capsys.readouterr().out
    assert "   git repository, not set up\n" in text
    assert __version__ in (repo / ".ai" / "config.toml").read_text()


def test_the_pin_is_never_replaced_without_a_dated_copy_and_a_line_of_its_own(repo, capsys):
    """The four instruction files each got a dated backup and the one file this project's
    own vocabulary calls *the pin* got none: `--project` with a value asks nothing and
    rewrote .ai/config.toml and .ai/.gitignore unconditionally, so a hand-edited pin went
    back to defaults with no copy and no line. This is the file that names which version
    governs the repository, and a change of governance is never silent."""
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text('[framework]\nversion = "0.0.1"\n', encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo)]))
    saved = [p for p in (repo / ".ai").iterdir() if p.name.startswith("config.toml.bak-")]
    assert len(saved) == 1
    assert saved[0].read_text() == '[framework]\nversion = "0.0.1"\n'
    assert f"   ✓ .ai/config.toml backup → {saved[0].name} written\n" in capsys.readouterr().out
    assert f'version = "{__version__}"' in (repo / ".ai" / "config.toml").read_text()


def test_a_pin_that_already_says_what_we_would_write_is_not_copied(repo, capsys):
    """Catches a backup on every re-run, which turns `--project` into a directory that
    fills with identical copies of a file nobody changed."""
    init.project_step(init.parse(["--project", str(repo)]))
    capsys.readouterr()
    init.project_step(init.parse(["--project", str(repo)]))
    assert "backup" not in capsys.readouterr().out
    assert {p.name for p in (repo / ".ai").iterdir()} == {"config.toml", ".gitignore"}


def test_saying_no_to_the_project_writes_nothing_and_says_so(repo, monkeypatch, tty, typed, capsys):
    """Catches the project setup running before the person answered, and catches the
    reassurance that nothing was written going missing."""
    monkeypatch.chdir(repo)
    typed.replies.append("n")
    assert init.project_step(init.parse([])) == 0
    assert typed.prompts == ["◆ Set up this project too? (Y/n) › "]
    assert "   → skipped. Nothing was written.\n" in capsys.readouterr().out
    assert not (repo / ".ai").exists()
    assert not (repo / "specs").exists()


def test_the_project_setup_writes_the_pin_the_ignore_file_and_specs_under_those_names(
    repo, capsys, no_keyboard
):
    """Catches a file landing under a different name than the one reported — a pin that
    `doctor` and every later command then cannot find."""
    assert init.project_step(init.parse(["--project", str(repo)])) == 0
    assert ".ai" in {p.name for p in repo.iterdir()}
    assert "specs" in {p.name for p in repo.iterdir()}
    assert {p.name for p in (repo / ".ai").iterdir()} == {"config.toml", ".gitignore"}
    assert {p.name for p in (repo / "specs").iterdir()} == {".gitkeep"}
    assert (repo / ".ai" / ".gitignore").read_text() == skeletons.AI_GITIGNORE
    assert f'version = "{__version__}"' in (repo / ".ai" / "config.toml").read_text()
    assert "   ✓ .ai/config.toml · .ai/.gitignore · specs/\n" in capsys.readouterr().out


def test_each_offered_file_is_written_with_the_description_the_user_was_shown(
    repo, capsys, no_keyboard
):
    """Catches the report printing the function that makes a file instead of the sentence
    describing it, which is what somebody reads to decide whether to keep it."""
    init.project_step(init.parse(["--project", str(repo)]))
    text = capsys.readouterr().out
    assert "   ✓ CLAUDE.md written (one line: @./AGENTS.md)\n" in text
    assert "   ✓ AGENTS.md written (skeleton, ~48 lines, TODO marker per section)\n" in text
    assert "   ✓ CONSTITUTION.md written (skeleton, ~40 lines, MANDATORY)\n" in text
    assert "   ✓ justfile written (5 recipes + the RAN lines)\n" in text
    assert (repo / "CLAUDE.md").read_text() == skeletons.CLAUDE_MD


def test_running_the_project_setup_twice_changes_nothing_and_still_succeeds(
    repo, capsys, no_keyboard
):
    """Catches the second run crashing on a directory that is already there — the
    installer promises it is safe to run a thousand times."""
    init.project_step(init.parse(["--project", str(repo)]))
    assert init.project_step(init.parse(["--project", str(repo)])) == 0


def test_files_that_are_already_there_are_named_and_left_as_they_are(repo, capsys, no_keyboard):
    """Catches somebody's own CLAUDE.md being overwritten without being asked, and
    catches the list of what was spared going empty."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    (repo / "justfile").write_text("mine too\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo)]))
    assert (
        "   → left as is: CLAUDE.md, justfile. "
        "Nothing was written to them and nothing recorded that they were skipped.\n"
    ) in capsys.readouterr().out
    assert (repo / "CLAUDE.md").read_text() == "mine\n"
    assert (repo / "justfile").read_text() == "mine too\n"


def test_the_sentence_that_declines_the_overwrite_promises_no_check_nobody_wrote(
    repo, capsys, no_keyboard
):
    """This line is what a person reads in order to decline. It promised `doctor` lists
    these files as unmanaged; the word appears nowhere in doctor.py and none of its
    twenty-one assertions looks at them."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo)]))
    assert "unmanaged" not in capsys.readouterr().out


def test_the_files_the_installer_just_wrote_are_not_reported_as_left_as_is(
    repo, capsys, no_keyboard
):
    """One screen says "✓ AGENTS.md written" and the next says AGENTS.md was left as is.
    Both cannot be true, and the second one is the wrong half."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo)]))
    left = capsys.readouterr().out.split("   → left as is: ")[1].split(". Nothing")[0]
    assert left == "CLAUDE.md"


def test_an_overwritten_file_is_copied_to_a_timestamped_backup_first(repo, capsys, no_keyboard):
    """Catches a backup whose name has no timestamp in it, which means the second
    overwrite silently destroys the first backup."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo), "--overwrite", "CLAUDE.md"]))
    backups = [p.name for p in repo.iterdir() if p.name.startswith("CLAUDE.md.bak-")]
    assert len(backups) == 1
    assert re.fullmatch(r"CLAUDE\.md\.bak-\d{8}-\d{6}-\d{6}", backups[0])
    assert (repo / backups[0]).read_text() == "mine\n"
    assert (repo / "CLAUDE.md").read_text() == skeletons.CLAUDE_MD
    assert f"   ✓ CLAUDE.md backup → {backups[0]} written\n" in capsys.readouterr().out


def test_two_overwrites_inside_one_second_leave_two_backups(repo, no_keyboard):
    """The docstring above says the timestamp is what stops the second overwrite
    destroying the first backup, and until the stamp had sub-second resolution that was
    the one thing it did not do. This is the test that makes it mean what it says."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    for _ in range(2):
        init.project_step(init.parse(["--project", str(repo), "--overwrite", "CLAUDE.md"]))
    backups = sorted(p for p in repo.iterdir() if p.name.startswith("CLAUDE.md.bak-"))
    assert len(backups) == 2
    assert backups[0].read_text() == "mine\n"


@pytest.mark.parametrize("found, warns", [(None, True), ("/opt/bin/gitleaks", False)])
def test_the_wall_the_repository_is_about_to_hit_is_named_now_not_at_the_next_commit(
    repo, capsys, no_keyboard, monkeypatch, found, warns
):
    """Wiring a project sets ai.managed, and the shipped pre-commit exits 1 when that flag
    is set and gitleaks is absent. So `ai-eng init` on a machine without it left a
    repository that refuses every commit from then on, and the first the person heard of
    it was their next commit. Nothing in init looked for the binary."""
    monkeypatch.setattr(init.shutil, "which", lambda name: found)
    init.project_step(init.parse(["--project", str(repo)]))
    text = capsys.readouterr().out
    assert ("gitleaks is not on your PATH" in text) is warns
    assert ("exits 1 on every commit until it is there" in text) is warns
    assert ("`brew install gitleaks`" in text) is warns


def test_the_stacks_it_found_are_named_and_it_installs_none_of_them(repo, capsys, no_keyboard):
    """Catches the stack line going blank or crashing, which is the one place the
    installer tells you it did not install your toolchain."""
    (repo / "pyproject.toml").touch()
    (repo / "package.json").touch()
    init.project_step(init.parse(["--project", str(repo)]))
    assert (
        "\n   Stacks detected: node, python. The binaries each one needs are listed "
        "in docs/tools.md; this installs none of them.\n"
    ) in capsys.readouterr().out


def test_a_repository_with_no_marker_file_gets_no_stack_line(repo, capsys, no_keyboard):
    """Catches a stack being claimed for a repository that has nothing to claim it with."""
    init.project_step(init.parse(["--project", str(repo)]))
    assert "Stacks detected" not in capsys.readouterr().out


def test_the_ci_block_is_printed_indented_and_pinned_to_this_version(repo, capsys, no_keyboard):
    """Catches the workflow block arriving as one run-together line or without the
    version pin, either of which fails the moment it is pasted."""
    assert init.project_step(init.parse(["--project", str(repo)])) == 0
    text = capsys.readouterr().out
    assert "\n   Paste these lines into .github/workflows/check.yml:\n\n" in text
    assert "   name: check\n   on: [push, pull_request]\n" in text
    assert f"\n             PIN: {__version__}\n" in text


def test_a_project_dry_run_prints_the_plan_and_writes_no_file(repo, capsys, no_keyboard):
    """Catches --dry-run writing anyway, which is the one promise a preview makes."""
    assert init.project_step(init.parse(["--project", str(repo), "--dry-run"])) == 0
    assert not (repo / ".ai").exists()
    assert not (repo / "specs").exists()
    assert not (repo / "CLAUDE.md").exists()
    assert "   · .ai/config.toml · .ai/.gitignore · specs/\n" in capsys.readouterr().out


def test_a_dry_run_never_says_anything_was_written(repo, capsys, no_keyboard):
    """The writes were guarded by the flag and the printing was not, so a dry run emitted
    "✓ CLAUDE.md backup → … written" and "✓ CLAUDE.md written" having written neither.
    The test beside this one asserted the files were absent and never that the output had
    stopped claiming otherwise, which is how it survived."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo), "--dry-run", "--overwrite", "all"]))
    text = capsys.readouterr().out
    assert "written" not in text
    assert {p.name for p in repo.iterdir()} == {"CLAUDE.md", ".git"}
    assert (repo / "CLAUDE.md").read_text() == "mine\n"


def test_a_dry_run_over_an_empty_repository_prints_the_checklist_it_promises(
    repo, capsys, no_keyboard
):
    """--dry-run's help says "print the checklist, write nothing". On a repository with
    nothing in it, every line of that checklist is a file this run would create, and
    those are exactly the lines the flag used to suppress on the write side only."""
    init.project_step(init.parse(["--project", str(repo), "--dry-run"]))
    text = capsys.readouterr().out
    assert "   · .ai/config.toml · .ai/.gitignore · specs/\n" in text
    assert "   · core.hooksPath → " in text
    for name, (becomes, _) in init.OFFERS.items():
        assert f"   · {name} would be created ({becomes})\n" in text


# ── main ────────────────────────────────────────────────────────────────────────────


def test_main_runs_the_machine_step_then_the_project_step_and_returns_its_code(
    repo, capsys, no_keyboard
):
    """Catches main losing the project step's exit code, which is what CI reads."""
    assert init.main(["--no-global", "--project", str(repo)]) == 0
    text = capsys.readouterr().out
    assert "\n◇ Project" in text
    assert "\n◇ Global" not in text
