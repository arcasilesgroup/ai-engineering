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
* :func:`tier3_harvest`       -- bounded poll of ``job_status`` against an
  injected ``clock`` until completion or timeout.

The ``nlm_*`` callables, ``job_status`` poll, and ``clock`` are passed in by
the caller so tests can inject mocks (deterministic async modelling).
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

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
_JobStatusCallable = Callable[[str], dict]
_ClockCallable = Callable[[], float]

_RESEARCH_INSTRUCTION = (
    " Run autonomous deep research and cite discovered sources using `[N]` notation."
)

# Operator recovery path for an absent / unauthenticated NotebookLM. References
# the ``claude-world/notebooklm-skill`` auth model (NOT the legacy ``nlm login``).
_UNAVAILABLE_WARNING = (
    "notebooklm unavailable or unauthenticated -- run `uvx notebooklm login` "
    "(auth state at `~/.notebooklm/storage_state.json`); Tier 3 skipped, "
    "synthesizing from Tiers 0-2 only"
)


def _notebooklm_available(nlm_list: _NlmListCallable) -> bool:
    """Capability/auth probe via ``nlm_list`` (replaces ``server_info``).

    NotebookLM is treated as unavailable when the probe raises, returns a
    falsy payload, or reports ``{"authenticated": False}``. Fail-soft (D7):
    a probe error never propagates.
    """
    try:
        info = nlm_list()
    except Exception:
        return False
    if not info:
        return False
    return bool(info.get("authenticated", True))


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

    1. Probe ``nlm_list`` (capability/auth). If NotebookLM is unavailable or
       unauthenticated, return ``{"degraded": True, "notebook_id": "",
       "warnings": [...]}`` and call NOTHING else (D7 fail-soft).
    2. Resolve the notebook id: reuse ``reuse_notebook`` when provided, else
       call ``nlm_create_notebook(title=...)`` and read ``notebook_id``.
    3. Start ``nlm_research(notebook=..., query=..., mode="deep")`` -- the
       autonomous deep-research job. Per D1/OQ2 this is assumed BLOCKING
       (the background subagent holds it); a future non-blocking handle is
       supported because the harvest reads job state via the injected
       ``job_status`` callable rather than this return value.

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

    # Step 2: resolve notebook id.
    if reuse_notebook is not None:
        notebook_id = reuse_notebook
    else:
        title = notebook_title(query, timestamp_iso)
        created = nlm_create_notebook(title=title)
        notebook_id = created["notebook_id"]

    # Step 3: start the autonomous deep-research job.
    research_query = f"{query}{_RESEARCH_INSTRUCTION}"
    nlm_research(notebook=notebook_id, query=research_query, mode="deep")

    return {"notebook_id": notebook_id, "degraded": False, "warnings": []}


# --- Harvest (bounded wait, after Tiers 0-2) ---------------------------------


def _read_report(payload: dict) -> str:
    """Read the deep report from a completed ``job_status`` payload.

    Accepts either ``report_markdown`` or ``report`` (backend field-name
    variance) and normalises onto a single string.
    """
    return payload.get("report_markdown") or payload.get("report") or ""


def tier3_harvest(
    launch: dict,
    *,
    job_status: _JobStatusCallable,
    clock: _ClockCallable,
    wait_budget_sec: float,
    nlm_ask: _AskCallable | None = None,
) -> Tier3Result:
    """Harvest the deep-research job with a bounded wait (D4).

    Sequence (mirrors ``tier3-notebooklm.md`` §"Harvest"):

    1. If ``launch`` is already degraded (NotebookLM was unavailable at
       launch), pass it straight through -- no polling.
    2. Otherwise poll ``job_status(notebook_id)`` repeatedly. ``clock()`` is
       a zero-arg monotonically-increasing wall-clock reading. The first
       reading is the start time; on each subsequent reading, if the elapsed
       time exceeds ``wait_budget_sec`` the harvest *times out*: return
       ``timed_out=True`` with the ``notebook_id`` preserved (for a later
       ``--reuse-notebook`` harvest) and a degraded warning. No report.
    3. When ``job_status`` reports ``{"status": "completed"}``, read the
       ``report_markdown`` (or ``report``) and ``sources``.
    4. If ``nlm_ask`` is provided, run one optional cited follow-up after
       completion and fill ``synthesized_response``.

    Returns a :class:`Tier3Result`.
    """
    notebook_id = launch.get("notebook_id", "")

    # Step 1: a degraded launch is passed straight through.
    if launch.get("degraded"):
        return Tier3Result(
            notebook_id=notebook_id,
            degraded=True,
            warnings=list(launch.get("warnings", [])),
        )

    # Step 2: bounded poll. The first reading anchors the start time.
    start = clock()
    while True:
        status = job_status(notebook_id)
        if status.get("status") == "completed":
            break
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
    report_markdown = _read_report(status)
    sources_discovered = list(status.get("sources", []))

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
