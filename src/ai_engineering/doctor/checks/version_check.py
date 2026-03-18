"""Version lifecycle diagnostic check."""

from __future__ import annotations

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport


def check_version(report: DoctorReport) -> None:
    """Check the version lifecycle status of the installed framework.

    Reports OK for current, WARN for outdated/supported, FAIL for deprecated/eol.
    Fail-open: registry errors produce a WARN, not a FAIL.
    """
    from ai_engineering.__version__ import __version__
    from ai_engineering.version.checker import check_version as _check_ver

    result = _check_ver(__version__)

    if result.status is None:
        report.checks.append(
            CheckResult(
                name="version-lifecycle",
                status=CheckStatus.WARN,
                message=result.message,
            )
        )
    elif result.is_current:
        report.checks.append(
            CheckResult(
                name="version-lifecycle",
                status=CheckStatus.OK,
                message=result.message,
            )
        )
    elif result.is_deprecated or result.is_eol:
        report.checks.append(
            CheckResult(
                name="version-lifecycle",
                status=CheckStatus.FAIL,
                message=result.message,
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="version-lifecycle",
                status=CheckStatus.WARN,
                message=result.message,
            )
        )
