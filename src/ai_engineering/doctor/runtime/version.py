"""Doctor runtime check: version -- checks framework version lifecycle status.

Compares the installed ``ai_engineering`` version against the embedded
version registry. Maps registry status to doctor CheckStatus:

- Registry unavailable -> WARN (fail-open)
- Current release      -> OK
- Deprecated / EOL     -> FAIL
- Outdated but supported -> WARN
"""

from __future__ import annotations

from ai_engineering import __version__
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.version.checker import check_version

# spec-113 D-113-13: when the lifecycle registry lookup fails for a network
# reason (DNS error, HTTP timeout, registry file missing), the result has
# ``status=None`` AND a "Version registry unavailable" / "Version <X> not
# found in registry" message. Treat both shapes as INFO -- the user does
# not have a version problem, the framework simply could not contact the
# registry. Genuine deprecation/EOL signals (real status responses) keep
# their FAIL/WARN classification.
_OFFLINE_LOOKUP_HINTS: tuple[str, ...] = (
    "registry unavailable",
    "not found in registry",
)


def _is_offline_lookup_failure(message: str) -> bool:
    """Return True when *message* indicates a network / lookup failure (D-113-13)."""
    lowered = message.lower()
    return any(hint.lower() in lowered for hint in _OFFLINE_LOOKUP_HINTS)


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Check the installed framework version against the lifecycle registry.

    spec-113 G-10 / D-113-13: registry lookup failures (offline, DNS,
    timeout, missing registry file) downgrade the result to INFO so the
    user does not see a false WARN when the lifecycle registry is just
    unreachable. Real deprecation / EOL responses retain their original
    severity.
    """
    result = check_version(__version__)

    if result.status is None:
        # Lookup failed -- distinguish offline failure from a real
        # "version not found" registry response.
        status = CheckStatus.OK if _is_offline_lookup_failure(result.message) else CheckStatus.WARN
        return [
            CheckResult(
                name="version",
                status=status,
                message=result.message,
            )
        ]

    if result.is_current:
        return [
            CheckResult(
                name="version",
                status=CheckStatus.OK,
                message=result.message,
            )
        ]

    if result.is_deprecated or result.is_eol:
        return [
            CheckResult(
                name="version",
                status=CheckStatus.FAIL,
                message=result.message,
            )
        ]

    # Outdated but still supported
    return [
        CheckResult(
            name="version",
            status=CheckStatus.WARN,
            message=result.message,
        )
    ]
