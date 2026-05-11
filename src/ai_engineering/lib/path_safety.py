"""Path-traversal sanitiser shared across the framework (spec-128 sub-d).

Centralises the CWE-22 / SonarCloud S2083 mitigation that previously lived
inline in ``installer/merge.py`` and ``updater/service.py``. Both call
sites validate that a candidate destination resolves *within* a trusted
base directory before opening it for write.

Two surfaces are exposed:

* :func:`safe_realpath_within` — returns the validated absolute path as a
  ``str``. This is the SonarCloud-recognised shape (``os.path.realpath`` +
  string prefix check with ``os.sep``); downstream I/O uses the returned
  string directly so taint propagation collapses on the sanitised value.
* :func:`safe_resolve_within` — same guarantee with a ``Path`` return for
  callers that prefer pathlib semantics. The internal implementation
  delegates to :func:`safe_realpath_within` so both surfaces share a
  single sanitiser.

Both functions raise :class:`PathTraversalError` (subclass of ``ValueError``
for backwards compatibility with callers that already except ``ValueError``)
when the candidate resolves outside the base.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ("PathTraversalError", "safe_realpath_within", "safe_resolve_within")


class PathTraversalError(ValueError):
    """Raised when a candidate path escapes its trusted base directory.

    Inherits from :class:`ValueError` so legacy ``except ValueError``
    blocks in callers keep behaving as before.
    """


def safe_realpath_within(candidate: os.PathLike[str] | str, base: os.PathLike[str] | str) -> str:
    """Validate that ``candidate`` resolves inside ``base`` and return the realpath.

    Uses ``os.path.realpath`` (resolves symlinks) plus a string prefix
    check on ``os.sep`` so SonarCloud's taint analyser recognises the
    sanitisation. The returned value is the absolute string path —
    callers should pass that string to subsequent file I/O instead of
    re-deriving a ``Path`` from ``candidate``, otherwise the taint
    cleanup is lost.

    Args:
        candidate: The path to validate.
        base: The trusted root directory.

    Returns:
        The realpath of ``candidate`` as a string.

    Raises:
        PathTraversalError: If ``candidate`` resolves outside ``base``.
    """
    real_base = os.path.realpath(base)
    real_candidate = os.path.realpath(candidate)
    if real_candidate != real_base and not real_candidate.startswith(real_base + os.sep):
        raise PathTraversalError(
            f"Path traversal rejected: {os.fspath(candidate)!r} resolves outside "
            f"trusted base {os.fspath(base)!r}"
        )
    return real_candidate


def safe_resolve_within(candidate: os.PathLike[str] | str, base: os.PathLike[str] | str) -> Path:
    """Pathlib variant of :func:`safe_realpath_within`.

    Returns the validated absolute ``Path``. Internally delegates to
    :func:`safe_realpath_within` so both surfaces share the same
    sanitiser shape that SonarCloud recognises.

    Args:
        candidate: The path to validate.
        base: The trusted root directory.

    Returns:
        The realpath of ``candidate`` as a ``Path``.

    Raises:
        PathTraversalError: If ``candidate`` resolves outside ``base``.
    """
    return Path(safe_realpath_within(candidate, base))
