"""The one command a stranger runs first, with both halves in one invocation.

`ai-eng init --global --project . -y` is what the install matrix runs on three operating
systems, and no test here had ever run both halves together — the suite covered the machine
half and the repository half separately, each with the other switched off. So the outcome of
the command a stranger actually types was unmeasured, and the first run of it that anybody
watched was on a CI runner.

Everything lands under `tmp_path` with `HOME` and `AI_ENGINEERING_HOME` redirected, which is
how every other installer test here isolates itself: nothing touches the machine running it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering import init, outcome


@pytest.fixture
def stranger(tmp_path, monkeypatch):
    """A machine with nothing on it, and a repository with one commit made before us."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(home / ".ai-engineering"))

    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "--quiet", "-b", "main", str(root)], check=True)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.email=stranger@example.com",
            "-c",
            "user.name=stranger",
            "commit",
            "--quiet",
            "-m",
            "chore: seed",
        ],
        check=True,
        capture_output=True,
    )
    monkeypatch.chdir(root)
    return root


def test_both_halves_in_one_command_report_one_outcome(stranger, capsys):
    """The exact argv the install matrix runs, and the exact thing it checks: an outcome a
    person can act on, and the files that outcome claims."""

    # `.` and not an absolute path: the matrix passes a dot, and the two travel different
    # code paths through the preflight. A test that passed the resolved path would be
    # testing the argv nobody types.
    result = init.main(["--global", "--project", ".", "-y"])
    printed = capsys.readouterr().err

    assert type(result) in (outcome.Result, outcome.Execution)
    assert (stranger / ".ai" / "config.toml").is_file(), "the pin was never written"
    assert (stranger / "CONSTITUTION.md").is_file(), "identity was never written"
    assert "files written" in printed, "the closing report never printed"

    # INCOMPLETE, and for one nameable reason. A repository with no Intent is not a
    # governed repository, and this verb will not say PASS over one — but until now it said
    # so with `INTENT_SCHEMA_INVALID`, a schema failure in a file nobody had written. The
    # code is what a person acts on, so the code is what this asserts.
    from ai_engineering import intent

    assert result.outcome == "INCOMPLETE"
    state = intent.validate(stranger / ".ai" / "intent.md", stranger)
    assert state.code == intent.MISSING[0], state.code
    assert not (stranger / ".ai" / "intent.md").exists()


def test_an_intent_that_is_absent_and_one_that_is_malformed_are_two_answers(stranger):
    """The distinction this install had lost. `claim_scope_guard` refuses to call unreadable
    and absent the same thing one directory over; this is the same rule, on the record that
    decides whether a repository is governed at all."""

    from ai_engineering import intent

    absent = intent.validate(stranger / ".ai" / "intent.md", stranger)
    assert absent.code == "INTENT_MISSING"

    (stranger / ".ai").mkdir(exist_ok=True)
    (stranger / ".ai" / "intent.md").write_bytes(b'{"user_owned":"not an Intent"}\n')
    malformed = intent.validate(stranger / ".ai" / "intent.md", stranger)
    assert malformed.code == "INTENT_SCHEMA_INVALID"


def test_the_matrix_runs_this_exact_command(stranger):
    """The argv above is the matrix's argv. A test that drifted from it would be a test of
    something nobody runs."""

    matrix = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "install-matrix.yml"
    ).read_text(encoding="utf-8")
    assert "ai-eng init --global --project . -y" in matrix


def test_a_skills_root_that_already_holds_empty_folders_does_not_stop_the_install(
    stranger, monkeypatch, capsys
):
    """What the install matrix does on purpose, and what it found.

    It creates `~/.claude/skills/ai-*` before installing, to force the copy path that
    Windows takes on every platform. Those empty directories made `_global_paths_safe`
    refuse, so `init` returned INCOMPLETE having written nothing and printed no reason —
    on all three operating systems, in the smoke test for the command a stranger runs
    first."""

    from ai_engineering import paths

    root = Path.home() / ".claude" / "skills"
    for source in sorted(paths.skills().glob("ai-*")):
        (root / source.name).mkdir(parents=True)

    init.main(["--global", "--project", ".", "-y"])

    assert (stranger / ".ai" / "config.toml").is_file(), capsys.readouterr().err[-500:]
    assert (Path.home() / ".claude" / "settings.json").is_file()


def test_a_folder_this_install_never_wrote_is_named_and_skipped_and_the_rest_install(
    stranger, monkeypatch, capsys
):
    """The other side of it, and the assertion this test used to make was the defect.

    It asserted INCOMPLETE over one foreign directory, with a docstring arguing that
    refusing was right. It passed in 0.18s while a real machine could not install at all:
    one folder named `ai-design`, owned by the person four weeks before this repository
    shipped a skill of that name, refused eight surfaces and named no path. A skills root
    is shared — eighteen `ai-*` skills from other publishers sat in that one. Their folder
    is theirs, so it is skipped and printed; the other fifteen are ours to install."""

    from ai_engineering import paths

    root = Path.home() / ".claude" / "skills"
    for source in sorted(paths.skills().glob("ai-*")):
        (root / source.name).mkdir(parents=True)
    stranger_file = root / "ai-spec" / "somebody-elses.md"
    stranger_file.write_text("not ours\n", encoding="utf-8")

    init.main(["--global", "--project", ".", "-y"])
    printed = capsys.readouterr().err

    assert str(root / "ai-spec") in printed, printed[-800:]
    assert stranger_file.read_text(encoding="utf-8") == "not ours\n"
    # Skipped, not merged: `link` copies into a directory that already exists, so the
    # failure this guards against is our SKILL.md landing on top of theirs.
    assert not (root / "ai-spec" / "SKILL.md").exists()
    # And the whole point — one collision costs one skill, not the machine.
    landed = sorted(p.name for p in root.glob("ai-*") if (p / "SKILL.md").exists())
    assert len(landed) == len(list(paths.skills().glob("ai-*"))) - 1, landed
    assert (Path.home() / ".claude" / "settings.json").is_file()


def test_the_first_spec_names_the_missing_intent_rather_than_a_path(stranger, capsys):
    """The command `init` closes by recommending, on the machine `init` just set up.

    It answered "filesystem resolved a missing or differently spelled entry" — true about a
    path and useless about a decision. A spec is a decision inside a Solution Intent, this
    repository has none yet, and that is the ordinary state of every repository on its first
    day. The refusal says so and names what to write."""

    from ai_engineering import spec

    init.main(["--global", "--project", ".", "-y"])
    capsys.readouterr()

    result = spec.main(["new", "first-thing"])
    printed = capsys.readouterr().out

    assert result.outcome == "INCOMPLETE"
    assert "no Solution Intent here yet" in printed
    assert not list((stranger / "specs").glob("*first-thing")), "a spec was published anyway"


def test_uninstall_refuses_without_a_keyboard_and_removes_nothing(stranger, monkeypatch, capsys):
    """The gate no test had exercised outside a faked terminal, on a real install.

    `-y` does not substitute for a keyboard here — `test_uninstall_is_explicit` pins that,
    and it stands. What this adds is the same refusal against a repository this session
    actually installed into, and the proof that a refusal removes nothing."""

    import sys

    from ai_engineering import uninstall, wiring

    init.main(["--global", "--project", ".", "-y"])
    capsys.readouterr()
    before = wiring.receipt().get("wrote")
    assert before, "the install wrote nothing, so this proves nothing"

    class NoTerminal:
        def isatty(self):
            return False

    monkeypatch.setattr(sys, "stdin", NoTerminal())
    refused = uninstall.main(["--project", "-y"])

    assert refused.outcome == "INCOMPLETE"
    assert "requires a person at a keyboard" in capsys.readouterr().out
    assert wiring.receipt().get("wrote") == before, "a refusal changed the receipt"


def test_a_real_install_writes_a_real_router_and_doctor_reads_it_back(stranger, monkeypatch):
    """The proof every other router fixture does not give.

    All of them plant a fabricated surface `{"id": "invented", "commands": tmp_path}`, which
    proves the generator works and says nothing about whether `ai-eng init` ever reaches it.
    An independent reader pointed that out: on a machine where the install ran, assertion 24
    still answered "no router has been written here". A generator nothing calls is the same
    shape as a contract nothing reads, and this file has spent a week on those.

    So: a real `init` on a stranger's machine, and the router read back off the receipt by
    the check that is supposed to notice it.
    """

    from ai_engineering import doctor, paths, wiring

    (Path.home() / ".claude").mkdir(parents=True, exist_ok=True)  # the surface is detected
    init.main(["--global", "--project", ".", "-y"])

    recorded = [row for row in wiring.receipt().get("wrote", []) if row.get("kind") == "router"]
    assert recorded, "the install wrote no router on a machine where Claude Code is present"

    expected = {f"{skill.name}.md" for skill in paths.skills().glob("ai-*")}
    assert {Path(row["path"]).name for row in recorded} == expected
    for row in recorded:
        assert Path(row["path"]).is_file()
        assert Path(row["path"]).parent == Path.home() / ".claude" / "commands"

    # And the check that reads them back agrees, on the same machine, with no argument.
    assert doctor.routers_intact(stranger) is None


# ── D-024-02: context-aware init ─────────────────────────────────────────────────────
# The split stops needing to be remembered: inside a repository with a person answering it
# offers the project step; outside a repository it does global only; `-y` stays a promise
# about the machine and never turns the project half on. Spec 024 example 2 pins these
# three behaviours.


class _Tty:
    def isatty(self) -> bool:
        return True


@pytest.fixture
def tty(monkeypatch):
    import sys

    monkeypatch.setattr(sys, "stdin", _Tty())


@pytest.fixture
def typed(monkeypatch):
    import builtins

    box = {"prompts": [], "replies": []}

    def fake_input(prompt=""):
        box["prompts"].append(prompt)
        return box["replies"].pop(0) if box["replies"] else "y"

    monkeypatch.setattr(builtins, "input", fake_input)
    return box


def test_bare_init_inside_a_repo_offers_the_project_step(stranger, tty, typed, capsys):
    result = init.main(["--harness", "claude-code"])
    # The stranger repo carries no canonical Intent, so the honest terminal outcome is
    # INCOMPLETE ("a repository without its canonical Intent is not a governed one", the
    # product's own gate). What D-024-02 pins is the offer, not that gate: the project
    # step asked, and the files were written on the yes.
    assert result.outcome == "INCOMPLETE", result.as_dict()
    asked = "".join(typed["prompts"])
    assert "Set up this project too?" in asked, asked
    assert (stranger / "AGENTS.md").is_file()


def test_bare_init_outside_a_repo_does_global_only(tmp_path, monkeypatch, capsys):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(home / ".ai-engineering"))
    monkeypatch.chdir(tmp_path)
    result = init.main(["--harness", "claude-code", "-y"])
    assert result.outcome == "PASS", result.as_dict()
    out = capsys.readouterr().err
    assert "Set up this project too?" not in out
    assert not list(tmp_path.glob("AGENTS.md"))


def test_bare_init_dash_y_in_a_repo_stays_global_only(stranger, tty, capsys):
    # On a real terminal the machine half's default is yes, and the project half used to
    # inherit it: `-y` then set up whatever repository the person happened to be standing
    # in. D-024-02 pins that `-y` stays a promise about the machine only.
    result = init.main(["--harness", "claude-code", "-y"])
    assert result.outcome == "PASS", result.as_dict()
    assert not (stranger / "AGENTS.md").is_file()
    assert not (stranger / "CONSTITUTION.md").is_file()
