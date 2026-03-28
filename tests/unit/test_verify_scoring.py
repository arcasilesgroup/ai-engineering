"""Tests for ai_engineering.verify.scoring — pure logic, ZERO mocks.

Every test follows AAA pattern (Arrange-Act-Assert) and tests BEHAVIOR,
not implementation. This is the TDD-ready (Type-E) exemplar test file.
"""

from __future__ import annotations

import pytest

from ai_engineering.verify.scoring import (
    Finding,
    FindingSeverity,
    SpecialistResult,
    Verdict,
    VerifyScore,
)

pytestmark = pytest.mark.unit


# ── VerifyScore: score calculation ────────────────────────────────────────


class TestVerifyScoreCalculation:
    def test_initial_score_is_100_with_no_findings(self) -> None:
        # Arrange
        score = VerifyScore()

        # Assert
        assert score.score == 100

    def test_score_decreases_by_20_per_blocker(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act
        score.add(FindingSeverity.BLOCKER, "secrets", "Token detected")

        # Assert
        assert score.score == 80

    def test_score_decreases_by_10_per_critical(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act
        score.add(FindingSeverity.CRITICAL, "deps", "CVE found")

        # Assert
        assert score.score == 90

    def test_score_decreases_by_5_per_major(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act
        score.add(FindingSeverity.MAJOR, "lint", "Unused import")

        # Assert
        assert score.score == 95

    def test_score_decreases_by_1_per_minor(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act
        score.add(FindingSeverity.MINOR, "style", "Long line")

        # Assert
        assert score.score == 99

    def test_info_findings_have_zero_weight(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act
        score.add(FindingSeverity.INFO, "note", "FYI")

        # Assert
        assert score.score == 100

    def test_score_caps_at_zero_not_negative(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act — add 6 blockers = 120 penalty, but score can't go below 0
        for i in range(6):
            score.add(FindingSeverity.BLOCKER, "secrets", f"Leak {i}")

        # Assert
        assert score.score == 0

    def test_multiple_severities_accumulate(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act — 1 blocker (20) + 1 critical (10) + 2 major (10) = 40
        score.add(FindingSeverity.BLOCKER, "secrets", "Token")
        score.add(FindingSeverity.CRITICAL, "deps", "CVE")
        score.add(FindingSeverity.MAJOR, "lint", "Issue 1")
        score.add(FindingSeverity.MAJOR, "lint", "Issue 2")

        # Assert
        assert score.score == 60


# ── VerifyScore: verdict thresholds ───────────────────────────────────────


class TestVerifyScoreVerdict:
    def test_verdict_pass_at_score_100(self) -> None:
        score = VerifyScore()
        assert score.verdict == Verdict.PASS

    def test_verdict_pass_at_score_90(self) -> None:
        # Arrange — 1 critical (10 penalty) → score 90
        score = VerifyScore()
        score.add(FindingSeverity.CRITICAL, "deps", "CVE")

        # Assert
        assert score.verdict == Verdict.PASS

    def test_verdict_warn_at_score_89(self) -> None:
        # Arrange — 1 critical + 1 minor = 11 penalty → score 89
        score = VerifyScore()
        score.add(FindingSeverity.CRITICAL, "deps", "CVE")
        score.add(FindingSeverity.MINOR, "style", "Issue")

        # Assert
        assert score.verdict == Verdict.WARN

    def test_verdict_warn_at_score_60(self) -> None:
        # Arrange — 8 major = 40 penalty → score 60
        score = VerifyScore()
        for i in range(8):
            score.add(FindingSeverity.MAJOR, "lint", f"Issue {i}")

        # Assert
        assert score.verdict == Verdict.WARN

    def test_verdict_fail_at_score_59(self) -> None:
        # Arrange — 1 blocker + 2 critical + 1 minor = 41 penalty → score 59
        score = VerifyScore()
        score.add(FindingSeverity.BLOCKER, "secrets", "Token")
        score.add(FindingSeverity.CRITICAL, "deps", "CVE-1")
        score.add(FindingSeverity.CRITICAL, "deps", "CVE-2")
        score.add(FindingSeverity.MINOR, "style", "Issue")

        # Assert
        assert score.verdict == Verdict.FAIL

    def test_verdict_fail_at_score_zero(self) -> None:
        score = VerifyScore()
        for i in range(6):
            score.add(FindingSeverity.BLOCKER, "secrets", f"Leak {i}")

        assert score.verdict == Verdict.FAIL


# ── VerifyScore: add and summary ──────────────────────────────────────────


class TestVerifyScoreAddAndSummary:
    def test_add_appends_finding_to_list(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act
        score.add(FindingSeverity.MAJOR, "lint", "Unused import")

        # Assert
        assert len(score.findings) == 1
        assert score.findings[0].category == "lint"
        assert score.findings[0].message == "Unused import"

    def test_add_with_file_and_line(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act
        score.add(
            FindingSeverity.MAJOR,
            "lint",
            "Unused import",
            file="foo.py",
            line=42,
        )

        # Assert
        assert score.findings[0].file == "foo.py"
        assert score.findings[0].line == 42

    def test_add_without_optional_fields_defaults_to_none(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act
        score.add(FindingSeverity.INFO, "note", "FYI")

        # Assert
        assert score.findings[0].file is None
        assert score.findings[0].line is None

    def test_summary_counts_by_severity(self) -> None:
        # Arrange
        score = VerifyScore()
        score.add(FindingSeverity.MAJOR, "lint", "Issue 1")
        score.add(FindingSeverity.MAJOR, "lint", "Issue 2")
        score.add(FindingSeverity.MINOR, "style", "Issue 3")

        # Act
        result = score.summary()

        # Assert
        assert result == {"major": 2, "minor": 1}

    def test_summary_empty_when_no_findings(self) -> None:
        # Arrange
        score = VerifyScore()

        # Act
        result = score.summary()

        # Assert
        assert result == {}

    def test_findings_for_specialist_filters_to_original_lens(self) -> None:
        # Arrange
        score = VerifyScore()
        score.add(
            FindingSeverity.BLOCKER,
            "secrets",
            "Token detected",
            specialist="security",
            runner="macro-agent-1",
        )
        score.add(
            FindingSeverity.MAJOR,
            "lint",
            "Unused import",
            specialist="quality",
            runner="macro-agent-2",
        )

        # Act
        result = score.findings_for_specialist("security")

        # Assert
        assert len(result) == 1
        assert result[0].category == "secrets"
        assert result[0].specialist == "security"


# ── Finding dataclass ─────────────────────────────────────────────────────


class TestFinding:
    def test_finding_creation_with_all_fields(self) -> None:
        finding = Finding(
            severity=FindingSeverity.BLOCKER,
            category="secrets",
            message="API key exposed",
            file="config.py",
            line=10,
        )

        assert finding.severity == FindingSeverity.BLOCKER
        assert finding.category == "secrets"
        assert finding.message == "API key exposed"
        assert finding.file == "config.py"
        assert finding.line == 10


class TestSpecialistResult:
    def test_add_sets_specialist_and_runner(self) -> None:
        specialist = SpecialistResult(name="security", label="Security", runner="macro-agent-1")

        specialist.add(FindingSeverity.BLOCKER, "secrets", "Leak detected", file="x.py", line=3)

        finding = specialist.findings[0]
        assert finding.specialist == "security"
        assert finding.runner == "macro-agent-1"

    def test_summary_counts_findings(self) -> None:
        specialist = SpecialistResult(name="quality", label="Quality", runner="macro-agent-2")
        specialist.add(FindingSeverity.MAJOR, "lint", "Issue 1")
        specialist.add(FindingSeverity.MINOR, "style", "Issue 2")

        assert specialist.summary() == {"major": 1, "minor": 1}

    def test_finding_defaults_optional_fields_to_none(self) -> None:
        finding = Finding(
            severity=FindingSeverity.INFO,
            category="note",
            message="Informational",
        )

        assert finding.file is None
        assert finding.line is None
