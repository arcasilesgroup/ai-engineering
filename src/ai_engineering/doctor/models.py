"""Data models for the doctor diagnostic subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CheckStatus(StrEnum):
    """Status of a single diagnostic check."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"
    FIXED = "fixed"


@dataclass
class CheckResult:
    """Result of a single diagnostic check."""

    name: str
    status: CheckStatus
    message: str


@dataclass
class DoctorReport:
    """Aggregated report from all diagnostic checks."""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no checks failed."""
        return all(c.status != CheckStatus.FAIL for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        """True if at least one WARN exists and no FAIL exists."""
        has_warn = any(c.status == CheckStatus.WARN for c in self.checks)
        has_fail = any(c.status == CheckStatus.FAIL for c in self.checks)
        return has_warn and not has_fail

    @property
    def summary(self) -> dict[str, int]:
        """Count of checks by status."""
        counts: dict[str, int] = {}
        for check in self.checks:
            counts[check.status.value] = counts.get(check.status.value, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        """Serialize report for JSON output."""
        return {
            "passed": self.passed,
            "summary": self.summary,
            "checks": [
                {"name": c.name, "status": c.status.value, "message": c.message}
                for c in self.checks
            ],
        }
