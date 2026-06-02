"""Authoritative "latest known release" resolver — single source of truth.

Before this module two independent signals each claimed to be "the latest
version" and disagreed in practice:

- the bundled ``registry.json`` high-water mark (offline, known at build time,
  read by :mod:`ai_engineering.version.checker`), and
- the live PyPI poll cache (:mod:`ai_engineering.version.cache`, refreshed out
  of band by :mod:`ai_engineering.version.refresh`).

``ai-eng version`` rendered one from each, producing contradictory output, and
the update notice consulted only the cache, so it stayed silent whenever the
cache lagged the bundled registry. This resolver reconciles both into one value
— the newer of the two by PEP 440 comparison — so every surface (the inline
update notice, ``ai-eng version``, and the ``/ai-start`` dashboard) agrees.

Fail-open (D-010-3): any IO/parse error yields ``None`` so the CLI hot path
never breaks.
"""

from __future__ import annotations

from ai_engineering.version import cache
from ai_engineering.version.checker import find_latest_version, load_registry
from ai_engineering.version.compare import is_newer


def _registry_latest() -> str | None:
    """Highest version in the bundled registry, or None on any error."""
    try:
        registry = load_registry()
        if registry is None:
            return None
        latest = find_latest_version(registry)
        return latest if isinstance(latest, str) and latest else None
    except Exception:
        return None


def _cache_latest() -> str | None:
    """Latest version from the PyPI poll cache, or None on any error."""
    try:
        latest = cache.read().get("latest")
        return latest if isinstance(latest, str) and latest else None
    except Exception:
        return None


def resolve_latest_known() -> str | None:
    """Return the authoritative latest-known release across all signals.

    Reconciles the bundled registry high-water mark and the live PyPI cache by
    returning whichever is newer (PEP 440). Returns ``None`` only when neither
    signal yields a usable version, so callers can fall back to "version
    registry unavailable" semantics. Pure read; no side effects.
    """
    candidates = [v for v in (_registry_latest(), _cache_latest()) if v]
    if not candidates:
        return None
    best = candidates[0]
    for candidate in candidates[1:]:
        if is_newer(candidate, best):
            best = candidate
    return best
