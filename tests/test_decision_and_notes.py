"""Tests for spec 034 / B-034-1..2: appendix notes and decision frameworks.

The appendix rule (B-034-1): ai-note's instruction must refuse rewriting a note — a
finding appends with a date, never edits what a past session recorded. The decision
frameworks (B-034-2): a decision names a framework (RICE / Effort-Value / Kano) and
applies it; a bare "ranked by impact" with no method is refused.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import contract, decision_fw  # noqa: E402


def _skill(tmp_path: Path, folder: str, body: str) -> Path:
    d = tmp_path / folder
    d.mkdir(parents=True, exist_ok=True)
    p = d / "SKILL.md"
    p.write_text(
        "---\n"
        f"name: {folder}\n"
        "description: Does X. Not for Y — use /ai-other.\n"
        "license: Apache-2.0\n"
        "---\n\n" + body,
        encoding="utf-8",
    )
    (d / "corpus.md").write_text(
        f"# Corpus: {folder}\n\n## Routes here\n\n- a job — taken\n\n"
        "## Refuses\n\n- another — use /ai-other\n",
        encoding="utf-8",
    )
    return p


def _craft() -> str:
    return (
        "## What it produces\n\n`docs/notes/<slug>.md`\n\n"
        '## What this is not\n\n- "Nah" — do it; it is fast.\n'
    )


def test_appendix_note_rewrite_instruction_is_refused(tmp_path):
    """B-034-1: a skill body that says rewrite/edit the note is refused."""
    body = _craft() + "\n## Procedure\n\n1. Rewrite the note with the new findings.\n"
    p = _skill(tmp_path, "ai-note", body)
    problems = contract.audit_one(p)
    assert any("append" in prob or "rewrite" in prob for prob in problems), problems


def test_appendix_append_only_instruction_passes(tmp_path):
    body = _craft() + "\n## Procedure\n\n1. Append the new finding with today's date.\n"
    p = _skill(tmp_path, "ai-note", body)
    problems = contract.audit_one(p)
    assert not any("append" in prob or "rewrite" in prob for prob in problems), problems


def test_framework_rice_returns_a_deterministic_verdict():
    """B-034-2: RICE = Reach x Impact x Confidence / Effort."""
    assert decision_fw.rice(reach=10, impact=2, confidence=0.8, effort=4) == 4.0


def test_framework_effort_value_returns_a_deterministic_verdict():
    assert decision_fw.effort_value(value=8, effort=2) == 4.0


def test_framework_kano_returns_a_category():
    assert decision_fw.kano("delighter") == "delighter"
    assert decision_fw.kano("basic") == "basic"
    assert decision_fw.kano("performance") == "performance"


def test_framework_bare_rationale_with_no_method_is_refused():
    """A ranking with no named method is not a decision this framework supports."""
    assert decision_fw.named("ranked by impact") is None
    assert decision_fw.named("RICE") == "rice"
