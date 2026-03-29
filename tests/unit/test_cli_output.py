"""Unit tests for cli_output module."""

from __future__ import annotations

import json

import pytest

from ai_engineering.cli_output import is_json_mode, output, set_json_mode


class TestJsonModeToggle:
    """Tests for set_json_mode / is_json_mode."""

    def test_default_is_false(self) -> None:
        set_json_mode(False)
        assert is_json_mode() is False

    def test_enable_json_mode(self) -> None:
        set_json_mode(True)
        try:
            assert is_json_mode() is True
        finally:
            set_json_mode(False)


class TestOutputRouting:
    """Tests for the output() dual-mode routing function."""

    def test_json_mode_emits_envelope(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        set_json_mode(True)
        try:
            # Act
            output(
                command="test-cmd",
                result={"key": "val"},
                human_fn=lambda: None,
            )
            data = json.loads(capsys.readouterr().out)

            # Assert
            assert data["ok"] is True
            assert data["command"] == "test-cmd"
            assert data["result"]["key"] == "val"
        finally:
            set_json_mode(False)

    def test_human_mode_calls_human_fn(self) -> None:
        # Arrange
        set_json_mode(False)
        called = []

        # Act
        output(
            command="test-cmd",
            result={"key": "val"},
            human_fn=lambda: called.append(True),
        )

        # Assert
        assert called == [True]

    def test_json_mode_with_next_actions(self, capsys: pytest.CaptureFixture[str]) -> None:
        # Arrange
        from ai_engineering.cli_envelope import NextAction

        set_json_mode(True)
        try:
            # Act
            output(
                command="test-cmd",
                result={"done": True},
                next_actions=[NextAction(command="next", description="do next")],
                human_fn=lambda: None,
            )
            data = json.loads(capsys.readouterr().out)

            # Assert
            assert len(data["next_actions"]) == 1
        finally:
            set_json_mode(False)
