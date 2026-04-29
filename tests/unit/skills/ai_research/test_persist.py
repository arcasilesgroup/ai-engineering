"""RED-phase tests for spec-111 T-3.8/T-3.9 -- /ai-research artifact persistence.

Spec acceptance:
    Persist artifact handler at ``persist-artifact.md`` writes
    ``.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md`` with
    deterministic frontmatter (query, depth, tiers_invoked, sources_used,
    notebook_id, created_at, slug) and Question/Findings/Sources/
    Notebook Reference body sections.

    Trigger: auto-persist when Tier 3 was invoked; opt-in via ``--persist``
    flag for quick/standard depth queries.

The handler is Markdown consumed by an LLM agent. The lockstep Python
helper at ``tests/integration/_ai_research_persist_helper.py`` mirrors
the algorithm 1:1; these tests exercise the helper.

Status: RED until T-3.10 lands the helper module + handler logic.
"""

from __future__ import annotations

from pathlib import Path

from tests.integration._ai_research_persist_helper import (
    PersistInputs,
    Source,
    persist_artifact,
    should_persist,
)

# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------


def _make_inputs(
    *,
    query: str = "compare option A vs option B",
    depth: str = "deep",
    tiers_invoked: list[int] | None = None,
    sources: list[Source] | None = None,
    notebook_id: str | None = "nb-fresh-123",
    findings: str = "Option A is faster [1]; option B is simpler [2].",
    created_at: str = "2026-04-28T12:00:00+00:00",
) -> PersistInputs:
    return PersistInputs(
        query=query,
        depth=depth,
        tiers_invoked=tiers_invoked or [0, 1, 2, 3],
        sources_used=sources
        or [
            Source(
                title="Source One",
                url="https://example.com/one",
                accessed_at="2026-04-28T11:55:00+00:00",
            ),
            Source(
                title="Source Two",
                url="https://example.com/two",
                accessed_at="2026-04-28T11:56:00+00:00",
            ),
        ],
        notebook_id=notebook_id,
        findings=findings,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# T-3.8: artifact format complete
# ---------------------------------------------------------------------------


def test_artifact_format_complete(tmp_path: Path) -> None:
    """Persisted artifact has full frontmatter + 4 body sections.

    Arrange: A standard persist input with Tier 3 invoked, 2 sources, a
    notebook_id, and a multi-citation findings paragraph.

    Act: invoke ``persist_artifact``.

    Assert:
      * File path is ``<repo>/.ai-engineering/research/<slug>-<YYYY-MM-DD>.md``.
      * Frontmatter block contains: ``query``, ``depth``, ``tiers_invoked``,
        ``sources_used`` (list with title/url/accessed_at per item),
        ``notebook_id``, ``created_at``, ``slug``.
      * Body has ``## Question``, ``## Findings`` (with ``[1]``, ``[2]``
        citations preserved inline), ``## Sources`` (numbered list with
        title -- url and accessed-at), and ``## Notebook Reference``
        section pointing at the notebook id.
    """
    repo_root = tmp_path
    inputs = _make_inputs()

    written_path = persist_artifact(inputs, repo_root=repo_root)

    expected_dir = repo_root / ".ai-engineering" / "research"
    assert written_path.parent == expected_dir, (
        f"Artifact must land under .ai-engineering/research/; got {written_path.parent}"
    )
    expected_name = "compare-option-a-vs-option-b-2026-04-28.md"
    assert written_path.name == expected_name, (
        f"Filename must be '<slug>-<YYYY-MM-DD>.md'; got {written_path.name!r}"
    )
    assert written_path.exists(), "persist_artifact must create the file on disk"

    text = written_path.read_text(encoding="utf-8")

    # --- Frontmatter must be a single ``--- ... ---`` block at start.
    assert text.startswith("---\n"), "Artifact must start with YAML frontmatter fence"
    end_fence = text.find("\n---\n", 3)
    assert end_fence != -1, "Artifact must close the YAML frontmatter fence"
    frontmatter = text[4:end_fence]
    body = text[end_fence + len("\n---\n") :]

    # --- Frontmatter required keys
    for required_key in (
        'query: "compare option A vs option B"',
        "depth: deep",
        "tiers_invoked: [0, 1, 2, 3]",
        "sources_used:",
        "notebook_id: nb-fresh-123",
        "created_at: 2026-04-28T12:00:00+00:00",
        "slug: compare-option-a-vs-option-b",
    ):
        assert required_key in frontmatter, (
            f"Frontmatter missing required entry {required_key!r}; got:\n{frontmatter}"
        )

    # --- sources_used list entries
    assert "title: Source One" in frontmatter
    assert "url: https://example.com/one" in frontmatter
    assert "accessed_at: 2026-04-28T11:55:00+00:00" in frontmatter
    assert "title: Source Two" in frontmatter
    assert "url: https://example.com/two" in frontmatter

    # --- Body sections in order
    sections = ("## Question", "## Findings", "## Sources", "## Notebook Reference")
    last_index = -1
    for section in sections:
        idx = body.find(section)
        assert idx != -1, f"Body missing required section {section!r}"
        assert idx > last_index, (
            f"Section {section!r} must appear AFTER prior sections (got out-of-order body)"
        )
        last_index = idx

    # --- Question section echoes the verbatim query
    question_index = body.find("## Question")
    findings_index = body.find("## Findings")
    question_block = body[question_index:findings_index]
    assert "compare option A vs option B" in question_block

    # --- Findings preserves inline citations
    sources_index = body.find("## Sources")
    findings_block = body[findings_index:sources_index]
    assert "[1]" in findings_block and "[2]" in findings_block, (
        f"Findings section must preserve inline [N] citations; got:\n{findings_block}"
    )

    # --- Sources is a numbered list
    notebook_index = body.find("## Notebook Reference")
    sources_block = body[sources_index:notebook_index]
    assert "1. Source One -- https://example.com/one" in sources_block, (
        f"Sources block must list each source as numbered '<title> -- <url>'; got:\n{sources_block}"
    )
    assert "2. Source Two -- https://example.com/two" in sources_block

    # --- Notebook Reference section exposes the notebook id when present
    notebook_block = body[notebook_index:]
    assert "nb-fresh-123" in notebook_block, (
        f"Notebook Reference must mention notebook id; got:\n{notebook_block}"
    )


# ---------------------------------------------------------------------------
# T-3.9: trigger conditions
# ---------------------------------------------------------------------------


def test_auto_persist_when_tier3_invoked() -> None:
    """When Tier 3 was invoked, ``should_persist`` returns True regardless of flag."""
    assert should_persist(tier3_invoked=True, persist_flag=False) is True
    assert should_persist(tier3_invoked=True, persist_flag=True) is True


def test_opt_in_persist_for_quick_standard() -> None:
    """When Tier 3 was NOT invoked, only ``--persist`` flips persistence on."""
    # Without flag: do not persist.
    assert should_persist(tier3_invoked=False, persist_flag=False) is False
    # With flag: persist even though Tier 3 did not run.
    assert should_persist(tier3_invoked=False, persist_flag=True) is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_artifact_omits_notebook_section_when_no_notebook(tmp_path: Path) -> None:
    """No Tier 3 -> ``notebook_id`` is null and the section is still present but empty.

    The persisted format always includes the four sections so downstream
    Tier 0 readers can rely on a stable layout. Without a notebook, the
    section body is a placeholder ('_(none)_').
    """
    inputs = _make_inputs(notebook_id=None, depth="standard", tiers_invoked=[0, 1, 2])
    path = persist_artifact(inputs, repo_root=tmp_path)
    text = path.read_text(encoding="utf-8")

    # Frontmatter notebook_id must encode null.
    assert "notebook_id: null" in text
    # Body section still present.
    assert "## Notebook Reference" in text
    notebook_block = text[text.find("## Notebook Reference") :]
    assert "_(none)_" in notebook_block, (
        f"Notebook Reference must show placeholder when no notebook; got:\n{notebook_block}"
    )


def test_artifact_filename_uses_created_at_date(tmp_path: Path) -> None:
    """Filename date stamp comes from ``created_at`` (ISO prefix)."""
    inputs = _make_inputs(
        query="another topic",
        created_at="2025-12-31T23:59:59+00:00",
    )
    path = persist_artifact(inputs, repo_root=tmp_path)
    assert path.name == "another-topic-2025-12-31.md"
