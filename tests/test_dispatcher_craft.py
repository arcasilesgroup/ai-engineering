"""Tests for spec 033 / B-033-3: the dispatcher/examples craft rule.

A skill whose procedure has conditional branches past the tier bound must keep the branch
bodies in on-demand files (examples/ or references/) rather than in the body — the shape
cc-creators' dispatcher+examples and headstart's references proved. The rule fires only
where the bloat is real: branches present and the body over the tier bound.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import contract  # noqa: E402


def _skill(tmp_path: Path, body: str) -> Path:
    d = tmp_path / "ai-demo"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(
        "---\nname: ai-demo\ndescription: Does X. Not for Y — use /ai-other.\n"
        "license: Apache-2.0\n---\n\n" + body,
        encoding="utf-8",
    )
    (d / "corpus.md").write_text(
        "# Corpus: ai-demo\n\n## Routes here\n\n- a job — taken\n\n"
        "## Refuses\n\n- other — use /ai-other\n",
        encoding="utf-8",
    )
    return p


def _craft_clean() -> str:
    return (
        "## What it produces\n\n`out.md`\n\n"
        "## What this is not\n\n- \"Nah\" — do it; it is fast.\n"
    )


def test_a_branchbloated_body_is_refused(tmp_path):
    """Branches present and body over the tier bound must split into on-demand files."""
    body = _craft_clean() + "\n## Procedure\n\n1. Do A. When the target is X, run the X\n" + (
        "branch that follows: use the X flow in the explanation of what X needs, and then\n"
        "the second branch for Y as well, and the third branch for Z over there, and the\n"
        "fourth branch for W across the board, and enough padding to cross five hundred\n"
        "lines of body text easily and surely.\n" * 550
    )
    p = _skill(tmp_path, body)
    problems = contract.audit_one(p)
    assert any("dispatcher" in prob or "branch" in prob for prob in problems), problems


def test_a_clean_dispatcher_passes(tmp_path):
    """A dispatcher body under the bound, with branches delegated to files, passes."""
    body = _craft_clean() + (
        "\n## Procedure\n\n1. Read the target.\n2. When X, load `examples/x.md`; "
        "when Y, load `examples/y.md`.\n"
    )
    (tmp_path / "ai-demo" / "examples").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ai-demo" / "examples" / "x.md").write_text("the X flow\n", encoding="utf-8")
    (tmp_path / "ai-demo" / "examples" / "y.md").write_text("the Y flow\n", encoding="utf-8")
    p = _skill(tmp_path, body)
    problems = contract.audit_one(p)
    assert not any("dispatcher" in prob or "branch" in prob for prob in problems), problems


def test_a_clean_linear_body_passes(tmp_path):
    """No branches: the rule does not fire, even near the bound."""
    body = _craft_clean() + "\n## Procedure\n\n1. Do A.\n2. Do B.\n3. Check C.\n"
    p = _skill(tmp_path, body)
    problems = contract.audit_one(p)
    assert not any("dispatcher" in prob for prob in problems), problems