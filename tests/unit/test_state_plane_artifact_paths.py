"""Unit tests for HX-05 T-2.3 state-plane artifact relocation helpers."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.state.control_plane import (
    StatePlaneArtifactClass,
    resolve_state_plane_artifact_path,
    resolve_state_plane_contract,
)

_LEGACY_AUDIT_CLASSIFICATION = ".ai-engineering/state/spec-116-t31-audit-classification.json"
_CANONICAL_AUDIT_CLASSIFICATION = (
    ".ai-engineering/specs/evidence/spec-116/spec-116-t31-audit-classification.json"
)


def test_state_plane_contract_reports_canonical_path_for_legacy_spec_local_evidence() -> None:
    contract = resolve_state_plane_contract()

    assert contract.canonical_relative_path(_LEGACY_AUDIT_CLASSIFICATION) == (
        _CANONICAL_AUDIT_CLASSIFICATION
    )
    assert contract.compatibility_shim_relative_path(_CANONICAL_AUDIT_CLASSIFICATION) == (
        _LEGACY_AUDIT_CLASSIFICATION
    )
    assert (
        contract.classify(_CANONICAL_AUDIT_CLASSIFICATION)
        is StatePlaneArtifactClass.SPEC_LOCAL_EVIDENCE
    )
    assert contract.requires_compatibility_shim(_LEGACY_AUDIT_CLASSIFICATION) is True
    assert contract.requires_compatibility_shim(_CANONICAL_AUDIT_CLASSIFICATION) is False


def test_resolve_state_plane_artifact_path_prefers_canonical_relocation(tmp_path: Path) -> None:
    legacy_path = tmp_path / _LEGACY_AUDIT_CLASSIFICATION
    canonical_path = tmp_path / _CANONICAL_AUDIT_CLASSIFICATION
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text('{"source": "legacy"}\n', encoding="utf-8")
    canonical_path.write_text('{"source": "canonical"}\n', encoding="utf-8")

    resolved = resolve_state_plane_artifact_path(tmp_path, _LEGACY_AUDIT_CLASSIFICATION)

    assert resolved == canonical_path
    assert resolved.read_text(encoding="utf-8") == '{"source": "canonical"}\n'


def test_resolve_state_plane_artifact_path_stays_canonical_after_cutover(tmp_path: Path) -> None:
    legacy_path = tmp_path / _LEGACY_AUDIT_CLASSIFICATION
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text('{"source": "legacy"}\n', encoding="utf-8")

    resolved = resolve_state_plane_artifact_path(tmp_path, _LEGACY_AUDIT_CLASSIFICATION)

    assert resolved == tmp_path / _CANONICAL_AUDIT_CLASSIFICATION
    assert resolved.exists() is False
