"""``LLMPort`` — minimal LLM client for eval-case generation.

The corpus generator (``skill_app.eval_runner``) needs to ask an LLM
to produce 8 should-trigger / 8 near-miss prompts per skill. That
call is gated behind a port so:

1. Tests can substitute a deterministic stub that returns a fixed
   list of cases, removing flakiness from the regression gate.
2. Operators can swap the concrete provider (Anthropic Sonnet, OpenAI,
   Bedrock, …) by editing only the infra adapter.
3. The application layer remains free of HTTP / SDK imports.

The contract is intentionally small: one call, structured-list reply.
Anything richer (tool use, system prompt assembly, retry policy)
belongs in the concrete adapter.
"""

from __future__ import annotations

from typing import Protocol


class LLMPort(Protocol):
    """Generate structured-list completions for eval-case authoring."""

    def generate_cases(
        self,
        skill_name: str,
        skill_description: str,
        near_miss_phrases: tuple[str, ...] = (),
    ) -> list[dict[str, object]]:
        """Return a list of case dicts (``{prompt, kind, expected, notes}``).

        ``near_miss_phrases`` is an optional bag of adversarial seeds
        (see :class:`GitLogPort`); the adapter is free to weave them
        into the prompt to bias the LLM toward realistic confusion
        cases. The shape of each returned dict must match the
        :class:`~skill_domain.eval_types.EvalCase` constructor.
        """
        ...
