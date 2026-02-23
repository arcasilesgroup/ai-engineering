"""Tests for duplication checker module."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.policy.duplication import _duplication_ratio


def test_duplication_ratio_zero_for_unique_content(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("\n".join(f"line_{i}" for i in range(20)), encoding="utf-8")
    ratio, duplicates, total = _duplication_ratio(src)
    assert total > 0
    assert duplicates == 0
    assert ratio == 0.0


def test_duplication_ratio_detects_repeated_blocks(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    block = "\n".join(["value = 1", "value += 1", "value += 2", "value += 3"] * 3)
    (src / "a.py").write_text(block, encoding="utf-8")
    (src / "b.py").write_text(block, encoding="utf-8")
    ratio, duplicates, total = _duplication_ratio(src)
    assert total > 0
    assert duplicates > 0
    assert ratio > 0
