"""Governance package -- minimal Rego-subset policy engine (spec-110 G-7).

Public API:

* :func:`evaluate` -- evaluate a ``.rego`` file against an ``input_data`` dict
  and return a :class:`Decision`.
* :class:`Decision` -- frozen dataclass carrying the allow verdict and an
  optional human-readable reason for denials.

The engine is intentionally a *subset* of OPA Rego, sufficient to express the
three policies shipped with spec-110 (branch protection, conventional commits,
risk-acceptance TTL). See :mod:`ai_engineering.governance.policy_engine` for
the supported grammar and evaluation rules.
"""

from __future__ import annotations

from .policy_engine import Decision, evaluate

__all__ = ["Decision", "evaluate"]
