"""Tests for /ai-research Tier 3 -- NotebookLM autonomous deep research.

Spec: ``notebooklm-async-tier3`` (D1 async background, D3 default-on, D4
bounded-wait, D5 backend swap, D7 fail-soft).

Tier 3 is redesigned around the ``claude-world/notebooklm-skill`` backend
(13 ``nlm_*`` MCP tools). The deep-research job is *launched first* (at T0,
in a background subagent) and *harvested last* with a bounded wait,
overlapping Tiers 0-2. NotebookLM discovers its own sources autonomously,
so Tier 3 no longer ingests Tier 1+2 URLs.

The handler is Markdown consumed by an LLM agent. The lockstep Python
helper at ``tests/integration/_ai_research_tier3_helper.py`` mirrors the
algorithm 1:1; these tests exercise the helper.

Algorithm under test:

* ``should_launch_tier3(*, notebooklm_available)`` -- launch whenever the
  tool is available (D3 default-on; no depth/comparative/source gating).
* ``tier3_launch(...)`` -- probe ``nlm_list`` (capability/auth); if
  unavailable, return degraded and call NOTHING else; otherwise create (or
  reuse) a notebook and start ``nlm_research(mode='deep')``.
* ``tier3_harvest(...)`` -- bounded poll of ``job_status`` against an
  injected monotonic ``clock`` until the job completes (read
  ``report_markdown`` + ``sources``) or the wait budget is exceeded
  (``timed_out=True``, ``notebook_id`` preserved).
"""

from __future__ import annotations

import pytest

from tests.integration._ai_research_tier3_helper import (
    Tier3Result,
    hash6,
    notebook_title,
    should_launch_tier3,
    tier3_harvest,
    tier3_launch,
    topic_slug,
)

# ---------------------------------------------------------------------------
# Fakes -- record every nlm_* MCP call with its kwargs.
# ---------------------------------------------------------------------------


class _RecordingNlmList:
    """Stand-in for ``mcp__notebooklm__nlm_list`` (capability/auth probe).

    Returns a truthy/authenticated payload by default. Set ``available`` to
    ``False`` to simulate an absent or unauthenticated NotebookLM, or set
    ``raises`` to simulate a probe that errors (network / MCP down).
    """

    def __init__(self, *, available: bool = True, raises: bool = False) -> None:
        self.calls: list[dict] = []
        self.available = available
        self.raises = raises

    def __call__(self) -> dict:
        self.calls.append({})
        if self.raises:
            raise RuntimeError("nlm_list probe failed: MCP server unavailable")
        if not self.available:
            return {"authenticated": False, "notebooks": []}
        return {"authenticated": True, "notebooks": []}


class _RecordingCreateNotebook:
    """Stand-in for ``mcp__notebooklm__nlm_create_notebook``."""

    def __init__(self, returned_id: str = "nb-fresh-123") -> None:
        self.calls: list[dict] = []
        self.returned_id = returned_id

    def __call__(self, *, title: str) -> dict:
        self.calls.append({"title": title})
        return {"notebook_id": self.returned_id}


class _RecordingResearch:
    """Stand-in for ``mcp__notebooklm__nlm_research`` (deep mode)."""

    def __init__(self, job_id: str = "job-deep-1") -> None:
        self.calls: list[dict] = []
        self.job_id = job_id

    def __call__(self, *, notebook: str, query: str, mode: str) -> dict:
        self.calls.append({"notebook": notebook, "query": query, "mode": mode})
        return {"job_id": self.job_id, "status": "running"}


class _RecordingAsk:
    """Stand-in for ``mcp__notebooklm__nlm_ask`` (optional follow-up)."""

    def __init__(self, answer: str = "follow-up answer with [1] citation") -> None:
        self.calls: list[dict] = []
        self.answer = answer

    def __call__(self, *, notebook: str, query: str) -> dict:
        self.calls.append({"notebook": notebook, "query": query})
        return {"answer": self.answer}


class _FakeClock:
    """Monotonically increasing zero-arg clock for deterministic harvests.

    Each call returns the next value from ``ticks`` (then holds the last
    value). Models elapsed wall-clock without real sleeping.
    """

    def __init__(self, ticks: list[float]) -> None:
        self._ticks = list(ticks)
        self._i = 0

    def __call__(self) -> float:
        if self._i < len(self._ticks):
            value = self._ticks[self._i]
            self._i += 1
            return value
        return self._ticks[-1]


class _ScriptedJobStatus:
    """Stand-in for the injected ``job_status(notebook_id)`` poll callable.

    Yields each scripted payload in turn (then repeats the last one), so a
    test can model "running, running, completed" or "running forever".
    """

    def __init__(self, payloads: list[dict]) -> None:
        self._payloads = list(payloads)
        self._i = 0
        self.calls: list[str] = []

    def __call__(self, notebook_id: str) -> dict:
        self.calls.append(notebook_id)
        if self._i < len(self._payloads):
            payload = self._payloads[self._i]
            self._i += 1
            return payload
        return self._payloads[-1]


# ---------------------------------------------------------------------------
# should_launch_tier3 -- D3 default-on
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("available,expected", [(True, True), (False, False)])
def test_should_launch_tier3_default_on(available: bool, expected: bool) -> None:
    """Tier 3 launches whenever NotebookLM is available (no depth gating).

    D3: the deep-research job is the DEFAULT path -- there is no
    ``--depth=deep`` / comparative / >=10-sources heuristic any more.
    """
    assert should_launch_tier3(notebooklm_available=available) is expected


# ---------------------------------------------------------------------------
# tier3_launch -- capability probe + start deep research
# ---------------------------------------------------------------------------


def test_launch_starts_deep_research_when_available() -> None:
    """Available NotebookLM: create a notebook and start deep research.

    Arrange: ``nlm_list`` reports authenticated.

    Act: invoke ``tier3_launch``.

    Assert:
      * ``nlm_list`` probed exactly once.
      * ``nlm_create_notebook`` called once with an
        ``ai-research/<slug>-<date>-<hash6>`` title.
      * ``nlm_research`` started once with ``mode='deep'`` against the
        created notebook id and the verbatim query.
      * The launch dict carries the notebook id, ``degraded=False``, no
        warnings.
    """
    nlm_list = _RecordingNlmList(available=True)
    nlm_create_notebook = _RecordingCreateNotebook(returned_id="nb-fresh-123")
    nlm_research = _RecordingResearch(job_id="job-deep-1")

    query = "how should we design an async harvest model"
    launch = tier3_launch(
        query,
        timestamp_iso="2026-04-28T12:00:00+00:00",
        nlm_list=nlm_list,
        nlm_create_notebook=nlm_create_notebook,
        nlm_research=nlm_research,
    )

    assert len(nlm_list.calls) == 1, "Capability/auth probe must run exactly once"

    assert len(nlm_create_notebook.calls) == 1
    title = nlm_create_notebook.calls[0]["title"]
    assert title.startswith("ai-research/"), f"Bad notebook title: {title!r}"
    assert "how-should-we-design-an-async-harvest" in title
    assert "2026-04-28" in title

    assert len(nlm_research.calls) == 1
    research_call = nlm_research.calls[0]
    assert research_call["notebook"] == "nb-fresh-123"
    assert research_call["mode"] == "deep"
    assert query in research_call["query"]

    assert launch["notebook_id"] == "nb-fresh-123"
    assert launch["degraded"] is False
    assert launch["warnings"] == []


def test_launch_reuse_notebook_skips_creation() -> None:
    """``reuse_notebook`` short-circuits ``nlm_create_notebook``.

    Arrange: ``reuse_notebook='nb-existing-9'``.

    Act: invoke ``tier3_launch``.

    Assert:
      * ``nlm_create_notebook`` is never called.
      * ``nlm_research`` runs against the reused notebook id.
      * The launch dict echoes the reused id, not degraded.
    """
    nlm_list = _RecordingNlmList(available=True)
    nlm_create_notebook = _RecordingCreateNotebook(returned_id="should-not-be-used")
    nlm_research = _RecordingResearch()

    launch = tier3_launch(
        "follow-up deep dive on the same corpus",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        nlm_list=nlm_list,
        nlm_create_notebook=nlm_create_notebook,
        nlm_research=nlm_research,
        reuse_notebook="nb-existing-9",
    )

    assert nlm_create_notebook.calls == [], (
        f"reuse_notebook MUST skip nlm_create_notebook; got {nlm_create_notebook.calls}"
    )
    assert launch["notebook_id"] == "nb-existing-9"
    assert launch["degraded"] is False
    assert nlm_research.calls[0]["notebook"] == "nb-existing-9"


def test_launch_capability_probe_unavailable_degrades_without_side_effects() -> None:
    """``nlm_list`` reporting unavailable degrades and calls NOTHING else.

    D7 fail-soft: an absent / unauthenticated NotebookLM is skipped
    silently (recorded degraded), never raised. The probe is the ONLY
    ``nlm_*`` call made.

    Assert:
      * ``nlm_create_notebook`` and ``nlm_research`` were never called.
      * The launch dict is degraded with an empty ``notebook_id`` and a
        warning referencing the operator recovery path.
    """
    nlm_list = _RecordingNlmList(available=False)
    nlm_create_notebook = _RecordingCreateNotebook()
    nlm_research = _RecordingResearch()

    launch = tier3_launch(
        "compare A vs B",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        nlm_list=nlm_list,
        nlm_create_notebook=nlm_create_notebook,
        nlm_research=nlm_research,
    )

    assert len(nlm_list.calls) == 1, "Probe must run before short-circuit"
    assert nlm_create_notebook.calls == [], (
        f"nlm_create_notebook MUST NOT run when unavailable; got {nlm_create_notebook.calls}"
    )
    assert nlm_research.calls == [], (
        f"nlm_research MUST NOT run when unavailable; got {nlm_research.calls}"
    )
    assert launch["degraded"] is True
    assert launch["notebook_id"] == ""
    assert launch["warnings"], "A degraded launch must carry a visible warning"
    joined = " ".join(launch["warnings"])
    assert "uvx notebooklm login" in joined, (
        f"Warning must reference the operator login command; got {launch['warnings']!r}"
    )
    assert "~/.notebooklm/storage_state.json" in joined, (
        f"Warning must reference the auth state file; got {launch['warnings']!r}"
    )


def test_launch_capability_probe_raises_degrades_without_side_effects() -> None:
    """A ``nlm_list`` that *raises* is treated as unavailable (fail-soft).

    Assert: no notebook creation / research; degraded launch with warning.
    """
    nlm_list = _RecordingNlmList(raises=True)
    nlm_create_notebook = _RecordingCreateNotebook()
    nlm_research = _RecordingResearch()

    launch = tier3_launch(
        "any query",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        nlm_list=nlm_list,
        nlm_create_notebook=nlm_create_notebook,
        nlm_research=nlm_research,
    )

    assert nlm_create_notebook.calls == []
    assert nlm_research.calls == []
    assert launch["degraded"] is True
    assert launch["notebook_id"] == ""
    assert launch["warnings"]


# ---------------------------------------------------------------------------
# tier3_harvest -- bounded poll (success path)
# ---------------------------------------------------------------------------


def test_harvest_success_populates_report_and_sources() -> None:
    """A job that completes within budget yields the deep report + sources.

    Arrange: ``job_status`` returns running, running, completed (with a
    report and autonomously-discovered sources). The clock advances within
    the 300s budget.

    Act: invoke ``tier3_harvest`` on a healthy launch.

    Assert:
      * ``report_markdown`` and ``sources_discovered`` are populated from
        the completed payload.
      * ``notebook_id`` flows through.
      * ``timed_out`` and ``degraded`` are False; no warnings.
    """
    launch = {"notebook_id": "nb-fresh-123", "degraded": False, "warnings": []}
    job_status = _ScriptedJobStatus(
        [
            {"status": "running"},
            {"status": "running"},
            {
                "status": "completed",
                "report_markdown": "# Deep report\n\nFindings with [1] and [2].",
                "sources": [
                    "https://nlm.example.com/found-1",
                    "https://nlm.example.com/found-2",
                ],
            },
        ]
    )
    clock = _FakeClock([0.0, 10.0, 20.0, 30.0])

    result = tier3_harvest(
        launch,
        job_status=job_status,
        clock=clock,
        wait_budget_sec=300.0,
    )

    assert isinstance(result, Tier3Result)
    assert result.notebook_id == "nb-fresh-123"
    assert result.report_markdown == "# Deep report\n\nFindings with [1] and [2]."
    assert result.sources_discovered == [
        "https://nlm.example.com/found-1",
        "https://nlm.example.com/found-2",
    ]
    assert result.timed_out is False
    assert result.degraded is False
    assert result.warnings == []
    assert job_status.calls, "job_status must be polled at least once"
    assert all(nb == "nb-fresh-123" for nb in job_status.calls)


def test_harvest_reads_report_alias_field() -> None:
    """The completed payload may carry the report under ``report``.

    The harvester accepts either ``report_markdown`` or ``report`` (backend
    field name variance) and normalises onto ``report_markdown``.
    """
    launch = {"notebook_id": "nb-alias", "degraded": False, "warnings": []}
    job_status = _ScriptedJobStatus(
        [
            {
                "status": "completed",
                "report": "# Aliased report\n\nBody [1].",
                "sources": ["https://nlm.example.com/x"],
            }
        ]
    )
    clock = _FakeClock([0.0, 5.0])

    result = tier3_harvest(
        launch,
        job_status=job_status,
        clock=clock,
        wait_budget_sec=300.0,
    )

    assert result.report_markdown == "# Aliased report\n\nBody [1]."
    assert result.timed_out is False


def test_harvest_optional_ask_followup() -> None:
    """When ``nlm_ask`` is injected, its answer fills ``synthesized_response``.

    The optional cited follow-up runs only after the deep job completes.
    """
    launch = {"notebook_id": "nb-ask", "degraded": False, "warnings": []}
    job_status = _ScriptedJobStatus(
        [
            {
                "status": "completed",
                "report_markdown": "# Report\n\nBody [1].",
                "sources": ["https://nlm.example.com/a"],
            }
        ]
    )
    clock = _FakeClock([0.0, 5.0])
    nlm_ask = _RecordingAsk(answer="Concise cited synthesis [1].")

    result = tier3_harvest(
        launch,
        job_status=job_status,
        clock=clock,
        wait_budget_sec=300.0,
        nlm_ask=nlm_ask,
    )

    assert len(nlm_ask.calls) == 1
    assert nlm_ask.calls[0]["notebook"] == "nb-ask"
    assert result.synthesized_response == "Concise cited synthesis [1]."
    assert result.report_markdown == "# Report\n\nBody [1]."


# ---------------------------------------------------------------------------
# tier3_harvest -- bounded poll (timeout path, D4)
# ---------------------------------------------------------------------------


def test_harvest_timeout_preserves_notebook_id_and_degrades() -> None:
    """Exceeding the wait budget sets ``timed_out`` and preserves the id.

    D4 bounded-wait: if the deep job has not completed by the time the
    injected clock exceeds ``wait_budget_sec``, the harvest returns
    ``timed_out=True`` with the ``notebook_id`` preserved (for a later
    ``--reuse-notebook`` harvest) and a degraded note in ``warnings``. The
    deep report is necessarily absent.

    Arrange: ``job_status`` always returns running; the clock jumps past
    the 60s budget.
    """
    launch = {"notebook_id": "nb-slow-77", "degraded": False, "warnings": []}
    job_status = _ScriptedJobStatus([{"status": "running"}])
    # Budget is 60s; clock crosses it on the second reading.
    clock = _FakeClock([0.0, 70.0, 80.0])

    result = tier3_harvest(
        launch,
        job_status=job_status,
        clock=clock,
        wait_budget_sec=60.0,
    )

    assert isinstance(result, Tier3Result)
    assert result.timed_out is True, "Exceeding the budget must set timed_out"
    assert result.degraded is True, "A timed-out harvest is degraded"
    assert result.notebook_id == "nb-slow-77", (
        "notebook_id MUST be preserved for a later --reuse-notebook harvest"
    )
    assert result.report_markdown == "", "No report when the job did not complete"
    assert result.sources_discovered == []
    assert result.warnings, "A timeout must surface a visible degraded note"
    joined = " ".join(result.warnings)
    assert "reuse-notebook" in joined or "nb-slow-77" in joined, (
        f"Timeout warning must mention recovery via the notebook id; got {result.warnings!r}"
    )


def test_harvest_skips_when_launch_degraded() -> None:
    """A degraded launch is passed straight through without polling.

    If ``tier3_launch`` already short-circuited (NotebookLM unavailable),
    ``tier3_harvest`` performs no ``job_status`` polling and propagates the
    degraded launch warnings.
    """
    launch = {
        "notebook_id": "",
        "degraded": True,
        "warnings": ["notebooklm unavailable -- run `uvx notebooklm login`"],
    }
    job_status = _ScriptedJobStatus([{"status": "running"}])
    clock = _FakeClock([0.0, 1.0])

    result = tier3_harvest(
        launch,
        job_status=job_status,
        clock=clock,
        wait_budget_sec=300.0,
    )

    assert result.degraded is True
    assert result.notebook_id == ""
    assert result.report_markdown == ""
    assert job_status.calls == [], "A degraded launch must not poll job_status"
    assert result.warnings == launch["warnings"]


# ---------------------------------------------------------------------------
# Notebook-naming helpers stay correct (persist helper depends on these)
# ---------------------------------------------------------------------------


def test_topic_slug_normalisation() -> None:
    """``topic_slug`` lowercases, dashes non-alnum runs, truncates, strips."""
    assert topic_slug("Compare Option A vs Option B!") == "compare-option-a-vs-option-b"
    assert topic_slug("  spaced   query  ") == "spaced-query"
    long = "x" * 60
    assert len(topic_slug(long)) == 40


def test_hash6_is_stable_and_six_chars() -> None:
    """``hash6`` is a deterministic 6-char SHA-256 prefix of query|timestamp."""
    h1 = hash6("query", "2026-04-28T12:00:00+00:00")
    h2 = hash6("query", "2026-04-28T12:00:00+00:00")
    h3 = hash6("query", "2026-04-28T12:00:01+00:00")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 6


def test_notebook_title_format() -> None:
    """``notebook_title`` composes ``ai-research/<slug>-<YYYY-MM-DD>-<hash6>``."""
    title = notebook_title("Async harvest design", "2026-04-28T12:00:00+00:00")
    assert title.startswith("ai-research/async-harvest-design-2026-04-28-")
    suffix = title.rsplit("-", 1)[-1]
    assert len(suffix) == 6
