"""Shared capability-detection guard for the /ai-research tiers.

Spec ``notebooklm-async-tier3`` D7 / G5: every external tool (NotebookLM,
Context7, Exa, MS Learn) is *capability-detected* and *fail-soft*. An
absent or unauthenticated tool is skipped silently, recorded in
``degraded_sources``, and NEVER raised.

This module is the single DRY predicate (§10.4) the tiers route through so
"absent" means the same thing everywhere. It is deliberately tiny -- a
single boolean probe, not a generic capability framework (§10.2 YAGNI;
spec Non-Goal "not building a generic async-job framework").

A *probe* is a zero-argument callable returning the tool's introspection
payload (e.g. ``nlm_list`` for NotebookLM). It is treated as UNAVAILABLE
when it is ``None``, raises, returns a falsy payload, or reports
``{"authenticated": False}``; otherwise the tool is AVAILABLE.

Note: this is the up-front *absence* check. A present-but-flaky tool that
raises mid-call is handled separately by each tier's post-hoc
exception-to-``degraded_sources`` path; the two together realise D7.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

# A capability probe: zero-arg, returns the tool's introspection payload.
CapabilityProbe = Callable[[], object]


def is_available(probe: CapabilityProbe | None) -> bool:
    """Return ``True`` only if ``probe`` reports a usable, authenticated tool.

    Unavailable (returns ``False``) when ``probe`` is:

    * ``None`` -- the tool is not wired at all;
    * a callable that raises -- the tool cannot even be introspected;
    * a callable returning a falsy payload (``{}``, ``[]``, ``0``, ``None``);
    * a callable returning ``{"authenticated": False}`` -- present but
      unauthenticated.

    Available (returns ``True``) for any other truthy payload. A truthy
    payload with no ``authenticated`` key defaults to available.

    Fail-soft (D7): a raising probe is swallowed -- this guard never
    propagates an exception.
    """
    if probe is None:
        return False
    try:
        payload = probe()
    except Exception:
        return False
    if not payload:
        return False
    if isinstance(payload, dict):
        return bool(payload.get("authenticated", True))
    return True


__all__: Iterable[str] = ("CapabilityProbe", "is_available")
