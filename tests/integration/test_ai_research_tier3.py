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
  reuse) a notebook and start ``nlm_research(mode='deep')`` (the launch
  wraps create/research in a bounded retry, fail-soft on exhaustion).
* ``tier3_harvest(...)`` -- bounded *status* poll of ``poll_status`` against
  an injected monotonic ``clock`` until a terminal status. ``nlm_research``
  is NON-blocking and there is NO ``mcp__notebooklm__job_status`` tool, so
  completion is detected by re-polling the research status (D-172-05):
  ``status == "completed"`` reads ``report_markdown`` + ``sources``;
  ``failed``/``error`` or an ``[AUTH_REQUIRED]`` signal stops and degrades;
  exceeding the wait budget yields ``timed_out=True`` with the
  ``notebook_id`` preserved. Polls are spaced by a capped back-off so the
  loop never spins without sleeping (D-172-08).
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
    """Stand-in for ``mcp__notebooklm__nlm_create_notebook``.

    ``raises_n`` makes the first ``raises_n`` calls raise (transient create
    failure) before the remaining calls return the notebook id -- so a test
    can exercise the bounded launch retry (T-14, D-172-08).
    """

    def __init__(self, returned_id: str = "nb-fresh-123", *, raises_n: int = 0) -> None:
        self.calls: list[dict] = []
        self.returned_id = returned_id
        self.raises_n = raises_n

    def __call__(self, *, title: str) -> dict:
        self.calls.append({"title": title})
        if len(self.calls) <= self.raises_n:
            raise RuntimeError("nlm_create_notebook transient failure")
        return {"notebook_id": self.returned_id}


class _RecordingResearch:
    """Stand-in for ``mcp__notebooklm__nlm_research`` (deep mode).

    ``raises_n`` makes the first ``raises_n`` calls raise (transient research
    failure); set it higher than the retry budget to exhaust the bounded
    launch retry (T-14, D-172-08). ``nlm_research(mode="deep")`` is
    NON-blocking -- it returns an immediate ``status="in_progress"`` ack.
    """

    def __init__(self, job_id: str = "job-deep-1", *, raises_n: int = 0) -> None:
        self.calls: list[dict] = []
        self.job_id = job_id
        self.raises_n = raises_n

    def __call__(self, *, notebook: str, query: str, mode: str) -> dict:
        self.calls.append({"notebook": notebook, "query": query, "mode": mode})
        if len(self.calls) <= self.raises_n:
            raise RuntimeError("nlm_research transient failure")
        return {"job_id": self.job_id, "status": "in_progress"}


class _RecordingSleep:
    """Recording stand-in for the injected ``sleep(seconds)`` back-off.

    Captures every requested delay so a test can assert the harvest spaces
    its polls with a non-decreasing, capped interval and never spins without
    sleeping (T-13, D-172-08). It does NOT actually sleep.
    """

    def __init__(self) -> None:
        self.delays: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.delays.append(seconds)


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


class _ScriptedPollStatus:
    """Stand-in for the injected ``poll_status(notebook_id)`` status callable.

    Yields each scripted payload in turn (then repeats the last one), so a
    test can model "in_progress, in_progress, completed" or "in_progress
    forever". There is NO ``mcp__notebooklm__job_status`` tool -- completion
    is observed by re-polling the research status (D-172-05). A scripted
    entry that is an ``Exception`` instance (or class) is *raised* instead of
    returned, so a test can model an ``[AUTH_REQUIRED]`` exception mid-poll.
    """

    def __init__(self, payloads: list[object]) -> None:
        self._payloads = list(payloads)
        self._i = 0
        self.calls: list[str] = []

    def __call__(self, notebook_id: str) -> dict:
        self.calls.append(notebook_id)
        if self._i < len(self._payloads):
            payload = self._payloads[self._i]
            self._i += 1
        else:
            payload = self._payloads[-1]
        if isinstance(payload, BaseException) or (
            isinstance(payload, type) and issubclass(payload, BaseException)
        ):
            raise payload
        return payload  # type: ignore[return-value]


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
    assert "uvx --from notebooklm-skill notebooklm login" in joined, (
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

    Arrange: ``poll_status`` returns in_progress, in_progress, completed
    (with a report and autonomously-discovered sources). The clock advances
    within the 300s budget.

    Act: invoke ``tier3_harvest`` on a healthy launch.

    Assert:
      * ``report_markdown`` and ``sources_discovered`` are populated from
        the completed payload.
      * ``notebook_id`` flows through.
      * ``timed_out`` and ``degraded`` are False; no warnings.
    """
    launch = {"notebook_id": "nb-fresh-123", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus(
        [
            {"status": "in_progress"},
            {"status": "in_progress"},
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
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        sleep=_RecordingSleep(),
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
    assert poll_status.calls, "poll_status must be polled at least once"
    assert all(nb == "nb-fresh-123" for nb in poll_status.calls)


def test_harvest_does_not_terminate_on_early_sources_only_status() -> None:
    """Sources stream mid-run; only ``status=="completed"`` terminates.

    Regression for the D-172-05 weak-heuristic trap: an early ``in_progress``
    payload that *already* carries a non-empty ``sources`` list MUST NOT be
    treated as complete -- NotebookLM streams sources while the job is still
    running, so the source/artifact count is only a weak secondary heuristic.
    The loop keeps polling until the status field itself says ``completed``.
    """
    launch = {"notebook_id": "nb-stream", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus(
        [
            # Sources already present but the job is NOT done -- must not stop.
            {
                "status": "in_progress",
                "sources": ["https://nlm.example.com/early-1"],
            },
            {
                "status": "in_progress",
                "sources": [
                    "https://nlm.example.com/early-1",
                    "https://nlm.example.com/early-2",
                ],
            },
            {
                "status": "completed",
                "report_markdown": "# Final report\n\nBody [1][2].",
                "sources": [
                    "https://nlm.example.com/early-1",
                    "https://nlm.example.com/early-2",
                ],
            },
        ]
    )
    clock = _FakeClock([0.0, 10.0, 20.0, 30.0])

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        sleep=_RecordingSleep(),
    )

    assert len(poll_status.calls) == 3, (
        "Harvest must keep polling past in_progress payloads that already carry "
        f"sources; only status==completed terminates. Got {len(poll_status.calls)} polls"
    )
    assert result.report_markdown == "# Final report\n\nBody [1][2]."
    assert result.degraded is False
    assert result.timed_out is False


@pytest.mark.parametrize(
    "report_field",
    ["report", "report_markdown", "summary"],
)
def test_harvest_reads_report_alias_field(report_field: str) -> None:
    """The completed payload may carry the report under any alias field.

    The harvester accepts the report under ``report_markdown``, ``report``,
    or ``summary`` (backend field-name variance, D-172-08) and normalises
    onto ``report_markdown``. Sources read tuple OR list with the same
    tolerance.
    """
    launch = {"notebook_id": "nb-alias", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus(
        [
            {
                "status": "completed",
                report_field: "# Aliased report\n\nBody [1].",
                # sources delivered as a tuple, not a list.
                "sources": ("https://nlm.example.com/x",),
            }
        ]
    )
    clock = _FakeClock([0.0, 5.0])

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        sleep=_RecordingSleep(),
    )

    assert result.report_markdown == "# Aliased report\n\nBody [1]."
    assert result.sources_discovered == ["https://nlm.example.com/x"]
    assert result.timed_out is False


class _AttrStatusPayload:
    """A status payload exposed via *attributes* rather than dict keys.

    Models a backend that returns an object (e.g. a pydantic/SDK model). The
    harvester prefers attribute access, then ``.get`` -- dict subscript is
    deprecated (D-172-08 alias tolerance).
    """

    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


def test_harvest_reads_status_and_report_via_attribute_access() -> None:
    """An attribute-exposing payload is read via attributes, not subscript.

    The status, report, and sources are read with attribute access taking
    precedence so an SDK model (no ``__getitem__``) is tolerated.
    """
    launch = {"notebook_id": "nb-attr", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus(
        [
            _AttrStatusPayload(status="in_progress"),
            _AttrStatusPayload(
                status="completed",
                report_markdown="# Attr report\n\nBody [1].",
                sources=["https://nlm.example.com/attr-1"],
            ),
        ]
    )
    clock = _FakeClock([0.0, 5.0, 10.0])

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        sleep=_RecordingSleep(),
    )

    assert result.report_markdown == "# Attr report\n\nBody [1]."
    assert result.sources_discovered == ["https://nlm.example.com/attr-1"]
    assert result.degraded is False
    assert result.timed_out is False


@pytest.mark.parametrize("completed_literal", ["COMPLETED", "Completed", "completed"])
def test_harvest_status_is_case_insensitive(completed_literal: str) -> None:
    """The status literal is matched case-insensitively (D-172-05).

    ``"COMPLETED"`` / ``"Completed"`` / ``"completed"`` all terminate the
    poll loop and read the report (normalised ``str(...).strip().lower()``).
    """
    launch = {"notebook_id": "nb-case", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus(
        [
            {
                "status": completed_literal,
                "report_markdown": "# Cased report\n\nBody [1].",
                "sources": ["https://nlm.example.com/c"],
            }
        ]
    )
    clock = _FakeClock([0.0, 5.0])

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        sleep=_RecordingSleep(),
    )

    assert result.report_markdown == "# Cased report\n\nBody [1]."
    assert result.degraded is False
    assert result.timed_out is False


def test_harvest_optional_ask_followup() -> None:
    """When ``nlm_ask`` is injected, its answer fills ``synthesized_response``.

    The optional cited follow-up runs only after the deep job completes.
    """
    launch = {"notebook_id": "nb-ask", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus(
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
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        nlm_ask=nlm_ask,
        sleep=_RecordingSleep(),
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

    Arrange: ``poll_status`` always returns in_progress; the clock jumps
    past the 60s budget.
    """
    launch = {"notebook_id": "nb-slow-77", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus([{"status": "in_progress"}])
    # Budget is 60s; clock crosses it on the second reading.
    clock = _FakeClock([0.0, 70.0, 80.0])

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=60.0,
        sleep=_RecordingSleep(),
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


# ---------------------------------------------------------------------------
# tier3_harvest -- terminal-status branches (D-172-08): stop early, degrade
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("terminal_status", ["failed", "error"])
def test_harvest_failed_status_stops_and_degrades(terminal_status: str) -> None:
    """A terminal ``failed``/``error`` status stops the poll and degrades.

    D-172-08: a dead job must NOT be polled until the wait budget drains.
    The first poll that reports a terminal failure short-circuits with
    ``degraded=True``, ``timed_out=False`` (terminal, not wall-clock), the
    ``notebook_id`` preserved, an empty report, and a failure warning.
    """
    launch = {"notebook_id": "nb-dead-9", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus([{"status": terminal_status}])
    clock = _FakeClock([0.0, 5.0, 10.0])

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        sleep=_RecordingSleep(),
    )

    assert poll_status.calls == ["nb-dead-9"], (
        "A terminal failure must short-circuit on the first poll without burning "
        f"the wait budget; got {poll_status.calls}"
    )
    assert result.degraded is True, "A failed job must degrade"
    assert result.timed_out is False, "A terminal failure is not a wall-clock timeout"
    assert result.notebook_id == "nb-dead-9", "notebook_id must be preserved"
    assert result.report_markdown == "", "No report from a failed job"
    assert result.warnings, "A failed harvest must surface a visible note"


def test_harvest_auth_required_escalates_not_keep_polling() -> None:
    """An ``[AUTH_REQUIRED]`` signal mid-poll escalates immediately.

    D-172-06 / D-172-08: when ``poll_status`` reports/raises an
    ``[AUTH_REQUIRED]`` signal, the harvest stops on the FIRST poll (not
    "still running"), degrades, and surfaces the CORRECT login command.
    Pinned in lockstep with the helper ``_UNAVAILABLE_WARNING`` (T-19).
    """
    launch = {"notebook_id": "nb-auth-1", "degraded": False, "warnings": []}
    # The status payload carries the [AUTH_REQUIRED] sentinel string.
    poll_status = _ScriptedPollStatus([{"status": "[AUTH_REQUIRED]"}])
    clock = _FakeClock([0.0, 5.0, 10.0])

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        sleep=_RecordingSleep(),
    )

    assert poll_status.calls == ["nb-auth-1"], (
        f"[AUTH_REQUIRED] must stop on the first poll; got {poll_status.calls}"
    )
    assert result.degraded is True
    assert result.timed_out is False, "Auth escalation is not a wall-clock timeout"
    joined = " ".join(result.warnings)
    assert "uvx --from notebooklm-skill notebooklm login" in joined, (
        f"Auth warning must carry the CORRECT login command; got {result.warnings!r}"
    )


def test_harvest_auth_required_raised_escalates() -> None:
    """An ``[AUTH_REQUIRED]`` *exception* mid-poll is caught and escalated.

    The MCP may raise an ``[AUTH_REQUIRED]`` error rather than return it. The
    harvest catches it, stops, degrades, and surfaces the correct login
    command -- never propagating the exception (fail-soft D-172-09).
    """
    launch = {"notebook_id": "nb-auth-2", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus([RuntimeError("[AUTH_REQUIRED] session expired")])
    clock = _FakeClock([0.0, 5.0, 10.0])

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        sleep=_RecordingSleep(),
    )

    assert poll_status.calls == ["nb-auth-2"]
    assert result.degraded is True
    assert result.timed_out is False
    joined = " ".join(result.warnings)
    assert "uvx --from notebooklm-skill notebooklm login" in joined, (
        f"Auth warning must carry the CORRECT login command; got {result.warnings!r}"
    )


# ---------------------------------------------------------------------------
# tier3_harvest -- capped back-off cadence (D-172-08): no tight while-True
# ---------------------------------------------------------------------------


def test_harvest_polls_with_capped_backoff() -> None:
    """The harvest spaces polls with a capped, non-decreasing back-off.

    D-172-08: the former tight ``while True`` with no sleep risked MCP
    rate-limits + context blowup. Now a ``sleep(seconds)`` is injected and
    called between polls with a non-decreasing interval that never exceeds a
    cap -- the loop never spins without sleeping. The budget check uses the
    injected clock.
    """
    launch = {"notebook_id": "nb-backoff", "degraded": False, "warnings": []}
    poll_status = _ScriptedPollStatus(
        [
            {"status": "in_progress"},
            {"status": "in_progress"},
            {"status": "in_progress"},
            {
                "status": "completed",
                "report_markdown": "# Done\n\nBody [1].",
                "sources": ["https://nlm.example.com/b"],
            },
        ]
    )
    # Plenty of budget so the loop runs to completion, not to timeout.
    clock = _FakeClock([0.0, 5.0, 10.0, 15.0, 20.0, 25.0])
    sleep = _RecordingSleep()

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=900.0,
        sleep=sleep,
    )

    assert result.report_markdown == "# Done\n\nBody [1]."
    assert result.degraded is False
    # The loop polled 4 times (3 in_progress + 1 completed) -> at least one
    # sleep between the non-terminal polls; the loop never spun without sleeping.
    assert sleep.delays, "The harvest must sleep between polls, never tight-loop"
    assert all(d > 0 for d in sleep.delays), "Every back-off interval must be positive"
    # Non-decreasing (fixed OR capped exponential both satisfy this).
    assert sleep.delays == sorted(sleep.delays), (
        f"Back-off must be non-decreasing; got {sleep.delays}"
    )
    # Capped: no interval may exceed the documented 60s ceiling.
    assert max(sleep.delays) <= 60, f"Back-off must be capped at 60s; got {sleep.delays}"


def test_harvest_skips_when_launch_degraded() -> None:
    """A degraded launch is passed straight through without polling.

    If ``tier3_launch`` already short-circuited (NotebookLM unavailable),
    ``tier3_harvest`` performs no ``poll_status`` polling and propagates the
    degraded launch warnings.
    """
    launch = {
        "notebook_id": "",
        "degraded": True,
        "warnings": [
            "notebooklm unavailable -- run `uvx --from notebooklm-skill notebooklm login`"
        ],
    }
    poll_status = _ScriptedPollStatus([{"status": "in_progress"}])
    clock = _FakeClock([0.0, 1.0])

    result = tier3_harvest(
        launch,
        poll_status=poll_status,
        clock=clock,
        wait_budget_sec=300.0,
        sleep=_RecordingSleep(),
    )

    assert result.degraded is True
    assert result.notebook_id == ""
    assert result.report_markdown == ""
    assert poll_status.calls == [], "A degraded launch must not poll poll_status"
    assert result.warnings == launch["warnings"]


# ---------------------------------------------------------------------------
# tier3_launch -- bounded retry + subagent MCP pre-check (D-172-08, D-172-11)
# ---------------------------------------------------------------------------


def test_launch_retries_transient_create_then_succeeds() -> None:
    """A transient ``nlm_create_notebook`` failure is retried once, succeeds.

    D-172-08: ``nlm_create_notebook`` is wrapped in a bounded retry. A single
    transient failure is retried (<=2 attempts) and the launch then succeeds
    with no degrade.
    """
    nlm_list = _RecordingNlmList(available=True)
    nlm_create_notebook = _RecordingCreateNotebook(returned_id="nb-retry-ok", raises_n=1)
    nlm_research = _RecordingResearch()

    launch = tier3_launch(
        "retry transient create",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        nlm_list=nlm_list,
        nlm_create_notebook=nlm_create_notebook,
        nlm_research=nlm_research,
    )

    assert len(nlm_create_notebook.calls) == 2, (
        f"A transient create failure must be retried once; got {nlm_create_notebook.calls}"
    )
    assert launch["notebook_id"] == "nb-retry-ok"
    assert launch["degraded"] is False, "A successful retry must not degrade"
    assert launch["warnings"] == []
    assert len(nlm_research.calls) == 1, "Research must run after a successful create retry"


def test_launch_degrades_after_retry_budget_exhausted() -> None:
    """An always-raising ``nlm_research`` exhausts the retry and degrades.

    D-172-08 / D-172-09: when a launch step keeps failing past the bounded
    retry, the launch returns ``degraded=True`` with a warning naming the
    failed step and NEVER propagates the exception (fail-soft).
    """
    nlm_list = _RecordingNlmList(available=True)
    nlm_create_notebook = _RecordingCreateNotebook(returned_id="nb-created")
    nlm_research = _RecordingResearch(raises_n=99)  # always raises

    launch = tier3_launch(
        "research always fails",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        nlm_list=nlm_list,
        nlm_create_notebook=nlm_create_notebook,
        nlm_research=nlm_research,
    )

    assert launch["degraded"] is True, "An exhausted launch retry must degrade"
    # notebook_id is the created id (so a later --reuse-notebook can retry).
    assert launch["notebook_id"] == "nb-created"
    assert launch["warnings"], "A degraded launch must carry a visible warning"
    # Bounded: research attempted at most twice (attempts=2), never propagated.
    assert len(nlm_research.calls) <= 2, (
        f"Launch retry must be bounded to <=2 attempts; got {nlm_research.calls}"
    )


def test_launch_subagent_mcp_unavailable_degrades_at_launch() -> None:
    """The ``nlm_list`` probe is the in-subagent D-172-11 availability gate.

    When the background subagent's ``nlm_list`` probe reports unavailable (or
    raises), the launch degrades at T0 with the CORRECT login warning and
    ZERO ``nlm_create_notebook``/``nlm_research`` calls -- no empty
    ``notebook_id`` reaches the harvest.
    """
    nlm_list = _RecordingNlmList(available=False)
    nlm_create_notebook = _RecordingCreateNotebook()
    nlm_research = _RecordingResearch()

    launch = tier3_launch(
        "subagent has no notebooklm mcp",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        nlm_list=nlm_list,
        nlm_create_notebook=nlm_create_notebook,
        nlm_research=nlm_research,
    )

    assert len(nlm_list.calls) == 1, "The availability gate probes exactly once"
    assert nlm_create_notebook.calls == [], (
        "An unavailable subagent MCP must not create a notebook (D-172-11)"
    )
    assert nlm_research.calls == [], (
        "An unavailable subagent MCP must not start research (D-172-11)"
    )
    assert launch["degraded"] is True
    assert launch["notebook_id"] == ""
    joined = " ".join(launch["warnings"])
    assert "uvx --from notebooklm-skill notebooklm login" in joined, (
        f"Degrade warning must carry the CORRECT login command; got {launch['warnings']!r}"
    )


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
