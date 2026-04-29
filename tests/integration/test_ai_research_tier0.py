"""RED-phase tests for spec-111 T-1.6 -- /ai-research Tier 0 local search.

Spec acceptance:
    Tier 0 (local) implemented in ``tier0-local.md`` -- handler executes:
    (a) glob ``.ai-engineering/research/*.md`` and match topic-slug
    similarity ≥0.7; (b) grep ``LESSONS.md`` by keywords from the query;
    (c) parse ``framework-events.ndjson`` last 30 days filtering by
    ``kind: skill_invoked`` with ``detail.skill = "ai-research"`` for prior
    queries. If Tier 0 produces ≥3 relevant hits, skill MAY short-circuit.

The handler is Markdown consumed by an LLM agent. The standard pattern in
this project for validating skill-handler logic is a lockstep Python helper
module (here: ``tests/integration/_ai_research_tier0_helper.py``) that
mirrors the algorithm documented in the handler 1:1. These tests exercise
the helper.

Status: RED until T-1.7 lands the helper module + handler logic.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.integration._ai_research_tier0_helper import (
    Tier0Result,
    slugify,
    tier0_local,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed_repo_layout(repo: Path) -> None:
    """Create the three local-source directories the Tier 0 algorithm reads."""
    (repo / ".ai-engineering" / "research").mkdir(parents=True, exist_ok=True)
    (repo / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)


def _write_research_artifact(
    repo: Path,
    *,
    slug: str,
    date: str,
    query: str,
) -> Path:
    """Write a research artifact with frontmatter at the canonical path."""
    artifact = repo / ".ai-engineering" / "research" / f"{slug}-{date}.md"
    artifact.write_text(
        (
            "---\n"
            f'query: "{query}"\n'
            "depth: deep\n"
            "tiers_invoked: [0, 1, 2, 3]\n"
            "---\n\n"
            "## Findings\nplaceholder\n"
        ),
        encoding="utf-8",
    )
    return artifact


def _write_lessons(repo: Path, body: str) -> Path:
    path = repo / ".ai-engineering" / "LESSONS.md"
    path.write_text(body, encoding="utf-8")
    return path


def _write_events(repo: Path, records: list[dict]) -> Path:
    path = repo / ".ai-engineering" / "state" / "framework-events.ndjson"
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_local_match_short_circuits_when_sufficient(tmp_path: Path) -> None:
    """≥3 local hits trigger short-circuit (Tier 0 sufficient).

    Arrange: a research artifact with a near-identical slug, a LESSONS.md
    containing the query keywords on multiple lines, and 1 prior /ai-research
    skill_invoked event in the last 30 days. Total local hits ≥ 3.

    Act: invoke ``tier0_local``.

    Assert: ``should_short_circuit`` is True and ``total_hits >= 3``.
    """
    _seed_repo_layout(tmp_path)
    query = "react state management 2026"

    _write_research_artifact(
        tmp_path,
        slug="react-state-management-2026",
        date="2026-04-15",
        query=query,
    )
    _write_lessons(
        tmp_path,
        "Notes about react patterns.\n"
        "Lesson 1: prefer state colocation in react components.\n"
        "Lesson 2: management of state matters in 2026.\n",
    )
    now = datetime(2026, 4, 28, tzinfo=UTC)
    _write_events(
        tmp_path,
        [
            {
                "kind": "skill_invoked",
                "timestamp": (now - timedelta(days=2)).isoformat(),
                "detail": {"skill": "ai-research", "query": "react state libs"},
            }
        ],
    )

    result = tier0_local(query, repo_root=tmp_path, now=now)

    assert isinstance(result, Tier0Result)
    assert result.total_hits >= 3, (
        f"expected ≥3 hits across all sources; got {result.total_hits}: "
        f"artifacts={len(result.research_artifact_hits)} "
        f"lessons={len(result.lessons_hits)} "
        f"prior={len(result.prior_query_hits)}"
    )
    assert result.should_short_circuit is True


def test_local_match_escalates_when_insufficient(tmp_path: Path) -> None:
    """<3 local hits MUST NOT short-circuit -- agent escalates to Tier 1."""
    _seed_repo_layout(tmp_path)
    query = "completely new topic that has zero prior history"

    # No research artifacts, empty LESSONS, no events.
    _write_lessons(tmp_path, "Unrelated lesson about gitleaks.\n")
    _write_events(tmp_path, [])

    now = datetime(2026, 4, 28, tzinfo=UTC)
    result = tier0_local(query, repo_root=tmp_path, now=now)

    assert result.total_hits < 3
    assert result.should_short_circuit is False


def test_grep_research_artifacts_finds_topic_slug_match(tmp_path: Path) -> None:
    """Slug-similarity match returns artifacts above the 0.7 threshold."""
    _seed_repo_layout(tmp_path)

    # Slug match: target query slug is "react-state-management"; this artifact's
    # slug is identical, so similarity == 1.0.
    matched = _write_research_artifact(
        tmp_path,
        slug="react-state-management",
        date="2026-03-01",
        query="react state management",
    )
    # Mismatch artifact unrelated to the query.
    _write_research_artifact(
        tmp_path,
        slug="postgres-vacuum-tuning",
        date="2026-03-15",
        query="postgres vacuum tuning",
    )

    now = datetime(2026, 4, 28, tzinfo=UTC)
    result = tier0_local(
        "react state management",
        repo_root=tmp_path,
        now=now,
    )

    paths = [hit["path"] for hit in result.research_artifact_hits]
    assert matched in paths, (
        f"expected matched artifact in result; got hits with similarities="
        f"{[(h['slug'], h['similarity']) for h in result.research_artifact_hits]}"
    )

    # Sanity-check the bare slugify helper as well.
    assert slugify("react state management") == "react-state-management"


# ---------------------------------------------------------------------------
# Edge cases that pin down algorithm details
# ---------------------------------------------------------------------------


def test_lookback_excludes_old_events(tmp_path: Path) -> None:
    """Events older than ``lookback_days`` (default 30) are excluded."""
    _seed_repo_layout(tmp_path)
    now = datetime(2026, 4, 28, tzinfo=UTC)
    _write_events(
        tmp_path,
        [
            {
                "kind": "skill_invoked",
                "timestamp": (now - timedelta(days=45)).isoformat(),
                "detail": {"skill": "ai-research"},
            },
        ],
    )

    result = tier0_local("anything", repo_root=tmp_path, now=now)
    assert result.prior_query_hits == []


def test_events_filter_to_ai_research_only(tmp_path: Path) -> None:
    """Only ``detail.skill == "ai-research"`` skill_invoked events count."""
    _seed_repo_layout(tmp_path)
    now = datetime(2026, 4, 28, tzinfo=UTC)
    _write_events(
        tmp_path,
        [
            {
                "kind": "skill_invoked",
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "detail": {"skill": "ai-debug"},
            },
            {
                "kind": "skill_invoked",
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "detail": {"skill": "ai-research"},
            },
            {
                "kind": "agent_dispatched",
                "timestamp": (now - timedelta(days=1)).isoformat(),
                "detail": {"skill": "ai-research"},
            },
        ],
    )

    result = tier0_local("anything", repo_root=tmp_path, now=now)
    assert len(result.prior_query_hits) == 1
    assert result.prior_query_hits[0]["detail"]["skill"] == "ai-research"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("React State Management", "react-state-management"),
        ("  spaces   only  ", "spaces-only"),
        ("a/b/c?d=e&f=g", "a-b-c-d-e-f-g"),
        # Truncation at 40 chars + trailing dash strip.
        ("x" * 50, "x" * 40),
    ],
)
def test_slugify_invariants(raw: str, expected: str) -> None:
    assert slugify(raw) == expected
