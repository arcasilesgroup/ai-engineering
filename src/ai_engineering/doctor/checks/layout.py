"""Framework layout diagnostic check."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport

# Required directories under .ai-engineering/
_REQUIRED_DIRS: list[str] = [
    "context",
    "contexts",
    "state",
    "tasks",
]


def check_layout(target: Path, report: DoctorReport) -> None:
    """Check that required framework directories exist."""
    ai_eng = target / ".ai-engineering"

    if not ai_eng.is_dir():
        report.checks.append(
            CheckResult(
                name="framework-layout",
                status=CheckStatus.FAIL,
                message=".ai-engineering/ directory not found",
            )
        )
        return

    missing: list[str] = []
    for d in _REQUIRED_DIRS:
        if not (ai_eng / d).is_dir():
            missing.append(d)

    if missing:
        report.checks.append(
            CheckResult(
                name="framework-layout",
                status=CheckStatus.FAIL,
                message=f"Missing directories: {', '.join(missing)}",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="framework-layout",
                status=CheckStatus.OK,
                message="All required directories present",
            )
        )
