"""Lockstep Python implementation of the Tier 3 algorithm documented in
``.claude/skills/ai-research/handlers/tier3-notebooklm.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Backend: the ``notebooklm-py`` CLI (``notebooklm`` on PATH, operator
``uv tool install "notebooklm-py[browser]"``; ``uvx --from
"notebooklm-py[browser]" notebooklm`` fallback). Supersedes the
``notebooklm-skill`` MCP model (spec-175 D-175-01; supersedes D-172-05/08).

NotebookLM runs an *autonomous deep-research* job that discovers its own
sources AND imports them (``--import-all``) -- so Tier 3 no longer ingests
Tier 1+2 URLs. The deep job is launched as ONE CLI command::

    notebooklm source add-research "<query>" -n <notebook> --from web \
        --mode deep --import-all --timeout <deep_timeout_sec> --json

``--mode deep`` is Deep Research; ``--import-all`` imports the discovered
sources (the step the MCP could not do); ``--timeout`` is the DETACHED job's
own deadline; ``--json`` makes the result structured (no text scraping). The
job is *launched first* (at T0, in a background subagent) as a detached
process and *harvested last* with a single BLOCKING bounded wait that
overlaps Tiers 0-2 (D-175-03).

Public API:

* :class:`Tier3Result`        -- aggregated dataclass (report_markdown,
  sources_discovered, notebook_id, timed_out, degraded, ...).
* :func:`topic_slug`          -- query -> URL-safe topic slug.
* :func:`hash6`               -- stable 6-char SHA-256 prefix of
  ``query|timestamp``.
* :func:`notebook_title`      -- compose ``ai-research/<slug>-<date>-<hash6>``.
* :func:`should_launch_tier3` -- D3 trigger: launch whenever NotebookLM is
  available (no depth/comparative/source gating).
* :func:`tier3_launch`        -- gate on ``doctor_probe`` (``notebooklm
  doctor`` exit 0); create (or reuse) a notebook and launch the DETACHED
  deep+import job via ``add_research``; fail-soft on absence/failure (the
  created ``notebook_id`` is preserved for ``--reuse-notebook``).
* :func:`tier3_harvest`       -- a SINGLE blocking bounded wait via
  ``wait_for_job(job, timeout=wait_budget_sec)`` returning ``completed`` /
  ``failed`` / ``timeout`` / ``auth_required``; on ``completed`` parse the
  ``--json`` result via ``read_result``; on ``timeout`` degrade + preserve
  ``notebook_id`` WITHOUT killing the still-importing detached job.

The capability gate (``doctor_probe``), the notebook resolver
(``create_notebook``), the detached launcher (``add_research``), the bounded
wait (``wait_for_job``), the result parser (``read_result``), and the optional
follow-up (``ask``) are all passed in by the caller so tests can inject mocks
(deterministic modelling). The CLI's native ``--timeout`` owns the deep job's
deadline, so there is NO poll loop, no back-off, and no re-poll wrap.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

# --- Result types ------------------------------------------------------------


@dataclass
class Tier3Result:
    """Output of a Tier 3 NotebookLM autonomous deep-research harvest.

    * ``synthesized_response`` -- optional final ``ask`` answer.
    * ``report_markdown``      -- the deep-research report parsed from the
      CLI ``--json`` result (the primary Tier 3 product).
    * ``notebook_id``          -- preserved on timeout for a later
      ``--reuse-notebook`` harvest.
    * ``sources_discovered``   -- URLs NotebookLM found + imported autonomously.
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

# doctor_probe() -> bool: runs ``notebooklm doctor`` (exit 0 = available); the
# CLI capability/auth gate (D-175-04). Fail-soft -- the real probe swallows any
# subprocess error and returns a bool, so the launch never raises here.
_DoctorProbe = Callable[[], bool]
# create_notebook(title=...) -> notebook_id: resolves a fresh notebook.
_CreateNotebookCallable = Callable[..., str]
# add_research(notebook_id, query, deep_timeout_sec) -> job_handle: launches the
# DETACHED deep+import-all CLI job and returns an opaque handle for the wait.
_AddResearchCallable = Callable[[str, str, int], Any]
# wait_for_job(job, timeout=...) -> status: a SINGLE blocking bounded wait on
# the detached job; replaces the entire MCP poll loop (D-175-02 native wait).
_WaitForJobCallable = Callable[..., str]
# read_result(notebook_id) -> {report_markdown, sources}: parses the --json
# result of the completed job.
_ReadResultCallable = Callable[[str], Any]
# ask(notebook_id, q) -> answer: optional cited follow-up after completion.
_AskCallable = Callable[[str, str], str]

_RESEARCH_INSTRUCTION = (
    " Run autonomous deep research and cite discovered sources using `[N]` notation."
)


def build_add_research_cmd(notebook_id: str, query: str, deep_timeout_sec: int) -> list[str]:
    """Build the canonical ``notebooklm source add-research`` token list.

    Returns the exact argv (minus the ``notebooklm`` entrypoint) that the
    DETACHED deep+import-all job is launched with (mirrors
    ``tier3-notebooklm.md`` §"Launch"; the spec's central command claim)::

        notebooklm source add-research "<query>" -n <notebook_id> --from web \
            --mode deep --import-all --timeout <deep_timeout_sec> --json

    ``--mode deep`` is Deep Research; ``--import-all`` imports the sources the
    job discovers (the step the MCP could not do); ``--timeout`` is the detached
    job's own deadline; ``--json`` makes the result structured.
    """
    return [
        "source",
        "add-research",
        query,
        "-n",
        notebook_id,
        "--from",
        "web",
        "--mode",
        "deep",
        "--import-all",
        "--timeout",
        str(deep_timeout_sec),
        "--json",
    ]


# Terminal statuses returned by ``wait_for_job`` (D-175-02/03).
_STATUS_COMPLETED = "completed"
_STATUS_TIMEOUT = "timeout"
_STATUS_FAILED = "failed"
_STATUS_AUTH_REQUIRED = "auth_required"

# Operator recovery path for an absent / unauthenticated NotebookLM. References
# the ``notebooklm-py`` CLI auth model (``notebooklm login`` / ``notebooklm
# doctor``) -- NOT the legacy ``notebooklm-skill`` MCP login string (D-175-01).
_UNAVAILABLE_WARNING = (
    "notebooklm unavailable or unauthenticated (`notebooklm doctor` reported "
    "non-zero) -- run `notebooklm login`, then re-check with `notebooklm doctor`; "
    "Tier 3 skipped, synthesizing from Tiers 0-2 only"
)


def tier3_launch(
    query: str,
    *,
    timestamp_iso: str,
    doctor_probe: _DoctorProbe,
    create_notebook: _CreateNotebookCallable,
    add_research: _AddResearchCallable,
    reuse_notebook: str | None = None,
    deep_timeout_sec: int,
) -> dict:
    """Launch the Tier 3 autonomous deep-research job (at T0).

    Sequence (mirrors ``tier3-notebooklm.md`` §"Launch"):

    1. **Capability/auth gate** -- call ``doctor_probe()`` (``notebooklm
       doctor``, exit 0 = available; D-175-04). If it returns ``False``
       (non-zero exit -- absent binary or expired Google session), return
       ``{"notebook_id": "", "job": None, "degraded": True, "warnings": [...]}``
       and call NOTHING else (fail-soft; zero create/research).
    2. **Resolve the notebook id** -- reuse ``reuse_notebook`` when provided,
       else ``create_notebook(title=notebook_title(...))``.
    3. **Launch the detached deep+import job** -- ``add_research(notebook_id,
       query, deep_timeout_sec)`` runs ``notebooklm source add-research
       "<query>" -n <notebook> --from web --mode deep --import-all --timeout
       <deep_timeout_sec> --json`` DETACHED and returns an opaque job handle.

    Steps 2-3 never raise out of this function (fail-soft D-175-03): a failure
    DEGRADES (returns a degraded dict naming the failed step) while PRESERVING
    the created ``notebook_id`` so a later ``--reuse-notebook`` can recover.

    Returns a launch dict ``{"notebook_id", "job", "degraded", "warnings"}``
    handed to :func:`tier3_harvest`.
    """
    # Step 1: capability/auth gate. Non-zero doctor -> degrade, no side effects.
    if not doctor_probe():
        return {
            "notebook_id": "",
            "job": None,
            "degraded": True,
            "warnings": [_UNAVAILABLE_WARNING],
        }

    # Step 2: resolve notebook id (degrade fail-soft on a create failure).
    if reuse_notebook is not None:
        notebook_id = reuse_notebook
    else:
        try:
            title = notebook_title(query, timestamp_iso)
            notebook_id = create_notebook(title=title)
        except Exception:
            return _degraded_launch("", "create_notebook")

    # Step 3: launch the DETACHED deep+import-all job (degrade fail-soft).
    research_query = f"{query}{_RESEARCH_INSTRUCTION}"
    try:
        job = add_research(notebook_id, research_query, deep_timeout_sec)
    except Exception:
        # Preserve the notebook id so a later --reuse-notebook can recover.
        return _degraded_launch(notebook_id, "add_research")

    return {"notebook_id": notebook_id, "job": job, "degraded": False, "warnings": []}


def _degraded_launch(notebook_id: str, failed_step: str) -> dict:
    """Build a fail-soft degraded launch dict naming the step that failed.

    Used when a launch step fails (D-175-03): the launch never raises; it
    degrades with a visible warning and preserves the ``notebook_id`` (when one
    was created) for a ``--reuse-notebook`` recovery.
    """
    return {
        "notebook_id": notebook_id,
        "job": None,
        "degraded": True,
        "warnings": [
            f"notebooklm Tier 3 launch degraded -- `{failed_step}` failed; "
            "synthesizing from Tiers 0-2 only"
            + (f" (retry later with `--reuse-notebook={notebook_id}`)" if notebook_id else "")
        ],
    }


# --- Harvest (single bounded wait, after Tiers 0-2) --------------------------


def _read_field(payload: Any, *names: str) -> Any:
    """Read the first present field from ``payload`` by any of ``names``.

    Alias-tolerant: prefers ATTRIBUTE access, then ``.get`` (dict subscript is
    deprecated). Returns the first non-``None`` value, else ``None``. Tolerates
    both an SDK model (attributes) and a plain ``dict`` parsed from ``--json``.
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


def _read_report(payload: Any) -> str:
    """Read the deep report from a parsed ``--json`` result.

    Accepts the report under ``report_markdown``, ``report``, or ``summary``
    (backend field-name variance) and normalises onto a single string.
    """
    return _read_field(payload, "report_markdown", "report", "summary") or ""


def _read_sources(payload: Any) -> list[str]:
    """Read the autonomously-discovered + imported sources (tuple|list)."""
    sources = _read_field(payload, "sources")
    if not sources:
        return []
    return list(sources)


def tier3_harvest(
    launch: dict,
    *,
    wait_for_job: _WaitForJobCallable,
    read_result: _ReadResultCallable,
    wait_budget_sec: float,
    ask: _AskCallable | None = None,
) -> Tier3Result:
    """Harvest the detached deep-research job with a single bounded wait (D4).

    The CLI launches the deep+import job DETACHED with its own ``--timeout``;
    the harvest observes completion via ONE blocking, bounded
    ``wait_for_job(job, timeout=wait_budget_sec)`` call that REPLACES the entire
    MCP poll loop (D-175-02 native wait). Sequence (mirrors
    ``tier3-notebooklm.md`` §"Harvest"):

    1. **Degraded passthrough** -- if ``launch`` is already degraded (NotebookLM
       was unavailable at launch), return it straight through with no wait.
    2. **Bounded wait** -- ``wait_for_job(job, timeout=wait_budget_sec)`` returns
       one terminal status:
         * ``completed``      -> ``read_result(notebook_id)`` parses the
           ``--json`` report + imported ``sources``.
         * ``timeout``        -> the detached job is STILL RUNNING (it keeps
           importing) -- do NOT kill it and do NOT read a result; degrade with
           ``timed_out=True`` and the ``notebook_id`` preserved (for a later
           ``--reuse-notebook`` recovery).
         * ``failed``         -> degrade (``timed_out=False``) with a failure
           warning; the ``notebook_id`` is preserved.
         * ``auth_required``  -> degrade with the ``notebooklm login`` warning
           (an expired Google session, not "still running").
    3. **Optional follow-up** -- if ``ask`` is provided, run one cited
       ``ask(notebook_id, q)`` after completion and fill
       ``synthesized_response``.

    Never raises on a degrade path (fail-soft D-175-03).

    Returns a :class:`Tier3Result`.
    """
    notebook_id = launch.get("notebook_id", "")

    # Step 1: a degraded launch is passed straight through (no wait).
    if launch.get("degraded"):
        return Tier3Result(
            notebook_id=notebook_id,
            degraded=True,
            warnings=list(launch.get("warnings", [])),
        )

    # Step 2: a single blocking, bounded wait on the detached job.
    status = wait_for_job(launch.get("job"), timeout=wait_budget_sec)

    # Terminal: timeout -> the detached job keeps importing; do NOT kill/read it.
    if status == _STATUS_TIMEOUT:
        return Tier3Result(
            notebook_id=notebook_id,
            timed_out=True,
            degraded=True,
            warnings=[
                "notebooklm deep research still running after the wait budget; "
                "synthesizing without it -- the detached --import-all job keeps "
                f"running, harvest later with `--reuse-notebook={notebook_id}`"
            ],
        )

    # Terminal: auth expired -> degrade with the correct login warning.
    if status == _STATUS_AUTH_REQUIRED:
        return Tier3Result(
            notebook_id=notebook_id,
            degraded=True,
            timed_out=False,
            warnings=[_UNAVAILABLE_WARNING],
        )

    # Terminal: failed -> degrade (not a wall-clock timeout).
    if status == _STATUS_FAILED:
        return Tier3Result(
            notebook_id=notebook_id,
            degraded=True,
            timed_out=False,
            warnings=[
                "notebooklm deep research reported status 'failed'; synthesizing "
                f"from Tiers 0-2 only -- harvest later with `--reuse-notebook={notebook_id}`"
            ],
        )

    # Terminal: any non-`completed` status degrades fail-soft (D-175-03) -- a
    # still-running ("running"/"in_progress"/""/unknown) job must NOT be read as
    # if finished, which would fuse a partial report and skip the degrade +
    # notebook_id preservation.
    if status != _STATUS_COMPLETED:
        return Tier3Result(
            notebook_id=notebook_id,
            degraded=True,
            timed_out=False,
            warnings=[
                f"notebooklm deep research returned unexpected status "
                f"{status!r}; synthesizing from Tiers 0-2 only -- harvest "
                f"later with `--reuse-notebook={notebook_id}`"
            ],
        )

    # Terminal: completed -> parse the --json report + imported sources.
    result = read_result(notebook_id)
    report_markdown = _read_report(result)
    sources_discovered = _read_sources(result)

    # Step 3: optional cited follow-up.
    synthesized_response = ""
    if ask is not None:
        synthesized_response = ask(notebook_id, "Summarise the key findings with citations.")

    return Tier3Result(
        synthesized_response=synthesized_response,
        report_markdown=report_markdown,
        notebook_id=notebook_id,
        sources_discovered=sources_discovered,
    )


__all__: Iterable[str] = (
    "Tier3Result",
    "build_add_research_cmd",
    "hash6",
    "notebook_title",
    "should_launch_tier3",
    "tier3_harvest",
    "tier3_launch",
    "topic_slug",
)
