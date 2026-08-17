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
    total = sum(
        len(skill["claims"]) + len(skill["refusals"]) + len(skill["takes"]) + len(skill["sends"])
        for skill in found.values()
    )
    assert f"RAN skilleval={total}" in done.stdout
    assert "labelled cases beside them" in done.stdout
    assert f"{len(found)} skills route" in done.stdout

    # The map, printed. `phase` is declared for a person meeting the catalogue with no idea
    # what any of it is for, and a field no command ever shows that person answers nobody.
    # Read from the manifest here rather than restated, so a phase moving there moves this.
    import tomllib

    declared = tomllib.loads((ROOT / "policy" / "capabilities.toml").read_text(encoding="utf-8"))
    for row in declared["capabilities"]:
        line = next(
            one for one in done.stdout.splitlines() if one.strip().startswith(str(row["phase"]))
        )
        assert str(row["id"]) in line, (row["id"], row["phase"])

    # And a hand-off that leaves the framework is visible rather than silent.
    assert "hand-offs leave the framework" in done.stdout
    assert "that is just check in CI" in done.stdout


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
    broken["ai-debug"]["refusals"].append(("designing the fix", "   "))
    assert any("names nowhere to take it" in line for line in skill_eval.problems(broken))


def test_a_hand_off_out_of_the_framework_is_legal_and_counted():
    """Three of these are written today and none has a skill, because no skill owns the
    repository's documentation, the person saying go, or the gate in CI. Requiring one would
    have made this harness demand a fake route to satisfy itself. So it stays legal — and it
    is printed, because a hand-off nobody can see reads as an absence."""
    fine = copy.deepcopy(corpus())
    fine["ai-debug"]["refusals"].append(("running the gates", "that is just check in CI"))
    assert skill_eval.problems(fine) == []


def test_the_extraction_reads_the_shapes_the_tree_actually_writes():
    """The layer every other fixture skipped. Each of these mutates the parsed dictionary,
    so for a while nothing exercised the reading of a `SKILL.md` at all — and the reading is
    where the defect was: the pattern demanded the word "use" after the dash, so five of the
    thirty-one written refusals were invisible, including the one that names no skill, which
    is the case the rule exists for. A rule that cannot see its own input is the thing this
    repository is named after."""
    written = 0
    for folder in sorted((ROOT / ".agents" / "skills").iterdir()):
        body = (folder / "SKILL.md").read_text(encoding="utf-8")
        text = skill_eval.description(body)
        assert text, folder.name
        assert skill_eval._TRIGGER.findall(text), f"{folder.name} declares no trigger phrase"

        # Every clause the file writes is a clause the harness reads. Counted from the file
        # rather than from the parser, which is the only way the two can disagree.
        import re

        clauses = re.findall(r"Not for [^.]*\.", text)
        assert len(clauses) == len(skill_eval._REFUSAL.findall(text)), (
            f"{folder.name}: {len(clauses)} refusals written, "
            f"{len(skill_eval._REFUSAL.findall(text))} read"
        )
        written += len(clauses)
    assert written >= 30, written

    # And a file with no frontmatter description at all yields nothing rather than raising.
    assert skill_eval.description("# just a heading\n") == ""


def test_it_reads_the_tree_it_is_pointed_at(tmp_path):
    """`corpus` takes a root, and this is what proves the parameter is wired: the default is
    read on the call rather than bound to the signature, so pointing it elsewhere reads
    elsewhere. Before that fix it went on reading this repository and would have reported a
    pass about a corpus it never opened."""
    body = (ROOT / ".agents" / "skills" / "ai-debug" / "SKILL.md").read_text(encoding="utf-8")
    (tmp_path / "ai-debug").mkdir()
    (tmp_path / "ai-debug" / "SKILL.md").write_text(body, encoding="utf-8")

    assert sorted(skill_eval.corpus(tmp_path)) == ["ai-debug"]
    assert len(skill_eval.corpus()) > 1


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


# The labelled sample, and one fixture per rule it answers. Every case below is a real shape
# a corpus can take, and each one is defensible in the file it lives in — which is why
# nothing that reads one file at a time could ever have caught it.
def test_the_labelled_cases_are_read_off_the_files_that_hold_them():
    """The sample is real and it is the one the admission gate already demands. Counted from
    the files rather than written down here, because a number typed into a test is the same
    defect one file further along."""
    found = corpus()
    assert sum(len(skill["takes"]) for skill in found.values()) >= 70
    assert sum(len(skill["sends"]) for skill in found.values()) >= 80

    # And the labels are labels: most refusals name the skill that should have the case.
    named = [target for skill in found.values() for _, target in skill["sends"] if target]
    assert len(named) >= 60
    assert set(named) <= set(found)


def test_two_skills_taking_one_case_is_a_fork_the_descriptions_cannot_show():
    broken = copy.deepcopy(corpus())
    borrowed = broken["ai-report"]["takes"][0]
    broken["ai-debug"]["takes"].append(borrowed)
    found = skill_eval.problems(broken)
    assert any("both take the case" in line for line in found), found


def test_a_case_both_skills_refuse_leaves_the_person_who_wrote_it_nowhere():
    """The one this exists to catch. `ai-report` sends "this is failing, work out why" to
    `/ai-debug`; if `ai-debug` also refused it, each file would still read correctly on its
    own and the person who typed the sentence would have two skills declining it."""
    broken = copy.deepcopy(corpus())
    case, target = next((case, target) for case, target in broken["ai-report"]["sends"] if target)
    broken[target]["sends"].append((case, "ai-report"))
    found = skill_eval.problems(broken)
    assert any("which refuses it too" in line for line in found), found


def test_a_case_sent_to_a_skill_that_is_not_there_is_a_dead_end():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["sends"].append(("naming the release", "ai-release"))
    assert any("which is not a skill" in line for line in skill_eval.problems(broken))


def test_a_skill_that_takes_and_refuses_the_same_case_contradicts_itself():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["sends"].append((broken["ai-debug"]["takes"][0], "ai-plan"))
    assert any("both takes and refuses" in line for line in skill_eval.problems(broken))


def test_a_case_sent_to_itself_is_a_loop():
    broken = copy.deepcopy(corpus())
    broken["ai-debug"]["sends"].append(("designing the fix", "ai-debug"))
    assert any("to itself" in line for line in skill_eval.problems(broken))


def test_a_corpus_row_that_is_not_a_quoted_case_is_skipped_and_not_guessed_at(tmp_path):
    """Inventing a label out of unquoted prose would put this harness in the business of
    deciding what somebody meant. The admission gate already refuses a corpus with no rows,
    so silence here cannot hide an empty file."""
    (tmp_path / "corpus.md").write_text(
        '## Routes here\n\n- a sentence with no quotes\n- "a real case" — and why\n\n'
        "## Refuses\n\n- prose\n",
        encoding="utf-8",
    )
    read = skill_eval.cases(tmp_path)
    assert read == {"takes": ["a real case"], "sends": []}

    # A skill directory with no corpus at all reads as no cases rather than raising: the
    # admission gate in `contract.audit_one` is what refuses that, and two checks refusing
    # the same thing in different words is one of them going stale.
    assert skill_eval.cases(tmp_path / "nothing-here") == {"takes": [], "sends": []}
