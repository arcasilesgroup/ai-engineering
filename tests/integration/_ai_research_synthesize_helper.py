"""Lockstep Python implementation of the synthesizer + validator algorithm
documented in ``.claude/skills/ai-research/handlers/synthesize-with-citations.md``.

The handler is a Markdown spec consumed by an LLM agent. To validate the
algorithm with deterministic tests, this helper mirrors it 1:1. If the
handler changes, this module must follow (and vice versa).

Public API:

* :class:`Source`               -- per-source dataclass shared with persist.
* :class:`SynthesizeResult`     -- aggregated output (findings, validation,
  warnings).
* :data:`CITATION_PATTERN`      -- pinned regex from the spec.
* :func:`validate_citations`    -- per-paragraph regex validator.
* :func:`synthesize_with_citations` -- orchestrates LLM call + retry loop.

The synthesizer callable is injected so tests can drive it deterministically
without any external API.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
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


@dataclass
class SynthesizeResult:
    """Output of the synthesizer + validator pipeline."""

    findings: str = ""
    validation_passed: bool = False
    warnings: list[str] = field(default_factory=list)
    attempts: int = 0


# --- Validator ---------------------------------------------------------------

# Pinned regex from ``synthesize-with-citations.md``. Either a numbered
# ``[N]`` citation OR the ``[unsourced]`` literal is accepted as a marker.
CITATION_PATTERN = re.compile(r"\[\d+\]|\[unsourced\]")


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


# --- Retry loop --------------------------------------------------------------

# System messages -- pinned strings let tests assert escalation without
# string-matching the entire prompt template.
DEFAULT_SYSTEM_MESSAGE = (
    "Synthesize a research summary for the user query. Cite every external "
    "claim with `[N]` referring to the numbered Sources list. If a claim "
    "comes from prior knowledge with no source, mark it `[unsourced]`."
)

STRICT_SYSTEM_MESSAGE = (
    DEFAULT_SYSTEM_MESSAGE
    + "\nSTRICT: every external claim MUST carry [N] or [unsourced]. No exceptions."
)

_MAX_RETRIES = 2

_SynthesizerCallable = Callable[..., str]


def synthesize_with_citations(
    *,
    query: str,
    sources: list[Source],
    synthesizer: _SynthesizerCallable,
) -> SynthesizeResult:
    """Run the synthesizer with a citation-validation retry loop.

    Sequence (mirrors ``synthesize-with-citations.md`` §"Retry Loop"):

    1. Synthesize with the default system message.
    2. Run the validator. On pass, return immediately.
    3. On fail, retry with the stricter system message (max 2 retries).
    4. On retry exhaustion, return the last output annotated with the
       ``citations malformed`` warning.

    The synthesizer callable receives ``query``, ``sources``, and
    ``system_message`` and returns the synthesized markdown string.
    """
    findings = ""
    last_passed = False
    attempts = 0

    for attempt_index in range(_MAX_RETRIES + 1):
        system_message = DEFAULT_SYSTEM_MESSAGE if attempt_index == 0 else STRICT_SYSTEM_MESSAGE
        findings = synthesizer(
            query=query,
            sources=list(sources),
            system_message=system_message,
        )
        attempts = attempt_index + 1
        passed, _ = validate_citations(findings)
        if passed:
            return SynthesizeResult(
                findings=findings,
                validation_passed=True,
                warnings=[],
                attempts=attempts,
            )
        last_passed = passed

    return SynthesizeResult(
        findings=findings,
        validation_passed=last_passed,
        warnings=["citations malformed"],
        attempts=attempts,
    )


__all__: Iterable[str] = (
    "CITATION_PATTERN",
    "DEFAULT_SYSTEM_MESSAGE",
    "STRICT_SYSTEM_MESSAGE",
    "Source",
    "SynthesizeResult",
    "synthesize_with_citations",
    "validate_citations",
)
