"""Unit tests for cli_envelope module."""

from __future__ import annotations

import json

import pytest

from ai_engineering.cli_envelope import (
    ErrorEnvelope,
    NextAction,
    SuccessEnvelope,
    emit_error,
    emit_success,
    truncate_list,
)

pytestmark = pytest.mark.unit


class TestNextAction:
    """Tests for the NextAction model."""

    def test_basic_action(self) -> None:
        action = NextAction(command="ai-eng doctor", description="Run diagnostics")
        assert action.command == "ai-eng doctor"
        assert action.params is None


class TestSuccessEnvelope:
    """Tests for the SuccessEnvelope model."""

    def test_ok_is_true(self) -> None:
        env = SuccessEnvelope(command="install", result={"root": "/tmp"})
        assert env.ok is True

    def test_serialises_to_valid_json(self) -> None:
        # Arrange
        env = SuccessEnvelope(
            command="install",
            result={"root": "/tmp"},
            next_actions=[NextAction(command="doctor", description="Check health")],
        )

        # Act
        data = json.loads(env.model_dump_json())

        # Assert
        assert data["ok"] is True
        assert data["result"]["root"] == "/tmp"
        assert len(data["next_actions"]) == 1


class TestErrorEnvelope:
    """Tests for the ErrorEnvelope model."""

    def test_ok_is_false(self) -> None:
        env = ErrorEnvelope(
            command="install",
            error={"message": "not found", "code": "NOT_FOUND"},
            fix="Check the path",
        )
        assert env.ok is False

    def test_serialises_to_valid_json(self) -> None:
        env = ErrorEnvelope(
            command="install",
            error={"message": "fail", "code": "ERR"},
            fix="retry",
        )
        data = json.loads(env.model_dump_json())
        assert data["ok"] is False
        assert data["fix"] == "retry"


class TestEmitFunctions:
    """Tests for emit_success and emit_error."""

    def test_emit_success_writes_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Act
        emit_success("test-cmd", {"key": "val"})
        data = json.loads(capsys.readouterr().out)

        # Assert
        assert data["ok"] is True
        assert data["command"] == "test-cmd"

    def test_emit_error_writes_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Act
        emit_error("test-cmd", "boom", "ERR_BOOM", "fix it")
        data = json.loads(capsys.readouterr().out)

        # Assert
        assert data["ok"] is False
        assert data["error"]["message"] == "boom"
        assert data["fix"] == "fix it"

    def test_emit_success_with_next_actions(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        actions = [NextAction(command="doctor", description="Run doctor")]

        # Act
        emit_success("install", {"root": "/tmp"}, actions)
        data = json.loads(capsys.readouterr().out)

        # Assert
        assert len(data["next_actions"]) == 1


class TestTruncateList:
    """Tests for the truncate_list helper."""

    def test_no_truncation_needed(self) -> None:
        result = truncate_list([1, 2, 3], max_items=5)
        assert result["items"] == [1, 2, 3]
        assert result["total"] == 3
        assert result["truncated"] is False

    def test_truncation_applied(self) -> None:
        # Act
        result = truncate_list(list(range(30)), max_items=10)

        # Assert
        assert len(result["items"]) == 10
        assert result["total"] == 30
        assert result["truncated"] is True
