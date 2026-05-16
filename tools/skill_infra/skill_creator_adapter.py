"""``OptimizerPort`` adapter — wraps Anthropic's ``skill-creator`` subprocess.

Sub-007 M6 infrastructure layer, pilot stub. The full adapter shells
out to ``skill-creator`` with the corpus on stdin and parses pass@1
from the structured-output reply. The pilot stub returns a fixed
pass@1 (defaulting to 1.0) so the regression-gate path can be
exercised end-to-end without a live LLM dependency in CI.

Upstream pin
~~~~~~~~~~~~

Pinned ``skill-creator`` upstream SHA: TBD — sub-007 T-0.2 follow-up.
The pin will land in this docstring once the adapter is wired to
real subprocess execution. Until then, callers should treat the
returned pass@1 as advisory; the regression-gate test suite uses a
deterministic stub via direct port substitution.
"""

from __future__ import annotations

from skill_app.ports.optimizer import OptimizerPort
from skill_domain.eval_types import EvalCorpus


class StubSkillCreatorAdapter(OptimizerPort):
    """Deterministic stub adapter — returns a fixed pass@1.

    Used by:
    - the CLI smoke test (no live LLM in CI lanes);
    - integration tests that exercise the runner end-to-end without
      provisioning an API key;
    - operators previewing the regression-gate path before flipping
      on the full corpus rollout.
    """

    def __init__(self, fixed_pass_at_1: float = 1.0) -> None:
        self._fixed = float(fixed_pass_at_1)

    def run(self, skill: str, corpus: EvalCorpus) -> float:
        """Return ``fixed_pass_at_1`` regardless of corpus contents."""
        # ``skill`` and ``corpus`` are accepted to satisfy the port
        # signature; the stub deliberately ignores them so the gate
        # path stays exercisable without a live optimizer.
        del skill, corpus
        return self._fixed


__all__ = ["StubSkillCreatorAdapter"]
