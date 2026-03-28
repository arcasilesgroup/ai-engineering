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
    specialist: str | None = None
    runner: str | None = None


@dataclass
class SpecialistResult:
    """Evidence-backed output for one verify specialist."""

    name: str
    label: str
    runner: str
    applicable: bool = True
    rationale: str = ""
    findings: list[Finding] = field(default_factory=list)

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
                specialist=self.name,
                runner=self.runner,
            )
        )

    @property
    def score(self) -> int:
        score = VerifyScore()
        score.findings.extend(self.findings)
        return score.score

    @property
    def verdict(self) -> Verdict:
        score = VerifyScore()
        score.findings.extend(self.findings)
        return score.verdict

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.severity.value] = counts.get(finding.severity.value, 0) + 1
        return counts


@dataclass
class VerifyScore:
    raw: int = 100
    findings: list[Finding] = field(default_factory=list)
    specialists: list[SpecialistResult] = field(default_factory=list)
    mode: str = "platform"
    profile: str = "normal"

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
        penalty = sum(self.WEIGHTS[finding.severity] for finding in self.findings)
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
        specialist: str | None = None,
        runner: str | None = None,
    ) -> None:
        self.findings.append(
            Finding(
                severity=severity,
                category=category,
                message=message,
                file=file,
                line=line,
                specialist=specialist,
                runner=runner,
            )
        )

    def include_specialist(self, specialist: SpecialistResult) -> None:
        self.specialists.append(specialist)
        self.findings.extend(specialist.findings)

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.severity.value] = counts.get(finding.severity.value, 0) + 1
        return counts

    def findings_for_specialist(self, specialist: str) -> list[Finding]:
        return [finding for finding in self.findings if finding.specialist == specialist]
