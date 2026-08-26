"""Tests for spec 040 / B-040-1/2/3: the ai-write skill.

Verified doc (names real files, no environment restatement, checkable sections) passes;
no-cache (repeating the environment) is refused; an unverifiable claim exits
`not-covered: <reason>`; routing keeps ai-write apart from the four existing surfaces; the
count pin moves to eighteen.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_verified_doc_passes():
    body = (ROOT / ".agents" / "skills" / "ai-write" / "SKILL.md").read_text()
    assert "references/documentation-writer.md" in body  # the single standard
    assert "not-covered" in body  # the honest exit is in the contract
    assert "## What it produces" in body and "## Done when" in body  # audit shape


def test_no_cache_and_not_covered_live_in_the_contract():
    body = (ROOT / ".agents" / "skills" / "ai-write" / "SKILL.md").read_text()
    assert "restates" in body or "no-cache" in body
    assert "completion" in body  # checkable completion criteria


def test_routing_keeps_it_apart():
    corpus = (ROOT / ".agents" / "skills" / "ai-write" / "corpus.md").read_text()
    assert "## Routes here" in corpus and "## Refuses" in corpus
    assert "/ai-ship" in corpus.replace("/ai-ship", " /ai-ship")  # changelog refuses away
    for skill in ("ai-ship", "ai-spec", "ai-note", "ai-report"):
        other = (ROOT / ".agents" / "skills" / skill / "corpus.md").read_text()
        assert "ai-write" in other  # the reverse route exists


def test_capability_entry():
    caps = (ROOT / "policy" / "capabilities.toml").read_text()
    assert 'id = "ai-write"' in caps


def test_count_pin_moves_to_eighteen():
    readme = (ROOT / "README.md").read_text()
    agents = (ROOT / "AGENTS.md").read_text()
    assert "Eighteen written procedures" in readme
    assert "eighteen skills" in agents