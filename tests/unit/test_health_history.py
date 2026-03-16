"""Tests for health history persistence and direction indicator."""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.lib.signals import (
    _MAX_HISTORY_ENTRIES,
    health_direction,
    load_health_history,
    save_health_snapshot,
)


class TestSaveHealthSnapshot:
    def test_creates_file_if_missing(self, tmp_path: Path) -> None:
        # Arrange
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)

        # Act
        save_health_snapshot(tmp_path, 75, "YELLOW", {"gate": 80.0})

        # Assert
        path = state_dir / "health-history.json"
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert len(data["entries"]) == 1
        assert data["entries"][0]["overall"] == 75
        assert data["entries"][0]["semaphore"] == "YELLOW"
        assert data["entries"][0]["components"]["gate"] == 80.0

    def test_appends_to_existing(self, tmp_path: Path) -> None:
        # Arrange
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        existing = {
            "entries": [
                {"date": "2026-03-01", "overall": 60, "semaphore": "YELLOW", "components": {}},
            ]
        }
        (state_dir / "health-history.json").write_text(json.dumps(existing), encoding="utf-8")

        # Act
        save_health_snapshot(tmp_path, 70, "YELLOW", {"gate": 85.0})

        # Assert
        data = json.loads((state_dir / "health-history.json").read_text(encoding="utf-8"))
        assert len(data["entries"]) == 2
        assert data["entries"][1]["overall"] == 70

    def test_deduplicates_same_date(self, tmp_path: Path) -> None:
        # Arrange
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        save_health_snapshot(tmp_path, 60, "YELLOW", {})

        # Act
        save_health_snapshot(tmp_path, 70, "YELLOW", {})

        # Assert
        data = json.loads((state_dir / "health-history.json").read_text(encoding="utf-8"))
        assert len(data["entries"]) == 1
        assert data["entries"][0]["overall"] == 70

    def test_rolling_window(self, tmp_path: Path) -> None:
        # Arrange
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        entries = [
            {"date": f"2026-01-{i:02d}", "overall": 50 + i, "semaphore": "RED", "components": {}}
            for i in range(1, _MAX_HISTORY_ENTRIES + 1)
        ]
        (state_dir / "health-history.json").write_text(
            json.dumps({"entries": entries}), encoding="utf-8"
        )

        # Act
        save_health_snapshot(tmp_path, 99, "GREEN", {})

        # Assert
        data = json.loads((state_dir / "health-history.json").read_text(encoding="utf-8"))
        assert len(data["entries"]) == _MAX_HISTORY_ENTRIES
        assert data["entries"][-1]["overall"] == 99
        # Oldest entry should have been dropped
        assert data["entries"][0]["date"] == "2026-01-02"


class TestLoadHealthHistory:
    def test_returns_empty_if_no_file(self, tmp_path: Path) -> None:
        assert load_health_history(tmp_path) == []

    def test_returns_entries(self, tmp_path: Path) -> None:
        # Arrange
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        entries = [{"date": "2026-03-01", "overall": 60, "semaphore": "YELLOW", "components": {}}]
        (state_dir / "health-history.json").write_text(
            json.dumps({"entries": entries}), encoding="utf-8"
        )

        # Act
        result = load_health_history(tmp_path)

        # Assert
        assert len(result) == 1
        assert result[0]["overall"] == 60

    def test_handles_corrupt_json(self, tmp_path: Path) -> None:
        # Arrange
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "health-history.json").write_text("not json", encoding="utf-8")

        # Act & Assert
        assert load_health_history(tmp_path) == []


class TestHealthDirection:
    def test_no_history_returns_empty(self) -> None:
        assert health_direction([], 75) == ""

    def test_improving(self) -> None:
        history = [{"overall": 60}]
        assert health_direction(history, 70) == "↑"

    def test_degrading(self) -> None:
        history = [{"overall": 80}]
        assert health_direction(history, 70) == "↓"

    def test_stable(self) -> None:
        history = [{"overall": 75}]
        assert health_direction(history, 76) == "→"

    def test_stable_exact_same(self) -> None:
        history = [{"overall": 75}]
        assert health_direction(history, 75) == "→"

    def test_threshold_boundary_up(self) -> None:
        history = [{"overall": 70}]
        # diff = 3 > 2 → improving
        assert health_direction(history, 73) == "↑"

    def test_threshold_boundary_down(self) -> None:
        history = [{"overall": 70}]
        # diff = -3 < -2 → degrading
        assert health_direction(history, 67) == "↓"
