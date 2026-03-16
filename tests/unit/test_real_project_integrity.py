"""Validate the REAL project's content integrity.

These tests run the validator service against the actual .ai-engineering/
directory in the repo — NOT against tmp_path fixtures. If governance files
are missing, mirrors are out of sync, or counts don't match, these tests FAIL.

This is the "canary test" — it breaks immediately when the architecture
changes without updating all mirrors and instruction files.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.validator._shared import IntegrityCategory, IntegrityStatus
from ai_engineering.validator.service import validate_content_integrity

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _has_governance_dir() -> bool:
    return (_PROJECT_ROOT / ".ai-engineering").is_dir()


def _run_category(category: IntegrityCategory) -> list[str]:
    """Run a single integrity category and return failure messages."""
    report = validate_content_integrity(
        _PROJECT_ROOT,
        categories=[category],
    )
    return [f"{c.category}: {c.message}" for c in report.checks if c.status == IntegrityStatus.FAIL]


@pytest.mark.skipif(not _has_governance_dir(), reason="No .ai-engineering/ in project")
class TestRealProjectIntegrity:
    """Run content integrity checks against the actual repo."""

    def test_file_existence(self) -> None:
        """All internal path references in governance docs resolve to files."""
        failures = _run_category(IntegrityCategory.FILE_EXISTENCE)
        assert not failures, "File existence failures:\n" + "\n".join(f"  {f}" for f in failures)

    def test_counter_accuracy(self) -> None:
        """Skill/agent counts are consistent across instruction files."""
        failures = _run_category(IntegrityCategory.COUNTER_ACCURACY)
        assert not failures, "Counter accuracy failures:\n" + "\n".join(f"  {f}" for f in failures)

    def test_manifest_coherence(self) -> None:
        """Manifest governance_surface matches filesystem reality."""
        failures = _run_category(IntegrityCategory.MANIFEST_COHERENCE)
        assert not failures, "Manifest coherence failures:\n" + "\n".join(
            f"  {f}" for f in failures
        )

    def test_skill_frontmatter(self) -> None:
        """All skill SKILL.md files have valid YAML frontmatter."""
        failures = _run_category(IntegrityCategory.SKILL_FRONTMATTER)
        assert not failures, "Skill frontmatter failures:\n" + "\n".join(f"  {f}" for f in failures)

    def test_cross_references(self) -> None:
        """Bidirectional references between skills and agents are valid."""
        failures = _run_category(IntegrityCategory.CROSS_REFERENCE)
        assert not failures, "Cross-reference failures:\n" + "\n".join(f"  {f}" for f in failures)

    def test_all_categories_pass(self) -> None:
        """All 7 integrity categories pass together."""
        report = validate_content_integrity(_PROJECT_ROOT)
        assert report.passed, f"Integrity check failed: {report.summary}\n" + "\n".join(
            f"  [{c.status.value}] {c.category}: {c.message}"
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
        )
