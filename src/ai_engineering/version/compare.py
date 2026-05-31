"""Canonical PEP 440 version comparison (spec-156 D-156-11).

The hand-rolled ``tuple(int(x) for x in v.split("."))`` comparators scattered
across cli_ui / checker / scope_status silently returned ``False`` for any
pre/post/dev/local or ragged version — notably ``-e``/CI dev installs and
release candidates — so the update notice never fired for those. This module is
the single source of truth: parse with :mod:`packaging.version`, treat any
``InvalidVersion`` as "not newer" (fail-open: a malformed string never nags).
"""

from __future__ import annotations

from packaging.version import InvalidVersion, Version


def is_newer(latest: str, current: str) -> bool:
    """Return True when *latest* is a strictly greater release than *current*.

    PEP 440-aware (rc/dev/post/local/ragged arity). Any unparseable input
    returns False so a malformed cache or dev-install version never nags.
    """
    try:
        return Version(latest) > Version(current)
    except (InvalidVersion, TypeError):
        return False
