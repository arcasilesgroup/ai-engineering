"""Exit codes reserved by spec-101 (D-101-11).

Both values sit OUTSIDE the sysexits.h 64-78 range so they don't collide with
``ai-eng``'s pre-existing exit conventions or the platform's standard codes.

* :data:`EXIT_TOOLS_FAILED` (80) -- one or more required tools' mechanism
  ``install()`` returned ``failed=True``. The ``InstallState`` records the
  failure as ``ToolInstallState.FAILED_NEEDS_MANUAL`` so ``ai-eng doctor``
  can resume / remediate.

* :data:`EXIT_PREREQS_MISSING` (81) -- a hard prerequisite was missing or
  out-of-range BEFORE the tools phase ran. Covers (a) ``uv`` absent, (b)
  ``uv --version`` outside the manifest's ``prereqs.uv.version_range``, and
  (eventually) the 9 SDK prereqs from D-101-14.

Strict precedence: missing prereqs short-circuit BEFORE the tools phase
runs, so a project with both a missing prereq AND a broken tool surface
returns 81, never 80.
"""

from __future__ import annotations

EXIT_TOOLS_FAILED: int = 80
"""Exit code emitted when one or more required tools fail to install."""

EXIT_PREREQS_MISSING: int = 81
"""Exit code emitted when a hard prerequisite is missing or out-of-range."""


__all__ = (
    "EXIT_PREREQS_MISSING",
    "EXIT_TOOLS_FAILED",
)


class PrereqMissing(RuntimeError):
    """Raised when a hard prerequisite is missing or out-of-range.

    The CLI install flow catches this before the tools phase runs and
    surfaces :data:`EXIT_PREREQS_MISSING`.
    """


class PrereqOutOfRange(PrereqMissing):
    """Raised when a prerequisite is present but its version is out of range.

    Specialises :class:`PrereqMissing` so a single ``except PrereqMissing``
    clause handles both ``absent`` and ``out-of-range`` cases.
    """
