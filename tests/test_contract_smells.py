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


# --- Task 2: existence-check rule -------------------------------------------


def test_existence_rule_rejects_a_ref_without_a_fail_closed_clause(tmp_path):
    """A skill that names policy/threat-model.toml as if it is always there refuses."""
    skill = _skill(
        tmp_path,
        SKILL_HEADER + "\n## Steps\n\n1. Read `policy/threat-model.toml` for the boundary.\n",
    )
    problems = contract.audit_one(skill)
    assert any("fail-closed" in p and "policy/threat-model.toml" in p for p in problems), problems


def test_existence_rule_passes_a_ref_with_a_fail_closed_clause(tmp_path):
    """The ai-spec pattern — ref plus 'if absent, refuse' — passes."""
    skill = _skill(
        tmp_path,
        SKILL_HEADER
        + "\n## Steps\n\n1. Read `policy/threat-model.toml`; if it is absent, refuse to continue.\n",
    )
    problems = contract.audit_one(skill)
    assert not any("fail-closed" in p for p in problems), problems


def test_existence_rule_checks_corpus_md_and_sibling_references(tmp_path):
    """corpus.md refs and ai-/references/ cross-skill refs are read too."""
    skill = _skill(
        tmp_path,
        SKILL_HEADER + "\n## Done when\n\nRun `ai-eng audit verify`.\n",
        corpus="## Routes here\n\n- read `ai-review/references/testing.md`\n\n## Refuses\n\n- refuse it\n",
    )
    problems = contract.audit_one(skill)
    assert any("fail-closed" in p and "testing.md" in p for p in problems), problems


def test_existence_rule_passes_a_skills_own_references_subfolder(tmp_path):
    """The skill's own references/ ships with it and is not a dependency."""
    skill = _skill(
        tmp_path,
        SKILL_HEADER + "\n## Steps\n\n1. Work the checklists in `references/`.\n",
    )
    problems = contract.audit_one(skill)
    assert not any("fail-closed" in p for p in problems), problems