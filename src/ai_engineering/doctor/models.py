"""Data models for the doctor diagnostic subsystem (spec-071 redesign).

Phase-grouped report structure aligned with the install pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.state.models import InstallState


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
    fixable: bool = False


@dataclass(frozen=True)
class DoctorContext:
    """Shared context threaded through every doctor phase."""

    target: Path
    install_state: InstallState | None = None
    manifest_config: ManifestConfig | None = None
    fix_mode: bool = False
    dry_run: bool = False
    phase_filter: str | None = None


@dataclass
class PhaseReport:
    """Report for a single doctor phase (mirrors one install phase)."""

    name: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def status(self) -> CheckStatus:
        """Aggregate status: FAIL > WARN > OK. FIXED is treated as OK."""
        if not self.checks:
            return CheckStatus.OK
        has_fail = any(c.status == CheckStatus.FAIL for c in self.checks)
        if has_fail:
            return CheckStatus.FAIL
        has_warn = any(c.status == CheckStatus.WARN for c in self.checks)
        if has_warn:
            return CheckStatus.WARN
        return CheckStatus.OK

    def to_dict(self) -> dict[str, object]:
        """Serialize for JSON output."""
        return {
            "name": self.name,
            "status": self.status.value,
            "checks": [
                {"name": c.name, "status": c.status.value, "message": c.message}
                for c in self.checks
            ],
        }


@dataclass
class DoctorReport:
    """Phase-grouped diagnostic report."""

    installed: bool = True
    phases: list[PhaseReport] = field(default_factory=list)
    runtime: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if no FAIL status in any phase or runtime check."""
        for phase in self.phases:
            if any(c.status == CheckStatus.FAIL for c in phase.checks):
                return False
        return not any(c.status == CheckStatus.FAIL for c in self.runtime)

    @property
    def has_warnings(self) -> bool:
        """True if at least one WARN exists and no FAIL exists."""
        if not self.passed:
            return False
        all_checks = [c for p in self.phases for c in p.checks] + self.runtime
        return any(c.status == CheckStatus.WARN for c in all_checks)

    @property
    def summary(self) -> dict[str, int]:
        """Count of all checks by status."""
        counts: dict[str, int] = {}
        all_checks = [c for p in self.phases for c in p.checks] + self.runtime
        for check in all_checks:
            counts[check.status.value] = counts.get(check.status.value, 0) + 1
        return counts

    def to_dict(self) -> dict[str, object]:
        """Serialize to phase-grouped JSON schema."""
        return {
            "installed": self.installed,
            "phases": [p.to_dict() for p in self.phases],
            "runtime": [
                {"name": c.name, "status": c.status.value, "message": c.message}
                for c in self.runtime
            ],
            "summary": self.summary,
            "passed": self.passed,
        }
