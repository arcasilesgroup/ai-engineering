"""RED-phase tests for spec-111 T-4.1 -- citation validator.

Spec acceptance:
    The synthesizer in ``synthesize-with-citations.md`` must validate that
    every external claim carries a ``[N]`` numbered citation or a
    ``[unsourced]`` literal marker. The validator regex
    ``\\[\\d+\\]|\\[unsourced\\]`` must match at least once per claim
    paragraph; on failure, the synthesizer retries with a stricter system
    message (max 2 retries) and on retry exhaustion returns the output
    annotated with a "citations malformed" warning.

The lockstep Python helper at
``tests/integration/_ai_research_synthesize_helper.py`` mirrors the
algorithm 1:1 so deterministic unit tests can exercise it without
calling an LLM.

Status: RED until T-4.2 lands the helper module + handler logic.
"""

from __future__ import annotations

import pytest

from tests.integration._ai_research_synthesize_helper import (
    CITATION_PATTERN,
    Source,
    SynthesizeResult,
    synthesize_with_citations,
    validate_citations,
)

# ---------------------------------------------------------------------------
# T-4.1: validator regex behaviour
# ---------------------------------------------------------------------------


def _stub_sources(n: int) -> list[Source]:
    return [
        Source(title=f"Source {i}", url=f"https://example.com/s{i}", accessed_at="2026-04-28")
        for i in range(n)
    ]


# Test 1: output with `[N]` citations passes validation.
def test_output_with_citations_passes() -> None:
    """A paragraph carrying numbered ``[N]`` citations passes the validator.

    Arrange: a single-paragraph claim with ``[1]`` and ``[2]`` markers.

    Act: invoke ``validate_citations`` directly.

    Assert: returns True (passed) with no malformed paragraphs reported.
    """
    findings = (
        "React state libraries vary widely [1]. "
        "Redux has the strongest community while Zustand is more lightweight [2]."
    )
    passed, malformed = validate_citations(findings)

    assert passed is True, (
        f"A paragraph with [1] and [2] markers must pass; got malformed={malformed}"
    )
    assert malformed == [], (
        f"No paragraphs should be malformed when citations are present; got {malformed}"
    )


# Test 2: output without any citations fails validation.
def test_output_without_citations_fails_validation() -> None:
    """A paragraph claiming external facts without ``[N]`` or ``[unsourced]`` fails.

    Arrange: a single paragraph asserting external facts but no markers.

    Act: invoke ``validate_citations``.

    Assert: returns False with the malformed paragraph index reported.
    """
    findings = (
        "React state libraries vary widely. "
        "Redux has the strongest community while Zustand is more lightweight."
    )
    passed, malformed = validate_citations(findings)

    assert passed is False, "A paragraph with no citation markers must fail validation"
    assert malformed, "The malformed paragraph index must be surfaced for the retry loop"


# Test 3: output with `[unsourced]` marker passes validation.
def test_output_with_unsourced_marker_passes() -> None:
    """A paragraph using the ``[unsourced]`` literal passes the validator.

    Arrange: a paragraph honestly marking content as unsourced.

    Act: invoke ``validate_citations``.

    Assert: returns True; the literal marker is treated as a valid signal.
    """
    findings = "Redux is the dominant Flux-like state library in React projects [unsourced]."
    passed, malformed = validate_citations(findings)

    assert passed is True, (
        f"The [unsourced] marker must satisfy the validator regex; got malformed={malformed}"
    )
    assert malformed == []


# ---------------------------------------------------------------------------
# Validator regex pinning -- guards against accidental relaxation.
# ---------------------------------------------------------------------------


def test_citation_pattern_is_pinned() -> None:
    """The validator pattern matches the spec literal ``\\[\\d+\\]|\\[unsourced\\]``.

    This pins the regex so Phase 4 reviewers can grep for the contract.
    """
    assert CITATION_PATTERN.pattern == r"\[\d+\]|\[unsourced\]", (
        f"Citation regex must match spec exactly; got {CITATION_PATTERN.pattern!r}"
    )


# ---------------------------------------------------------------------------
# T-4.2: retry-loop wiring -- one synthesizer invocation per attempt,
# stricter system message on retry, warning on exhaustion.
# ---------------------------------------------------------------------------


class _StubSynthesizer:
    """Stand-in for the LLM synthesizer; produces canned outputs in order."""

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.calls: list[dict] = []

    def __call__(self, *, query: str, sources: list[Source], system_message: str) -> str:
        self.calls.append(
            {
                "query": query,
                "sources": list(sources),
                "system_message": system_message,
            }
        )
        if not self.outputs:
            raise AssertionError("Synthesizer was called more times than outputs were prepared")
        return self.outputs.pop(0)


def test_synthesize_retries_with_stricter_message_on_first_failure() -> None:
    """If the first synthesizer output fails validation, retry with stricter message.

    Arrange: stub returns malformed text first, well-formed text second.

    Act: invoke ``synthesize_with_citations``.

    Assert: synthesizer called twice; second call has a stricter system message;
    final result is the second output and validation_passed is True.
    """
    synthesizer = _StubSynthesizer(
        outputs=[
            "Without citations, this is the failing first attempt.",
            "Now properly cited [1].",
        ]
    )

    result = synthesize_with_citations(
        query="how do projects retry?",
        sources=_stub_sources(1),
        synthesizer=synthesizer,
    )

    assert isinstance(result, SynthesizeResult)
    assert result.validation_passed is True
    assert result.findings == "Now properly cited [1]."
    assert len(synthesizer.calls) == 2, (
        f"Expected one retry after first malformed output; got {len(synthesizer.calls)} calls"
    )
    second_message = synthesizer.calls[1]["system_message"]
    assert "STRICT" in second_message, (
        f"Retry must use a stricter system message; got {second_message!r}"
    )


def test_synthesize_returns_warning_when_retries_exhausted() -> None:
    """After 2 retries the synthesizer surfaces a 'citations malformed' warning.

    Arrange: stub returns malformed text three times (initial + 2 retries).

    Act: invoke ``synthesize_with_citations``.

    Assert: validation_passed is False, findings echoes the last malformed
    output, and the warning ``citations malformed`` is in result.warnings.
    """
    synthesizer = _StubSynthesizer(outputs=["Bad one.", "Bad two.", "Bad three."])

    result = synthesize_with_citations(
        query="needs sources",
        sources=_stub_sources(2),
        synthesizer=synthesizer,
    )

    assert result.validation_passed is False
    assert result.findings == "Bad three."
    assert "citations malformed" in result.warnings, (
        f"Warning must surface when retries are exhausted; got {result.warnings}"
    )
    assert len(synthesizer.calls) == 3, (
        f"Expected 1 initial + 2 retries (3 total) when all outputs malformed; "
        f"got {len(synthesizer.calls)} calls"
    )


@pytest.mark.parametrize(
    "text,expected",
    [
        ("First [1]. Then more [2].", True),
        ("No markers here at all.", False),
        ("Marked unsourced [unsourced].", True),
        ("Mixed forms: [1] then [unsourced].", True),
    ],
)
def test_validate_citations_parametrized(text: str, expected: bool) -> None:
    """Spot-check additional inputs against the validator.

    Pinned to assure no accidental relaxation when the helper evolves.
    """
    passed, _ = validate_citations(text)
    assert passed is expected
