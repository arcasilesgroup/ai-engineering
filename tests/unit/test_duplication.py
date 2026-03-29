"""Tests for duplication checker module — ratio calculation and CLI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ai_engineering.policy import duplication
from ai_engineering.policy.duplication import _duplication_ratio


class TestDuplicationRatio:
    def test_zero_ratio_for_unique_content(self, tmp_path: Path) -> None:
        # Arrange
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("\n".join(f"line_{i}" for i in range(20)), encoding="utf-8")

        # Act
        ratio, duplicates, total = _duplication_ratio(src)

        # Assert
        assert total > 0
        assert duplicates == 0
        assert ratio == 0.0

    def test_detects_repeated_blocks(self, tmp_path: Path) -> None:
        # Arrange
        src = tmp_path / "src"
        src.mkdir()
        block = "\n".join(["value = 1", "value += 1", "value += 2", "value += 3"] * 3)
        (src / "a.py").write_text(block, encoding="utf-8")
        (src / "b.py").write_text(block, encoding="utf-8")

        # Act
        ratio, duplicates, total = _duplication_ratio(src)

        # Assert
        assert total > 0
        assert duplicates > 0
        assert ratio > 0

    def test_window_hashes_returns_empty_for_short_input(self) -> None:
        # Act
        result = duplication._window_hashes(["a", "b"], width=8)

        # Assert
        assert result == []


class TestDuplicationMain:
    def test_main_exits_zero_below_threshold(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("\n".join(f"v{i}=1" for i in range(20)), encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["dup", "--path", str(src), "--threshold", "100"])

        # Act
        exit_code = duplication.main()

        # Assert
        assert exit_code == 0

    def test_main_exits_one_above_threshold(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange
        src = tmp_path / "src"
        src.mkdir()
        block = "\n".join(["x=1", "x+=1", "x+=2", "x+=3"] * 3)
        (src / "b.py").write_text(block, encoding="utf-8")
        (src / "c.py").write_text(block, encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["dup", "--path", str(src), "--threshold", "0"])

        # Act
        exit_code = duplication.main()

        # Assert
        assert exit_code == 1
