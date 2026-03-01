"""Unit tests for paths module."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.paths import ai_engineering_dir, resolve_project_root, state_dir

pytestmark = pytest.mark.unit


class TestResolveProjectRoot:
    """Tests for resolve_project_root."""

    def test_returns_cwd_when_none(self) -> None:
        root = resolve_project_root(None)
        assert root == Path.cwd().resolve()

    def test_returns_explicit_path(self, tmp_path: Path) -> None:
        root = resolve_project_root(tmp_path)
        assert root == tmp_path.resolve()

    def test_raises_on_missing_dir(self, tmp_path: Path) -> None:
        bad_path = tmp_path / "nonexistent"
        with pytest.raises(FileNotFoundError, match="Project root not found"):
            resolve_project_root(bad_path)


class TestAiEngineeringDir:
    """Tests for ai_engineering_dir."""

    def test_returns_ai_engineering_subdir(self, tmp_path: Path) -> None:
        result = ai_engineering_dir(tmp_path)
        assert result == tmp_path / ".ai-engineering"


class TestStateDir:
    """Tests for state_dir."""

    def test_returns_state_subdir(self, tmp_path: Path) -> None:
        result = state_dir(tmp_path)
        assert result == tmp_path / ".ai-engineering" / "state"
