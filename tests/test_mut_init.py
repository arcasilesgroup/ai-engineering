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
def picker(monkeypatch):
    """Stands in for the checkbox. Records the question, the rows offered and which of them
    arrived ticked, and answers whatever the test put in `answer` — None being Ctrl-C."""
    box = SimpleNamespace(question="", rows=[], checked=set(), answer=[])

    def fake(question, rows, checked):
        box.question, box.rows, box.checked = question, rows, checked
        return box.answer

    monkeypatch.setattr(init.ui, "pick", fake)
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
    assert capsys.readouterr().err == "hello\n\n"


def test_the_banner_stays_out_of_logs_and_ci_transcripts(capsys):
    """Catches the banner being printed when stderr is a pipe rather than a terminal."""
    init.ui.banner()
    assert capsys.readouterr().err == ""


def test_the_banner_names_the_product_and_this_version_on_a_terminal(monkeypatch, capsys):
    """Catches a banner that goes blank on the one screen it exists for. FORCE_COLOR is how
    a terminal says it wants decoration past a pipe, and it is what makes the console call
    itself a terminal here."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    init.ui.reset()
    init.ui.banner()
    written = capsys.readouterr().err
    assert "e n g i n e e r i n g" in written
    assert f"v{__version__} · AI Governance Framework" in written


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
    # argparse writes --help to stdout and that is right: it is what a person pipes into
    # a pager. This one line is not ours to move to stderr with the rest of the messaging.
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


def test_the_machine_counts_as_ready_only_when_the_surfaces_here_carry_the_entry(home):
    """Catches `init` calling an old install ready, which leaves guards pointing at an
    interpreter path that has moved — and the larger one this replaced it for.

    It used to ask the receipt: non-empty and at this version. A receipt is a log of writes,
    so it answered True for a machine whose settings files had been emptied a second earlier
    by `ai-eng uninstall`, by a hand edit, or by a home restored from a backup. The entry it
    was believing here pointed at `/somewhere/settings.json`, which never existed."""
    assert init.global_ready() is False, "ready with no surface installed at all"
    (home / ".claude").mkdir()
    wiring.write_json(wiring.receipt_path(), {"wrote": [], "version": __version__})
    assert init.global_ready() is False, "ready with a surface here and no entry in it"

    wiring.json_claude(home / ".claude" / "settings.json")
    assert init.global_ready() is True

    wiring.write_json(wiring.receipt_path(), {"wrote": [], "version": "0.0.0"})
    assert init.global_ready() is False, "an entry from an older install is wired, not ready"

    wiring.write_json(wiring.receipt_path(), {"wrote": [], "version": __version__})
    (home / ".codex").mkdir()
    assert init.global_ready() is False, "a second surface arrived and nothing wired it"


# ── global_step ─────────────────────────────────────────────────────────────────────


def test_an_already_wired_machine_gets_the_block_it_left_behind_and_no_survey(home, capsys):
    """Catches the installer walking the whole surface table again on a machine that is
    already set up, which is how a second guard entry gets written.

    Every number is counted, none is written into the sentence. The line this replaced said
    `8 skills` as a literal, which is a fact about the wheel that shipped the line and not
    about the machine reading it — and the count here is deliberately one guard and two
    links against a machine that is not fully wired, because a summary that can only be
    right on a healthy machine is a summary that hides the unhealthy one.

    Every number is now read off the disk, which is what spec 007 claimed a version before
    it was true: skills came from the store and links and guards came from the receipt, so
    this block reported four of each over a machine `uninstall` had just emptied. The rows
    it used to be given here — `/a`, `/b`, `/c` — were three paths that never existed."""
    wiring.write_json(wiring.receipt_path(), {"wrote": [], "version": __version__})
    # Two skills and one directory that is not one. The count is of what is installed, so a
    # count of everything under that root is a count that goes up when a cache lands there.
    store = paths.home() / "skills"
    for name in ("ai-spec", "ai-plan", "cache"):
        (store / name).mkdir(parents=True)
    # One surface carrying the entry, and two of the four roots holding a link of ours.
    (home / ".claude").mkdir()
    wiring.json_claude(home / ".claude" / "settings.json")
    for root in (home / ".claude" / "skills", home / ".agents" / "skills"):
        root.mkdir(parents=True)
        (root / "ai-spec").symlink_to(store / "ai-spec")
    init.global_step(init.parse([]))
    assert capsys.readouterr().err == (
        f"\n◇ Global   ready · v{__version__}\n"
        f"   skills      2  {paths.home() / 'skills'}\n"
        f"   links       2  one skills root per surface found\n"
        f"   guards      1  one entry in each surface's own settings file\n"
        f"   receipt        {wiring.receipt_path()}\n"
    )


def test_no_project_sets_up_the_machine_and_leaves_the_repository_alone(repo, capsys, no_keyboard):
    """The safety inside every cure `doctor --fix` runs. Without it the only way to ask for
    the machine and nothing else is to answer a question, so a repair with nobody in the
    room would set up whatever repository the person happened to be standing in — writing
    four instruction files and a workflow into a tree that never asked for any of them."""
    result = init.main(["--global", "--harness", "claude-code", "--no-project", "-y"])
    assert result.outcome == "PASS"
    assert {p.name for p in repo.iterdir()} == {".git"}
    assert "◇ Project" not in capsys.readouterr().err


def test_no_global_says_nothing_at_all_when_there_is_no_receipt(home, capsys, no_keyboard):
    """Catches --no-global falling through into the machine setup it exists to prevent."""
    init.global_step(init.parse(["--no-global"]))
    assert capsys.readouterr().err == ""


def test_the_dry_run_surveys_every_surface_marks_the_found_one_and_writes_nothing(home, capsys):
    """Catches the survey mislabelling which editors are installed, or a dry run that
    writes anyway — the two things a person reads this screen to check."""
    (home / ".claude").mkdir()
    init.global_step(init.parse(["--global", "--dry-run"]))
    text = capsys.readouterr().err
    marks = survey(text)
    assert len(marks) == len([s for s in wiring.table()["surface"] if s["detect"]])
    assert marks["~/.claude"] == "found"
    assert marks["~/.codex"] == "not installed — skipped"
    # The one row with no detect path of its own. "not installed" would be a claim, and
    # nothing here is in a position to make it.
    assert "   VS Code Copilot    —                          wired by name only\n" in text
    assert "\n◇ Global\n" in text
    shipped = len(list(paths.skills().glob("ai-*")))
    assert (
        f"   Writes {shipped} skills into {paths.home() / 'skills'}, symlinks from the roots above,"
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
    marks = survey(capsys.readouterr().err)
    assert marks["~/.claude"] == "found"
    assert marks["~/.cursor"] == "found"
    assert marks["~/.codex"] == "not installed — skipped"


def test_the_machine_question_offers_every_surface_and_ticks_only_the_ones_found(
    home, tty, no_keyboard, picker, capsys
):
    """The machine question is the list, and it is the whole of the first question. Every
    surface is offered because a person knows what they have installed better than a path
    check does; only the detected ones arrive ticked, because a widget that pre-ticks all
    eight has a default that writes into eight places."""
    (home / ".claude").mkdir()
    picker.answer = []
    init.global_step(init.parse(["--global"]))
    assert picker.question == "Set up which surfaces?"
    assert [row[0] for row in picker.rows] == [s["id"] for s in wiring.table()["surface"]]
    assert picker.checked == {"claude-code"}
    assert "   → skipped.\n" in capsys.readouterr().err
    assert not wiring.receipt_path().exists()


def test_choosing_one_surface_wires_that_one_and_no_other(home, tty, no_keyboard, picker):
    """Catches the answer being read and then ignored, which would wire whatever the path
    check found and make the question decoration."""
    for folder in (".claude", ".codex"):
        (home / folder).mkdir()
    picker.answer = ["codex-cli"]
    init.global_step(init.parse(["--global"]))
    assert [row["path"] for row in wiring.receipt()["wrote"] if row["kind"] == "guard"] == [
        "~/.codex/hooks.json"
    ]


def test_an_interrupted_machine_question_writes_nothing_and_stops(home, tty, no_keyboard, picker):
    """Ctrl-C is not the empty selection: one means stop, the other means "none of these"
    and carry on to the project half."""
    (home / ".claude").mkdir()
    picker.answer = None
    with pytest.raises(KeyboardInterrupt):
        init.global_step(init.parse(["--global"]))
    assert not wiring.receipt_path().exists()


def test_unattended_and_piped_runs_never_reach_the_widget(home, tty, typed, capsys):
    """-y, --harness and a run with no terminal each already said which surfaces, and a
    widget with nobody in front of it is a hang rather than a question."""
    (home / ".claude").mkdir()
    typed.replies.append("n")
    init.global_step(init.parse(["--global", "--harness", "claude-code"]))
    assert typed.prompts == ["◆ Set up this machine? (Y/n) › "]
    assert "   → skipped.\n" in capsys.readouterr().err
    assert not wiring.receipt_path().exists()


def test_both_skill_counts_are_counted_rather_than_typed(home, capsys, no_keyboard, monkeypatch):
    """The literal `8` that `already`'s docstring says was removed, in the two lines beside
    it that still had it.

    A number written into a sentence is a fact about the wheel that shipped the sentence and
    not about the machine reading it, and this repository's own audit counted that shape
    twenty times. So the wheel is stood in for with three skills: a count that is read says
    three, and a count that is typed says eight on a machine where eight is wrong.

    Both lines are here on purpose. They are computed from different things — the first from
    what the wheel carries, before anything is written, and the second from what landed in
    the store — because a plan and a receipt that read the same variable cannot disagree,
    and disagreeing is the whole job of the second one."""
    shipped = home / "wheel-skills"
    for name in ("ai-spec", "ai-plan", "ai-review"):
        (shipped / name).mkdir(parents=True)
        (shipped / name / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    monkeypatch.setattr(paths, "skills", lambda: shipped)
    (home / ".claude").mkdir()

    init.global_step(init.parse(["--global", "--dry-run"]))
    assert f"   Writes 3 skills into {paths.home() / 'skills'}" in capsys.readouterr().err

    init.global_step(init.parse(["--global", "-y"]))
    assert f"   ✓ 3 skills   → {paths.home() / 'skills'}/ai-*/\n" in capsys.readouterr().err


def test_the_machine_setup_reports_the_skills_every_link_and_each_guard_entry(
    home, capsys, no_keyboard
):
    """Catches a report that hides half of what was written — a skipped link root, or a
    Codex entry that needs human approval being flagged as done."""
    (home / ".claude").mkdir()
    (home / ".codex").mkdir()
    init.global_step(init.parse(["--global", "-y"]))
    text = capsys.readouterr().err
    installed = len(list((paths.home() / "skills").glob("ai-*")))
    # Whitespace-normalised: the label is padded to a column, so a two-digit count moves the
    # arrow one place left. What this row is about is the number and the destination.
    squeezed = re.sub(r"[ ]+", " ", text)
    assert f"✓ {installed} skills → {paths.home() / 'skills'}/ai-*/\n" in squeezed
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


def test_the_overwrite_question_is_a_list_with_nothing_ticked(tty, no_keyboard, capsys, picker):
    """At a keyboard the question is a list you move a cursor over. Nothing is ticked, which
    is the same default the typed prompt had and the same promise: pressing Enter without
    reading destroys nothing."""
    picker.answer = ["CLAUDE.md"]
    assert init.choose(ROWS, init.parse([])) == {"CLAUDE.md"}
    assert "\n◇ 2 files already exist and are not ours\n" in capsys.readouterr().err
    assert picker.question.startswith("Overwrite which?")
    assert picker.rows == [
        ("CLAUDE.md", "   3 lines  →  one line: @./AGENTS.md"),
        ("justfile", "  12 lines  →  5 recipes + the RAN lines"),
    ]
    assert picker.checked == set()


def test_an_interrupted_overwrite_question_writes_nothing_and_stops(tty, no_keyboard, picker):
    """Ctrl-C is not "overwrite none of them". One means stop; the other means carry on
    having written nothing, and only the second should reach the rest of the install."""
    picker.answer = None
    with pytest.raises(KeyboardInterrupt):
        init.choose(ROWS, init.parse([]))


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
        ("1, 2", {"CLAUDE.md", "justfile"}),
        ("1,2", {"CLAUDE.md", "justfile"}),
        ("all", {"CLAUDE.md", "justfile"}),
        ("CLAUDE.md", {"CLAUDE.md"}),
    ],
)
def test_the_parser_takes_every_spelling_and_nothing_off_the_list(reply, picked):
    """The parser is still the answer for `--overwrite`, for -y and for every run with no
    terminal, so all eleven spellings stay held. It is driven directly now rather than
    through a prompt the picker replaced — a test that reaches its subject through a
    widget is a test of the widget."""
    assert init.select(reply, ROWS)[0] == picked


def test_anything_it_could_not_use_is_named_rather_than_dropped(repo, capsys, no_keyboard):
    """Catches a selection that takes half of what you asked for and says nothing — the
    failure mode of a parser that filters instead of refusing."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo), "--overwrite", "CLAUDE.md,9,nope.md"]))
    assert "   → ignored, nothing on the list matches: 9, nope.md\n" in capsys.readouterr().err


def test_an_empty_list_asks_nothing_at_all(tty, no_keyboard, capsys):
    """Catches the checklist appearing on a repository where nothing pre-existed, which
    is what asking the disk before the writes leaves behind if nobody guards the zero."""
    assert init.choose([], init.parse([])) == set()
    assert capsys.readouterr().err == ""


# ── project_step ────────────────────────────────────────────────────────────────────


def test_outside_a_git_repository_dash_y_creates_nothing_and_is_incomplete(tmp_path, home, capsys):
    """An explicitly named non-repository stays untouched and cannot claim completion."""
    plain = tmp_path / "plain"
    plain.mkdir()
    result = init.project_step(init.parse(["--project", str(plain), "-y"]))
    assert result.outcome == "INCOMPLETE"
    assert capsys.readouterr().err == (
        f"\n◇ Project   {plain}   not a git repository\n"
        "   → skipped. There is nothing to set up outside a repository.\n"
    )
    assert not (plain / ".git").exists()


def test_a_directory_that_is_not_a_repository_is_offered_one(tmp_path, home, tty, typed, capsys):
    """Before this the installer printed one line and stopped, in the one place a person
    is most likely to be starting from nothing. The default is still no, and the question
    is only asked at a keyboard."""
    plain = tmp_path / "plain"
    plain.mkdir()
    typed.replies.append("y")
    result = init.project_step(init.parse(["--project", str(plain)]))
    assert result.outcome == "PASS"
    assert typed.prompts[0] == "◆ Run `git init` here? (y/N) › "
    assert (plain / ".git").is_dir()
    assert f"   ✓ git init   → {plain}\n" in capsys.readouterr().err
    assert (plain / ".ai" / "config.toml").exists()
    # main, not whatever this machine's git.defaultBranch happens to say: the CI block
    # this same run prints triggers on push, and a repository whose branch is named
    # something else is a workflow that never fires.
    head = subprocess.run(
        ["git", "-C", str(plain), "symbolic-ref", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert head.stdout.strip() == "main"


@pytest.mark.parametrize(
    "argv, why",
    [
        (["--dry-run"], "a preview creates nothing, including a repository"),
        (["-y"], "the default is no, and -y takes the default"),
    ],
    ids=["a dry run", "unattended"],
)
def test_the_git_init_offer_is_declined_without_a_person(tmp_path, home, no_keyboard, argv, why):
    """Both of these reach the offer with nobody at the keyboard, and both have to come out
    the same way: nothing created."""
    plain = tmp_path / "plain"
    plain.mkdir()
    result = init.project_step(init.parse(["--project", str(plain), *argv]))
    assert result.outcome == "INCOMPLETE", why
    assert not (plain / ".git").exists()


def test_with_no_project_flag_outside_a_repository_it_names_the_directory_you_are_in(
    tmp_path, home, monkeypatch, capsys, no_keyboard
):
    """Catches the current directory being replaced by a path that exists nowhere. The
    repository case has a test for this; outside one the path is printed straight from the
    argument, so nothing else was holding it."""
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.chdir(plain)
    result = init.project_step(init.parse(["-y"]))
    assert result.outcome == "READY"
    assert f"\n◇ Project   {plain}   not a git repository\n" in capsys.readouterr().err


def test_a_git_init_that_fails_stops_here_and_the_call_cannot_hang(
    tmp_path, home, tty, typed, monkeypatch
):
    """Two properties of one call. check=True is the difference between a failed `git
    init` stopping and the installer walking on into a directory with no repository in it,
    writing a pin and a hooks path nothing will ever read. The timeout is the difference
    between a git that hangs and an installer that hangs with it."""
    calls: list[dict] = []

    def fake(cmd, **kwargs):
        calls.append(kwargs)
        if kwargs.get("check"):
            raise subprocess.CalledProcessError(1, cmd)
        return subprocess.CompletedProcess(cmd, 1)

    monkeypatch.setattr(init.subprocess, "run", fake)
    plain = tmp_path / "plain"
    plain.mkdir()
    typed.replies.append("y")
    with pytest.raises(subprocess.CalledProcessError):
        init.project_step(init.parse(["--project", str(plain)]))
    assert calls[0]["timeout"] == 10


def test_a_project_path_that_is_not_a_directory_is_not_offered_a_repository(
    tmp_path, home, tty, no_keyboard, capsys
):
    """`git init` in something that is not a directory fails, and check=True turns that
    into a traceback in front of somebody who mistyped a path."""
    a_file = tmp_path / "notadir"
    a_file.write_text("I am a file\n", encoding="utf-8")
    result = init.project_step(init.parse(["--project", str(a_file)]))
    assert result.outcome == "INCOMPLETE"
    assert "   → skipped. There is nothing to set up outside a repository.\n" in (
        capsys.readouterr().err
    )


def test_pressing_enter_at_the_git_init_offer_creates_nothing(tmp_path, home, tty, typed, capsys):
    """Every default in this installer destroys nothing, and creating a repository in
    somebody's home directory because they pressed Enter is the version of that which
    cannot be undone by reading a backup."""
    plain = tmp_path / "plain"
    plain.mkdir()
    result = init.project_step(init.parse(["--project", str(plain)]))
    assert result.outcome == "INCOMPLETE"
    assert not (plain / ".git").exists()
    assert "   → skipped. There is nothing to set up outside a repository.\n" in (
        capsys.readouterr().err
    )


def test_with_no_project_flag_it_looks_at_the_directory_you_are_standing_in(
    repo, monkeypatch, capsys, tty, typed
):
    """Catches the current directory being replaced by a path that exists nowhere, which
    reports every repository as "not a git repository"."""
    monkeypatch.chdir(repo)
    typed.replies.append("n")
    result = init.project_step(init.parse([]))
    assert result.outcome == "READY"
    assert f"\n◇ Project   {repo}   git repository, not set up\n" in capsys.readouterr().err


def test_a_repository_that_is_already_pinned_is_left_alone(repo, monkeypatch, capsys, no_keyboard):
    """Catches a second run rewriting a pin that is already there, and catches the path
    it reports being anything other than the file it actually looked at."""
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text("already mine\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    result = init.project_step(init.parse([]))
    assert result.outcome == "READY"
    assert capsys.readouterr().err == (
        "  Project ready — .ai/config.toml, spec chain wired\n\n"
        "  Nothing to do. `ai-eng doctor` for the full check.\n"
    )
    assert (repo / ".ai" / "config.toml").read_text() == "already mine\n"


def test_naming_the_project_explicitly_runs_the_setup_over_an_existing_pin(repo, capsys):
    """Catches `--project` being ignored on a repository that is already set up, which is
    the only way to repair a half-written install."""
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text("stale\n", encoding="utf-8")
    result = init.project_step(init.parse(["--project", str(repo)]))
    assert result.outcome == "PASS"
    text = capsys.readouterr().err
    assert "   git repository, not set up\n" in text
    assert (repo / "CLAUDE.md").exists(), "the rest of the setup did not run"


def test_the_pin_is_never_rewritten_because_update_is_the_verb_that_changes_it(repo, capsys):
    """A pin that exists is left exactly as it is. This used to rewrite it on every run,
    taking a dated backup and printing a line — which is `ai-eng update` with its dirty-tree
    refusal, its keyboard and its typed y all removed, and a receipt handed over afterwards
    instead. It reset everything else in the file too: the guard windows, and the
    observability endpoint somebody's alerts point at.

    `doctor --fix` is what made this reachable with nobody in the room, which is the objection
    ADR 0002 raised, ADR 0003 promised was not true of this design, and this holds to."""
    (repo / ".ai").mkdir()
    mine = '[framework]\nversion = "0.0.1"\n\n[observability]\nendpoint = "https://mine"\n'
    (repo / ".ai" / "config.toml").write_text(mine, encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo)]))
    assert (repo / ".ai" / "config.toml").read_text() == mine
    assert [p for p in (repo / ".ai").iterdir() if ".bak-" in p.name] == []
    text = capsys.readouterr().err
    assert "   ✓ .ai/.gitignore · specs/.gitkeep\n" in text
    assert (
        "     .ai/config.toml was already here and is untouched. `ai-eng update` is the "
        "only verb that changes the pin.\n"
    ) in text


def test_a_second_run_writes_no_pin_and_no_copy_of_one(repo, capsys):
    """Catches a backup on every re-run, which turns `--project` into a directory that
    fills with identical copies of a file nobody changed."""
    init.project_step(init.parse(["--project", str(repo)]))
    capsys.readouterr()
    init.project_step(init.parse(["--project", str(repo)]))
    assert "backup" not in capsys.readouterr().err
    assert [p for p in (repo / ".ai").iterdir() if ".bak-" in p.name] == []
    assert {p.name for p in (repo / ".ai").iterdir()} == {"config.toml", ".gitignore"}


def test_saying_no_to_the_project_writes_nothing_and_says_so(repo, monkeypatch, tty, typed, capsys):
    """Catches the project setup running before the person answered, and catches the
    reassurance that nothing was written going missing."""
    monkeypatch.chdir(repo)
    typed.replies.append("n")
    result = init.project_step(init.parse([]))
    assert result.outcome == "READY"
    assert typed.prompts == ["◆ Set up this project too? (Y/n) › "]
    assert "   → skipped. Nothing was written.\n" in capsys.readouterr().err
    assert not (repo / ".ai").exists()
    assert not (repo / "specs").exists()


def test_the_project_setup_writes_the_pin_the_ignore_file_and_specs_under_those_names(
    repo, capsys, no_keyboard
):
    """Catches a file landing under a different name than the one reported — a pin that
    `doctor` and every later command then cannot find."""
    result = init.project_step(init.parse(["--project", str(repo)]))
    assert result.outcome == "PASS"
    assert ".ai" in {p.name for p in repo.iterdir()}
    assert "specs" in {p.name for p in repo.iterdir()}
    assert {p.name for p in (repo / ".ai").iterdir()} == {"config.toml", ".gitignore"}
    assert {p.name for p in (repo / "specs").iterdir()} == {".gitkeep"}
    assert (repo / ".ai" / ".gitignore").read_text() == skeletons.AI_GITIGNORE
    assert f'version = "{__version__}"' in (repo / ".ai" / "config.toml").read_text()
    assert "   ✓ .ai/config.toml · .ai/.gitignore · specs/.gitkeep\n" in capsys.readouterr().err


def test_each_offered_file_is_written_with_the_description_the_user_was_shown(
    repo, capsys, no_keyboard
):
    """Catches the report printing the function that makes a file instead of the sentence
    describing it, which is what somebody reads to decide whether to keep it."""
    init.project_step(init.parse(["--project", str(repo)]))
    text = capsys.readouterr().err
    assert "   ✓ CLAUDE.md written (one line: @./AGENTS.md)\n" in text
    assert "   ✓ AGENTS.md written (skeleton, ~48 lines, TODO marker per section)\n" in text
    assert "   ✓ CONSTITUTION.md written (skeleton, ~40 lines, MANDATORY)\n" in text
    assert "   ✓ justfile written (5 recipes, filled in for the stacks found here)\n" in text
    assert (
        "   ✓ .github/workflows/check.yml written (the check job, pinned to this version)\n"
    ) in text
    assert (repo / "CLAUDE.md").read_text() == skeletons.CLAUDE_MD


def test_running_the_project_setup_twice_changes_nothing_and_still_succeeds(
    repo, capsys, no_keyboard
):
    """Catches the second run crashing on a directory that is already there — the
    installer promises it is safe to run a thousand times."""
    init.project_step(init.parse(["--project", str(repo)]))
    result = init.project_step(init.parse(["--project", str(repo)]))
    assert result.outcome == "PASS"


def test_files_that_are_already_there_are_named_and_left_as_they_are(repo, capsys, no_keyboard):
    """Catches somebody's own CLAUDE.md being overwritten without being asked, and
    catches the list of what was spared going empty."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    (repo / "justfile").write_text("mine too\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo)]))
    assert (
        "   → left as is: CLAUDE.md, justfile. "
        "Nothing was written to them and nothing recorded that they were skipped.\n"
    ) in capsys.readouterr().err
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
    assert "unmanaged" not in capsys.readouterr().err


def test_the_files_the_installer_just_wrote_are_not_reported_as_left_as_is(
    repo, capsys, no_keyboard
):
    """One screen says "✓ AGENTS.md written" and the next says AGENTS.md was left as is.
    Both cannot be true, and the second one is the wrong half."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo)]))
    left = capsys.readouterr().err.split("   → left as is: ")[1].split(". Nothing")[0]
    assert left == "CLAUDE.md"


def test_an_overwritten_file_is_copied_to_a_timestamped_backup_first(repo, capsys, no_keyboard):
    """Catches a backup whose name has no timestamp in it, which means the second
    overwrite silently destroys the first backup — and a backup written beside the original
    at the repository root, where nothing ignores it and `git add -A` commits it."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo), "--overwrite", "CLAUDE.md"]))
    assert not [p for p in repo.iterdir() if p.name.startswith("CLAUDE.md.bak-")]
    backups = [p.name for p in (repo / ".ai" / "backups").iterdir()]
    assert len(backups) == 1
    assert re.fullmatch(r"CLAUDE\.md\.bak-\d{8}-\d{6}-\d{6}", backups[0])
    assert (repo / ".ai" / "backups" / backups[0]).read_text() == "mine\n"
    assert (repo / "CLAUDE.md").read_text() == skeletons.CLAUDE_MD
    assert f"   ✓ CLAUDE.md backup → .ai/backups/{backups[0]} written\n" in capsys.readouterr().err


def test_a_backup_makes_the_directory_it_needs_instead_of_assuming_it(tmp_path):
    """`.ai/backups/` is two levels under the root, and the file being replaced is offered
    before anything guarantees `.ai/` exists. A mkdir that does not create parents raises
    FileNotFoundError here — and the line after it is the one that overwrites the original,
    so the recovery path would be gone at exactly the moment it is needed."""
    from pathlib import Path

    (tmp_path / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    where = init.backup(tmp_path, tmp_path / "CLAUDE.md", SimpleNamespace(dry=False))
    assert Path(where).parts[:2] == (".ai", "backups")
    assert (tmp_path / where).read_text(encoding="utf-8") == "mine\n"


def test_two_overwrites_inside_one_second_leave_two_backups(repo, no_keyboard):
    """The docstring above says the timestamp is what stops the second overwrite
    destroying the first backup, and until the stamp had sub-second resolution that was
    the one thing it did not do. This is the test that makes it mean what it says."""
    for body in ("mine\n", "mine, edited again\n"):
        # Rewritten between the two runs on purpose: a file already holding exactly what we
        # would render is no longer offered, so without this the second run has nothing to
        # overwrite and this stops being a test about timestamps.
        (repo / "CLAUDE.md").write_text(body, encoding="utf-8")
        init.project_step(init.parse(["--project", str(repo), "--overwrite", "CLAUDE.md"]))
    backups = sorted((repo / ".ai" / "backups").iterdir())
    assert len(backups) == 2
    assert backups[0].read_text() == "mine\n"


WARNING = (
    "   ⚠ gitleaks is not on your PATH. While this repository is managed the shipped\n"
    "     pre-commit hook exits 1 on every commit until it is there: "
    "`brew install gitleaks`,\n"
    "     or your platform's package manager. This installs no binaries.\n"
)


@pytest.mark.parametrize("on_path, warns", [([], True), (["gitleaks"], False)])
def test_the_wall_the_repository_is_about_to_hit_is_named_now_not_at_the_next_commit(
    repo, capsys, no_keyboard, monkeypatch, on_path, warns
):
    """Wiring a project sets ai.managed, and the shipped pre-commit exits 1 when that flag
    is set and gitleaks is absent. So `ai-eng init` on a machine without it left a
    repository that refuses every commit from then on, and the first the person heard of
    it was their next commit. Nothing in init looked for the binary.

    The stand-in for `which` answers by name, so a lookup for anything other than gitleaks
    is a failure here rather than a warning nobody notices."""
    monkeypatch.setattr(
        init.shutil, "which", lambda name: f"/opt/bin/{name}" if name in on_path else None
    )
    init.project_step(init.parse(["--project", str(repo)]))
    assert (WARNING in capsys.readouterr().err) is warns


def test_the_stacks_it_found_are_named_and_it_installs_none_of_them(repo, capsys, no_keyboard):
    """Catches the stack line going blank or crashing, which is the one place the
    installer tells you it did not install your toolchain."""
    (repo / "pyproject.toml").touch()
    (repo / "package.json").touch()
    init.project_step(init.parse(["--project", str(repo)]))
    assert (
        "\n   Stacks detected: node, python. The justfile carries their lint, test and "
        "build commands; it installs none of the binaries they need.\n"
    ) in capsys.readouterr().err
    # And it is not just a sentence: the file it describes carries those commands.
    written = (repo / "justfile").read_text()
    assert "# Filled in for: node, python.\n" in written
    for command in ("npm run lint", "ruff check .", "npm test", "pytest -q"):
        assert f"\n    {command}\n" in written, command
    assert "TODO: your linter" not in written


def test_a_repository_with_no_marker_file_gets_no_stack_line(repo, capsys, no_keyboard):
    """Catches a stack being claimed for a repository that has nothing to claim it with."""
    init.project_step(init.parse(["--project", str(repo)]))
    assert "Stacks detected" not in capsys.readouterr().err
    written = (repo / "justfile").read_text()
    assert "# Filled in for:" not in written
    # Written out rather than read back from skeletons.TODOS: a loop over the same table
    # the renderer reads asserts that the file agrees with itself and nothing more.
    assert '\nlint:\n    @echo "TODO: your linter"\n' in written
    assert '\ntest:\n    @echo "TODO: your test runner"\n' in written
    assert '\nbuild:\n    @echo "TODO: compile, package, sign"\n' in written


@pytest.mark.parametrize("marker", ["thing.csproj", "Thing.sln"])
def test_a_dotnet_repository_is_recognised_by_a_name_nobody_can_write_down(repo, marker):
    """Every other stack is found by a fixed filename. .NET is found by a suffix, which is
    why this detector asks the directory instead of testing a path: `glob` answers for a
    literal too, so one call covers both kinds of marker and neither needs a branch."""
    (repo / marker).touch()
    assert init.stacks(repo) == ["dotnet"]


def test_the_ci_workflow_is_written_rather_than_pasted_and_nothing_goes_to_stdout(
    repo, capsys, no_keyboard
):
    """The workflow was printed at the reader under "Paste these lines into" — the one file
    this product asked a person to install by hand, and so the one step of an install that
    nothing afterwards could verify. It is a file now, written into a directory this creates
    if it has to, and stdout is empty because there is no longer anything to redirect."""
    result = init.project_step(init.parse(["--project", str(repo)]))
    assert result.outcome == "PASS"
    caught = capsys.readouterr()
    assert caught.out == ""
    assert "Paste these lines" not in caught.err
    written = (repo / ".github" / "workflows" / "check.yml").read_text()
    assert written == skeletons.CHECK_YML.format(version=__version__)
    assert written.startswith("name: check\non: [push, pull_request]\n")
    assert f"\n          PIN: {__version__}\n" in written


def test_a_project_dry_run_prints_the_plan_and_writes_no_file(repo, capsys, no_keyboard):
    """Catches --dry-run writing anyway, which is the one promise a preview makes."""
    result = init.project_step(init.parse(["--project", str(repo), "--dry-run"]))
    assert result.outcome == "WOULD_CHANGE"
    assert not (repo / ".ai").exists()
    assert not (repo / "specs").exists()
    assert not (repo / "CLAUDE.md").exists()
    assert "   · .ai/config.toml · .ai/.gitignore · specs/.gitkeep\n" in capsys.readouterr().err


def test_a_dry_run_never_says_anything_was_written(repo, capsys, no_keyboard):
    """The writes were guarded by the flag and the printing was not, so a dry run emitted
    "✓ CLAUDE.md backup → … written" and "✓ CLAUDE.md written" having written neither.
    The test beside this one asserted the files were absent and never that the output had
    stopped claiming otherwise, which is how it survived."""
    (repo / "CLAUDE.md").write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo), "--dry-run", "--overwrite", "all"]))
    text = capsys.readouterr().err
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
    text = capsys.readouterr().err
    assert "   · .ai/config.toml · .ai/.gitignore · specs/.gitkeep\n" in text
    assert f"   · core.hooksPath → {paths.git_hooks()}\n" in text
    for name, (becomes, _) in init.OFFERS.items():
        assert f"   · {name} would be created ({becomes})\n" in text


def framed(text: str) -> list[str]:
    """The panel's contents, with the border and its padding taken off. Asserting the box
    characters would pin rich's drawing rather than this product's words, and the widths
    move with the terminal; asserting nothing about the panel is how three of its lines
    went unheld the first time."""
    inside = text.split("╭─ Done ")[1].splitlines()[1:]
    return [row.strip("│").strip() for row in inside if row.startswith("│")]


def test_the_last_screen_says_what_happened_and_what_to_run_next(
    repo, capsys, no_keyboard, monkeypatch
):
    """The run used to end by pasting a block of YAML at the reader. A stranger who reads
    only the last screen now knows how many files were written, how many guard entries
    exist, and what to do — starting with the fact that the skeleton's TODO: markers are
    deliberate, and ending somewhere other than a command: the third step is the only one
    that says where the product actually gets used, and an install that never says it is an
    install nobody adopts. Every line is asserted, in order: a closing panel matched by two
    fragments is a closing panel most of which nothing is holding."""
    monkeypatch.setattr(init.shutil, "which", lambda name: f"/opt/bin/{name}")
    init.main(["--no-global", "--project", str(repo), "-y"])
    caught = capsys.readouterr()
    assert framed(caught.err) == [
        "8 files written · 0 guard entries on this machine",
        "",
        "Next:",
        "1. fill in the TODO: markers",
        "on purpose; `ai-eng doctor` fails until CONSTITUTION.md has none",
        "2. ai-eng doctor",
        "every assertion, and the coverage line under it",
        "3. open the agent you work in here",
        # `--no-global` placed no entry anywhere, and the first row of this same panel says
        # so. A step promising the guards are already loaded is that panel contradicting
        # itself two lines later, which is the one thing a last screen cannot do.
        "run `ai-eng init --global`: no guard is registered here yet",
        "4. ai-eng spec new <slug>",
        "or ask that agent for /ai-spec; the chain starts here",
    ]
    assert caught.err.rstrip().endswith("╯")


def test_the_step_that_says_where_to_go_names_the_surfaces_this_machine_has(
    repo, capsys, no_keyboard, monkeypatch
):
    """ "Open your editor" is advice; "open Claude Code" is an instruction. The names are
    read from the wiring table, so a surface added there arrives on this line without
    anybody remembering to add it — and at most two of them, because this is one line inside
    a panel and a third name wraps it into an item of its own."""
    # Zed is first and takes no guard entry: a surface that cannot be wired must not be
    # offered as the place the guards are already loaded, which is what this line claims.
    rows = [{"name": "Zed", "writer": "none"}] + [
        {"name": name, "writer": "json_claude"} for name in ("Claude Code", "Cursor", "Pi")
    ]
    monkeypatch.setattr(init.wiring, "detect", lambda only=None: rows)
    monkeypatch.setattr(init.shutil, "which", lambda name: f"/opt/bin/{name}")
    init.main(["--no-global", "--project", str(repo), "-y"])
    assert "3. open Claude Code or Cursor here" in framed(capsys.readouterr().err)


@pytest.mark.parametrize(
    ("guards", "line"),
    [
        (1, "the guards are already loaded there — nothing else to start"),
        (0, "run `ai-eng init --global`: no guard is registered here yet"),
    ],
    ids=["a machine that was wired", "a machine that was not"],
)
def test_the_step_that_says_where_to_go_agrees_with_the_row_above_it(guards, line):
    """The panel's first row counts the guard entries on this machine, and this step is the
    only other line on the screen that talks about them. Saying the guards are loaded over a
    row reading `0 guard entries` is a screen arguing with itself, and it is the last screen
    of the install — the one a stranger reads instead of everything above it."""
    assert init.opened(guards)[1] == line


def test_the_last_screen_counts_the_guard_entries_that_are_actually_there(
    repo, home, capsys, no_keyboard, monkeypatch
):
    """Two numbers, and neither of them is a constant. The guard count comes from the
    receipt, which is the only record of what the machine half placed — and it reads
    "1 guard entry", because a closing panel that says "1 entries" was written by nobody."""
    monkeypatch.setattr(init.shutil, "which", lambda name: f"/opt/bin/{name}")
    init.main(["--global", "--harness", "claude-code", "--project", str(repo), "-y"])
    assert framed(capsys.readouterr().err)[0] == ("8 files written · 1 guard entry on this machine")


def test_a_run_that_overwrites_counts_the_files_it_overwrote(
    repo, capsys, no_keyboard, monkeypatch
):
    """Catches the count losing the overwrite branch, which is the half of the number a
    fresh repository can never exercise."""
    monkeypatch.setattr(init.shutil, "which", lambda name: f"/opt/bin/{name}")
    for name in ("CLAUDE.md", "justfile"):
        (repo / name).write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo), "--overwrite", "all"]))
    assert framed(capsys.readouterr().err)[0].startswith("8 files written · ")


def test_what_is_still_on_a_person_reaches_the_last_screen(repo, capsys, no_keyboard, monkeypatch):
    """The inline warnings scroll away. A closing panel that omits them is the same
    silence one screen later. Two files, so the separator between them is held too."""
    monkeypatch.setattr(init.shutil, "which", lambda name: None)
    for name in ("justfile", "CLAUDE.md"):
        (repo / name).write_text("mine\n", encoding="utf-8")
    init.project_step(init.parse(["--project", str(repo), "-y"]))
    assert framed(capsys.readouterr().err)[1:3] == [
        "⚠ still on you: install gitleaks, or every commit here is refused",
        "⚠ still on you: 2 of your own files were left alone: CLAUDE.md, justfile",
    ]


# ── main ────────────────────────────────────────────────────────────────────────────


def test_main_runs_the_machine_step_then_the_project_step_and_returns_incomplete_intent(
    repo, capsys, no_keyboard
):
    """The install runs, but missing user-owned Intent cannot become a green result."""
    result = init.main(["--no-global", "--project", str(repo)])
    assert result.outcome == "INCOMPLETE"
    text = capsys.readouterr().err
    assert "\n◇ Project" in text
    assert "\n◇ Global" not in text


def test_init_can_be_run_twice_on_a_machine_it_already_set_up(home, monkeypatch):
    """The front door only opened once. `init` writes the skills into the application home
    and symlinks each surface root at *that*, then its own safety check compares those
    symlinks against `paths.skills()` — the source tree in a checkout, site-packages in a
    wheel. Neither can ever equal the store `init` just created, so every second run on
    every machine returned `_global_paths_safe() is False`.

    What that looks like to a person: `ai-eng init` prints `INCOMPLETE — The framework
    cannot decide or prove the claim`, with no surface table, no reason and no cure. It was
    measured on the operator's own machine minutes after a successful install, on the exact
    command that had worked.

    A guard that fails closed for the wrong reason and says nothing is the failure this
    product exists to cure, sitting in the only verb that installs it."""

    store = paths.home() / "skills"
    store.mkdir(parents=True)
    surfaces = home / ".config" / "opencode" / "skills"
    surfaces.mkdir(parents=True)
    for source in paths.skills().glob("ai-*"):
        (store / source.name).mkdir(exist_ok=True)
        (surfaces / source.name).symlink_to(store / source.name)

    args = init.parse(["--global", "--no-project", "--harness", "opencode", "--dry-run"])
    monkeypatch.setattr(
        init.wiring,
        "detect",
        lambda only=None: [
            {"id": "opencode", "settings": "", "writer": "ts_opencode", "skills": str(surfaces)}
        ],
    )
    monkeypatch.setattr(
        init,
        "_receipt_state",
        lambda: {"wrote": [{"path": str(store), "kind": "skills", "how": "wheel"}]},
    )
    assert init._global_paths_safe(args) == [], (
        "a machine this verb installed itself cannot be one it refuses to look at, and it "
        "has nobody else's skill folder in it either"
    )
