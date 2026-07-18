"""Tests for HX-12 engineering standards and legacy retirement governance."""

from __future__ import annotations

from dataclasses import replace

import pytest

from ai_engineering.standards import (
    EngineeringStandard,
    LegacyRetirementStatus,
    build_engineering_standards_matrix,
    build_legacy_retirement_manifest,
    standards_for_review_lens,
    standards_for_verify_mode,
    validate_engineering_standards_matrix,
    validate_legacy_retirement_manifest,
)


def test_standards_matrix_covers_required_standards_and_consumers() -> None:
    matrix = build_engineering_standards_matrix()

    validate_engineering_standards_matrix(matrix)

    assert {entry.standard for entry in matrix} == set(EngineeringStandard)
    assert all(entry.canonical_refs for entry in matrix)
    assert EngineeringStandard.HARNESS_ENGINEERING in standards_for_review_lens("architecture")
    assert EngineeringStandard.TDD in standards_for_review_lens("testing")
    assert EngineeringStandard.SDD in standards_for_verify_mode("governance")
    assert EngineeringStandard.HARNESS_ENGINEERING in standards_for_verify_mode("platform")


def test_legacy_retirement_manifest_is_family_by_family_and_parity_first() -> None:
    manifest = build_legacy_retirement_manifest()

    validate_legacy_retirement_manifest(manifest)

    assert len(manifest) >= 5
    assert [entry.sequence for entry in manifest] == sorted(entry.sequence for entry in manifest)
    assert all(entry.replacement_owner for entry in manifest)
    assert all(entry.parity_proofs for entry in manifest)
    assert all(entry.rollback for entry in manifest)
    assert all(not entry.delete_allowed for entry in manifest)
    assert {entry.status for entry in manifest} >= {
        LegacyRetirementStatus.PRESERVED,
        LegacyRetirementStatus.BLOCKED,
    }


def test_legacy_retirement_validation_rejects_unsafe_deletion() -> None:
    family = build_legacy_retirement_manifest()[0]
    unsafe = replace(family, delete_allowed=True, parity_proofs=())

    with pytest.raises(ValueError, match="parity proof"):
        validate_legacy_retirement_manifest((unsafe,))


def test_legacy_retirement_validation_rejects_deletion_before_ready_status() -> None:
    # Find a family whose status is not READY or RETIRED so the validation triggers.
    candidate = next(
        entry
        for entry in build_legacy_retirement_manifest()
        if entry.status not in {LegacyRetirementStatus.READY, LegacyRetirementStatus.RETIRED}
    )
    unsafe = replace(candidate, delete_allowed=True)

    with pytest.raises(ValueError, match="READY or RETIRED"):
        validate_legacy_retirement_manifest((unsafe,))
