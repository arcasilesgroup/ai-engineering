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


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Check the installed framework version against the lifecycle registry."""
    result = check_version(__version__)

    if result.status is None:
        return [
            CheckResult(
                name="version",
                status=CheckStatus.WARN,
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
