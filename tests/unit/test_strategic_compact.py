"""Unit tests for scripts/hooks/strategic-compact.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

# The hook uses sys.path.insert to import _lib.audit.
# We patch the module-level constants and test pure functions in isolation.

HOOK_DIR = Path(__file__).resolve().parents[2] / ".ai-engineering" / "scripts" / "hooks"


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear hook-related env vars to avoid leaking real session state."""
    monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
    monkeypatch.delenv("CLAUDE_HOOK_EVENT_NAME", raising=False)
    monkeypatch.delenv("COMPACT_THRESHOLD", raising=False)
    monkeypatch.delenv("COMPACT_REMINDER_INTERVAL", raising=False)


def _import_hook():
    """Import the hook module dynamically, handling its sys.path manipulation."""
    import importlib
    import sys

    # Ensure _lib.audit is importable
    if str(HOOK_DIR) not in sys.path:
        sys.path.insert(0, str(HOOK_DIR))

    spec = importlib.util.spec_from_file_location(
        "strategic_compact", HOOK_DIR / "strategic-compact.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestShouldAdvise:
    """Boundary tests for the advisory threshold logic."""

    def test_below_threshold_returns_false(self) -> None:
        mod = _import_hook()
        with (
            patch.object(mod, "_COMPACT_THRESHOLD", 50),
            patch.object(mod, "_COMPACT_REMINDER_INTERVAL", 25),
        ):
            assert mod._should_advise(49) is False

    def test_at_threshold_returns_true(self) -> None:
        mod = _import_hook()
        with (
            patch.object(mod, "_COMPACT_THRESHOLD", 50),
            patch.object(mod, "_COMPACT_REMINDER_INTERVAL", 25),
        ):
            assert mod._should_advise(50) is True

    def test_one_past_threshold_returns_false(self) -> None:
        mod = _import_hook()
        with (
            patch.object(mod, "_COMPACT_THRESHOLD", 50),
            patch.object(mod, "_COMPACT_REMINDER_INTERVAL", 25),
        ):
            assert mod._should_advise(51) is False

    def test_at_first_reminder_interval(self) -> None:
        mod = _import_hook()
        with (
            patch.object(mod, "_COMPACT_THRESHOLD", 50),
            patch.object(mod, "_COMPACT_REMINDER_INTERVAL", 25),
        ):
            assert mod._should_advise(75) is True

    def test_at_second_reminder_interval(self) -> None:
        mod = _import_hook()
        with (
            patch.object(mod, "_COMPACT_THRESHOLD", 50),
            patch.object(mod, "_COMPACT_REMINDER_INTERVAL", 25),
        ):
            assert mod._should_advise(100) is True

    def test_between_intervals_returns_false(self) -> None:
        mod = _import_hook()
        with (
            patch.object(mod, "_COMPACT_THRESHOLD", 50),
            patch.object(mod, "_COMPACT_REMINDER_INTERVAL", 25),
        ):
            assert mod._should_advise(60) is False


class TestLoadCounters:
    """Counter persistence with corrupt/missing file handling."""

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        mod = _import_hook()
        with patch.object(mod, "_COUNTER_FILE", tmp_path / "nonexistent.json"):
            result = mod._load_counters()
        assert result == {}

    def test_valid_file_returns_dict(self, tmp_path: Path) -> None:
        mod = _import_hook()
        counter_file = tmp_path / "counters.json"
        counter_file.write_text('{"session-1":5}', encoding="utf-8")
        with patch.object(mod, "_COUNTER_FILE", counter_file):
            result = mod._load_counters()
        assert result == {"session-1": 5}

    def test_corrupt_json_returns_empty(self, tmp_path: Path) -> None:
        mod = _import_hook()
        counter_file = tmp_path / "counters.json"
        counter_file.write_text("{bad json", encoding="utf-8")
        with patch.object(mod, "_COUNTER_FILE", counter_file):
            result = mod._load_counters()
        assert result == {}


class TestSaveCounters:
    """Counter persistence with pruning."""

    def test_saves_only_current_session(self, tmp_path: Path) -> None:
        mod = _import_hook()
        counter_file = tmp_path / "state" / "counters.json"
        with (
            patch.object(mod, "_COUNTER_FILE", counter_file),
            patch.object(mod, "_STATE_DIR", tmp_path / "state"),
        ):
            counters = {"old-session": 99, "current": 5}
            mod._save_counters(counters, "current")

        saved = json.loads(counter_file.read_text(encoding="utf-8"))
        assert saved == {"current": 5}
        assert "old-session" not in saved

    def test_creates_directory_if_missing(self, tmp_path: Path) -> None:
        mod = _import_hook()
        state_dir = tmp_path / "new" / "state"
        counter_file = state_dir / "counters.json"
        with (
            patch.object(mod, "_COUNTER_FILE", counter_file),
            patch.object(mod, "_STATE_DIR", state_dir),
        ):
            mod._save_counters({"key": 1}, "key")

        assert counter_file.exists()


class TestGetSessionKey:
    """Session key derivation from env or fallback."""

    def test_uses_claude_session_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAUDE_SESSION_ID", "abc-123")
        mod = _import_hook()
        assert mod._get_session_key() == "abc-123"

    def test_fallback_to_date_hour(self) -> None:
        mod = _import_hook()
        key = mod._get_session_key()
        # Format: YYYYMMDD-HH (11 chars)
        assert len(key) == 11
        assert key[8] == "-"
