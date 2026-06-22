"""Lockstep Python implementation of the Tier 3 algorithm documented in
``.claude/skills/ai-research/handlers/tier3-notebooklm.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Backend: ``claude-world/notebooklm-skill`` (``uvx --from notebooklm-skill
notebooklm-mcp``, the 13 ``nlm_*`` MCP tools). NotebookLM runs an
*autonomous deep-research* job that discovers its own sources -- so Tier 3
no longer ingests Tier 1+2 URLs. The job is *launched first* (at T0, in a
background subagent) and *harvested last* with a bounded wait, overlapping
Tiers 0-2 (spec ``notebooklm-async-tier3`` D1/D4).

Public API:

* :class:`Tier3Result`        -- aggregated dataclass (report_markdown,
  sources_discovered, notebook_id, timed_out, degraded, ...).
* :func:`topic_slug`          -- query -> URL-safe topic slug.
* :func:`hash6`               -- stable 6-char SHA-256 prefix of
  ``query|timestamp``.
* :func:`notebook_title`      -- compose ``ai-research/<slug>-<date>-<hash6>``.
* :func:`should_launch_tier3` -- D3 trigger: launch whenever NotebookLM is
  available (no depth/comparative/source gating).
* :func:`tier3_launch`        -- probe ``nlm_list``; create (or reuse) a
  notebook and start ``nlm_research(mode='deep')``; fail-soft on absence.
  Create + research are wrapped in a bounded retry (D-172-08) and degrade
  rather than raise on exhaustion (fail-soft D-172-09).
* :func:`tier3_harvest`       -- bounded *status* poll of ``poll_status``
  against an injected ``clock`` until a terminal status or timeout.

``nlm_research(mode="deep")`` is NON-blocking (it returns an immediate
``status="in_progress"`` ack) and there is NO real status-job MCP tool (the
old phantom poll mapped to nothing), so completion is detected by re-polling
the research status (D-172-05): ``status == "completed"`` reads report+sources;
``failed``/``error`` or an ``[AUTH_REQUIRED]`` signal stops and degrades;
exceeding the wait budget yields ``timed_out=True`` with the ``notebook_id``
preserved. The source/artifact count is only a WEAK secondary heuristic --
sources stream while the job runs, so ONLY the status field terminates the
loop. Polls are spaced by a capped back-off so the loop never spins without
sleeping (D-172-08).

The ``nlm_*`` callables, ``poll_status`` poll, ``clock``, and ``sleep`` are
passed in by the caller so tests can inject mocks (deterministic async
modelling).
"""

from __future__ import annotations

import hashlib
import re
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from tests.integration._ai_research_capability import is_available

# --- Result types ------------------------------------------------------------


@dataclass
class Tier3Result:
    """Output of a Tier 3 NotebookLM autonomous deep-research harvest.

    * ``synthesized_response`` -- optional final ``nlm_ask`` answer.
    * ``report_markdown``      -- the deep-research report from
      ``nlm_research`` (the primary Tier 3 product).
    * ``notebook_id``          -- preserved on timeout for a later
      ``--reuse-notebook`` harvest.
    * ``sources_discovered``   -- URLs NotebookLM found autonomously.
    * ``timed_out``            -- True when the bounded wait was exceeded.
    * ``degraded``             -- True when Tier 3 produced no usable report
      (unavailable backend or harvest timeout).
    * ``warnings``             -- visible operator-facing notes.
    """

    synthesized_response: str = ""
    report_markdown: str = ""
    notebook_id: str = ""
    sources_discovered: list[str] = field(default_factory=list)
    timed_out: bool = False
    degraded: bool = False
    warnings: list[str] = field(default_factory=list)


# --- Notebook-naming helpers (persist helper depends on ``topic_slug``) ------

_SLUG_CLEAN_RE = re.compile(r"[^a-z0-9]+")


def topic_slug(query: str) -> str:
    """Convert a query string to a URL-safe topic slug.

    Algorithm (mirrors ``tier3-notebooklm.md`` §"Notebook Naming"):

    1. Lowercase the query.
    2. Replace any run of non-``[a-z0-9]`` chars with a single dash.
    3. Truncate to 40 chars.
    4. Strip leading/trailing dashes.
    """
    return _SLUG_CLEAN_RE.sub("-", query.lower())[:40].strip("-")


def hash6(query: str, timestamp_iso: str) -> str:
    """Return a stable 6-char SHA-256 prefix for the (query, timestamp) pair.

    Mirrors ``tier3-notebooklm.md`` §"Notebook Naming". The hash gives the
    notebook a unique suffix even when the same query is launched twice on
    the same day (different timestamps).
    """
    return hashlib.sha256(f"{query}|{timestamp_iso}".encode()).hexdigest()[:6]


def notebook_title(query: str, timestamp_iso: str) -> str:
    """Compose ``ai-research/<topic-slug>-<YYYY-MM-DD>-<hash6>``.

    The date is the ``YYYY-MM-DD`` prefix of ``timestamp_iso`` (ISO 8601).
    """
    slug = topic_slug(query)
    date_part = timestamp_iso[:10]  # ISO 8601 prefix is YYYY-MM-DD
    return f"ai-research/{slug}-{date_part}-{hash6(query, timestamp_iso)}"


# --- D3 trigger --------------------------------------------------------------


def should_launch_tier3(*, notebooklm_available: bool) -> bool:
    """Decide whether to launch the Tier 3 autonomous deep-research job.

    Mirrors ``tier3-notebooklm.md`` §"Trigger (default-on)". D3: NotebookLM
    deep research is the DEFAULT path -- it launches whenever the backend is
    available. The legacy ``depth=deep`` / comparative / ``>=10-sources``
    heuristic is dropped (the source count is unknowable at T0, when the
    background launch happens).
    """
    return notebooklm_available


# --- Launch (T0, background subagent) ----------------------------------------

_NlmListCallable = Callable[[], dict]
_CreateNotebookCallable = Callable[..., dict]
_ResearchCallable = Callable[..., dict]
_AskCallable = Callable[..., dict]
# poll_status(notebook_id) -> a status payload (dict OR an attribute-exposing
# object). There is NO real status-job MCP tool -- this re-polls the research
# status itself (D-172-05; replaces the old phantom poll callable).
_PollStatusCallable = Callable[[str], Any]
_ClockCallable = Callable[[], float]
_SleepCallable = Callable[[float], None]

_RESEARCH_INSTRUCTION = (
    " Run autonomous deep research and cite discovered sources using `[N]` notation."
)

# Capped back-off cadence for the harvest status poll (D-172-08). Module-level
# defaults; a later wave wires the env tunable
# ``AIENG_RESEARCH_NLM_POLL_INTERVAL_SEC`` to the SAME 5/60 values. This helper
# does NOT import runtime_state.py -- it stays import-light and deterministic.
_DEFAULT_POLL_INTERVAL_SEC = 5
_POLL_INTERVAL_CAP_SEC = 60

# Sentinel substring the NotebookLM MCP emits (in a status string or an error
# message) when the Google session has expired (D-172-06).
_AUTH_REQUIRED_SIGNAL = "[AUTH_REQUIRED]"

# Terminal research-status literals (normalised lower-case).
_STATUS_COMPLETED = "completed"
_STATUS_FAILED = {"failed", "error"}

# Operator recovery path for an absent / unauthenticated NotebookLM. References
# the ``claude-world/notebooklm-skill`` auth model (NOT the legacy ``nlm login``).
_UNAVAILABLE_WARNING = (
    "notebooklm unavailable or unauthenticated -- run "
    "`uvx --from notebooklm-skill notebooklm login` "
    "(auth state at `~/.notebooklm/storage_state.json`); Tier 3 skipped, "
    "synthesizing from Tiers 0-2 only"
)

_T = TypeVar("_T")


def _with_retry(fn: Callable[[], _T], *, attempts: int = 2) -> _T:
    """Call ``fn`` with a bounded retry (D-172-08).

    Retries ``fn`` up to ``attempts`` times on any exception; re-raises the
    last exception once the attempt budget is exhausted. KISS -- no back-off
    (one transient retry; back-off belongs in the harvest poll). The caller
    (``tier3_launch``) catches the exhausted re-raise and degrades fail-soft
    (D-172-09).
    """
    last_exc: Exception | None = None
    for _ in range(max(1, attempts)):
        try:
            return fn()
        except Exception as exc:  # fail-soft: bounded retry, then degrade
            last_exc = exc
    assert last_exc is not None  # unreachable: the loop ran at least once
    raise last_exc  # _with_retry internal re-raise (caught by tier3_launch -> degrade)


def _notebooklm_available(nlm_list: _NlmListCallable) -> bool:
    """Capability/auth probe via ``nlm_list`` (replaces ``server_info``).

    Delegates to the shared :func:`is_available` guard so NotebookLM uses the
    same absence semantics as Context7 and Exa (notebooklm-async-tier3 D7,
    DRY §10.4): unavailable when the probe raises, returns a falsy payload,
    or reports ``{"authenticated": False}``; available otherwise. Fail-soft:
    a probe error never propagates.
    """
    return is_available(nlm_list)


def tier3_launch(
    query: str,
    *,
    timestamp_iso: str,
    nlm_list: _NlmListCallable,
    nlm_create_notebook: _CreateNotebookCallable,
    nlm_research: _ResearchCallable,
    reuse_notebook: str | None = None,
) -> dict:
    """Launch the Tier 3 autonomous deep-research job (at T0).

    Sequence (mirrors ``tier3-notebooklm.md`` §"Launch"):

    1. Probe ``nlm_list`` (capability/auth) -- the in-subagent D-172-11
       availability gate. If NotebookLM is unavailable or unauthenticated,
       return ``{"degraded": True, "notebook_id": "", "warnings": [...]}`` and
       call NOTHING else (fail-soft; zero create/research calls).
    2. Resolve the notebook id: reuse ``reuse_notebook`` when provided, else
       call ``nlm_create_notebook(title=...)`` (bounded retry) and read
       ``notebook_id``.
    3. Start ``nlm_research(notebook=..., query=..., mode="deep")`` (bounded
       retry) -- the autonomous deep-research job. It is NON-blocking (returns
       an immediate ``status="in_progress"`` ack); the harvest observes
       completion by re-polling the research status via the injected
       ``poll_status`` callable (D-172-05), not via this return value.

    Steps 2-3 are each wrapped in a bounded ``_with_retry`` (D-172-08): one
    transient failure is retried; on exhaustion the launch DEGRADES (returns a
    degraded dict naming the failed step) rather than raising (fail-soft
    D-172-09). The capability probe in step 1 is the only path that may itself
    raise -- and ``is_available`` already swallows that.

    Returns a launch dict ``{"notebook_id", "degraded", "warnings"}`` that is
    handed to :func:`tier3_harvest`.
    """
    # Step 1: capability/auth probe. Absent backend -> degrade, no side effects.
    if not _notebooklm_available(nlm_list):
        return {
            "notebook_id": "",
            "degraded": True,
            "warnings": [_UNAVAILABLE_WARNING],
        }

    # Step 2: resolve notebook id (bounded retry on a transient create failure).
    if reuse_notebook is not None:
        notebook_id = reuse_notebook
    else:
        title = notebook_title(query, timestamp_iso)
        try:
            created = _with_retry(lambda: nlm_create_notebook(title=title))
        except Exception:
            return _degraded_launch("", "nlm_create_notebook")
        notebook_id = created["notebook_id"]

    # Step 3: start the autonomous deep-research job (bounded retry).
    research_query = f"{query}{_RESEARCH_INSTRUCTION}"
    try:
        _with_retry(lambda: nlm_research(notebook=notebook_id, query=research_query, mode="deep"))
    except Exception:
        # Preserve the created notebook id so a later --reuse-notebook can retry.
        return _degraded_launch(notebook_id, "nlm_research")

    return {"notebook_id": notebook_id, "degraded": False, "warnings": []}


def _degraded_launch(notebook_id: str, failed_step: str) -> dict:
    """Build a fail-soft degraded launch dict naming the step that failed.

    Used when a bounded launch retry is exhausted (D-172-08/D-172-09): the
    launch never raises; it degrades with a visible warning and preserves the
    ``notebook_id`` (when one was created) for a ``--reuse-notebook`` retry.
    """
    return {
        "notebook_id": notebook_id,
        "degraded": True,
        "warnings": [
            f"notebooklm Tier 3 launch degraded -- `{failed_step}` failed after "
            "a bounded retry; synthesizing from Tiers 0-2 only"
            + (f" (retry later with `--reuse-notebook={notebook_id}`)" if notebook_id else "")
        ],
    }


# --- Harvest (bounded wait, after Tiers 0-2) ---------------------------------


def _read_field(payload: Any, *names: str) -> Any:
    """Read the first present field from ``payload`` by any of ``names``.

    Alias-tolerant (D-172-08): prefers ATTRIBUTE access, then ``.get`` (dict
    subscript is deprecated). Returns the first non-``None`` value, else
    ``None``. Tolerates both an SDK model (attributes) and a plain ``dict``.
    """
    for name in names:
        value = getattr(payload, name, None)
        if value is not None:
            return value
        getter = getattr(payload, "get", None)
        if callable(getter):
            value = getter(name)
            if value is not None:
                return value
    return None


def _read_status(payload: Any) -> str:
    """Read + normalise the research status (case-insensitive, D-172-05).

    Returns ``str(status).strip().lower()`` or ``""`` when absent. NotebookLM
    streams sources mid-run, so ONLY this status field terminates the loop --
    the source/artifact count is a weak secondary heuristic.
    """
    status = _read_field(payload, "status")
    return str(status).strip().lower() if status is not None else ""


def _read_report(payload: Any) -> str:
    """Read the deep report from a completed status payload.

    Accepts the report under ``report_markdown``, ``report``, or ``summary``
    (backend field-name variance) and normalises onto a single string.
    """
    return _read_field(payload, "report_markdown", "report", "summary") or ""


def _read_sources(payload: Any) -> list[str]:
    """Read the autonomously-discovered sources as a list (tuple|list)."""
    sources = _read_field(payload, "sources")
    if not sources:
        return []
    return list(sources)


def _is_auth_required(value: Any) -> bool:
    """True when ``value`` carries the ``[AUTH_REQUIRED]`` sentinel (D-172-06).

    Matches the sentinel in a status string OR an exception message so the
    harvest can distinguish an expired Google session from "still running".
    """
    return _AUTH_REQUIRED_SIGNAL.lower() in str(value).lower()


def _auth_required_result(notebook_id: str) -> Tier3Result:
    """Degraded result for an ``[AUTH_REQUIRED]`` escalation (not a timeout)."""
    return Tier3Result(
        notebook_id=notebook_id,
        degraded=True,
        timed_out=False,
        warnings=[_UNAVAILABLE_WARNING],
    )


def tier3_harvest(
    launch: dict,
    *,
    poll_status: _PollStatusCallable,
    clock: _ClockCallable,
    wait_budget_sec: float,
    nlm_ask: _AskCallable | None = None,
    sleep: _SleepCallable = time.sleep,
) -> Tier3Result:
    """Harvest the deep-research job with a bounded status poll (D4, D-172-05).

    ``nlm_research(mode="deep")`` is NON-blocking and there is NO real
    status-job MCP tool, so completion is observed by re-polling the research
    status via the injected ``poll_status(notebook_id)`` callable. Sequence
    (mirrors ``tier3-notebooklm.md`` §"Harvest"):

    1. If ``launch`` is already degraded (NotebookLM was unavailable at
       launch), pass it straight through -- no polling.
    2. Otherwise poll ``poll_status(notebook_id)`` repeatedly. ``clock()`` is
       a zero-arg monotonically-increasing wall-clock reading; the first
       reading anchors the start time. Each poll reads the normalised status
       and branches:
         * ``completed``            -> read report + sources, break.
         * ``failed`` / ``error``   -> stop, ``degraded=True``,
           ``timed_out=False`` + failure warning.
         * ``[AUTH_REQUIRED]`` (status sentinel OR caught exception) -> stop,
           ``degraded=True`` + the correct-login warning.
         * anything else (``in_progress``/``not_found``/...) -> keep polling.
       Before each *subsequent* poll the loop ``sleep(min(interval, cap))`` so
       it never spins without sleeping (D-172-08). If ``clock()-start`` exceeds
       ``wait_budget_sec`` the harvest *times out*: ``timed_out=True`` with the
       ``notebook_id`` preserved (for a later ``--reuse-notebook`` harvest).
    3. On ``completed`` read the report (``report_markdown``/``report``/
       ``summary``) and ``sources`` (tuple|list), alias-tolerant.
    4. If ``nlm_ask`` is provided, run one optional cited follow-up after
       completion and fill ``synthesized_response``.

    Never raises on a degrade path (fail-soft D-172-09): an exception during a
    poll is treated as ``[AUTH_REQUIRED]`` when it carries that sentinel, else
    as a transient failure that degrades.

    Returns a :class:`Tier3Result`.
    """
    notebook_id = launch.get("notebook_id", "")

    # Step 1: a degraded launch is passed straight through (no polling).
    if launch.get("degraded"):
        return Tier3Result(
            notebook_id=notebook_id,
            degraded=True,
            warnings=list(launch.get("warnings", [])),
        )

    # Step 2: bounded status poll. The first reading anchors the start time.
    start = clock()
    payload: Any = None
    poll_count = 0
    # Capped exponential back-off: start at the default interval and double each
    # subsequent poll up to the cap, so a long-running deep-research job is
    # polled progressively less aggressively without ever spinning (D-172-08).
    poll_interval = _DEFAULT_POLL_INTERVAL_SEC
    while True:
        # Back-off between polls -- never spin without sleeping. The first poll
        # happens immediately; each subsequent poll waits the (growing) interval.
        if poll_count > 0:
            sleep(poll_interval)
            poll_interval = min(poll_interval * 2, _POLL_INTERVAL_CAP_SEC)

        try:
            payload = poll_status(notebook_id)
        except Exception as exc:
            # An [AUTH_REQUIRED] error escalates to a login prompt; any other
            # poll error degrades fail-soft rather than propagating.
            if _is_auth_required(exc):
                return _auth_required_result(notebook_id)
            return Tier3Result(
                notebook_id=notebook_id,
                degraded=True,
                timed_out=False,
                warnings=[
                    "notebooklm deep research polling failed; synthesizing from "
                    f"Tiers 0-2 only -- harvest later with `--reuse-notebook={notebook_id}`"
                ],
            )
        poll_count += 1

        status = _read_status(payload)

        # Terminal: completed.
        if status == _STATUS_COMPLETED:
            break

        # Terminal: auth expired (sentinel in the status field).
        if _is_auth_required(status):
            return _auth_required_result(notebook_id)

        # Terminal: failed / error -> stop early and degrade (not a timeout).
        if status in _STATUS_FAILED:
            return Tier3Result(
                notebook_id=notebook_id,
                degraded=True,
                timed_out=False,
                warnings=[
                    f"notebooklm deep research reported status '{status}'; "
                    "synthesizing from Tiers 0-2 only -- harvest later with "
                    f"`--reuse-notebook={notebook_id}`"
                ],
            )

        # Not terminal (in_progress / not_found / ...): enforce the wall-clock
        # budget, then keep polling. Sources may already be present here but
        # only the status field terminates -- the source count is a weak
        # secondary heuristic (D-172-05).
        if (clock() - start) > wait_budget_sec:
            return Tier3Result(
                notebook_id=notebook_id,
                timed_out=True,
                degraded=True,
                warnings=[
                    "notebooklm deep research still running after the wait budget; "
                    f"synthesizing without it -- harvest later with "
                    f"`--reuse-notebook={notebook_id}`"
                ],
            )

    # Step 3: completed -- read report + autonomously-discovered sources.
    report_markdown = _read_report(payload)
    sources_discovered = _read_sources(payload)

    # Step 4: optional cited follow-up.
    synthesized_response = ""
    if nlm_ask is not None:
        answer = nlm_ask(notebook=notebook_id, query="Summarise the key findings with citations.")
        synthesized_response = answer.get("answer", "")

    return Tier3Result(
        synthesized_response=synthesized_response,
        report_markdown=report_markdown,
        notebook_id=notebook_id,
        sources_discovered=sources_discovered,
    )


__all__: Iterable[str] = (
    "Tier3Result",
    "hash6",
    "notebook_title",
    "should_launch_tier3",
    "tier3_harvest",
    "tier3_launch",
    "topic_slug",
)
