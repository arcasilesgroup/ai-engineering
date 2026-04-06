"""RED tests for the shared remediation contract in spec-102 Phase 4."""

from __future__ import annotations

import importlib

import pytest


def test_remediation_status_vocabulary_matches_spec102_contract() -> None:
    remediation = importlib.import_module("ai_engineering.doctor.remediation")

    assert remediation.RemediationStatus.REPAIRED.value == "repaired"
    assert remediation.RemediationStatus.MANUAL.value == "manual"
    assert remediation.RemediationStatus.BLOCKED.value == "blocked"
    assert remediation.RemediationStatus.NOT_APPLICABLE.value == "not-applicable"


@pytest.mark.parametrize("surface", ["install", "doctor --fix"])
def test_packaging_drift_uses_shared_repaired_result_for_install_and_doctor(
    surface: str,
) -> None:
    remediation = importlib.import_module("ai_engineering.doctor.remediation")
    attempts: list[tuple[str, str]] = []

    engine = remediation.RemediationEngine(
        packaging_repair=lambda detail, *, source: attempts.append((source, detail)) or True,
    )

    result = engine.remediate_packaging_drift(
        "typer requires click>=8.2.1 but found 8.1.8",
        source=surface,
    )

    assert attempts == [(surface, "typer requires click>=8.2.1 but found 8.1.8")]
    assert isinstance(result, remediation.RemediationResult)
    assert result.source == surface
    assert result.category == remediation.FailureCategory.PACKAGING
    assert result.status == remediation.RemediationStatus.REPAIRED
    assert result.repaired_items == ["framework-runtime"]
    assert result.remaining_items == []
    assert result.manual_steps == []


def test_packaging_drift_returns_not_applicable_when_no_detail_is_present() -> None:
    remediation = importlib.import_module("ai_engineering.doctor.remediation")

    engine = remediation.RemediationEngine()
    result = engine.remediate_packaging_drift("", source="doctor --fix")

    assert result.category == remediation.FailureCategory.PACKAGING
    assert result.status == remediation.RemediationStatus.NOT_APPLICABLE
    assert result.repaired_items == []
    assert result.remaining_items == []


def test_missing_tools_returns_manual_when_capability_matrix_disallows_auto_install() -> None:
    remediation = importlib.import_module("ai_engineering.doctor.remediation")

    engine = remediation.RemediationEngine(
        tool_capability=lambda tool: tool != "semgrep",
        tool_installer=lambda tool: True,
        tool_manual_step=lambda tool: f"Install `{tool}` manually for this platform",
    )

    result = engine.remediate_missing_tools(["semgrep"], source="install")

    assert result.category == remediation.FailureCategory.TOOLS
    assert result.status == remediation.RemediationStatus.MANUAL
    assert result.repaired_items == []
    assert result.remaining_items == ["semgrep"]
    assert result.manual_steps == ["Install `semgrep` manually for this platform"]


def test_missing_tools_returns_blocked_when_auto_install_attempt_raises() -> None:
    remediation = importlib.import_module("ai_engineering.doctor.remediation")

    def _raise_install_error(tool: str) -> bool:
        raise RuntimeError(f"installer failed for {tool}")

    engine = remediation.RemediationEngine(
        tool_capability=lambda tool: True,
        tool_installer=_raise_install_error,
    )

    result = engine.remediate_missing_tools(["ruff"], source="doctor --fix")

    assert result.category == remediation.FailureCategory.TOOLS
    assert result.status == remediation.RemediationStatus.BLOCKED
    assert result.repaired_items == []
    assert result.remaining_items == ["ruff"]
    assert "installer failed for ruff" in result.detail
