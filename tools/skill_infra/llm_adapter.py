"""``LLMPort`` adapter — pilot stub.

Sub-007 M6 defers live LLM-driven case generation (no live API
access in batch agent context per scope guardrail). The stub below
emits a deterministic placeholder list so the corpus generator can
be wired without external dependencies.

Concrete production adapter (future work) will:

1. Call Anthropic Sonnet via the ``messages`` API with structured
   output (``response_format=json_schema``).
2. Pass ``skill_name`` + ``skill_description`` + ``near_miss_phrases``
   into a system prompt that asks for 8 ``should_trigger`` and 8
   ``near_miss`` cases.
3. Validate the schema and return the parsed list.

Until the adapter lands, callers should treat the stub output as a
seed and rely on operator-curated corpora for real evaluation.
"""

from __future__ import annotations

from skill_app.ports.llm import LLMPort


class StubLLMAdapter(LLMPort):
    """Deterministic stub — returns 2 placeholder cases per call."""

    def generate_cases(
        self,
        skill_name: str,
        skill_description: str,
        near_miss_phrases: tuple[str, ...] = (),
    ) -> list[dict[str, object]]:
        """Return a 2-case placeholder list for the corpus generator.

        The shape matches :class:`~skill_domain.eval_types.EvalCase` so
        downstream consumers can serialize / round-trip the cases
        without special-casing the stub.
        """
        # ``skill_description`` and ``near_miss_phrases`` accepted for
        # protocol fit; the stub uses only ``skill_name`` so the seed
        # cases are self-describing in test logs.
        del skill_description, near_miss_phrases
        return [
            {
                "skill": skill_name,
                "prompt": f"placeholder-should-trigger for {skill_name}",
                "kind": "should_trigger",
                "expected": True,
                "notes": "stub seed — replace with LLM-generated case",
            },
            {
                "skill": skill_name,
                "prompt": f"placeholder-near-miss for {skill_name}",
                "kind": "near_miss",
                "expected": False,
                "notes": "stub seed — replace with LLM-generated case",
            },
        ]


__all__ = ["StubLLMAdapter"]
