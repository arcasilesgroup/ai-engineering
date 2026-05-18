"""Tests for _parse_counter and IntegrityReport model.

Split from tests/unit/test_validator.py during spec-140 W2.5.T4.
"""

from __future__ import annotations

from ai_engineering.validator.service import (
    IntegrityCategory,
    IntegrityCheckResult,
    IntegrityReport,
    IntegrityStatus,
    _parse_counter,
)


class TestParseCounter:
    """Tests for _parse_counter plain-string parsing (ReDoS-safe)."""

    def test_comma_separated_objective(self) -> None:
        text = "Complete governance content: 37 skills, 9 agents."
        result = _parse_counter(text, ",")
        assert result == (37, 9)

    def test_plus_separated_kpi(self) -> None:
        text = "| Agent coverage | 37 skills + 9 agents | 37/37 |"
        result = _parse_counter(text, "+")
        assert result == (37, 9)

    def test_singular_forms(self) -> None:
        text = "1 skill, 1 agent"
        result = _parse_counter(text, ",")
        assert result == (1, 1)

    def test_no_match_returns_none(self) -> None:
        text = "No counters here at all."
        result = _parse_counter(text, ",")
        assert result is None

    def test_multiline_finds_first_match(self) -> None:
        text = "Header line\n37 skills, 9 agents\nAnother line"
        result = _parse_counter(text, ",")
        assert result == (37, 9)

    def test_empty_text(self) -> None:
        result = _parse_counter("", ",")
        assert result is None

    def test_separator_missing(self) -> None:
        text = "37 skills and 9 agents"
        result = _parse_counter(text, ",")
        assert result is None


class TestIntegrityReport:
    """Tests for IntegrityReport dataclass."""

    def test_empty_report_passes(self) -> None:
        report = IntegrityReport()
        assert report.passed is True
        assert report.summary == {}

    def test_report_with_ok_passes(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="test",
                    status=IntegrityStatus.OK,
                    message="all good",
                ),
            ]
        )
        assert report.passed is True

    def test_report_with_fail_does_not_pass(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="test",
                    status=IntegrityStatus.FAIL,
                    message="broken",
                ),
            ]
        )
        assert report.passed is False

    def test_report_with_warn_still_passes(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="test",
                    status=IntegrityStatus.WARN,
                    message="warning",
                ),
            ]
        )
        assert report.passed is True

    def test_summary_counts(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.OK,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="b",
                    status=IntegrityStatus.FAIL,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="c",
                    status=IntegrityStatus.FAIL,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.COUNTER_ACCURACY,
                    name="d",
                    status=IntegrityStatus.WARN,
                    message="",
                ),
            ]
        )
        assert report.summary == {"ok": 1, "fail": 2, "warn": 1}

    def test_by_category(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.OK,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="b",
                    status=IntegrityStatus.FAIL,
                    message="",
                ),
            ]
        )
        cats = report.by_category()
        assert IntegrityCategory.FILE_EXISTENCE in cats
        assert IntegrityCategory.MIRROR_SYNC in cats
        assert len(cats[IntegrityCategory.FILE_EXISTENCE]) == 1

    def test_category_passed(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.OK,
                    message="",
                ),
                IntegrityCheckResult(
                    category=IntegrityCategory.MIRROR_SYNC,
                    name="b",
                    status=IntegrityStatus.FAIL,
                    message="",
                ),
            ]
        )
        assert report.category_passed(IntegrityCategory.FILE_EXISTENCE) is True
        assert report.category_passed(IntegrityCategory.MIRROR_SYNC) is False

    def test_to_dict_structure(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.OK,
                    message="ok msg",
                ),
            ]
        )
        d = report.to_dict()
        assert d["passed"] is True
        assert "summary" in d
        assert "categories" in d
        assert "file-existence" in d["categories"]

    def test_to_dict_includes_file_path(self) -> None:
        report = IntegrityReport(
            checks=[
                IntegrityCheckResult(
                    category=IntegrityCategory.FILE_EXISTENCE,
                    name="a",
                    status=IntegrityStatus.FAIL,
                    message="broken",
                    file_path="some/file.md",
                ),
            ]
        )
        d = report.to_dict()
        checks = d["categories"]["file-existence"]["checks"]
        assert checks[0]["file"] == "some/file.md"
