"""RED-phase test for spec-111 T-4.4 -- /ai-brainstorm invokes /ai-research.

Spec acceptance:
    When the brainstorm interrogation flow surfaces a question that
    requires external evidence the model cannot confirm from training
    data (e.g., "what patterns does the industry use", "what does the
    state of the art say"), ``/ai-brainstorm``'s ``handlers/interrogate.md``
    must invoke ``/ai-research --depth=standard <subquery>``, consume the
    resulting artifact, and cite it in the spec under
    ``## References`` with the prefix ``research:``.

The handlers are Markdown specs consumed by an LLM agent, so this test
validates the contract by parsing the handler files for the required
language and asserting the spec-schema documents the prefix convention.

Status: RED until T-4.5 (interrogate.md), T-4.6 (spec-schema.md), and
T-4.7 confirm GREEN.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

INTERROGATE_MD = REPO_ROOT / ".claude" / "skills" / "ai-brainstorm" / "handlers" / "interrogate.md"
SPEC_SCHEMA_MD = REPO_ROOT / ".ai-engineering" / "contexts" / "spec-schema.md"


# ---------------------------------------------------------------------------
# T-4.4: interrogation invokes /ai-research when external evidence is required
# ---------------------------------------------------------------------------


def test_interrogation_invokes_research_when_evidence_required() -> None:
    """``/ai-brainstorm`` interrogate handler MUST instruct invoking ``/ai-research``.

    The handler is Markdown; the contract is encoded as a literal step
    instructing the agent to invoke ``/ai-research --depth=standard``
    when a question requires external evidence and to cite the resulting
    artifact under ``## References`` with prefix ``research:``.

    Asserts:
      * ``interrogate.md`` mentions ``/ai-research`` and ``--depth=standard``.
      * The instruction includes a heuristic for "external evidence" /
        "state of the art" / "industry patterns" so the agent can decide
        without invoking blindly on every UNKNOWN.
      * The instruction tells the agent to cite the artifact in
        ``## References`` with prefix ``research:``.
    """
    assert INTERROGATE_MD.is_file(), (
        f"interrogate handler must exist at {INTERROGATE_MD}; spec-111 modifies it."
    )
    text = INTERROGATE_MD.read_text(encoding="utf-8")

    assert "/ai-research" in text, (
        "interrogate.md must mention /ai-research as the escalation target "
        "for evidence-required questions; spec-111 T-4.5"
    )
    assert "--depth=standard" in text, (
        "interrogate.md must specify --depth=standard for the default research "
        "invocation depth so brainstorm doesn't auto-trigger Tier 3; spec-111 T-4.5"
    )
    # Heuristic phrasing -- at least one of the trigger phrases must appear.
    trigger_phrases = (
        "evidencia externa",
        "external evidence",
        "state of the art",
        "patrones usa la industria",
        "industry patterns",
    )
    assert any(phrase.lower() in text.lower() for phrase in trigger_phrases), (
        "interrogate.md must include at least one trigger phrase that helps the "
        "agent decide whether the question needs research; expected one of "
        f"{trigger_phrases}"
    )
    # Reference convention.
    assert "## References" in text, (
        "interrogate.md must instruct citing the artifact in spec ## References"
    )
    assert "research:" in text, (
        "interrogate.md must specify the 'research:' prefix for the citation"
    )


# ---------------------------------------------------------------------------
# T-4.6: spec-schema documents research: prefix in ## References
# ---------------------------------------------------------------------------


def test_spec_schema_documents_research_prefix_convention() -> None:
    """``spec-schema.md`` ``## References`` description must permit ``research:`` entries.

    Asserts:
      * The Optional Sections / References row mentions the
        ``- research: .ai-engineering/research/<artifact>.md`` syntax.
      * The prefix convention is named explicitly so authors of brand-new
        prefixes (e.g., ``rfc:``) can follow the same shape.
    """
    assert SPEC_SCHEMA_MD.is_file(), f"spec-schema must exist at {SPEC_SCHEMA_MD}"
    text = SPEC_SCHEMA_MD.read_text(encoding="utf-8")

    assert "research:" in text, (
        "spec-schema.md must document the 'research:' prefix in the "
        "References section per spec-111 T-4.6"
    )
    assert ".ai-engineering/research/" in text, (
        "spec-schema.md must show the canonical artifact path "
        ".ai-engineering/research/<artifact>.md"
    )
    assert "prefix" in text.lower(), (
        "spec-schema.md must call out the convention as a 'prefix' so future "
        "additions follow the same shape"
    )
