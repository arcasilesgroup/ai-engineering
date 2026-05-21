"""Surface-count drift guard: CLAUDE.md ↔ on-disk .claude/ (spec-147 T-2.1/2.2).

The filesystem under ``.claude/`` is the source of truth for the skill
and agent rosters (D-147-07: there is NO ``agents.registry`` manifest
key — the on-disk directories ARE the registry). This guard pins the
counts CLAUDE.md states against the actual globbed counts so the doc
cannot drift away from the tree, modelled on the locked-constant style
of ``tests/unit/hooks/test_canonical_events_count.py``.

Two distinct agent counts exist and BOTH are intentional:

* **User-facing agents (9)** — the ``ai-*`` agents the operator invokes.
  This is the number CLAUDE.md's ``## Agents (N)`` header and the
  Source-of-Truth table state (it is what the mirror generator
  interpolates from ``discover_agents()`` globbing ``ai-*.md``).
* **Total agent files (19)** — the 9 user-facing ``ai-*`` plus the
  internal specialist families dispatched by orchestrators: 2
  ``review-*``, 6 ``reviewer-*``, 2 ``verifier-*``. These are real files
  under ``.claude/agents/`` but are not user-invocable, so they are not
  part of the ``## Agents (9)`` count.

Drift in either direction (doc count vs disk, or family roster vs locked
breakdown) fails CI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"
_SKILLS_DIR = _REPO_ROOT / ".claude" / "skills"
_AGENTS_DIR = _REPO_ROOT / ".claude" / "agents"

# Locked family breakdown for .claude/agents/*.md. Bump these only after
# auditing the new agent file AND the canonical roster docs. The point of
# the guard is to make roster drift visible in code review.
_EXPECTED_USER_FACING_AGENTS = 9  # ai-*.md
_EXPECTED_REVIEW_AGENTS = 2  # review-*.md (review-context, review-validator)
_EXPECTED_REVIEWER_AGENTS = 6  # reviewer-*.md specialist roster (spec-140 W3)
_EXPECTED_VERIFIER_AGENTS = 2  # verifier-*.md (acceptance, deterministic)
_EXPECTED_TOTAL_AGENTS = (
    _EXPECTED_USER_FACING_AGENTS
    + _EXPECTED_REVIEW_AGENTS
    + _EXPECTED_REVIEWER_AGENTS
    + _EXPECTED_VERIFIER_AGENTS
)


def _disk_skill_count() -> int:
    return len(list(_SKILLS_DIR.glob("*/SKILL.md")))


def _disk_user_facing_agent_count() -> int:
    return len(list(_AGENTS_DIR.glob("ai-*.md")))


def _disk_total_agent_count() -> int:
    return len(list(_AGENTS_DIR.glob("*.md")))


def _claude_md_stated_counts(label: str) -> set[int]:
    """Return every integer N stated as ``label (N)`` in CLAUDE.md."""
    text = _CLAUDE_MD.read_text(encoding="utf-8")
    return {int(m) for m in re.findall(rf"{re.escape(label)} \((\d+)\)", text)}


@pytest.mark.unit
def test_claude_md_skill_count_matches_disk() -> None:
    """Every ``Skills (N)`` in CLAUDE.md equals the on-disk SKILL.md count."""
    disk = _disk_skill_count()
    stated = _claude_md_stated_counts("Skills")
    assert stated, "CLAUDE.md states no 'Skills (N)' count — surface index missing?"
    assert stated == {disk}, (
        f"CLAUDE.md 'Skills (N)' states {sorted(stated)} but .claude/skills/*/SKILL.md "
        f"globs {disk}. Regenerate mirrors / fix the surface index."
    )


@pytest.mark.unit
def test_claude_md_agent_count_matches_disk_user_facing() -> None:
    """Every ``Agents (N)`` in CLAUDE.md equals the user-facing ai-*.md count."""
    disk = _disk_user_facing_agent_count()
    stated = _claude_md_stated_counts("Agents")
    assert stated, "CLAUDE.md states no 'Agents (N)' count — surface index missing?"
    assert stated == {disk}, (
        f"CLAUDE.md 'Agents (N)' states {sorted(stated)} but .claude/agents/ai-*.md "
        f"globs {disk} user-facing agents. Regenerate mirrors / fix the surface index."
    )


@pytest.mark.unit
def test_user_facing_agent_roster_locked() -> None:
    """The user-facing ``ai-*`` roster is pinned at the locked count."""
    disk = _disk_user_facing_agent_count()
    assert disk == _EXPECTED_USER_FACING_AGENTS, (
        f"Expected {_EXPECTED_USER_FACING_AGENTS} user-facing ai-*.md agents, found {disk}: "
        f"{sorted(p.stem for p in _AGENTS_DIR.glob('ai-*.md'))}"
    )


@pytest.mark.unit
def test_total_agent_file_roster_locked() -> None:
    """``.claude/agents/*.md`` matches the locked family breakdown (19 files)."""
    review = len(list(_AGENTS_DIR.glob("review-*.md")))
    reviewer = len(list(_AGENTS_DIR.glob("reviewer-*.md")))
    verifier = len(list(_AGENTS_DIR.glob("verifier-*.md")))
    total = _disk_total_agent_count()

    assert review == _EXPECTED_REVIEW_AGENTS, f"review-*.md drift: {review}"
    assert reviewer == _EXPECTED_REVIEWER_AGENTS, f"reviewer-*.md drift: {reviewer}"
    assert verifier == _EXPECTED_VERIFIER_AGENTS, f"verifier-*.md drift: {verifier}"
    assert total == _EXPECTED_TOTAL_AGENTS, (
        f"Total .claude/agents/*.md is {total}, expected {_EXPECTED_TOTAL_AGENTS} "
        f"(9 ai- + 2 review- + 6 reviewer- + 2 verifier-). Roster drifted: "
        f"{sorted(p.stem for p in _AGENTS_DIR.glob('*.md'))}"
    )
