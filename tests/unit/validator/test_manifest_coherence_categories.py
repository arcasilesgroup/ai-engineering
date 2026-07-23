"""Tests for Category 5: Manifest Coherence.

Split from tests/unit/test_validator.py during spec-140 W2.5.T4.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ai_engineering.config.loader import load_manifest_root_entry_points
from ai_engineering.state.defaults import default_ownership_map
from ai_engineering.state.io import write_json_model
from ai_engineering.state.observability import write_framework_capabilities
from skill_app.lint_service import (
    IntegrityCategory,
    IntegrityStatus,
    validate_content_integrity,
)

from .conftest import (
    _make_governance,
    _setup_full_project,
    _source_repo_manifest_text,
    _write_active_spec,
    _write_manifest,
    _write_source_repo_markers,
)


class TestManifestCoherence:
    """Tests for manifest-coherence validation."""

    def test_complete_manifest_passes(self, tmp_path: Path) -> None:
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    def test_missing_manifest_fails(self, tmp_path: Path) -> None:
        _make_governance(tmp_path)
        _write_active_spec(tmp_path / ".ai-engineering")
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    def test_active_spec_valid(self, tmp_path: Path) -> None:
        # Spec-123: task-ledger validation no longer emits checks; only the
        # active-spec OK signal remains for valid spec.md/plan.md content.
        _setup_full_project(tmp_path)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        ok_checks = [
            c for c in report.checks if c.name == "active-spec" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

        # Task-ledger checks are no longer emitted post-spec-123.
        ledger_checks = [c for c in report.checks if c.name == "active-task-ledger"]
        assert ledger_checks == []

    def test_active_spec_plan_declared_identity_mismatch_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "spec.md").write_text(
            "---\nspec: spec-117-hx-02\n---\n\n# HX-02 Work Plane\n",
            encoding="utf-8",
        )
        (ai / "specs" / "plan.md").write_text(
            "---\ntotal: 1\ncompleted: 0\n---\n\n# Plan: spec-117-hx-06 Other Work\n",
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-plan-coherence" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "spec-117-hx-02" in fail_checks[0].message
        assert "spec-117-hx-06" in fail_checks[0].message
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE) is False

    def test_active_spec_missing_plan_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "plan.md").unlink()

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-plan-coherence" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "without specs/plan.md" in fail_checks[0].message

    def test_active_spec_idle_plan_placeholder_fails(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "plan.md").write_text(
            "# No active plan\n\nRun /ai-plan.\n",
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-plan-coherence" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
        assert "idle placeholder" in fail_checks[0].message

    def test_active_spec_plan_declared_identity_match_passes(self, tmp_path: Path) -> None:
        ai = _setup_full_project(tmp_path)
        (ai / "specs" / "spec.md").write_text(
            "---\nspec: spec-117-hx-02\n---\n\n# HX-02 Work Plane\n",
            encoding="utf-8",
        )
        (ai / "specs" / "plan.md").write_text(
            "---\ntotal: 1\ncompleted: 0\n---\n\n# Plan: spec-117-hx-02 Work Plane\n",
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "active-spec-plan-coherence" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1
        assert report.category_passed(IntegrityCategory.MANIFEST_COHERENCE)

    def test_missing_ownership_directory(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_manifest(ai)
        # spec-136 D-136-01: contexts/ retired; the validator now polices
        # reference/ as the canonical framework-owned directory.
        shutil.rmtree(ai / "reference")
        _write_active_spec(ai)
        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )
        fail_checks = [
            c for c in report.checks if c.status == IntegrityStatus.FAIL and "reference" in c.name
        ]
        assert len(fail_checks) >= 1

    def test_source_repo_ownership_snapshot_matches_default_contract(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        # spec-133: framework_defaults injects ownership.root_entry_points;
        # mirror the validator's resolution path so the snapshot matches.
        entry_points = load_manifest_root_entry_points(tmp_path)
        write_json_model(
            ai / "state" / "ownership-map.json",
            default_ownership_map(root_entry_points=entry_points),
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "ownership-map-snapshot" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_ownership_snapshot_drift_fails(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        drifted = default_ownership_map()
        drifted.paths = []
        write_json_model(ai / "state" / "ownership-map.json", drifted)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "ownership-map-snapshot" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_source_repo_framework_capabilities_snapshot_matches_builder(
        self, tmp_path: Path
    ) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        write_framework_capabilities(tmp_path)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "framework-capabilities-snapshot" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_framework_capabilities_snapshot_drift_fails(self, tmp_path: Path) -> None:
        """Spec-125 cutover: drift is induced by mutating the state.db
        ``tool_capabilities`` row directly (the legacy JSON sink is
        forbidden). The validator reads the catalog from state.db so
        the snapshot check picks up the divergence.
        """
        from ai_engineering.state.repository import DurableStateRepository

        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        drifted = write_framework_capabilities(tmp_path)
        drifted.context_classes = drifted.context_classes[:-1]
        DurableStateRepository(tmp_path).save_framework_capabilities(drifted)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "framework-capabilities-snapshot" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1

    def test_source_repo_control_plane_authority_contract_passes(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        write_json_model(ai / "state" / "ownership-map.json", default_ownership_map())
        write_framework_capabilities(tmp_path)

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        ok_checks = [
            c
            for c in report.checks
            if c.name == "control-plane-authority-contract" and c.status == IntegrityStatus.OK
        ]
        assert len(ok_checks) == 1

    def test_source_repo_control_plane_authority_contract_drift_fails(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_source_repo_markers(tmp_path, ai)
        _write_active_spec(ai)
        write_json_model(ai / "state" / "ownership-map.json", default_ownership_map())
        write_framework_capabilities(tmp_path)

        template_manifest = (
            tmp_path / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "manifest.yml"
        )
        template_manifest.write_text(
            _source_repo_manifest_text().replace(
                "    - CONSTITUTION.md\n",
                "    - .ai-engineering/CONSTITUTION.md\n",
            ),
            encoding="utf-8",
        )

        report = validate_content_integrity(
            tmp_path,
            categories=[IntegrityCategory.MANIFEST_COHERENCE],
        )

        fail_checks = [
            c
            for c in report.checks
            if c.name == "control-plane-authority-contract" and c.status == IntegrityStatus.FAIL
        ]
        assert len(fail_checks) == 1
