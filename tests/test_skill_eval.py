"""The routing evaluation, held to every refusal it claims to make.

Each case mutates a copy of the corpus and asserts the harness catches it. A harness tested
only on the corpus that already passes is a harness nobody has seen say no, which is the
whole class of defect this repository exists to remove.
"""

from __future__ import annotations

import copy
import subprocess
import sys
from pathlib import Path

import skill_eval

ROOT = Path(__file__).resolve().parents[1]


def corpus() -> dict:
    return skill_eval.corpus()


def test_the_corpus_this_repository_ships_routes():
    assert skill_eval.problems(corpus()) == []


def test_it_runs_as_a_command_and_says_what_it_did_not_evaluate():
    """`just check` runs this file, so it has to answer as a process and not only as an
    import — and it prints what it did not measure, because a green from a harness named
    after evaluation reads as an evaluation of the writing until it says otherwise."""
    done = subprocess.run(
        [sys.executable, str(ROOT / "tests" / "skill_eval.py")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert "RAN skilleval=" in done.stdout
    assert "whether a skill's instructions are any good" in done.stdout

    # The score is read off the corpus rather than typed here: a number in a test is the
    # same defect one file further along.
    found = corpus()
    total = sum(len(skill["claims"]) + len(skill["refusals"]) for skill in found.values())
    assert f"RAN skilleval={total}" in done.stdout
    assert f"{len(found)} skills route" in done.stdout


def test_a_skill_that_claims_nothing_is_a_skill_nothing_reaches():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["claims"] = []
    assert any("claims no situation" in line for line in skill_eval.problems(broken))


def test_a_skill_that_refuses_nothing_is_the_answer_to_everything():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["refusals"] = []
    assert any("refuses nothing" in line for line in skill_eval.problems(broken))


def test_two_skills_claiming_one_situation_is_a_fork_with_no_rule():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["claims"].append("review this")
    found = skill_eval.problems(broken)
    assert any("both claim" in line for line in found), found


def test_a_claim_contained_in_another_is_the_same_fork_one_word_longer():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["claims"].append("please review this now")
    found = skill_eval.problems(broken)
    assert any("one contains the other" in line for line in found), found


def test_a_refusal_to_a_skill_that_is_not_there_is_a_dead_end():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["refusals"].append(("naming the release", "/ai-release"))
    assert any("which is not a skill" in line for line in skill_eval.problems(broken))


def test_a_refusal_to_a_verb_this_cli_does_not_have_is_a_dead_end_too():
    """`ai-security` sends an accepted risk to `ai-eng accept`, so a refusal can name a
    command rather than a skill — and a command is a route worth exactly as much as the
    verb existing."""
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["refusals"].append(("accepting a risk", "`ai-eng absolve`"))
    assert any("not a verb this CLI has" in line for line in skill_eval.problems(broken))

    fine = copy.deepcopy(corpus())
    fine["ai-debug"]["refusals"].append(("accepting a risk", "`ai-eng accept`"))
    assert skill_eval.problems(fine) == []


def test_a_skill_refusing_work_to_itself_is_a_loop():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["refusals"].append(("designing the fix", "/ai-debug"))
    assert any("to itself" in line for line in skill_eval.problems(broken))


def test_a_refusal_that_names_nowhere_is_not_a_route():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["refusals"].append(("designing the fix", "somebody else"))
    assert any("names nowhere to take it" in line for line in skill_eval.problems(broken))


def test_a_third_skill_claiming_what_a_refusal_sends_elsewhere_is_a_disagreement():
    """The one this exists to catch. `ai-ship` sends the bug to `/ai-debug`; if `ai-explore`
    started claiming "finding the bug" as its own trigger, both files would be green on
    their own and the reader would have two answers with nothing to choose between them."""
    broken = copy.deepcopy(corpus())
    broken["ai-explore"]["claims"].append("finding the bug")
    found = skill_eval.problems(broken)
    assert any("but ai-explore claims" in line for line in found), found


def test_a_verb_target_is_checked_against_the_cli_and_not_a_list_here():
    """The verbs come from the package that defines them. A copy of that list in this file
    would pass for as long as it took somebody to rename a verb."""
    from ai_engineering import cli

    assert skill_eval.verbs() == set(cli.VERBS)
    assert "accept" in skill_eval.verbs()


def test_a_skill_the_manifest_never_declared_is_refused(tmp_path, monkeypatch):
    """The contradiction an audit already found once between these two files, from the other
    side: the manifest is the only place the capabilities are enumerated, and a skill nobody
    declared is one nothing admitted."""
    monkeypatch.setattr(skill_eval, "SKILLS", tmp_path)
    for name in ("ai-debug", "ai-invented"):
        body = (ROOT / ".agents" / "skills" / "ai-debug" / "SKILL.md").read_text(encoding="utf-8")
        (tmp_path / name).mkdir()
        (tmp_path / name / "SKILL.md").write_text(body, encoding="utf-8")

    assert skill_eval.main() == 1


def test_an_empty_corpus_evaluates_nothing_and_says_so(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_eval, "SKILLS", tmp_path)
    assert skill_eval.main() == 1
