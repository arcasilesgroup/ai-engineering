"""RED-phase tests for spec-111 T-2.1/T-2.2 -- /ai-research Tier 1 free MCPs.

Spec acceptance:
    Tier 1 (free MCPs, parallel) implemented in ``tier1-free-mcps.md`` --
    handler classifies the query into MCP-specific tags, then invokes the
    three free MCPs CONCURRENTLY when applicable: Context7 (library docs),
    Microsoft Learn (Azure/.NET), and ``gh search code/repos`` (real-world
    code). Results are deduplicated by URL (web/docs) or ``repo+path`` (code).

The handler is Markdown consumed by an LLM agent. The lockstep Python
helper at ``tests/integration/_ai_research_tier1_helper.py`` mirrors the
algorithm 1:1; these tests exercise the helper.

Status: RED until T-2.3 lands the helper module + handler logic.
"""

from __future__ import annotations

import time

import pytest

from tests.integration._ai_research_tier1_helper import (
    Tier1Hit,
    classify_tags,
    dedup_hits,
    tier1_free_mcps,
)

# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


class _RecordingMCP:
    """Stand-in MCP callable. Records the start timestamp on every call.

    Each instance simulates a slow (~50ms) MCP roundtrip so the parallel
    invocation test has a meaningful window in which to measure start
    timestamps.
    """

    def __init__(self, name: str, hits: list[Tier1Hit] | None = None) -> None:
        self.name = name
        self.hits = hits or []
        self.start_times: list[float] = []
        self.call_count = 0

    def __call__(self, query: str, *, tags: dict | None = None) -> list[Tier1Hit]:
        self.start_times.append(time.perf_counter())
        self.call_count += 1
        time.sleep(0.05)
        return list(self.hits)


# ---------------------------------------------------------------------------
# T-2.1: parallel invocation of all three MCPs
# ---------------------------------------------------------------------------


def test_three_mcps_called_in_parallel() -> None:
    """All 3 MCPs must be invoked concurrently (start delta < 100ms).

    Arrange: a query that triggers all three classifier tags, plus three
    recording fake MCPs that sleep 50ms each.

    Act: invoke ``tier1_free_mcps`` with the fakes injected.

    Assert: each MCP recorded exactly one call, and the maximum delta
    between start timestamps is < 100ms (clear evidence of concurrent
    dispatch rather than serial calls totalling >150ms).
    """
    context7 = _RecordingMCP("context7")
    ms_learn = _RecordingMCP("ms_learn")
    gh_search = _RecordingMCP("gh_search")

    query = "How does the React library compare to Microsoft .NET for github code patterns"

    tier1_free_mcps(
        query,
        context7=context7,
        ms_learn=ms_learn,
        gh_search=gh_search,
    )

    assert context7.call_count == 1, "Context7 MCP must be invoked exactly once for library queries"
    assert ms_learn.call_count == 1, (
        "MS Learn MCP must be invoked when query mentions Microsoft/.NET"
    )
    assert gh_search.call_count == 1, "gh search must be invoked when query mentions github/code"

    starts = [
        context7.start_times[0],
        ms_learn.start_times[0],
        gh_search.start_times[0],
    ]
    delta_ms = (max(starts) - min(starts)) * 1000.0
    assert delta_ms < 100.0, (
        f"Expected MCPs to start within 100ms of each other (parallel); "
        f"got delta={delta_ms:.1f}ms (likely serial invocation)"
    )


# ---------------------------------------------------------------------------
# T-2.2: dedup logic (URL for web, repo+path for code)
# ---------------------------------------------------------------------------


def test_dedup_by_url_or_path() -> None:
    """Dedup strips query params for web sources and uses ``repo+path`` for code.

    Arrange: hits where two web entries share the same URL apart from the
    query string and fragment, and two code entries share the same
    ``repo+path`` pair.

    Act: pass them through ``dedup_hits``.

    Assert: each web duplicate-pair collapses to one entry; each code
    duplicate-pair collapses to one entry. Distinct URLs/paths survive.
    """
    web_a = Tier1Hit(
        title="Hooks",
        url="https://react.dev/reference/react?utm=ad#section",
        snippet="useState",
        source="context7",
    )
    web_b = Tier1Hit(
        title="Hooks (mirror)",
        url="https://react.dev/reference/react?other=1",
        snippet="useState",
        source="ms_learn",
    )
    web_c = Tier1Hit(
        title="Different page",
        url="https://react.dev/learn/state",
        snippet="state",
        source="context7",
    )
    code_a = Tier1Hit(
        title="MyRepo helper",
        url=None,
        snippet="useEffect example",
        source="gh_search",
        repo="example/myrepo",
        path="src/lib/hook.ts",
    )
    code_b = Tier1Hit(
        title="MyRepo helper (dup)",
        url=None,
        snippet="useEffect example dup",
        source="gh_search",
        repo="example/myrepo",
        path="src/lib/hook.ts",
    )
    code_c = Tier1Hit(
        title="Different file",
        url=None,
        snippet="other",
        source="gh_search",
        repo="example/myrepo",
        path="src/lib/other.ts",
    )

    deduped = dedup_hits([web_a, web_b, web_c, code_a, code_b, code_c])

    assert len(deduped) == 4, (
        f"Expected 4 unique hits after dedup (2 web + 2 code); got {len(deduped)}: "
        f"{[(h.url, h.repo, h.path) for h in deduped]}"
    )

    surviving_urls = {h.url for h in deduped if h.url}
    assert surviving_urls == {
        "https://react.dev/reference/react?utm=ad#section",
        "https://react.dev/learn/state",
    } or surviving_urls == {
        "https://react.dev/reference/react?other=1",
        "https://react.dev/learn/state",
    }, f"Web dedup must keep one of the duplicate pair; got urls={surviving_urls}"

    surviving_paths = {(h.repo, h.path) for h in deduped if h.path}
    assert surviving_paths == {
        ("example/myrepo", "src/lib/hook.ts"),
        ("example/myrepo", "src/lib/other.ts"),
    }


# ---------------------------------------------------------------------------
# Edge cases that pin down classifier and dedup details
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query,expected",
    [
        # Library mention triggers Context7.
        ("Compare React state libraries", {"mentions_library": True}),
        ("How does the Django ORM handle joins", {"mentions_library": True}),
        # Microsoft/Azure/.NET trigger MS Learn.
        ("Best practices for Azure Functions", {"mentions_microsoft": True}),
        ("ASP.NET Core middleware pipeline", {"mentions_microsoft": True}),
        ("Microsoft Learn coverage of EF Core", {"mentions_microsoft": True}),
        # Code patterns trigger gh search.
        ("How do projects on github handle retries", {"mentions_code_pattern": True}),
        ("Real-world implementations of circuit breaker pattern", {"mentions_code_pattern": True}),
    ],
)
def test_classify_tags_picks_appropriate_mcps(query: str, expected: dict) -> None:
    tags = classify_tags(query)
    for key, value in expected.items():
        assert tags[key] is value, f"Query={query!r} expected {key}={value} but got tags={tags}"


def test_only_applicable_mcps_invoked() -> None:
    """An MS-only query must not invoke gh search or Context7."""
    context7 = _RecordingMCP("context7")
    ms_learn = _RecordingMCP("ms_learn")
    gh_search = _RecordingMCP("gh_search")

    tier1_free_mcps(
        "Configure Azure Functions cold-start timeouts",
        context7=context7,
        ms_learn=ms_learn,
        gh_search=gh_search,
    )

    assert ms_learn.call_count == 1
    assert context7.call_count == 0
    assert gh_search.call_count == 0
