"""Tests for spec 032 / B-032-1..4: the standard skill-craft contract.

Four checked rules in `contract.audit_one`, added the way spec 027 added its smell rules:
anti-rationalization (a skill names an excuse and answers it factually), output contract
(## What it produces names the artifact), Incorrect/Correct pairs (where a rules section
exists), and load tiers (body ≤500 lines, scripts in scripts/). One rule per fixture case.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import contract  # noqa: E402


def _skill(tmp_path: Path, name: str, body: str, *, description: str = "") -> Path:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    desc = description or "Does X. Not for Y — use /ai-other."
    p.write_text(
        f'---\nname: {name}\ndescription: >-\n  {desc}\nlicense: Apache-2.0\n---\n\n{body}',
        encoding="utf-8",
    )
    (d / "corpus.md").write_text(
        "# Corpus: " + name + "\n\n## Routes here\n\n- \"a job for this skill\" — taken.\n\n"
        "## Refuses\n\n- \"a job for another skill\" — use /ai-other.\n",
        encoding="utf-8",
    )
    return p


def test_anti_without_section_is_refused(tmp_path):
    """B-032-1: a skill with no anti-rationalization section is refused."""
    p = _skill(
        tmp_path,
        "ai-demo",
        "# Do the thing\n\n## What it produces\n\n`out/result.md`\n",
    )
    problems = contract.audit_one(p)
    assert any("anti" in prob or "rationaliz" in prob for prob in problems), problems


def test_anti_section_that_answers_an_excuse_passes(tmp_path):
    p = _skill(
        tmp_path,
        "ai-demo",
        "# Do the thing\n\n## What it produces\n\n`out/result.md`\n\n"
        "## What this is not\n\n- \"It's simple\" — then it is fast to prove; do it now.\n",
    )
    problems = contract.audit_one(p)
    assert not any("anti" in prob or "rationaliz" in prob for prob in problems), problems


def test_output_contract_names_no_artifact_is_refused(tmp_path):
    """B-032-2: an exit that names no artifact is refused."""
    p = _skill(
        tmp_path,
        "ai-demo",
        "# Do the thing\n\n## What it produces\n\nVerify the change is correct.\n\n"
        "## What this is not\n\n- \"It's simple\" — then it is fast to prove; do it now.\n",
    )
    problems = contract.audit_one(p)
    assert any("artifact" in prob or "produces" in prob for prob in problems), problems


def test_output_contract_naming_a_path_passes(tmp_path):
    p = _skill(
        tmp_path,
        "ai-demo",
        "# Do the thing\n\n## What it produces\n\n`out/result.md`\n\n"
        "## What this is not\n\n- \"It's simple\" — then it is fast to prove; do it now.\n",
    )
    problems = contract.audit_one(p)
    assert not any("artifact" in prob for prob in problems), problems


def test_rules_section_without_pair_is_refused(tmp_path):
    """B-032-3: a rules section stated as bare prose is refused."""
    p = _skill(
        tmp_path,
        "ai-demo",
        "# Do the thing\n\n## What it produces\n\n`out/result.md`\n\n"
        "## Rules\n\nUse semantic tokens.\n\n"
        "## What this is not\n\n- \"It's simple\" — then it is fast to prove; do it now.\n",
    )
    problems = contract.audit_one(p)
    assert any("incorrect" in prob or "pair" in prob for prob in problems), problems


def test_rules_section_with_pair_passes(tmp_path):
    p = _skill(
        tmp_path,
        "ai-demo",
        "# Do the thing\n\n## What it produces\n\n`out/result.md`\n\n## Rules\n\n"
        "### Incorrect\n\n```tsx\n<div style=\"color: red\">T</div>\n```\n\n"
        "### Correct\n\n```tsx\n<div className=\"text-red-500\">T</div>\n```\n\n"
        "## What this is not\n\n- \"It's simple\" — then it is fast to prove; do it now.\n",
    )
    problems = contract.audit_one(p)
    assert not any("incorrect" in prob or "pair" in prob for prob in problems), problems


def test_rules_absent_passes(tmp_path):
    """A skill with no rules section passes the pair rule (scoped, no fake pairs)."""
    p = _skill(
        tmp_path,
        "ai-demo",
        "# Do the thing\n\n## What it produces\n\n`out/result.md`\n\n"
        "## What this is not\n\n- \"It's simple\" — then it is fast to prove; do it now.\n",
    )
    problems = contract.audit_one(p)
    assert not any("incorrect" in prob or "pair" in prob for prob in problems), problems


def test_body_over_500_lines_is_refused(tmp_path):
    """B-032-4: a body over 500 lines is refused."""
    body = "# Do the thing\n\n## What it produces\n\n`out/result.md`\n\n" + (
        "line of padding\n" * 510
    )
    p = _skill(
        tmp_path,
        "ai-demo",
        body + "## What this is not\n\n- \"It's simple\" — then it is fast to prove; do it now.\n",
    )
    problems = contract.audit_one(p)
    assert any("500" in prob or "load" in prob for prob in problems), problems


def test_body_under_bound_with_scripts_dir_passes(tmp_path):
    p = _skill(
        tmp_path,
        "ai-demo",
        "# Do the thing\n\n## What it produces\n\n`out/result.md`\n\n"
        "## What this is not\n\n- \"It's simple\" — then it is fast to prove; do it now.\n",
    )
    problems = contract.audit_one(p)
    assert not any("500" in prob or "load" in prob for prob in problems), problems