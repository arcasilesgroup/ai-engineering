"""RED-phase tests for spec-111 T-4.8 -- /ai-research degraded-mode resilience.

Spec acceptance:
    Tier 1 MCP failures (Context7, MS Learn, gh search) MUST NOT abort
    the other futures: each per-MCP failure appends the source name to a
    ``degraded_sources`` list and the synthesizer surfaces a visible
    warning to the user.

    Tier 3 (NotebookLM) MUST probe ``server_info`` first; if auth is
    expired (probe returns ``authenticated: False``), Tier 3 is skipped
    with a ``notebooklm auth expired`` warning suggesting ``nlm login``.

    All-external-down case: Tier 1 + Tier 2 + Tier 3 all fail -> the
    synthesizer falls back to local context (Tier 0 results) and surfaces
    a "all external sources down" warning so the user knows the answer
    is local-only.

Status: RED until T-4.9 wires the auth probe into the Tier 3 helper and
T-4.10 confirms the test suite is GREEN.
"""

from __future__ import annotations

from tests.integration._ai_research_tier1_helper import (
    Tier1Hit,
    tier1_free_mcps,
)
from tests.integration._ai_research_tier3_helper import (
    Tier3Result,
    tier3_notebooklm,
)

# ---------------------------------------------------------------------------
# Test 1: Context7 down -> Tier 1 continues with MS Learn + gh search
# ---------------------------------------------------------------------------


def test_context7_down_degrades_to_other_tier1() -> None:
    """A Context7 outage MUST NOT abort the MS Learn / gh search futures.

    Arrange: Context7 callable raises; the other two return hits.

    Act: invoke ``tier1_free_mcps``.

    Assert:
      * ``degraded_sources`` includes ``context7``.
      * ``hits`` contains MS Learn and gh search results.
      * No exception propagates to the caller.
    """

    def context7_down(_query: str, **_) -> list[Tier1Hit]:
        raise RuntimeError("Context7 MCP down")

    def ms_learn_ok(_query: str, **_) -> list[Tier1Hit]:
        return [
            Tier1Hit(
                title="Azure Functions retry guide",
                url="https://learn.microsoft.com/azure/functions/retry",
                snippet="Retry policy for Azure Functions",
                source="ms_learn",
            )
        ]

    def gh_search_ok(_query: str, **_) -> list[Tier1Hit]:
        return [
            Tier1Hit(
                title="github.com/foo/bar",
                url=None,
                snippet="example retry pattern",
                source="gh_search",
                repo="foo/bar",
                path="src/retry.py",
            )
        ]

    # Use a query that triggers all three MCPs.
    query = "Azure dotnet retry patterns library github examples"
    result = tier1_free_mcps(
        query,
        context7=context7_down,
        ms_learn=ms_learn_ok,
        gh_search=gh_search_ok,
    )

    assert "context7" in result.degraded_sources, (
        f"Context7 failure must be reported in degraded_sources; got {result.degraded_sources}"
    )
    sources_in_hits = {hit.source for hit in result.hits}
    assert "ms_learn" in sources_in_hits, f"MS Learn hit missing; got {sources_in_hits}"
    assert "gh_search" in sources_in_hits, f"gh_search hit missing; got {sources_in_hits}"
    assert "context7" not in sources_in_hits, "Failed Context7 must contribute zero hits"


# ---------------------------------------------------------------------------
# Test 2: MS Learn down -> Tier 1 continues with Context7 + gh search
# ---------------------------------------------------------------------------


def test_ms_learn_down_continues_with_other_mcps() -> None:
    """An MS Learn outage MUST NOT abort the Context7 / gh search futures.

    Arrange: MS Learn callable raises; the other two return hits.

    Act: invoke ``tier1_free_mcps``.

    Assert:
      * ``degraded_sources`` includes ``ms_learn``.
      * ``hits`` contains Context7 and gh search results.
    """

    def context7_ok(_query: str, **_) -> list[Tier1Hit]:
        return [
            Tier1Hit(
                title="React hooks guide",
                url="https://context7.com/react/hooks",
                snippet="Hooks API",
                source="context7",
            )
        ]

    def ms_learn_down(_query: str, **_) -> list[Tier1Hit]:
        raise TimeoutError("MS Learn MCP timed out")

    def gh_search_ok(_query: str, **_) -> list[Tier1Hit]:
        return [
            Tier1Hit(
                title="github.com/baz/qux",
                url=None,
                snippet="example",
                source="gh_search",
                repo="baz/qux",
                path="src/hooks.tsx",
            )
        ]

    query = "Azure react library github examples how do projects use hooks"
    result = tier1_free_mcps(
        query,
        context7=context7_ok,
        ms_learn=ms_learn_down,
        gh_search=gh_search_ok,
    )

    assert "ms_learn" in result.degraded_sources, (
        f"MS Learn failure must be in degraded_sources; got {result.degraded_sources}"
    )
    sources_in_hits = {hit.source for hit in result.hits}
    assert "context7" in sources_in_hits
    assert "gh_search" in sources_in_hits
    assert "ms_learn" not in sources_in_hits


# ---------------------------------------------------------------------------
# Test 3: NotebookLM auth expired -> Tier 3 skipped with warning
# ---------------------------------------------------------------------------


def test_notebooklm_auth_expired_degrades_to_tier2_only_with_warning() -> None:
    """When ``server_info`` reports ``authenticated: False``, Tier 3 is skipped.

    Arrange: server_info probe returns ``{authenticated: False, ...}``.

    Act: invoke ``tier3_notebooklm`` with the probe injected.

    Assert:
      * ``notebook_create``, ``source_add``, ``notebook_query`` were NOT called.
      * The result is degraded with the ``notebooklm auth expired`` warning.
      * The warning suggests running ``nlm login`` so the user can recover.
    """
    create_calls: list[dict] = []
    source_calls: list[dict] = []
    query_calls: list[dict] = []

    def server_info_unauth() -> dict:
        return {"authenticated": False, "user": None}

    def notebook_create(*, title: str) -> dict:
        create_calls.append({"title": title})
        return {"notebook_id": "should-not-be-used"}

    def source_add(**kwargs) -> dict:
        source_calls.append(kwargs)
        return {"source_id": "x"}

    def notebook_query(**kwargs) -> dict:
        query_calls.append(kwargs)
        return {"answer": "should not happen", "conversation_id": "x"}

    result = tier3_notebooklm(
        "compare A vs B",
        sources=["https://example.com/a", "https://example.com/b"],
        timestamp_iso="2026-04-28T12:00:00+00:00",
        notebook_create=notebook_create,
        source_add=source_add,
        notebook_query=notebook_query,
        server_info=server_info_unauth,
    )

    assert isinstance(result, Tier3Result)
    assert result.degraded is True, "Tier 3 must mark degraded when auth expired"
    assert create_calls == [], (
        f"notebook_create MUST NOT be called when auth expired; got {create_calls}"
    )
    assert source_calls == [], (
        f"source_add MUST NOT be called when auth expired; got {source_calls}"
    )
    assert query_calls == [], (
        f"notebook_query MUST NOT be called when auth expired; got {query_calls}"
    )
    assert any("auth" in w.lower() for w in result.warnings), (
        f"Warnings must mention 'auth' so the user knows what's wrong; got {result.warnings}"
    )
    assert any("nlm login" in w for w in result.warnings), (
        f"Warnings must suggest 'nlm login' for recovery; got {result.warnings}"
    )


# ---------------------------------------------------------------------------
# Test 4: All external sources down -> local-only with warning
# ---------------------------------------------------------------------------


def test_all_external_down_returns_local_only_with_warning() -> None:
    """When every external MCP fails Tier 1 still returns degraded list of all 3.

    The helper does not orchestrate fallback to Tier 0 itself (that's the
    skill's responsibility), but it MUST surface every failed source so the
    synthesizer can emit the all-external-down warning visible to the user.

    Arrange: all three Tier 1 callables raise.

    Act: invoke ``tier1_free_mcps``.

    Assert:
      * ``degraded_sources`` lists all three names.
      * ``hits`` is empty.
    """

    def boom_context7(*_args, **_kw):
        raise RuntimeError("network down")

    def boom_ms_learn(*_args, **_kw):
        raise ConnectionError("MS Learn unreachable")

    def boom_gh(*_args, **_kw):
        raise RuntimeError("gh CLI failure")

    query = "Azure react github library how do projects retry"
    result = tier1_free_mcps(
        query,
        context7=boom_context7,
        ms_learn=boom_ms_learn,
        gh_search=boom_gh,
    )

    assert set(result.degraded_sources) == {"context7", "ms_learn", "gh_search"}, (
        f"All three sources must be reported as degraded; got {result.degraded_sources}"
    )
    assert result.hits == [], (
        f"All sources failed; hits must be empty so the synthesizer falls back to local; "
        f"got {result.hits}"
    )
