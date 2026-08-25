"""The four smell rules of spec 027, as tests that fail.

A contract rule that exists only as a sentence is the failure family this repository
exists to kill, so each of the four smell classes gets a red case here before it is
hooked into `contract.audit_one`. Each test mutates a copy of a skill pair the way
`skill_eval.py` mutates the corpus, and asserts the audit catches it: a harness tested
only on the corpus that already passes is a harness nobody has seen say no.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering import contract


def _skill(tmp_path: Path, body: str, corpus: str | None = None) -> Path:
    """One temp skill directory with a minimal SKILL.md (and corpus.md when given)."""
    folder = tmp_path / "ai-fake"
    folder.mkdir(exist_ok=True)
    (folder / "SKILL.md").write_text(body, encoding="utf-8")
    if corpus is not None:
        (folder / "corpus.md").write_text(corpus, encoding="utf-8")
    return folder / "SKILL.md"


SKILL_HEADER = """---
name: ai-fake
description: Does it. Not for the other thing — use /ai-x.
license: Apache-2.0
---

# ai-fake

"""


# --- Task 1: portable-command rule -------------------------------------------


def test_portable_rule_accepts_only_ai_eng_verbs(tmp_path):
    """A skill that runs the tool the wheel guarantees passes."""
    skill = _skill(
        tmp_path,
        SKILL_HEADER
        + "## Done when\n\nRun `ai-eng spec show 003 --task 2` and paste the output.\n",
    )
    problems = contract.audit_one(skill)
    assert not any("repo-specific command" in p for p in problems), problems


def test_portable_rule_rejects_a_bare_just_recipe(tmp_path):
    """A skill that tells a downstream repo to `just check` refuses."""
    skill = _skill(tmp_path, SKILL_HEADER + "## Done when\n\nRun `just check` and show it.\n")
    problems = contract.audit_one(skill)
    assert any("repo-specific command" in p and "just check" in p for p in problems), problems


def test_portable_rule_rejects_a_bare_scanner(tmp_path):
    """A skill that runs bare semgrep or git grep refuses."""
    skill = _skill(
        tmp_path, SKILL_HEADER + "\n## Done when\n\nRun `semgrep` over the tree.\n"
    )
    problems = contract.audit_one(skill)
    assert any("repo-specific command" in p and "semgrep" in p for p in problems), problems

    skill2 = _skill(
        tmp_path, SKILL_HEADER + "\n## Done when\n\nRun `git grep` over docs/notes/.\n"
    )
    problems2 = contract.audit_one(skill2)
    assert any("repo-specific command" in p for p in problems2), problems2


def test_portable_rule_checks_corpus_md_too(tmp_path):
    """The rule reads corpus.md, not just SKILL.md — the council's finding."""
    skill = _skill(
        tmp_path,
        SKILL_HEADER + "\n## Done when\n\nRun `ai-eng audit verify`.\n",
        corpus="## Routes here\n\nrun `just check` now\n\n## Refuses\n\nrefuse it\n",
    )
    problems = contract.audit_one(skill)
    assert any("corpus.md" in p and "repo-specific command" in p for p in problems), problems


def test_portable_rule_passes_a_bare_mention_without_a_run_cue(tmp_path):
    """'the just recipe' is a reference, not a command, and passes."""
    skill = _skill(
        tmp_path,
        SKILL_HEADER + "\n## Done when\n\nThe `just` recipe stays with the maintainer.\n",
    )
    problems = contract.audit_one(skill)
    assert not any("repo-specific command" in p for p in problems), problems