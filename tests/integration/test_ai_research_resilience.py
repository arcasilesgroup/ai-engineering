"""RED-phase tests for spec-111 T-4.8 -- /ai-research degraded-mode resilience.

Spec acceptance:
    Tier 1 MCP failures (Context7, MS Learn, gh search) MUST NOT abort
    the other futures: each per-MCP failure appends the source name to a
    ``degraded_sources`` list and the synthesizer surfaces a visible
    warning to the user.

    Tier 3 (NotebookLM, ``notebooklm-py`` CLI backend) MUST probe
    ``notebooklm doctor`` first (capability/auth, via the injected
    ``doctor_probe``); if it reports unavailable (non-zero exit -> the probe
    returns ``False``), the launch is skipped (degraded) with a warning
    suggesting ``notebooklm login`` / ``notebooklm doctor`` and no other CLI
    mutation (``create_notebook`` / ``add_research``) -- D7 fail-soft
    (spec-175 D-175-04).

    All-external-down case: Tier 1 + Tier 2 + Tier 3 all fail -> the
    synthesizer falls back to local context (Tier 0 results) and surfaces
    a "all external sources down" warning so the user knows the answer
    is local-only.
"""

from __future__ import annotations

from tests.integration._ai_research_capability import is_available
from tests.integration._ai_research_tier1_helper import (
    Tier1Hit,
    tier1_free_mcps,
)
from tests.integration._ai_research_tier2_helper import tier2_web
from tests.integration._ai_research_tier3_helper import (
    tier3_harvest,
    tier3_launch,
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
    """When ``notebooklm doctor`` reports unavailable, Tier 3 is skipped.

    Arrange: the ``doctor_probe`` capability/auth gate returns ``False`` (a
    non-zero ``notebooklm doctor`` exit -- expired Google session).

    Act: invoke ``tier3_launch`` with the probe injected.

    Assert:
      * ``create_notebook`` and ``add_research`` were NOT called.
      * The launch is degraded with an empty ``notebook_id``.
      * A warning suggests ``notebooklm login`` so the user can recover.
    """
    create_calls: list[dict] = []
    research_calls: list[dict] = []

    def doctor_unavailable() -> bool:
        return False

    def create_notebook(*, title: str) -> str:
        create_calls.append({"title": title})
        return "should-not-be-used"

    def add_research(notebook_id: str, query: str, deep_timeout_sec: int) -> str:
        research_calls.append(
            {"notebook_id": notebook_id, "query": query, "deep_timeout_sec": deep_timeout_sec}
        )
        return "should-not-happen"

    launch = tier3_launch(
        "compare A vs B",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        doctor_probe=doctor_unavailable,
        create_notebook=create_notebook,
        add_research=add_research,
        deep_timeout_sec=1800,
    )

    assert launch["degraded"] is True, "Tier 3 must degrade when auth expired"
    assert launch["notebook_id"] == "", "No notebook id when the launch is skipped"
    assert create_calls == [], (
        f"create_notebook MUST NOT be called when auth expired; got {create_calls}"
    )
    assert research_calls == [], (
        f"add_research MUST NOT be called when auth expired; got {research_calls}"
    )
    assert any("notebooklm login" in w for w in launch["warnings"]), (
        f"Warnings must suggest 'notebooklm login' for recovery; got {launch['warnings']}"
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


# ===========================================================================
# Capability-ABSENCE resilience (notebooklm-async-tier3 D7 / AC2 / AC4)
#
# These tests are DISTINCT from the transient-exception cases above. Above, a
# present-but-flaky source RAISES during its call and is caught post-hoc. Here
# the source is ABSENT/unavailable up front (the capability probe says so), so
# it is skipped silently, recorded in ``degraded_sources``, and the underlying
# tool is NEVER invoked. Both paths converge on the same fail-soft contract:
# the run proceeds and never raises.
#
# The shared guard ``is_available(probe)`` gives every tier uniform semantics.
# ===========================================================================


def test_is_available_guard_treats_absence_as_unavailable() -> None:
    """The shared capability guard maps absence/falsy/auth-false to False.

    ``is_available`` is the single DRY predicate every tier routes through so
    "absent" means the same thing for Context7, Exa, and NotebookLM:

      * ``None`` probe (tool not wired)            -> False
      * probe raises (cannot even introspect)      -> False
      * probe returns a falsy payload ({}, [], 0)  -> False
      * probe returns ``{"authenticated": False}`` -> False
      * any other truthy payload                   -> True
    """

    def probe_raises() -> dict:
        raise RuntimeError("MCP server not reachable")

    # Unavailable forms.
    assert is_available(None) is False, "A missing probe means the tool is absent"
    assert is_available(probe_raises) is False, "A raising probe is treated as absent"
    assert is_available(lambda: {}) is False, "An empty payload is unavailable"
    assert is_available(lambda: []) is False, "A falsy payload is unavailable"
    assert is_available(lambda: None) is False, "A None payload is unavailable"
    assert is_available(lambda: {"authenticated": False}) is False, (
        "An unauthenticated payload is unavailable"
    )

    # Available forms.
    assert is_available(lambda: {"authenticated": True}) is True
    assert is_available(lambda: {"notebooks": []}) is True, (
        "A truthy payload with no auth key defaults to available"
    )
    assert is_available(lambda: {"ok": 1}) is True


def test_notebooklm_absent_probe_degrades_tier3_run_proceeds() -> None:
    """AC2: NotebookLM ABSENT (``doctor`` non-zero) -> Tier 3 degraded, run proceeds.

    Distinct from ``test_notebooklm_auth_expired_*`` only in intent: there the
    ``notebooklm doctor`` gate fails because the Google session expired; here
    it fails because the ``notebooklm`` binary is simply not installed. Either
    way ``doctor_probe`` returns ``False``, no CLI mutation runs, and the launch
    degrades silently so Tiers 0-2 can carry the run (exit 0).
    """
    create_calls: list[dict] = []
    research_calls: list[dict] = []

    def doctor_absent() -> bool:
        # notebooklm binary not installed -> doctor exits non-zero.
        return False

    def create_notebook(*, title: str) -> str:
        create_calls.append({"title": title})
        return "should-not-be-used"

    def add_research(notebook_id: str, query: str, deep_timeout_sec: int) -> str:
        research_calls.append(
            {"notebook_id": notebook_id, "query": query, "deep_timeout_sec": deep_timeout_sec}
        )
        return "should-not-happen"

    launch = tier3_launch(
        "design an async harvest model",
        timestamp_iso="2026-05-22T12:00:00+00:00",
        doctor_probe=doctor_absent,
        create_notebook=create_notebook,
        add_research=add_research,
        deep_timeout_sec=1800,
    )

    assert launch["degraded"] is True, "Absent NotebookLM must degrade Tier 3"
    assert launch["notebook_id"] == "", "No notebook id when the tool is absent"
    assert create_calls == [], (
        f"create_notebook MUST NOT be called when the tool is absent; got {create_calls}"
    )
    assert research_calls == [], (
        f"add_research MUST NOT be called when the tool is absent; got {research_calls}"
    )

    # The run proceeds: harvesting a degraded launch passes through cleanly
    # (no wait, no raise) so synthesis continues on Tiers 0-2 only.
    harvest = tier3_harvest(
        launch,
        wait_for_job=lambda _job, *, timeout: (_ for _ in ()).throw(
            AssertionError("wait_for_job MUST NOT run for an absent NotebookLM")
        ),
        read_result=lambda _id: (_ for _ in ()).throw(
            AssertionError("read_result MUST NOT run for an absent NotebookLM")
        ),
        wait_budget_sec=300.0,
    )
    assert harvest.degraded is True
    assert harvest.report_markdown == "", "No deep report when NotebookLM is absent"
    assert harvest.warnings, "A degraded harvest must carry a visible note (AC2)"


def test_context7_absent_probe_skipped_silently_and_degraded() -> None:
    """AC4: an ABSENT Context7 is skipped silently and recorded as degraded.

    Distinct from ``test_context7_down_*`` (where Context7 RAISES mid-call).
    Here a per-source availability probe reports Context7 absent, so its
    callable is NEVER invoked; the source name still lands in
    ``degraded_sources`` and the surviving MCPs contribute hits. The run never
    raises.
    """
    context7_calls: list[str] = []

    def context7_absent_should_not_run(_query: str, **_) -> list[Tier1Hit]:
        context7_calls.append(_query)
        raise AssertionError("Context7 callable MUST NOT run when probed absent")

    def ms_learn_ok(_query: str, **_) -> list[Tier1Hit]:
        return [
            Tier1Hit(
                title="Azure Functions retry guide",
                url="https://learn.microsoft.com/azure/functions/retry",
                snippet="Retry policy",
                source="ms_learn",
            )
        ]

    def gh_search_ok(_query: str, **_) -> list[Tier1Hit]:
        return [
            Tier1Hit(
                title="github.com/foo/bar",
                url=None,
                snippet="example",
                source="gh_search",
                repo="foo/bar",
                path="src/retry.py",
            )
        ]

    query = "Azure dotnet retry patterns library github examples"
    result = tier1_free_mcps(
        query,
        context7=context7_absent_should_not_run,
        ms_learn=ms_learn_ok,
        gh_search=gh_search_ok,
        # Per-source availability: Context7 absent, the others present.
        context7_available=False,
    )

    assert context7_calls == [], "An absent Context7 must be skipped silently, not invoked"
    assert "context7" in result.degraded_sources, (
        f"Absent Context7 must be recorded in degraded_sources (AC4); got {result.degraded_sources}"
    )
    sources_in_hits = {hit.source for hit in result.hits}
    assert "ms_learn" in sources_in_hits, "Surviving MS Learn hit must be present"
    assert "gh_search" in sources_in_hits, "Surviving gh_search hit must be present"
    assert "context7" not in sources_in_hits, "Absent Context7 contributes zero hits"


def test_exa_absent_falls_back_to_builtin_and_records_degraded() -> None:
    """AC4: ABSENT Exa -> built-in WebSearch fallback + ``exa`` degraded.

    The Tier 2 capability flag is derived through the shared guard. When Exa
    is absent the built-in WebSearch carries the search, ``"exa"`` is recorded
    in ``degraded_sources`` (fail-soft), and the run still returns output.
    """
    exa_calls: list[str] = []
    builtin_calls: list[str] = []

    def tavily_search_absent(_query: str, **_) -> list[dict]:
        raise AssertionError("Tavily search MUST NOT run when Tavily is absent")

    def tavily_fetch_absent(_url: str, **_) -> list[dict]:
        raise AssertionError("Tavily fetch MUST NOT run when Tavily is absent")

    def exa_search_absent(_query: str, **_) -> list[dict]:
        exa_calls.append(_query)
        raise AssertionError("Exa search MUST NOT run when Exa is absent")

    def exa_fetch_absent(_url: str, **_) -> list[dict]:
        raise AssertionError("Exa fetch MUST NOT run when Exa is absent")

    def builtin_search(_query: str, **_) -> list[dict]:
        builtin_calls.append(_query)
        return [{"title": "fallback result", "url": "https://example.org/x"}]

    def builtin_fetch(_url: str, **_) -> list[dict]:
        return []

    # Absent Tavily + Exa probes routed through the shared guard -> both
    # unavailable, so the built-in WebSearch carries the search.
    exa_probe_absent = None
    exa_available = is_available(exa_probe_absent)
    assert exa_available is False, "An absent Exa probe must resolve to unavailable"

    result = tier2_web(
        "best practices for retries",
        # Fewer than the skip threshold so Tier 2 actually runs.
        tier1_hits=[{"title": "h", "url": "https://a"}],
        tavily_search=tavily_search_absent,
        tavily_fetch=tavily_fetch_absent,
        tavily_available=False,
        exa_search=exa_search_absent,
        exa_fetch=exa_fetch_absent,
        web_search=builtin_search,
        web_fetch=builtin_fetch,
        exa_available=exa_available,
    )

    assert exa_calls == [], "Absent Exa must be skipped silently, not invoked"
    assert len(builtin_calls) == 1, "Built-in WebSearch must carry the fallback"
    assert "exa" in result.degraded_sources, (
        f"Absent Exa must be recorded in degraded_sources (AC4); got {result.degraded_sources}"
    )
    assert result.skipped is False, "Tier 2 must still run and return output"
    assert result.hits, "The built-in fallback must produce hits"


# ===========================================================================
# D-172-09 fail-soft: a degraded Tier-3 NEVER blocks synthesis (no banner)
#
# First-class fail-soft contract (closes completeness-critic gap #3). For
# every Tier-3 degrade terminal -- timeout, failed status, [AUTH_REQUIRED],
# and launch-retry-exhausted -- the launch/harvest must return a result with
# ``degraded=True`` and the run is expected to proceed on Tiers 0-2: neither
# ``tier3_launch`` nor ``tier3_harvest`` may raise, call ``sys.exit``, or
# return a "blocking" sentinel. The degrade is a WARNING, not a hard stop.
# ===========================================================================


def _healthy_launch(notebook_id: str = "nb-soft") -> dict:
    """A non-degraded launch dict to feed harvest degrade-terminal cases."""
    return {"notebook_id": notebook_id, "degraded": False, "warnings": []}


def test_degraded_tier3_does_not_block_synthesis() -> None:
    """Every Tier-3 degrade terminal returns degraded=True without aborting.

    D-172-09 (carried into spec-175): NotebookLM degradation is fail-soft -- it
    surfaces a warning and the run continues on Tiers 0-2. This pins that NONE
    of the four degrade terminals raises or returns a blocking sentinel. Under
    the CLI model the harvest terminals are the ``wait_for_job`` statuses
    (``timeout`` / ``failed`` / ``auth_required``) and the launch terminal is a
    failed ``add_research`` (D-175-03).
    """

    def _never_read(_id: str) -> dict:
        raise AssertionError("read_result MUST NOT run on a degrade terminal")

    # --- Terminal 1: harvest wall-clock timeout -----------------------------
    timeout_result = tier3_harvest(
        _healthy_launch("nb-timeout"),
        wait_for_job=lambda _job, *, timeout: "timeout",
        read_result=_never_read,
        wait_budget_sec=60.0,
    )
    assert timeout_result.degraded is True, "A harvest timeout must degrade, not block"
    assert timeout_result.timed_out is True, "A timeout status must set timed_out"
    assert timeout_result.warnings, "The timeout degrade must be a visible warning"

    # --- Terminal 2: harvest failed status ----------------------------------
    failed_result = tier3_harvest(
        _healthy_launch("nb-failed"),
        wait_for_job=lambda _job, *, timeout: "failed",
        read_result=_never_read,
        wait_budget_sec=300.0,
    )
    assert failed_result.degraded is True, "A failed status must degrade, not block"
    assert failed_result.warnings, "The failed degrade must be a visible warning"

    # --- Terminal 3: harvest auth_required ----------------------------------
    auth_result = tier3_harvest(
        _healthy_launch("nb-auth"),
        wait_for_job=lambda _job, *, timeout: "auth_required",
        read_result=_never_read,
        wait_budget_sec=300.0,
    )
    assert auth_result.degraded is True, "auth_required must degrade, not block"
    assert any("notebooklm login" in w for w in auth_result.warnings), (
        f"Auth degrade must carry the correct login command; got {auth_result.warnings}"
    )

    # --- Terminal 4: launch failed (add_research always raises) -------------
    research_attempts: list[dict] = []

    def _doctor_ok() -> bool:
        return True

    def _create(*, title: str) -> str:
        return "nb-launch-exhausted"

    def _add_research_always_fails(notebook_id: str, query: str, deep_timeout_sec: int) -> str:
        research_attempts.append(
            {"notebook_id": notebook_id, "query": query, "deep_timeout_sec": deep_timeout_sec}
        )
        raise RuntimeError("add_research keeps failing")

    launch = tier3_launch(
        "launch exhausted",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        doctor_probe=_doctor_ok,
        create_notebook=_create,
        add_research=_add_research_always_fails,
        deep_timeout_sec=1800,
    )
    assert launch["degraded"] is True, "A failed launch must degrade, not raise"
    assert launch["warnings"], "The launch degrade must be a visible warning"
    # And harvesting that degraded launch still passes through cleanly.
    harvest = tier3_harvest(
        launch,
        wait_for_job=lambda _job, *, timeout: (_ for _ in ()).throw(
            AssertionError("a degraded launch must not wait on a job")
        ),
        read_result=lambda _id: (_ for _ in ()).throw(
            AssertionError("a degraded launch must not read a result")
        ),
        wait_budget_sec=300.0,
    )
    assert harvest.degraded is True, "The downstream harvest stays degraded, not blocking"
