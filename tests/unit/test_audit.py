"""Unit tests for state.audit event emission."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.state.audit import (
    emit_build_event,
    emit_deploy_event,
    emit_guard_advisory,
    emit_guard_drift,
    emit_guard_gate,
    emit_scan_event,
)

pytestmark = pytest.mark.unit


class TestEmitScanEvent:
    """Tests for scan_complete audit emission."""

    def test_emits_scan_event(self, tmp_path: Path) -> None:
        # Arrange
        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        log_path.parent.mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.state.audit.audit_log_path",
            return_value=log_path,
        ):
            emit_scan_event(
                tmp_path,
                mode="security",
                score=85,
                findings={"high": 0, "medium": 1},
            )

        # Assert
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8")
        assert "scan_complete" in content
        assert "security" in content


class TestEmitBuildEvent:
    """Tests for build_complete audit emission."""

    def test_emits_build_event(self, tmp_path: Path) -> None:
        # Arrange
        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        log_path.parent.mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.state.audit.audit_log_path",
            return_value=log_path,
        ):
            emit_build_event(
                tmp_path,
                mode="implement",
                files_changed=3,
                lines_added=50,
            )

        # Assert
        content = log_path.read_text(encoding="utf-8")
        assert "build_complete" in content


class TestEmitDeployEvent:
    """Tests for deploy_complete audit emission."""

    def test_emits_deploy_event(self, tmp_path: Path) -> None:
        # Arrange
        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        log_path.parent.mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.state.audit.audit_log_path",
            return_value=log_path,
        ):
            emit_deploy_event(
                tmp_path,
                environment="staging",
                strategy="rolling",
                version="1.0.0",
                result="success",
            )

        # Assert
        content = log_path.read_text(encoding="utf-8")
        assert "deploy_complete" in content


class TestEmitGuardAdvisory:
    """Tests for guard_advisory audit emission."""

    def test_emits_guard_advisory(self, tmp_path: Path) -> None:
        # Arrange
        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        log_path.parent.mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.state.audit.audit_log_path",
            return_value=log_path,
        ):
            emit_guard_advisory(
                tmp_path,
                files_checked=5,
                warnings=2,
                concerns=1,
            )

        # Assert
        content = log_path.read_text(encoding="utf-8")
        assert "guard_advisory" in content
        assert '"warnings": 2' in content


class TestEmitGuardGate:
    """Tests for guard_gate audit emission."""

    def test_emits_guard_gate(self, tmp_path: Path) -> None:
        # Arrange
        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        log_path.parent.mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.state.audit.audit_log_path",
            return_value=log_path,
        ):
            emit_guard_gate(
                tmp_path,
                verdict="PASS",
                task="T1",
                agent="build",
            )

        # Assert
        content = log_path.read_text(encoding="utf-8")
        assert "guard_gate" in content
        assert "PASS" in content


class TestEmitGuardDrift:
    """Tests for guard_drift audit emission."""

    def test_emits_guard_drift(self, tmp_path: Path) -> None:
        # Arrange
        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        log_path.parent.mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.state.audit.audit_log_path",
            return_value=log_path,
        ):
            emit_guard_drift(
                tmp_path,
                decisions_checked=10,
                drifted=2,
                critical=1,
            )

        # Assert
        content = log_path.read_text(encoding="utf-8")
        assert "guard_drift" in content
        assert '"drifted": 2' in content
