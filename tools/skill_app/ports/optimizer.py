"""``OptimizerPort`` — run an eval corpus against a skill's description.

The optimizer port abstracts Anthropic's ``skill-creator`` (or any
equivalent eval pass-rate engine). The application layer only needs
the per-skill pass@1 number for the regression gate; concrete adapters
(``skill_infra.skill_creator_adapter``) handle the subprocess wiring,
output parsing, and structured-output back-translation.

The default no-op adapter (constructed with a fixed pass@1) is useful
for tests that only exercise the gate logic without running a real
optimizer.
"""

from __future__ import annotations

from typing import Protocol

from skill_domain.eval_types import EvalCorpus


class OptimizerPort(Protocol):
    """Run an eval corpus against a skill and return its pass@1 score."""

    def run(self, skill: str, corpus: EvalCorpus) -> float:
        """Return the pass@1 fraction in ``[0.0, 1.0]`` for ``skill``.

        Implementations must be deterministic enough that two
        consecutive runs with the same corpus produce the same score
        (or document the noise floor in the adapter docstring so the
        regression threshold can be tuned to absorb it).
        """
        ...
