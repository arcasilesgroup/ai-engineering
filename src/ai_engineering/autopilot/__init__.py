"""Autopilot helpers (spec-139).

This package hosts pure-stdlib helpers consumed by the
``/ai-autopilot`` skill handlers. Currently exposes
:func:`stack_context.resolve_stack_context` (spec-139 M3) — the Phase 0
single-read of ``.ai-engineering/manifest.yml`` that downstream agents
consume via the ``STACK_CONTEXT`` dispatch-prompt variable instead of
re-reading the manifest from disk per dispatch.
"""

from __future__ import annotations
