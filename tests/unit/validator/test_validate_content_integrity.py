"""Tests for the validate_content_integrity entry-point.

Split from tests/unit/test_validator.py during spec-140 W2.5.T4.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator.service import (
    IntegrityCategory,
    validate_content_integrity,
)

from .conftest import _setup_full_project


class TestValidateContentIntegrity:
    """Tests for the main validate_content_integrity entry point."""

    def test_all_categories_checked_by_default(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(tmp_path)
        cats_found = {c.category for c in report.checks}
        assert IntegrityCategory.FILE_EXISTENCE in cats_found
        assert IntegrityCategory.COUNTER_ACCURACY in cats_found
        assert IntegrityCategory.MANIFEST_COHERENCE in cats_found

    def test_category_filter_limits_checks(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        cats = {c.category for c in report.checks}
        assert cats == {IntegrityCategory.FILE_EXISTENCE}

    def test_to_dict_roundtrip(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "passed" in d
        assert "categories" in d
        assert isinstance(d["categories"], dict)
