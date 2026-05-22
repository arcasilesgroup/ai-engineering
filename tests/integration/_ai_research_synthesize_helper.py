"""Lockstep Python implementation of the synthesizer + validator algorithm
documented in ``.claude/skills/ai-research/handlers/synthesize-with-citations.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Public API:

* :class:`Source`               -- per-source dataclass shared with persist.
* :class:`Direction`            -- one recommended strategic direction
  ("rumbo"): title, rationale, trade-off, and cited evidence.
* :class:`SynthesizeResult`     -- aggregated output (findings, validation,
  warnings, recommended_directions).
* :data:`CITATION_PATTERN`      -- pinned regex from the spec.
* :func:`validate_citations`    -- per-paragraph regex validator.
* :func:`validate_directions`   -- enforces EXACTLY 3 directions, each cited.
* :func:`merge_sources`         -- fuse tier Sources with NotebookLM URLs
  (dedup by URL, tier sources first; spec ``notebooklm-async-tier3`` D2).
* :func:`synthesize_with_citations` -- orchestrates LLM call + retry loop.

The synthesizer callable is injected so tests can drive it deterministically
without any external API.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

# --- Public types ------------------------------------------------------------


@dataclass(frozen=True)
class Source:
    """A single source the synthesizer can cite as ``[N]``.

    Mirrors the structure consumed by ``persist-artifact.md`` so the same
    ``Source`` instances can flow through both modules without conversion.
    """

    title: str
    url: str
    accessed_at: str


@dataclass(frozen=True)
class Direction:
    """One recommended strategic direction ("rumbo").

    Mirrors ``synthesize-with-citations.md`` §"Recommended Directions". The
    output contract (spec ``notebooklm-async-tier3`` D8/G7, AC5) requires
    EXACTLY 3 of these, each carrying at least one ``[N]`` or ``[unsourced]``
    citation marker -- either in :attr:`citations` or inline in the prose.

    * ``title``     -- short imperative label for the direction.
    * ``rationale`` -- 1-2 line justification.
    * ``trade_off`` -- the cost / risk the option carries.
    * ``citations`` -- the ``[N]`` / ``[unsourced]`` markers backing the
      direction. May be empty when the marker is embedded in the prose.
    """

    title: str
    rationale: str
    trade_off: str
    citations: list[str] = field(default_factory=list)


@dataclass
class SynthesizeResult:
    """Output of the synthesizer + validator pipeline."""

    findings: str = ""
    validation_passed: bool = False
    warnings: list[str] = field(default_factory=list)
    attempts: int = 0
    recommended_directions: list[Direction] = field(default_factory=list)


# --- Validator ---------------------------------------------------------------

# Pinned regex from ``synthesize-with-citations.md``. Either a numbered
# ``[N]`` citation OR the ``[unsourced]`` literal is accepted as a marker.
CITATION_PATTERN = re.compile(r"\[\d+\]|\[unsourced\]")

# The output contract requires EXACTLY this many recommended directions (D8).
REQUIRED_DIRECTIONS = 3


def _split_paragraphs(text: str) -> list[str]:
    """Split a synthesized response into paragraphs by blank-line gaps.

    Preserves order and discards leading/trailing whitespace. Empty
    fragments (e.g., from ``\\n\\n\\n``) are filtered.
    """
    return [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]


def validate_citations(text: str) -> tuple[bool, list[int]]:
    """Validate that every paragraph carries at least one citation marker.

    Returns ``(passed, malformed_paragraphs)`` where ``passed`` is True iff
    every non-empty paragraph contains at least one ``[N]`` or
    ``[unsourced]`` marker, and ``malformed_paragraphs`` lists the 1-indexed
    positions of paragraphs that failed.

    A response with no paragraphs at all is considered malformed (a single
    empty paragraph is reported at index 1).
    """
    paragraphs = _split_paragraphs(text)
    if not paragraphs:
        return False, [1]

    malformed: list[int] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        if not CITATION_PATTERN.search(paragraph):
            malformed.append(index)
    return (not malformed), malformed


def _direction_is_cited(direction: Direction) -> bool:
    """A direction is cited iff a ``[N]``/``[unsourced]`` marker appears.

    The marker may live in :attr:`Direction.citations` OR inline in the
    ``rationale`` / ``trade_off`` prose. Reuses the pinned ``CITATION_PATTERN``
    so the directions rule never drifts from the per-paragraph rule.
    """
    if any(CITATION_PATTERN.search(marker) for marker in direction.citations):
        return True
    return bool(CITATION_PATTERN.search(f"{direction.rationale}\n{direction.trade_off}"))


def validate_directions(directions: Sequence[Direction]) -> tuple[bool, list[str]]:
    """Validate the recommended-directions block (D8/G7, AC5).

    Returns ``(passed, problems)``. ``passed`` is True iff:

    1. there are EXACTLY :data:`REQUIRED_DIRECTIONS` (3) directions, AND
    2. every direction carries at least one ``[N]`` or ``[unsourced]`` marker.

    ``problems`` lists human-readable violation notes for the retry/warning
    path; it is empty on success.
    """
    problems: list[str] = []

    count = len(directions)
    if count != REQUIRED_DIRECTIONS:
        problems.append(
            f"expected exactly {REQUIRED_DIRECTIONS} recommended directions, got {count}"
        )

    for index, direction in enumerate(directions, start=1):
        if not _direction_is_cited(direction):
            problems.append(
                f"direction {index} ({direction.title!r}) carries no [N]/[unsourced] citation"
            )

    return (not problems), problems


# --- Source merge (spec ``notebooklm-async-tier3`` D2) -----------------------

# Placeholder title prefix for a NotebookLM-discovered URL that arrives without
# a human-readable title. Kept short and greppable.
_DERIVED_TITLE_PREFIX = "NotebookLM source: "


def _derive_title(url: str) -> str:
    """Derive a placeholder title for an untitled NotebookLM URL.

    Strips the scheme and trailing slash so the title reads as the bare
    host/path; falls back to the raw URL when nothing remains.
    """
    stripped = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url).rstrip("/")
    return f"{_DERIVED_TITLE_PREFIX}{stripped or url}"


def merge_sources(
    tier_sources: Iterable[Source],
    notebooklm_sources: Iterable[str],
) -> list[Source]:
    """Fuse Tier 0-2 ``Source`` rows with NotebookLM-discovered URLs (D2).

    Mirrors ``synthesize-with-citations.md`` §"Source Merge". NotebookLM runs
    autonomous deep research and discovers its own sources; Tiers 0-2 run
    independently. At synthesis the two source sets are fused and de-duplicated
    by URL, with **tier sources first** (stable order). A NotebookLM URL that
    is already present in the tier sources is dropped (the richer tier
    ``Source`` -- with its real title -- wins). NotebookLM URLs with no title
    become ``Source`` entries with a derived placeholder title and an empty
    ``accessed_at`` (the discovery timestamp is owned by Tier 3, not synthesis).

    ``notebooklm_sources`` is accepted as a plain ``list[str]`` to keep the
    synthesizer decoupled from the Tier 3 helper (no cross-import).
    """
    merged: list[Source] = []
    seen: set[str] = set()

    for source in tier_sources:
        if source.url in seen:
            continue
        seen.add(source.url)
        merged.append(source)

    for url in notebooklm_sources:
        if url in seen:
            continue
        seen.add(url)
        merged.append(Source(title=_derive_title(url), url=url, accessed_at=""))

    return merged


# --- Retry loop --------------------------------------------------------------

# System messages -- pinned strings let tests assert escalation without
# string-matching the entire prompt template.
DEFAULT_SYSTEM_MESSAGE = (
    "Synthesize a research summary for the user query. Cite every external "
    "claim with `[N]` referring to the numbered Sources list. If a claim "
    "comes from prior knowledge with no source, mark it `[unsourced]`. "
    "End with exactly 3 recommended directions, each with a title, a 1-2 line "
    "rationale, a trade-off, and at least one `[N]` or `[unsourced]` citation."
)

STRICT_SYSTEM_MESSAGE = (
    DEFAULT_SYSTEM_MESSAGE
    + "\nSTRICT: every external claim MUST carry [N] or [unsourced], and there "
    "MUST be EXACTLY 3 recommended directions, each individually cited. "
    "No exceptions."
)

_MAX_RETRIES = 2

# The synthesizer may return either the findings string alone (legacy contract)
# or a ``(findings, directions)`` tuple. Both shapes are normalised by
# :func:`_unpack` before validation.
_SynthesizerCallable = Callable[..., object]


def _unpack(output: object) -> tuple[str, list[Direction], bool]:
    """Normalise a synthesizer return into ``(findings, directions, supplied)``.

    Accepts a bare findings string (no directions) or a
    ``(findings, directions)`` tuple. ``supplied`` is True only for the tuple
    form: a synthesizer that returns a bare string is not participating in the
    directions contract, so the directions gate is skipped for it. This keeps
    the legacy string-returning synthesizer stubs (citation-only retry tests)
    working while the directions contract is layered on for tuple-form callers.
    """
    if isinstance(output, tuple):
        findings, directions = output
        return findings, list(directions), True
    return str(output), [], False


def synthesize_with_citations(
    *,
    query: str,
    sources: list[Source],
    synthesizer: _SynthesizerCallable,
) -> SynthesizeResult:
    """Run the synthesizer with a citation + directions validation retry loop.

    Sequence (mirrors ``synthesize-with-citations.md`` §"Retry Loop"):

    1. Synthesize with the default system message.
    2. Run BOTH validators (per-paragraph citations AND the exactly-3 cited
       recommended-directions rule). On a clean pass, return immediately.
    3. On any failure, retry with the stricter system message (max 2 retries).
    4. On retry exhaustion, return the last output annotated with the relevant
       warning(s) -- ``"citations malformed"`` and/or
       ``"recommended directions invalid: ..."`` -- WITHOUT raising.

    The synthesizer callable receives ``query``, ``sources``, and
    ``system_message`` and returns either the synthesized markdown string
    (citation-only contract) or a ``(findings, directions)`` tuple (full
    contract). The exactly-3-directions gate applies only to the tuple form.
    """
    findings = ""
    directions: list[Direction] = []
    citations_passed = False
    directions_passed = True
    direction_problems: list[str] = []
    attempts = 0

    for attempt_index in range(_MAX_RETRIES + 1):
        system_message = DEFAULT_SYSTEM_MESSAGE if attempt_index == 0 else STRICT_SYSTEM_MESSAGE
        output = synthesizer(
            query=query,
            sources=list(sources),
            system_message=system_message,
        )
        findings, directions, directions_supplied = _unpack(output)
        attempts = attempt_index + 1

        citations_passed, _ = validate_citations(findings)
        if directions_supplied:
            directions_passed, direction_problems = validate_directions(directions)
        else:
            directions_passed, direction_problems = True, []

        if citations_passed and directions_passed:
            return SynthesizeResult(
                findings=findings,
                validation_passed=True,
                warnings=[],
                attempts=attempts,
                recommended_directions=directions,
            )

    warnings: list[str] = []
    if not citations_passed:
        warnings.append("citations malformed")
    if not directions_passed:
        warnings.append("recommended directions invalid: " + "; ".join(direction_problems))

    return SynthesizeResult(
        findings=findings,
        validation_passed=False,
        warnings=warnings,
        attempts=attempts,
        recommended_directions=directions,
    )


__all__: Iterable[str] = (
    "CITATION_PATTERN",
    "DEFAULT_SYSTEM_MESSAGE",
    "REQUIRED_DIRECTIONS",
    "STRICT_SYSTEM_MESSAGE",
    "Direction",
    "Source",
    "SynthesizeResult",
    "merge_sources",
    "synthesize_with_citations",
    "validate_citations",
    "validate_directions",
)
