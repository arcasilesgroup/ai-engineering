"""Tests for Category 1: File Existence validation.

Split from tests/unit/test_validator.py during spec-140 W2.5.T4.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering.validator.service import (
    IntegrityCategory,
    IntegrityStatus,
    validate_content_integrity,
)

from .conftest import (
    _make_governance,
    _setup_full_project,
    _write_active_spec,
    _write_source_repo_control_plane_files,
    _write_source_repo_markers,
)


class TestFileExistence:
    """Tests for file-existence validation."""

    def test_missing_governance_directory(self, tmp_path: Path) -> None:
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        assert report.passed is False
        assert any(c.name == "governance-directory" for c in report.checks)

    def test_all_references_resolve(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        assert report.category_passed(IntegrityCategory.FILE_EXISTENCE)

    def test_broken_reference_detected(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        # spec-136 D-136-01: reference/ is the framework reference home.
        doc = ai / "reference" / "broken.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            "# Broken\n\nSee `skills/nonexistent/phantom.md` for details.\n",
            encoding="utf-8",
        )
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        fail_checks = [
            c
            for c in report.checks
            if c.category == IntegrityCategory.FILE_EXISTENCE and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) >= 1

    def test_legacy_state_plane_reference_requires_canonical_path(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        legacy_path = ai / "state" / "spec-116-t31-audit-classification.json"
        canonical_path = (
            ai / "specs" / "evidence" / "spec-116" / "spec-116-t31-audit-classification.json"
        )
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text('{"source": "legacy"}\n', encoding="utf-8")
        canonical_path.write_text('{"source": "canonical"}\n', encoding="utf-8")

        doc = ai / "reference" / "legacy-state-plane.md"
        doc.parent.mkdir(parents=True, exist_ok=True)
        doc.write_text(
            "# Legacy State Plane\n\n"
            "See `state/spec-116-t31-audit-classification.json` for details.\n",
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.category == IntegrityCategory.FILE_EXISTENCE and c.status == IntegrityStatus.FAIL
        ]
        assert any(
            c.name == "legacy-state-plane-reference"
            and "state/spec-116-t31-audit-classification.json" in c.message
            and "specs/evidence/spec-116/spec-116-t31-audit-classification.json" in c.message
            for c in fail_checks
        )

    def test_spec_buffer_completeness(self, tmp_path: Path) -> None:
        """Missing spec buffer files (spec.md or plan.md) are flagged."""
        ai = _setup_full_project(tmp_path)
        # Remove plan.md to trigger failure
        (ai / "specs" / "plan.md").unlink()
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        fail_checks = [
            c for c in report.checks if c.name == "spec-buffer" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "plan.md" in fail_checks[0].message

    def test_spec_buffer_present_passes(self, tmp_path: Path) -> None:
        """Complete spec buffer files (spec.md + plan.md) pass validation."""
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )
        ok_checks = [
            c for c in report.checks if c.name == "spec-buffer" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_spec_buffer_uses_resolved_work_plane_paths(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Spec-123: dead work-plane artifacts (task-ledger.json,
        # current-summary.md, history-summary.md, handoffs/, evidence/)
        # were removed. Spec buffer is now the canonical three-file
        # contract: spec.md, plan.md, _history.md.
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "spec.md").unlink()
        (ai / "specs" / "plan.md").unlink()
        (ai / "specs" / "_history.md").unlink()

        resolved_specs_dir = tmp_path / "resolved-work-plane"
        resolved_specs_dir.mkdir()
        resolved_spec = resolved_specs_dir / "spec.md"
        resolved_plan = resolved_specs_dir / "plan.md"
        resolved_history = resolved_specs_dir / "_history.md"
        resolved_spec.write_text("# Spec\n", encoding="utf-8")
        resolved_plan.write_text("# Plan\n", encoding="utf-8")
        resolved_history.write_text("# History\n", encoding="utf-8")

        monkeypatch.setattr(
            "ai_engineering.validator.categories.file_existence.resolve_active_work_plane",
            lambda _root: SimpleNamespace(
                project_root=tmp_path,
                specs_dir=resolved_specs_dir,
                spec_path=resolved_spec,
                plan_path=resolved_plan,
                history_path=resolved_history,
            ),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )

        ok_checks = [
            c for c in report.checks if c.name == "spec-buffer" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_control_plane_paths_present_pass(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_source_repo_control_plane_files(tmp_path, ai)
        _write_active_spec(ai)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "control-plane-paths" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_missing_project_constitution_template_fails(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_source_repo_control_plane_files(tmp_path, ai)
        _write_active_spec(ai)
        (tmp_path / "src" / "ai_engineering" / "templates" / "project" / "CONSTITUTION.md").unlink()

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.FILE_EXISTENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "control-plane-paths" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "src/ai_engineering/templates/project/CONSTITUTION.md" in fail_checks[0].message
