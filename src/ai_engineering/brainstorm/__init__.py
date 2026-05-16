"""Domain helpers for ``/ai-brainstorm`` (spec-134 D-134-04).

This package hosts pure domain logic for the brainstorm workflow.
Today it exposes a single public helper — :func:`classify_diff` — used
by the auto-spec gate to route trivial diffs to a condensed-spec path
and everything else to full interrogation.

The package boundary is hexagonal (§10.8): no module under
``ai_engineering.brainstorm`` may import a subprocess, network, or
file-system adapter directly. The skill handler (markdown) is the
orchestration layer — it runs ``git diff`` and feeds the raw output
into the helper.
"""

from __future__ import annotations

from ai_engineering.brainstorm.auto_spec_gate import (
    AutoSpecGateConfig,
    GateDecision,
    classify_diff,
)

__all__ = ["AutoSpecGateConfig", "GateDecision", "classify_diff"]
