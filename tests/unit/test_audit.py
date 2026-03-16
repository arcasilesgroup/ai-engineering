"""Unit tests for state.audit event emission."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.state.audit import (
    emit_build_event,
    emit_deploy_event,
    emit_scan_event,
    emit_session_event,
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


class TestEmitSessionEvent:
    """Tests for session_metric audit emission."""

    def test_emits_session_event(self, tmp_path: Path) -> None:
        # Arrange
        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        log_path.parent.mkdir(parents=True)

        # Act
        with patch(
            "ai_engineering.state.audit.audit_log_path",
            return_value=log_path,
        ):
            emit_session_event(
                tmp_path,
                tokens_used=5000,
                skills_loaded=["build", "test"],
            )

        # Assert
        content = log_path.read_text(encoding="utf-8")
        assert "session_metric" in content
