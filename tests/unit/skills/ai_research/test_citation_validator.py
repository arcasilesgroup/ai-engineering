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
    Direction,
    Source,
    SynthesizeResult,
    merge_sources,
    synthesize_with_citations,
    validate_citations,
    validate_directions,
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


# ---------------------------------------------------------------------------
# sub-003 / D2: source merge -- dedup NotebookLM URLs with tier Sources.
# ---------------------------------------------------------------------------


def _tier_sources() -> list[Source]:
    return [
        Source(title="Tier One", url="https://example.com/a", accessed_at="2026-05-01"),
        Source(title="Tier Two", url="https://example.com/b", accessed_at="2026-05-01"),
    ]


def test_merge_sources_appends_notebooklm_urls() -> None:
    """NotebookLM-discovered URLs are appended after the tier sources (D2).

    Arrange: two tier ``Source`` rows + two distinct NotebookLM URLs.

    Act: merge.

    Assert: tier sources come first (order preserved), NotebookLM URLs follow
    as ``Source`` entries with a derived (non-empty) title.
    """
    merged = merge_sources(
        _tier_sources(),
        ["https://nlm.example/x", "https://nlm.example/y"],
    )

    assert [s.url for s in merged] == [
        "https://example.com/a",
        "https://example.com/b",
        "https://nlm.example/x",
        "https://nlm.example/y",
    ], "Tier sources must precede appended NotebookLM URLs in stable order"
    # The two appended NotebookLM entries must carry a derived placeholder title.
    assert merged[2].title, "A NotebookLM URL with no title must get a derived title"
    assert merged[3].title


def test_merge_sources_dedups_by_url() -> None:
    """A NotebookLM URL already present in the tier sources is not duplicated.

    Arrange: NotebookLM rediscovers ``https://example.com/a`` (a tier URL) plus
    one genuinely new URL.

    Act: merge.

    Assert: the duplicate is dropped (dedup by URL); only the new URL is added,
    and the surviving tier ``Source`` keeps its original rich title.
    """
    merged = merge_sources(
        _tier_sources(),
        ["https://example.com/a", "https://nlm.example/new"],
    )

    urls = [s.url for s in merged]
    assert urls == [
        "https://example.com/a",
        "https://example.com/b",
        "https://nlm.example/new",
    ], f"Duplicate NotebookLM URL must be deduped by URL; got {urls}"
    assert urls.count("https://example.com/a") == 1, "URL must not appear twice"
    # The tier source's original title survives (NotebookLM does not overwrite it).
    assert merged[0].title == "Tier One"


def test_merge_sources_dedups_repeated_notebooklm_urls() -> None:
    """Repeated URLs *within* the NotebookLM list are themselves deduped."""
    merged = merge_sources(
        _tier_sources(),
        ["https://nlm.example/z", "https://nlm.example/z"],
    )
    assert [s.url for s in merged].count("https://nlm.example/z") == 1


# ---------------------------------------------------------------------------
# sub-003 / D8, G7, AC5: recommended directions -- exactly 3, each cited.
# ---------------------------------------------------------------------------


def _direction(n: int, citation: str = "[1]") -> Direction:
    return Direction(
        title=f"Direction {n}",
        rationale=f"Why option {n} is worth pursuing {citation}.",
        trade_off=f"Cost of option {n}.",
        citations=[citation] if citation else [],
    )


def test_validate_directions_exactly_three_passes() -> None:
    """Exactly 3 directions, each carrying a citation marker, passes (AC5)."""
    directions = [_direction(1), _direction(2, "[unsourced]"), _direction(3, "[2]")]
    passed, problems = validate_directions(directions)

    assert passed is True, f"Three cited directions must pass; got problems={problems}"
    assert problems == []


@pytest.mark.parametrize("count", [0, 1, 2, 4, 5])
def test_validate_directions_wrong_count_fails(count: int) -> None:
    """Any direction count other than exactly 3 fails the validator (D8)."""
    directions = [_direction(i) for i in range(count)]
    passed, problems = validate_directions(directions)

    assert passed is False, f"{count} directions must fail the exactly-3 rule"
    assert problems, "A count violation must surface a problem note for the warning"


def test_validate_directions_uncited_direction_fails() -> None:
    """Three directions where one carries no ``[N]``/``[unsourced]`` marker fails.

    AC5: each direction must carry >=1 citation marker. A direction whose
    ``citations`` list is empty AND whose prose has no marker is invalid.
    """
    directions = [
        _direction(1),
        Direction(
            title="Uncited option",
            rationale="This rationale cites nothing at all.",
            trade_off="Unknown.",
            citations=[],
        ),
        _direction(3),
    ]
    passed, problems = validate_directions(directions)

    assert passed is False, "A direction with no citation marker must fail"
    assert problems, "The uncited direction must be reported"


def test_validate_directions_citation_in_prose_counts() -> None:
    """A marker embedded in rationale/trade-off prose satisfies the per-direction rule.

    The citation may live in the ``citations`` list OR inline in the prose; the
    validator reuses the pinned ``CITATION_PATTERN``.
    """
    directions = [
        _direction(1),
        Direction(
            title="Prose-cited option",
            rationale="Rationale with an inline marker [3].",
            trade_off="Trade-off prose.",
            citations=[],
        ),
        _direction(3),
    ]
    passed, problems = validate_directions(directions)

    assert passed is True, f"Inline prose citation must count; got problems={problems}"


# ---------------------------------------------------------------------------
# sub-003: synthesize loop wires directions into SynthesizeResult + retries.
# ---------------------------------------------------------------------------


class _DirectionSynthesizer:
    """Stub synthesizer that also returns ``recommended_directions`` per attempt.

    Each prepared output is a ``(findings, directions)`` tuple; the helper reads
    both from the callable so the directions validator can drive retries.
    """

    def __init__(self, outputs: list[tuple[str, list[Direction]]]) -> None:
        self.outputs = list(outputs)
        self.calls: list[dict] = []

    def __call__(
        self, *, query: str, sources: list[Source], system_message: str
    ) -> tuple[str, list[Direction]]:
        self.calls.append({"system_message": system_message})
        if not self.outputs:
            raise AssertionError("Synthesizer called more times than outputs prepared")
        return self.outputs.pop(0)


def test_synthesize_populates_three_directions() -> None:
    """A passing synthesize run carries exactly 3 directions on the result (G7)."""
    good = [_direction(1), _direction(2), _direction(3)]
    synthesizer = _DirectionSynthesizer(outputs=[("Cited finding [1].", good)])

    result = synthesize_with_citations(
        query="strategy?",
        sources=_stub_sources(1),
        synthesizer=synthesizer,
    )

    assert result.validation_passed is True
    assert len(result.recommended_directions) == 3
    assert result.recommended_directions == good
    assert result.warnings == []


def test_synthesize_retries_on_bad_directions_then_recovers() -> None:
    """A first output with the wrong direction count triggers a stricter retry.

    Arrange: attempt 1 returns well-cited findings but only 2 directions
    (invalid); attempt 2 returns 3 cited directions.

    Act: synthesize.

    Assert: the synthesizer is called twice, the retry uses the STRICT message,
    and the final result carries 3 directions with no warning.
    """
    synthesizer = _DirectionSynthesizer(
        outputs=[
            ("Cited finding [1].", [_direction(1), _direction(2)]),
            ("Cited finding [1].", [_direction(1), _direction(2), _direction(3)]),
        ]
    )

    result = synthesize_with_citations(
        query="strategy?",
        sources=_stub_sources(1),
        synthesizer=synthesizer,
    )

    assert len(synthesizer.calls) == 2, "Bad direction count must trigger one retry"
    assert "STRICT" in synthesizer.calls[1]["system_message"]
    assert result.validation_passed is True
    assert len(result.recommended_directions) == 3
    assert result.warnings == []


def test_synthesize_warns_when_directions_invalid_after_retries() -> None:
    """Persistently invalid directions exhaust retries and warn (no raise).

    Arrange: every attempt returns cited findings but only 1 direction.

    Act: synthesize.

    Assert: validation_passed is False, a directions warning is recorded, and
    the call does NOT raise (consistent with the citations retry contract).
    """
    bad = ("Cited finding [1].", [_direction(1)])
    synthesizer = _DirectionSynthesizer(outputs=[bad, bad, bad])

    result = synthesize_with_citations(
        query="strategy?",
        sources=_stub_sources(1),
        synthesizer=synthesizer,
    )

    assert result.validation_passed is False
    assert len(synthesizer.calls) == 3, "1 initial + 2 retries when always invalid"
    assert any("direction" in w.lower() for w in result.warnings), (
        f"A directions warning must surface on exhaustion; got {result.warnings}"
    )
