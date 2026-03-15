"""Scoring engine for verify reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Verdict(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class FindingSeverity(StrEnum):
    BLOCKER = "blocker"
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    INFO = "info"


@dataclass
class Finding:
    severity: FindingSeverity
    category: str
    message: str
    file: str | None = None
    line: int | None = None


@dataclass
class VerifyScore:
    raw: int = 100
    findings: list[Finding] = field(default_factory=list)

    WEIGHTS: dict[FindingSeverity, int] = field(
        default_factory=lambda: {
            FindingSeverity.BLOCKER: 20,
            FindingSeverity.CRITICAL: 10,
            FindingSeverity.MAJOR: 5,
            FindingSeverity.MINOR: 1,
            FindingSeverity.INFO: 0,
        },
        init=False,
        repr=False,
    )

    @property
    def score(self) -> int:
        penalty = sum(self.WEIGHTS[f.severity] for f in self.findings)
        return max(0, self.raw - penalty)

    @property
    def verdict(self) -> Verdict:
        if self.score >= 90:
            return Verdict.PASS
        if self.score >= 60:
            return Verdict.WARN
        return Verdict.FAIL

    def add(
        self,
        severity: FindingSeverity,
        category: str,
        message: str,
        *,
        file: str | None = None,
        line: int | None = None,
    ) -> None:
        self.findings.append(
            Finding(
                severity=severity,
                category=category,
                message=message,
                file=file,
                line=line,
            )
        )

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for f in self.findings:
            counts[f.severity.value] = counts.get(f.severity.value, 0) + 1
        return counts
