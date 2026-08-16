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


def test_a_folder_this_install_never_wrote_is_still_refused_and_says_why(
    stranger, monkeypatch, capsys
):
    """The other side of it. An empty directory has nothing to lose; one with somebody
    else's file in it is theirs, and refusing is right — refusing in silence is not."""

    from ai_engineering import paths

    root = Path.home() / ".claude" / "skills"
    for source in sorted(paths.skills().glob("ai-*")):
        (root / source.name).mkdir(parents=True)
    stranger_file = root / "ai-spec" / "somebody-elses.md"
    stranger_file.write_text("not ours\n", encoding="utf-8")

    result = init.main(["--global", "--project", ".", "-y"])
    printed = capsys.readouterr().err

    assert result.outcome == "INCOMPLETE"
    assert "not this installer's to write" in printed
    assert stranger_file.read_text(encoding="utf-8") == "not ours\n"
