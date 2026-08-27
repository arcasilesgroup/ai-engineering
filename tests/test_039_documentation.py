"""Tests for spec 039 / B-039-1/2: the documentation discipline.

The reference (references/documentation-writer.md beside ai-report) names the
writing-for-agents levers and the STE100 controlled-language rules; the three corpus routes
name it and refuse a vague completion bound; the three routes differ (no fork).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _reference() -> str:
    return (
        ROOT / ".agents" / "skills" / "ai-report" / "references" / "documentation-writer.md"
    ).read_text()


def test_reference_names_the_levers():
    text = _reference().casefold()
    assert "context pointer" in text
    assert "context load" in text
    assert "cognitive load" in text
    assert "leading word" in text
    assert "prun" in text
    assert "one idea" in text  # STE100: one idea per sentence


def test_routes_name_the_discipline_and_differ():
    routes = []
    for skill in ("ai-spec", "ai-plan", "ai-report"):
        body = (ROOT / ".agents" / "skills" / skill / "corpus.md").read_text()
        assert "documentation-writer.md" in body
        routes.append(body)
    # Three distinct phrasings, not one fork the harness would read three times.
    assert len({r for r in routes}) == 3


def test_bare_bound_is_refused():
    # A doc handing an agent a vague completion bound is refused by the discipline route:
    # each corpus carries a refusal naming the reference.
    for skill in ("ai-spec", "ai-plan", "ai-report"):
        body = (ROOT / ".agents" / "skills" / skill / "corpus.md").read_text()
        assert "documentation-writer.md" in body
        assert "refused" in body
