"""RED-phase tests for spec-111 T-3.1/T-3.2 -- /ai-research Tier 3 NotebookLM.

Spec acceptance:
    Tier 3 (NotebookLM persistent corpus) implemented in
    ``tier3-notebooklm.md`` -- handler creates a notebook (or reuses one
    via ``--reuse-notebook=<id>``), adds each Tier 1+2 source URL (capped
    at 20), and runs ``notebook_query`` with a citation instruction. The
    notebook ID and conversation ID are returned for persistence.

    Triggers: ``--depth=deep`` flag, comparative queries (regex
    ``\\b(vs|versus|compare|difference between|alternatives?)\\b``), or
    Tier 1+2 collected ≥10 sources.

The handler is Markdown consumed by an LLM agent. The lockstep Python
helper at ``tests/integration/_ai_research_tier3_helper.py`` mirrors the
algorithm 1:1; these tests exercise the helper.

Status: RED until T-3.5 lands the helper module + handler logic.
"""

from __future__ import annotations

import pytest

from tests.integration._ai_research_tier3_helper import (
    Tier3Result,
    should_invoke_tier3,
    tier3_notebooklm,
)

# ---------------------------------------------------------------------------
# Fakes -- record every MCP call with its kwargs.
# ---------------------------------------------------------------------------


class _RecordingNotebookCreate:
    """Stand-in for ``mcp__notebooklm-mcp__notebook_create``."""

    def __init__(self, returned_id: str = "nb-fresh-123") -> None:
        self.calls: list[dict] = []
        self.returned_id = returned_id

    def __call__(self, *, title: str) -> dict:
        self.calls.append({"title": title})
        return {"notebook_id": self.returned_id}


class _RecordingSourceAdd:
    """Stand-in for ``mcp__notebooklm-mcp__source_add``."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(self, *, notebook_id: str, source_type: str, url: str) -> dict:
        self.calls.append({"notebook_id": notebook_id, "source_type": source_type, "url": url})
        return {"source_id": f"src-{len(self.calls)}"}


class _RecordingNotebookQuery:
    """Stand-in for ``mcp__notebooklm-mcp__notebook_query``."""

    def __init__(self, response: str = "synthesized response with [1] citation") -> None:
        self.calls: list[dict] = []
        self.response = response

    def __call__(self, *, notebook_id: str, query: str) -> dict:
        self.calls.append({"notebook_id": notebook_id, "query": query})
        return {
            "answer": self.response,
            "conversation_id": "conv-abc-789",
        }


def _stub_sources(n: int) -> list[str]:
    return [f"https://example.com/source-{i}" for i in range(n)]


# ---------------------------------------------------------------------------
# T-3.1: notebook creation + query with citation instruction
# ---------------------------------------------------------------------------


def test_notebooklm_creation_and_query_with_citations() -> None:
    """Full Tier 3 flow: create -> add 5 sources -> query with citations.

    Arrange: 5 source URLs, no ``--reuse-notebook`` flag, deep depth.

    Act: invoke ``tier3_notebooklm``.

    Assert:
      * ``notebook_create`` called once with a ``ai-research/<slug>-<date>-<hash6>``
        title.
      * ``source_add`` called once per URL (5 times) with ``source_type='url'``
        and ``notebook_id`` matching the returned id.
      * ``notebook_query`` called once with the user query plus the
        instruction string mentioning ``[N]`` notation.
      * Result captures ``notebook_id`` and ``conversation_id`` from the MCP
        responses, plus the synthesized answer.
    """
    notebook_create = _RecordingNotebookCreate(returned_id="nb-fresh-123")
    source_add = _RecordingSourceAdd()
    notebook_query = _RecordingNotebookQuery(
        response="Compared options: A is faster [1]; B is simpler [2].",
    )

    sources = _stub_sources(5)
    query = "compare option A vs option B for retries"

    result = tier3_notebooklm(
        query,
        sources=sources,
        timestamp_iso="2026-04-28T12:00:00+00:00",
        notebook_create=notebook_create,
        source_add=source_add,
        notebook_query=notebook_query,
    )

    assert isinstance(result, Tier3Result)

    # notebook_create was called exactly once with a templated title.
    assert len(notebook_create.calls) == 1, (
        f"Expected exactly one notebook_create call; got {len(notebook_create.calls)}"
    )
    title = notebook_create.calls[0]["title"]
    assert title.startswith("ai-research/"), (
        f"Notebook title must start with 'ai-research/' prefix; got {title!r}"
    )
    # The slug portion derives from the query and the date is included.
    assert "compare-option-a-vs-option-b" in title, (
        f"Title must embed the query slug; got {title!r}"
    )
    assert "2026-04-28" in title, f"Title must embed the YYYY-MM-DD date; got {title!r}"

    # source_add was called once per URL with the captured notebook id.
    assert len(source_add.calls) == 5
    for call, expected_url in zip(source_add.calls, sources, strict=True):
        assert call["notebook_id"] == "nb-fresh-123"
        assert call["source_type"] == "url"
        assert call["url"] == expected_url

    # notebook_query was called with the citation instruction appended.
    assert len(notebook_query.calls) == 1
    sent_query = notebook_query.calls[0]["query"]
    assert query in sent_query, "User query must be present in the notebook_query payload"
    assert "[N]" in sent_query, (
        f"notebook_query payload must instruct citation usage with [N] notation; got {sent_query!r}"
    )
    assert "citation" in sent_query.lower(), (
        f"notebook_query payload must mention citations; got {sent_query!r}"
    )

    # Captured IDs flow into the result.
    assert result.notebook_id == "nb-fresh-123"
    assert result.conversation_id == "conv-abc-789"
    assert "[1]" in result.synthesized_response


# ---------------------------------------------------------------------------
# T-3.1 (cont): cap sources at 20
# ---------------------------------------------------------------------------


def test_max_20_sources() -> None:
    """When more than 20 sources are passed, only the first 20 are added.

    Arrange: 25 source URLs.

    Act: invoke ``tier3_notebooklm``.

    Assert: ``source_add`` was called exactly 20 times, with the first 20
    URLs in order.
    """
    notebook_create = _RecordingNotebookCreate(returned_id="nb-cap-456")
    source_add = _RecordingSourceAdd()
    notebook_query = _RecordingNotebookQuery()

    sources = _stub_sources(25)

    tier3_notebooklm(
        "noisy query with many sources",
        sources=sources,
        timestamp_iso="2026-04-28T12:00:00+00:00",
        notebook_create=notebook_create,
        source_add=source_add,
        notebook_query=notebook_query,
    )

    assert len(source_add.calls) == 20, (
        f"Tier 3 must cap source ingestion at 20; got {len(source_add.calls)} calls"
    )
    added_urls = [call["url"] for call in source_add.calls]
    assert added_urls == sources[:20], "Capped sources must preserve original order"


# ---------------------------------------------------------------------------
# T-3.2: --reuse-notebook flag skips notebook_create
# ---------------------------------------------------------------------------


def test_reuse_notebook_flag_skips_creation() -> None:
    """When ``reuse_notebook='abc123'`` is passed, ``notebook_create`` is NOT called.

    Arrange: 3 source URLs, ``reuse_notebook='abc123'``.

    Act: invoke ``tier3_notebooklm``.

    Assert:
      * ``notebook_create`` was never called.
      * ``source_add`` and ``notebook_query`` use the provided id ``abc123``.
      * The result's ``notebook_id`` echoes ``abc123``.
    """
    notebook_create = _RecordingNotebookCreate(returned_id="should-not-be-used")
    source_add = _RecordingSourceAdd()
    notebook_query = _RecordingNotebookQuery()

    sources = _stub_sources(3)

    result = tier3_notebooklm(
        "follow-up question on same corpus",
        sources=sources,
        timestamp_iso="2026-04-28T12:00:00+00:00",
        reuse_notebook="abc123",
        notebook_create=notebook_create,
        source_add=source_add,
        notebook_query=notebook_query,
    )

    assert notebook_create.calls == [], (
        f"--reuse-notebook MUST short-circuit notebook_create; got calls {notebook_create.calls}"
    )
    assert result.notebook_id == "abc123"
    for call in source_add.calls:
        assert call["notebook_id"] == "abc123", (
            f"source_add must use reused notebook id 'abc123'; got {call['notebook_id']}"
        )
    assert notebook_query.calls[0]["notebook_id"] == "abc123", (
        f"notebook_query must use reused notebook id 'abc123'; "
        f"got {notebook_query.calls[0]['notebook_id']}"
    )


# ---------------------------------------------------------------------------
# T-3.6: trigger heuristic
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "depth,query,tier12_count,expected",
    [
        # depth=deep always triggers
        ("deep", "what is foo", 0, True),
        # comparative trigger words
        ("standard", "compare A vs B", 0, True),
        ("standard", "Foo versus bar", 0, True),
        ("standard", "alternatives to widget", 0, True),
        ("standard", "difference between X and Y", 0, True),
        # ≥10 sources trigger Tier 3 even for non-comparative standard depth
        ("standard", "how does X work", 10, True),
        ("standard", "how does X work", 15, True),
        # otherwise: do not invoke
        ("standard", "how does X work", 5, False),
        ("quick", "how does X work", 9, False),
        ("standard", "neutral query", 0, False),
    ],
)
def test_should_invoke_tier3_heuristic(
    depth: str, query: str, tier12_count: int, expected: bool
) -> None:
    assert should_invoke_tier3(query, depth=depth, tier12_source_count=tier12_count) is expected
