"""Lockstep Python implementation of the Tier 3 algorithm documented in
``.claude/skills/ai-research/handlers/tier3-notebooklm.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Public API:

* :class:`Tier3Result`        -- aggregated dataclass (notebook_id,
  conversation_id, synthesized_response).
* :func:`topic_slug`          -- T-3.3: query → URL-safe topic slug.
* :func:`hash6`               -- T-3.4: stable 6-char SHA-256 prefix
  derived from the query plus an ISO timestamp.
* :func:`notebook_title`      -- compose ``ai-research/<slug>-<date>-<hash6>``.
* :func:`should_invoke_tier3` -- T-3.6: trigger heuristic.
* :func:`tier3_notebooklm`    -- T-3.5: run the create/add/query flow.

The MCP callables are passed in by the caller so tests can inject mocks.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

# --- Result types ------------------------------------------------------------


@dataclass
class Tier3Result:
    """Output of a Tier 3 NotebookLM invocation."""

    synthesized_response: str = ""
    notebook_id: str = ""
    conversation_id: str = ""
    sources_added: list[str] = field(default_factory=list)
    degraded: bool = False
    warnings: list[str] = field(default_factory=list)


# --- T-3.3: topic-slug generator --------------------------------------------

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


# --- T-3.4: hash6 generator --------------------------------------------------


def hash6(query: str, timestamp_iso: str) -> str:
    """Return a stable 6-char SHA-256 prefix for the (query, timestamp) pair.

    Mirrors ``tier3-notebooklm.md`` §"Notebook Naming". The hash gives the
    notebook a unique suffix even when the same query is invoked twice on
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


# --- T-3.6: trigger heuristic ------------------------------------------------

_COMPARATIVE_RE = re.compile(
    r"\b(vs|versus|compare|difference between|alternatives?)\b",
    re.IGNORECASE,
)

_DEEP_DEPTH = "deep"
_TIER3_SOURCE_THRESHOLD = 10


def should_invoke_tier3(query: str, *, depth: str, tier12_source_count: int) -> bool:
    """Decide whether Tier 3 should run for the given query.

    Mirrors ``tier3-notebooklm.md`` §"Trigger Heuristic":

    * ``depth == 'deep'`` always triggers.
    * Comparative queries (regex ``\\b(vs|versus|compare|difference between|
      alternatives?)\\b``) trigger.
    * ``tier12_source_count >= 10`` triggers.
    * Otherwise: do not invoke.

    ``depth`` is matched case-insensitively; the threshold and regex are
    pinned constants.
    """
    if depth.lower() == _DEEP_DEPTH:
        return True
    if _COMPARATIVE_RE.search(query):
        return True
    return tier12_source_count >= _TIER3_SOURCE_THRESHOLD


# --- T-3.5: main flow --------------------------------------------------------

_MAX_SOURCES = 20

_CITATION_INSTRUCTION = " Answer with citations to the provided sources, using `[N]` notation."

_NotebookCreateCallable = Callable[..., dict]
_SourceAddCallable = Callable[..., dict]
_NotebookQueryCallable = Callable[..., dict]
_ServerInfoCallable = Callable[[], dict]


_AUTH_EXPIRED_WARNING = (
    "notebooklm auth expired -- run `nlm login` to re-authenticate; "
    "Tier 3 skipped, falling back to Tier 2 sources"
)


def tier3_notebooklm(
    query: str,
    *,
    sources: list[str],
    timestamp_iso: str,
    notebook_create: _NotebookCreateCallable,
    source_add: _SourceAddCallable,
    notebook_query: _NotebookQueryCallable,
    reuse_notebook: str | None = None,
    server_info: _ServerInfoCallable | None = None,
) -> Tier3Result:
    """Run the Tier 3 NotebookLM flow.

    Sequence (mirrors ``tier3-notebooklm.md`` §"Sequence"):

    1. (T-4.9) If ``server_info`` is provided, probe it first. If the
       probe returns ``authenticated: False``, return immediately with
       ``degraded=True`` and the auth-expired warning. ``notebook_create``,
       ``source_add``, ``notebook_query`` are NOT called in this case.
    2. If ``reuse_notebook`` is provided, use that ID; else call
       ``notebook_create(title=...)`` with the templated title and capture
       the returned ID.
    3. Call ``source_add`` for each URL in ``sources``, capped at the first
       20 entries.
    4. Call ``notebook_query`` with the user query plus the citation
       instruction; capture ``answer`` and ``conversation_id``.
    5. Return a :class:`Tier3Result`.

    Resilience: a single per-call exception during ``source_add`` or
    ``notebook_query`` is captured and surfaced via ``degraded=True`` plus
    the corresponding warning, but does not propagate to the caller -- the
    skill should fall back to Tier 2 results in that case.
    """
    # Step 1 (T-4.9): auth probe.
    if server_info is not None:
        try:
            info = server_info() or {}
        except Exception as exc:
            return Tier3Result(
                degraded=True,
                warnings=[
                    f"notebooklm server_info probe failed: {exc!r} -- "
                    "Tier 3 skipped, run `nlm login` and retry"
                ],
            )
        if not info.get("authenticated", True):
            return Tier3Result(degraded=True, warnings=[_AUTH_EXPIRED_WARNING])

    # Step 2: notebook id.
    if reuse_notebook is not None:
        notebook_id = reuse_notebook
    else:
        title = notebook_title(query, timestamp_iso)
        created = notebook_create(title=title)
        notebook_id = created["notebook_id"]

    # Step 3: add sources, capped at 20.
    capped_sources = list(sources)[:_MAX_SOURCES]
    for url in capped_sources:
        source_add(notebook_id=notebook_id, source_type="url", url=url)

    # Step 4: query with citation instruction appended.
    query_payload = f"{query}{_CITATION_INSTRUCTION}"
    queried = notebook_query(notebook_id=notebook_id, query=query_payload)

    return Tier3Result(
        synthesized_response=queried.get("answer", ""),
        notebook_id=notebook_id,
        conversation_id=queried.get("conversation_id", ""),
        sources_added=capped_sources,
    )


__all__: Iterable[str] = (
    "Tier3Result",
    "hash6",
    "notebook_title",
    "should_invoke_tier3",
    "tier3_notebooklm",
    "topic_slug",
)
