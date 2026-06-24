"""Tests for /ai-research Tier 3 -- NotebookLM autonomous deep research (CLI).

Spec: ``spec-175`` (D-175-01 hard-cut to ``notebooklm-py`` CLI, D-175-02
one-command launch + native wait + ``--import-all``, D-175-03 detached
background launch + bounded harvest + reuse fallback, D-175-04 capability/auth
gate via ``notebooklm doctor``, D-175-05 lockstep rewrite). Supersedes the MCP
re-poll model (D-172-05/08).

Tier 3 drives the ``notebooklm-py`` CLI. The deep-research job is *launched
first* (at T0, in a background subagent) as a DETACHED CLI process and
*harvested last* with a single BLOCKING bounded wait (``wait_for_job``), so it
overlaps Tiers 0-2. The launch command is::

    notebooklm source add-research "<query>" -n <notebook> --from web \\
        --mode deep --import-all --timeout <deep_timeout_sec> --json

``--import-all`` imports the sources the deep-research job discovers (the step
the MCP could not do); ``--mode deep`` is Deep Research; ``--timeout`` is the
detached job's own deadline. NotebookLM discovers its own sources
autonomously, so Tier 3 no longer ingests Tier 1+2 URLs.

The handler is Markdown consumed by an LLM agent. The lockstep Python helper at
``tests/integration/_ai_research_tier3_helper.py`` mirrors the algorithm 1:1;
these tests exercise the helper.

Algorithm under test:

* ``should_launch_tier3(*, notebooklm_available)`` -- launch whenever the
  tool is available (D3 default-on; no depth/comparative/source gating).
* ``tier3_launch(...)`` -- probe ``doctor_probe`` (``notebooklm doctor`` exit
  0 = available); if unavailable, return degraded and call NOTHING else;
  otherwise create (or reuse) a notebook and launch the DETACHED deep+import
  job via ``add_research``.
* ``tier3_harvest(...)`` -- a SINGLE blocking bounded wait via
  ``wait_for_job(job, timeout=wait_budget_sec)`` returning one of
  ``completed`` / ``failed`` / ``timeout`` / ``auth_required``. On
  ``completed`` -> ``read_result`` parses the ``--json`` report + imported
  sources; on ``timeout`` -> ``timed_out=True`` with the ``notebook_id``
  preserved and the detached job NOT killed (it keeps importing;
  ``--reuse-notebook`` recovers); on ``failed`` / ``auth_required`` -> degrade.
"""

from __future__ import annotations

import types

import pytest

from tests.integration._ai_research_tier3_helper import (
    Tier3Result,
    build_add_research_cmd,
    hash6,
    notebook_title,
    should_launch_tier3,
    tier3_harvest,
    tier3_launch,
    topic_slug,
)

# ---------------------------------------------------------------------------
# Fakes -- record every CLI-shaped call with its arguments.
# ---------------------------------------------------------------------------


class _RecordingDoctorProbe:
    """Stand-in for the ``notebooklm doctor`` capability/auth gate.

    Returns ``True`` (exit 0 = available) by default. Set ``available`` to
    ``False`` to simulate ``doctor`` reporting a non-zero exit (absent binary
    or expired Google session). ``doctor_probe`` is fail-soft -- a real probe
    never raises (the helper's gate swallows any subprocess error), so this
    fake mirrors that contract by returning a bool.
    """

    def __init__(self, *, available: bool = True) -> None:
        self.calls = 0
        self.available = available

    def __call__(self) -> bool:
        self.calls += 1
        return self.available


class _RecordingCreateNotebook:
    """Stand-in for ``create_notebook(title=...) -> notebook_id``.

    ``raises_n`` makes the first ``raises_n`` calls raise (transient create
    failure) before the remaining calls return the notebook id -- so a test can
    exercise the launch fail-soft path.
    """

    def __init__(self, returned_id: str = "nb-fresh-123", *, raises_n: int = 0) -> None:
        self.calls: list[dict] = []
        self.returned_id = returned_id
        self.raises_n = raises_n

    def __call__(self, *, title: str) -> str:
        self.calls.append({"title": title})
        if len(self.calls) <= self.raises_n:
            raise RuntimeError("create_notebook transient failure")
        return self.returned_id


class _RecordingAddResearch:
    """Stand-in for ``add_research(notebook_id, query, deep_timeout_sec)``.

    Launches the DETACHED deep+import-all CLI job and returns an opaque job
    handle. Records the launched arguments so a test can assert the command
    carries ``--import-all``, ``--mode deep``, and the ``--timeout`` value.
    ``raises_n`` makes the first ``raises_n`` calls raise (transient launch
    failure) to exercise the degrade path.
    """

    def __init__(self, job_handle: str = "job-deep-1", *, raises_n: int = 0) -> None:
        self.calls: list[dict] = []
        self.job_handle = job_handle
        self.raises_n = raises_n

    def __call__(self, notebook_id: str, query: str, deep_timeout_sec: int) -> str:
        self.calls.append(
            {
                "notebook_id": notebook_id,
                "query": query,
                "deep_timeout_sec": deep_timeout_sec,
            }
        )
        if len(self.calls) <= self.raises_n:
            raise RuntimeError("add_research transient failure")
        return self.job_handle


class _RecordingWaitForJob:
    """Stand-in for ``wait_for_job(job, timeout=wait_budget_sec) -> status``.

    A SINGLE blocking bounded wait on the detached job -- it REPLACES the whole
    poll loop. Returns one terminal status literal:
    ``"completed"`` / ``"failed"`` / ``"timeout"`` / ``"auth_required"``.
    Records the ``(job, timeout)`` it was called with.
    """

    def __init__(self, status: str) -> None:
        self.status = status
        self.calls: list[dict] = []

    def __call__(self, job: object, *, timeout: float) -> str:
        self.calls.append({"job": job, "timeout": timeout})
        return self.status


class _RecordingReadResult:
    """Stand-in for ``read_result(notebook_id) -> {report_markdown, sources}``.

    Parses the ``--json`` payload of the completed deep-research job into the
    report + imported sources. Records the notebook id it was read for. The
    payload may be a ``dict`` (parsed ``--json``) or an SDK model exposing the
    fields as attributes -- the alias-tolerant parser handles both.
    """

    def __init__(self, payload: object) -> None:
        self.payload = payload
        self.calls: list[str] = []

    def __call__(self, notebook_id: str) -> object:
        self.calls.append(notebook_id)
        return self.payload


class _RecordingAsk:
    """Stand-in for the optional ``ask(notebook_id, q) -> answer`` follow-up."""

    def __init__(self, answer: str = "follow-up answer with [1] citation") -> None:
        self.calls: list[dict] = []
        self.answer = answer

    def __call__(self, notebook_id: str, q: str) -> str:
        self.calls.append({"notebook_id": notebook_id, "q": q})
        return self.answer


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
# tier3_launch -- capability probe + detached deep+import launch
# ---------------------------------------------------------------------------


def test_launch_starts_detached_deep_import_job_when_available() -> None:
    """Available NotebookLM: create a notebook and launch the detached job.

    Arrange: ``doctor_probe`` returns True (exit 0).

    Act: invoke ``tier3_launch`` with a deep timeout.

    Assert:
      * ``doctor_probe`` ran exactly once.
      * ``create_notebook`` called once with an
        ``ai-research/<slug>-<date>-<hash6>`` title.
      * ``add_research`` launched once against the created notebook id with
        the verbatim query and the deep timeout (the helper builds the
        ``--mode deep --import-all --timeout <N> --json`` command).
      * The launch dict carries the notebook id, the job handle,
        ``degraded=False``, no warnings.
    """
    doctor_probe = _RecordingDoctorProbe(available=True)
    create_notebook = _RecordingCreateNotebook(returned_id="nb-fresh-123")
    add_research = _RecordingAddResearch(job_handle="job-deep-1")

    query = "how should we design an async harvest model"
    launch = tier3_launch(
        query,
        timestamp_iso="2026-04-28T12:00:00+00:00",
        doctor_probe=doctor_probe,
        create_notebook=create_notebook,
        add_research=add_research,
        deep_timeout_sec=1800,
    )

    assert doctor_probe.calls == 1, "Capability/auth probe must run exactly once"

    assert len(create_notebook.calls) == 1
    title = create_notebook.calls[0]["title"]
    assert title.startswith("ai-research/"), f"Bad notebook title: {title!r}"
    assert "how-should-we-design-an-async-harvest" in title
    assert "2026-04-28" in title

    assert len(add_research.calls) == 1
    research_call = add_research.calls[0]
    assert research_call["notebook_id"] == "nb-fresh-123"
    assert research_call["deep_timeout_sec"] == 1800
    assert query in research_call["query"]

    assert launch["notebook_id"] == "nb-fresh-123"
    assert launch["job"] == "job-deep-1"
    assert launch["degraded"] is False
    assert launch["warnings"] == []


def test_launch_reuse_notebook_skips_creation() -> None:
    """``reuse_notebook`` short-circuits ``create_notebook``.

    Arrange: ``reuse_notebook='nb-existing-9'``.

    Act: invoke ``tier3_launch``.

    Assert:
      * ``create_notebook`` is never called.
      * ``add_research`` launches against the reused notebook id.
      * The launch dict echoes the reused id, not degraded.
    """
    doctor_probe = _RecordingDoctorProbe(available=True)
    create_notebook = _RecordingCreateNotebook(returned_id="should-not-be-used")
    add_research = _RecordingAddResearch()

    launch = tier3_launch(
        "follow-up deep dive on the same corpus",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        doctor_probe=doctor_probe,
        create_notebook=create_notebook,
        add_research=add_research,
        reuse_notebook="nb-existing-9",
        deep_timeout_sec=1800,
    )

    assert create_notebook.calls == [], (
        f"reuse_notebook MUST skip create_notebook; got {create_notebook.calls}"
    )
    assert launch["notebook_id"] == "nb-existing-9"
    assert launch["degraded"] is False
    assert add_research.calls[0]["notebook_id"] == "nb-existing-9"


def test_launch_passes_deep_timeout_through_to_add_research() -> None:
    """The deep timeout flows verbatim into the detached job command.

    D-175-02 / D-175-03: ``add_research`` receives the ``deep_timeout_sec`` so
    the helper builds ``--timeout <deep_timeout_sec>`` -- the detached job's own
    deadline (default 1800) that lets ``--import-all`` complete.
    """
    doctor_probe = _RecordingDoctorProbe(available=True)
    create_notebook = _RecordingCreateNotebook(returned_id="nb-timeout")
    add_research = _RecordingAddResearch()

    tier3_launch(
        "deep dive with custom timeout",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        doctor_probe=doctor_probe,
        create_notebook=create_notebook,
        add_research=add_research,
        deep_timeout_sec=2400,
    )

    assert add_research.calls[0]["deep_timeout_sec"] == 2400, (
        "The deep timeout must reach add_research so the CLI builds "
        f"--timeout 2400; got {add_research.calls}"
    )


def test_build_add_research_cmd_is_the_canonical_deep_import_command() -> None:
    """``build_add_research_cmd`` pins the spec's central ``--import-all`` shape.

    D-175-02: the detached deep+import job is the ONE command
    ``notebooklm source add-research "<query>" -n <notebook> --from web
    --mode deep --import-all --timeout <deep_timeout_sec> --json``. This is the
    spec's central executable claim, so the canonical token list is asserted
    end-to-end (verbatim query, notebook id under ``-n``, the ``--import-all``
    deep flags, the stringified timeout, and ``--json``).
    """
    cmd = build_add_research_cmd("nb-cmd-7", "compare A vs B", 1800)

    assert cmd == [
        "source",
        "add-research",
        "compare A vs B",
        "-n",
        "nb-cmd-7",
        "--from",
        "web",
        "--mode",
        "deep",
        "--import-all",
        "--timeout",
        "1800",
        "--json",
    ], f"Unexpected add-research command shape: {cmd!r}"

    # The deep-research switches that distinguish this from a plain source add
    # (the step the MCP could not do) must all be present.
    for token in ("source", "add-research", "--from", "web", "--mode", "deep"):
        assert token in cmd, f"Missing required token {token!r} in {cmd!r}"
    assert "--import-all" in cmd, "The autonomous import step must be pinned"
    assert "--json" in cmd, "The structured result flag must be pinned"
    # ``-n <notebook_id>`` adjacency and a stringified ``--timeout <N>``.
    assert cmd[cmd.index("-n") + 1] == "nb-cmd-7"
    assert cmd[cmd.index("--timeout") + 1] == "1800"


def test_launch_doctor_unavailable_degrades_without_side_effects() -> None:
    """``doctor_probe`` returning False degrades and calls NOTHING else.

    D-175-04 fail-soft: a non-zero ``notebooklm doctor`` exit (absent binary
    or expired session) is skipped silently (recorded degraded), never raised.
    The probe is the ONLY call made.

    Assert:
      * ``create_notebook`` and ``add_research`` were never called.
      * The launch dict is degraded with an empty ``notebook_id`` and a
        warning referencing ``notebooklm login`` / ``notebooklm doctor``.
    """
    doctor_probe = _RecordingDoctorProbe(available=False)
    create_notebook = _RecordingCreateNotebook()
    add_research = _RecordingAddResearch()

    launch = tier3_launch(
        "compare A vs B",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        doctor_probe=doctor_probe,
        create_notebook=create_notebook,
        add_research=add_research,
        deep_timeout_sec=1800,
    )

    assert doctor_probe.calls == 1, "Probe must run before short-circuit"
    assert create_notebook.calls == [], (
        f"create_notebook MUST NOT run when doctor fails; got {create_notebook.calls}"
    )
    assert add_research.calls == [], (
        f"add_research MUST NOT run when doctor fails; got {add_research.calls}"
    )
    assert launch["degraded"] is True
    assert launch["notebook_id"] == ""
    assert launch.get("job") is None, "A degraded launch carries no job handle"
    assert launch["warnings"], "A degraded launch must carry a visible warning"
    joined = " ".join(launch["warnings"])
    assert "notebooklm login" in joined, (
        f"Warning must reference `notebooklm login`; got {launch['warnings']!r}"
    )
    assert "notebooklm doctor" in joined, (
        f"Warning must reference `notebooklm doctor`; got {launch['warnings']!r}"
    )
    # The old MCP login string must be gone (D-175-01 hard-cut).
    assert "notebooklm-skill" not in joined, (
        f"The legacy MCP login string must be gone; got {launch['warnings']!r}"
    )


def test_launch_add_research_failure_preserves_notebook_id() -> None:
    """A failing ``add_research`` degrades but preserves the created id.

    D-175-03: the launch never raises; on a launch failure it degrades and
    preserves the created ``notebook_id`` so a later ``--reuse-notebook`` can
    recover.
    """
    doctor_probe = _RecordingDoctorProbe(available=True)
    create_notebook = _RecordingCreateNotebook(returned_id="nb-created")
    add_research = _RecordingAddResearch(raises_n=99)  # always raises

    launch = tier3_launch(
        "research launch fails",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        doctor_probe=doctor_probe,
        create_notebook=create_notebook,
        add_research=add_research,
        deep_timeout_sec=1800,
    )

    assert launch["degraded"] is True, "A failed launch must degrade, not raise"
    assert launch["notebook_id"] == "nb-created", (
        "notebook_id MUST be preserved for a later --reuse-notebook recovery"
    )
    assert launch.get("job") is None, "No job handle when the launch failed"
    assert launch["warnings"], "A degraded launch must carry a visible warning"
    joined = " ".join(launch["warnings"])
    assert "reuse-notebook" in joined or "nb-created" in joined, (
        f"Warning must mention recovery via the notebook id; got {launch['warnings']!r}"
    )


def test_launch_create_notebook_failure_degrades() -> None:
    """A failing ``create_notebook`` degrades without launching research.

    D-175-03 fail-soft: an always-raising ``create_notebook`` exhausts the
    launch and degrades with no ``add_research`` call and an empty notebook id.
    """
    doctor_probe = _RecordingDoctorProbe(available=True)
    create_notebook = _RecordingCreateNotebook(raises_n=99)  # always raises
    add_research = _RecordingAddResearch()

    launch = tier3_launch(
        "create always fails",
        timestamp_iso="2026-04-28T12:00:00+00:00",
        doctor_probe=doctor_probe,
        create_notebook=create_notebook,
        add_research=add_research,
        deep_timeout_sec=1800,
    )

    assert launch["degraded"] is True, "A failed create must degrade, not raise"
    assert add_research.calls == [], (
        f"add_research MUST NOT run when create failed; got {add_research.calls}"
    )
    assert launch["warnings"], "A degraded launch must carry a visible warning"


# ---------------------------------------------------------------------------
# tier3_harvest -- single bounded wait (success path)
# ---------------------------------------------------------------------------


_COMPLETED_REPORT = "# Deep report\n\nFindings with [1] and [2]."
_COMPLETED_SOURCES = [
    "https://nlm.example.com/found-1",
    "https://nlm.example.com/found-2",
]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {"report_markdown": _COMPLETED_REPORT, "sources": _COMPLETED_SOURCES},
            id="dict-report_markdown",
        ),
        pytest.param(
            {"report": _COMPLETED_REPORT, "sources": _COMPLETED_SOURCES},
            id="dict-report-alias",
        ),
        pytest.param(
            {"summary": _COMPLETED_REPORT, "sources": _COMPLETED_SOURCES},
            id="dict-summary-alias",
        ),
        pytest.param(
            types.SimpleNamespace(
                report_markdown=_COMPLETED_REPORT, sources=list(_COMPLETED_SOURCES)
            ),
            id="sdk-model-attributes",
        ),
    ],
)
def test_harvest_completed_fuses_report_and_imported_sources(payload: object) -> None:
    """A job that completes within budget yields the report + imported sources.

    Arrange: ``wait_for_job`` returns ``"completed"``; ``read_result`` parses
    the ``--json`` payload (report + the sources ``--import-all`` imported).
    The parser is alias-tolerant, so the report is extracted identically from
    ``report_markdown`` / ``report`` / ``summary`` dict keys AND from an SDK
    model exposing the same fields as attributes.

    Act: invoke ``tier3_harvest`` on a healthy launch.

    Assert:
      * ``wait_for_job`` called once with ``timeout=wait_budget_sec``.
      * ``report_markdown`` and ``sources_discovered`` populated from the
        parsed result, against the launch ``notebook_id``.
      * ``timed_out`` and ``degraded`` are False; no warnings.
    """
    launch = {
        "notebook_id": "nb-fresh-123",
        "job": "job-deep-1",
        "degraded": False,
        "warnings": [],
    }
    wait_for_job = _RecordingWaitForJob("completed")
    read_result = _RecordingReadResult(payload)

    result = tier3_harvest(
        launch,
        wait_for_job=wait_for_job,
        read_result=read_result,
        wait_budget_sec=300.0,
    )

    assert isinstance(result, Tier3Result)
    assert len(wait_for_job.calls) == 1, "The bounded wait runs exactly once"
    assert wait_for_job.calls[0]["timeout"] == 300.0
    assert wait_for_job.calls[0]["job"] == "job-deep-1"
    assert read_result.calls == ["nb-fresh-123"], (
        f"read_result must read the completed notebook; got {read_result.calls}"
    )
    assert result.notebook_id == "nb-fresh-123"
    assert result.report_markdown == _COMPLETED_REPORT
    assert result.sources_discovered == _COMPLETED_SOURCES
    assert result.timed_out is False
    assert result.degraded is False
    assert result.warnings == []


def test_harvest_optional_ask_followup() -> None:
    """When ``ask`` is injected, its answer fills ``synthesized_response``.

    The optional cited follow-up runs only after the deep job completes.
    """
    launch = {
        "notebook_id": "nb-ask",
        "job": "job-ask",
        "degraded": False,
        "warnings": [],
    }
    wait_for_job = _RecordingWaitForJob("completed")
    read_result = _RecordingReadResult(
        {
            "report_markdown": "# Report\n\nBody [1].",
            "sources": ["https://nlm.example.com/a"],
        }
    )
    ask = _RecordingAsk(answer="Concise cited synthesis [1].")

    result = tier3_harvest(
        launch,
        wait_for_job=wait_for_job,
        read_result=read_result,
        wait_budget_sec=300.0,
        ask=ask,
    )

    assert len(ask.calls) == 1
    assert ask.calls[0]["notebook_id"] == "nb-ask"
    assert result.synthesized_response == "Concise cited synthesis [1]."
    assert result.report_markdown == "# Report\n\nBody [1]."


# ---------------------------------------------------------------------------
# tier3_harvest -- timeout path (D-175-03: detached job NOT killed)
# ---------------------------------------------------------------------------


def test_harvest_timeout_preserves_notebook_id_and_does_not_kill_job() -> None:
    """A ``timeout`` status degrades, preserves the id, and reads no result.

    D-175-03 bounded-wait: when ``wait_for_job`` returns ``"timeout"`` the
    detached deep+import job is STILL RUNNING (it keeps importing) -- the
    harvest must NOT kill it, must set ``timed_out=True``, preserve the
    ``notebook_id`` (for a later ``--reuse-notebook`` recovery), and read no
    result. The report is necessarily absent.
    """
    launch = {
        "notebook_id": "nb-slow-77",
        "job": "job-slow",
        "degraded": False,
        "warnings": [],
    }
    wait_for_job = _RecordingWaitForJob("timeout")
    read_result = _RecordingReadResult({"report_markdown": "SHOULD NOT BE READ"})

    result = tier3_harvest(
        launch,
        wait_for_job=wait_for_job,
        read_result=read_result,
        wait_budget_sec=60.0,
    )

    assert isinstance(result, Tier3Result)
    assert result.timed_out is True, "A timeout status must set timed_out"
    assert result.degraded is True, "A timed-out harvest is degraded"
    assert result.notebook_id == "nb-slow-77", (
        "notebook_id MUST be preserved for a later --reuse-notebook harvest"
    )
    assert result.report_markdown == "", "No report when the job did not complete"
    assert result.sources_discovered == []
    assert read_result.calls == [], (
        "A timed-out (still-importing) job must NOT be read -- the detached job "
        f"keeps running; got read_result calls {read_result.calls}"
    )
    assert result.warnings, "A timeout must surface a visible degraded note"
    joined = " ".join(result.warnings)
    assert "reuse-notebook" in joined or "nb-slow-77" in joined, (
        f"Timeout warning must mention recovery via the notebook id; got {result.warnings!r}"
    )


# ---------------------------------------------------------------------------
# tier3_harvest -- failed / auth_required terminals (degrade, stop)
# ---------------------------------------------------------------------------


def test_harvest_failed_status_degrades() -> None:
    """A ``failed`` status degrades without reading a result.

    The job is dead -- the harvest degrades (``degraded=True``,
    ``timed_out=False``), preserves the ``notebook_id``, reads no result, and
    surfaces a failure warning.
    """
    launch = {
        "notebook_id": "nb-dead-9",
        "job": "job-dead",
        "degraded": False,
        "warnings": [],
    }
    wait_for_job = _RecordingWaitForJob("failed")
    read_result = _RecordingReadResult({"report_markdown": "SHOULD NOT BE READ"})

    result = tier3_harvest(
        launch,
        wait_for_job=wait_for_job,
        read_result=read_result,
        wait_budget_sec=300.0,
    )

    assert result.degraded is True, "A failed job must degrade"
    assert result.timed_out is False, "A terminal failure is not a wall-clock timeout"
    assert result.notebook_id == "nb-dead-9", "notebook_id must be preserved"
    assert result.report_markdown == "", "No report from a failed job"
    assert read_result.calls == [], "A failed job must not be read"
    assert result.warnings, "A failed harvest must surface a visible note"


def test_harvest_auth_required_degrades_with_login_warning() -> None:
    """An ``auth_required`` status degrades with the correct login warning.

    D-175-04: an expired Google session surfaced by the wait degrades (not a
    timeout) and surfaces ``notebooklm login`` -- never the legacy MCP string.
    """
    launch = {
        "notebook_id": "nb-auth-1",
        "job": "job-auth",
        "degraded": False,
        "warnings": [],
    }
    wait_for_job = _RecordingWaitForJob("auth_required")
    read_result = _RecordingReadResult({"report_markdown": "SHOULD NOT BE READ"})

    result = tier3_harvest(
        launch,
        wait_for_job=wait_for_job,
        read_result=read_result,
        wait_budget_sec=300.0,
    )

    assert result.degraded is True
    assert result.timed_out is False, "Auth escalation is not a wall-clock timeout"
    assert read_result.calls == [], "An auth-required job must not be read"
    joined = " ".join(result.warnings)
    assert "notebooklm login" in joined, (
        f"Auth warning must carry `notebooklm login`; got {result.warnings!r}"
    )
    assert "notebooklm-skill" not in joined, (
        f"The legacy MCP login string must be gone; got {result.warnings!r}"
    )


@pytest.mark.parametrize("status", ["running", "in_progress", "", "queued"])
def test_harvest_unknown_status_degrades_without_reading(status: str) -> None:
    """A non-terminal / unrecognized status degrades fail-soft, reads nothing.

    D-175-03: ``wait_for_job`` is only ever read as ``completed`` when it
    EXACTLY returns ``"completed"``. Any other status (a still-running
    ``"running"`` / ``"in_progress"`` / ``""`` / an unknown literal) must NOT
    fall through to ``read_result`` -- doing so would fuse a partial report and
    skip the degrade + ``notebook_id`` preservation. It degrades
    (``degraded=True``, ``timed_out=False``), preserves the id, and reads no
    result.
    """
    launch = {
        "notebook_id": "nb-unknown-5",
        "job": "job-unknown",
        "degraded": False,
        "warnings": [],
    }
    wait_for_job = _RecordingWaitForJob(status)
    read_result = _RecordingReadResult({"report_markdown": "SHOULD NOT BE READ"})

    result = tier3_harvest(
        launch,
        wait_for_job=wait_for_job,
        read_result=read_result,
        wait_budget_sec=300.0,
    )

    assert isinstance(result, Tier3Result)
    assert result.degraded is True, "An unrecognized status must degrade"
    assert result.timed_out is False, "A non-terminal status is not a wall-clock timeout"
    assert result.notebook_id == "nb-unknown-5", (
        "notebook_id MUST be preserved for a later --reuse-notebook harvest"
    )
    assert result.report_markdown == "", "No report when the job did not complete"
    assert result.sources_discovered == []
    assert read_result.calls == [], (
        "A non-completed (possibly still-running) job must NOT be read; "
        f"got read_result calls {read_result.calls}"
    )
    assert result.warnings, "An unknown status must surface a visible degraded note"
    joined = " ".join(result.warnings)
    assert "reuse-notebook" in joined or "nb-unknown-5" in joined, (
        f"Warning must mention recovery via the notebook id; got {result.warnings!r}"
    )


def test_harvest_skips_when_launch_degraded() -> None:
    """A degraded launch is passed straight through without waiting.

    If ``tier3_launch`` already short-circuited (NotebookLM unavailable),
    ``tier3_harvest`` performs no ``wait_for_job`` and propagates the degraded
    launch warnings.
    """
    launch = {
        "notebook_id": "",
        "job": None,
        "degraded": True,
        "warnings": ["notebooklm unavailable -- run `notebooklm login`"],
    }
    wait_for_job = _RecordingWaitForJob("completed")
    read_result = _RecordingReadResult({"report_markdown": "SHOULD NOT BE READ"})

    result = tier3_harvest(
        launch,
        wait_for_job=wait_for_job,
        read_result=read_result,
        wait_budget_sec=300.0,
    )

    assert result.degraded is True
    assert result.notebook_id == ""
    assert result.report_markdown == ""
    assert wait_for_job.calls == [], "A degraded launch must not wait on a job"
    assert read_result.calls == [], "A degraded launch must not read a result"
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
