"""Pure-data result + error types for install mechanisms (spec-101 Arch-2).

This module hosts :class:`InstallResult` and :class:`Sha256MismatchError`
extracted from :mod:`ai_engineering.installer.mechanisms` so the runtime
import cycle between :mod:`installer.user_scope_install` (publishes
``_safe_run``) and :mod:`installer.mechanisms` (consumes ``_safe_run``)
collapses to a single direction.

Before the extraction the cycle was broken with two scaffolds:

* ``TYPE_CHECKING`` forward-reference of ``InstallResult`` in
  ``user_scope_install.py``.
* Deferred local imports inside ``_check_simulate_fail`` and
  ``_check_simulate_install_ok``.

By keeping :class:`InstallResult` in this dependency-free leaf module both
``user_scope_install`` and ``mechanisms`` can import it directly without
reintroducing a cycle. The mechanisms package re-exports the symbols so
existing call sites (``from installer.mechanisms import InstallResult``)
continue to work unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = (
    "InstallResult",
    "SecurityError",
    "Sha256MismatchError",
)


@dataclass(frozen=True)
class InstallResult:
    """Structured result of a single mechanism ``install()`` call.

    Built from a ``subprocess.CompletedProcess``-shaped object: ``failed``
    is True when ``returncode != 0``; ``stderr`` carries the captured
    stderr text (empty on success). ``mechanism`` is the simple class name
    of the producing mechanism so callers can render diagnostics without
    re-introspecting; ``version`` is reserved for verify-time annotation
    and is None at install-time.
    """

    failed: bool
    stderr: str = ""
    mechanism: str = ""
    version: str | None = None


class SecurityError(RuntimeError):
    """Base class for security-relevant install-time failures.

    Distinguished from generic :class:`RuntimeError` so callers can catch
    security failures (SHA mismatch, signature mismatch, ...) without
    catching benign subprocess errors.
    """


class Sha256MismatchError(SecurityError):
    """Raised when a downloaded artifact's SHA256 does not match the pin.

    The error carries both the expected and received digests plus the
    artifact path so the operator can manually diff them. The message
    surface MUST include both digests -- the test asserts both substrings
    appear in ``str(error)`` to guarantee no silent fall-through.
    """

    def __init__(
        self,
        *,
        expected: str,
        received: str,
        path: str | Path,
    ) -> None:
        self.expected = expected
        self.received = received
        self.path = Path(path) if not isinstance(path, Path) else path
        super().__init__(
            f"SHA256 mismatch on {self.path}: expected {expected!r}, received {received!r}"
        )
