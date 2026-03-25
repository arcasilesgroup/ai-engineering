"""Integration tests for scripts/hooks/strategic-compact.py main() flow."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration

HOOK_DIR = Path(__file__).resolve().parents[2] / ".ai-engineering" / "scripts" / "hooks"


def _import_hook():
    """Import the hook module dynamically."""
    import importlib

    if str(HOOK_DIR) not in sys.path:
        sys.path.insert(0, str(HOOK_DIR))

    spec = importlib.util.spec_from_file_location(
        "strategic_compact_int", HOOK_DIR / "strategic-compact.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestMainFlow:
    """Integration tests for the main() orchestrator."""

    def test_non_pretooluse_passes_through(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Non-PreToolUse events should passthrough stdin and return."""
        mod = _import_hook()
        stdin_data = json.dumps({"tool_name": "Edit"})
        captured_stdout = StringIO()

        monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", "PostToolUse")
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))
        monkeypatch.setattr("sys.stdout", captured_stdout)

        mod.main()

        output = captured_stdout.getvalue()
        assert json.loads(output)["tool_name"] == "Edit"

    def test_unmatched_tool_passes_through(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Matched event but unmatched tool should passthrough without counting."""
        mod = _import_hook()
        stdin_data = json.dumps({"tool_name": "Read"})
        captured_stdout = StringIO()

        monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", "PreToolUse")
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))
        monkeypatch.setattr("sys.stdout", captured_stdout)

        mod.main()

        output = captured_stdout.getvalue()
        assert json.loads(output)["tool_name"] == "Read"

    def test_matched_tool_increments_counter(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Edit tool on PreToolUse should increment counter and passthrough."""
        mod = _import_hook()
        state_dir = tmp_path / "state"
        counter_file = state_dir / "counters.json"
        stdin_data = json.dumps({"tool_name": "Edit"})
        captured_stdout = StringIO()

        monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", "PreToolUse")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "test-session-42")
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))
        monkeypatch.setattr("sys.stdout", captured_stdout)

        with (
            patch.object(mod, "_COUNTER_FILE", counter_file),
            patch.object(mod, "_STATE_DIR", state_dir),
        ):
            mod.main()

        # Counter file should exist with session key
        saved = json.loads(counter_file.read_text(encoding="utf-8"))
        assert saved == {"test-session-42": 1}

        # Stdin should be passed through
        output = captured_stdout.getvalue()
        assert json.loads(output)["tool_name"] == "Edit"

    def test_advisory_printed_at_threshold(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Advisory message should appear on stderr when threshold is reached."""
        mod = _import_hook()
        state_dir = tmp_path / "state"
        counter_file = state_dir / "counters.json"

        # Pre-seed counter at threshold - 1
        state_dir.mkdir(parents=True)
        counter_file.write_text('{"test-session":49}', encoding="utf-8")

        stdin_data = json.dumps({"tool_name": "Write"})
        captured_stdout = StringIO()
        captured_stderr = StringIO()

        monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", "PreToolUse")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "test-session")
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))
        monkeypatch.setattr("sys.stdout", captured_stdout)
        monkeypatch.setattr("sys.stderr", captured_stderr)

        with (
            patch.object(mod, "_COUNTER_FILE", counter_file),
            patch.object(mod, "_STATE_DIR", state_dir),
            patch.object(mod, "_COMPACT_THRESHOLD", 50),
        ):
            mod.main()

        stderr_output = captured_stderr.getvalue()
        assert "[strategic-compact]" in stderr_output
        assert "50 tool calls" in stderr_output

    def test_no_advisory_below_threshold(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """No advisory when counter is below threshold."""
        mod = _import_hook()
        state_dir = tmp_path / "state"
        counter_file = state_dir / "counters.json"
        state_dir.mkdir(parents=True)
        counter_file.write_text('{"test-session":10}', encoding="utf-8")

        stdin_data = json.dumps({"tool_name": "Edit"})
        captured_stdout = StringIO()
        captured_stderr = StringIO()

        monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", "PreToolUse")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "test-session")
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))
        monkeypatch.setattr("sys.stdout", captured_stdout)
        monkeypatch.setattr("sys.stderr", captured_stderr)

        with (
            patch.object(mod, "_COUNTER_FILE", counter_file),
            patch.object(mod, "_STATE_DIR", state_dir),
            patch.object(mod, "_COMPACT_THRESHOLD", 50),
        ):
            mod.main()

        assert captured_stderr.getvalue() == ""

    def test_counter_pruning_removes_old_sessions(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """After save, only the current session key should remain."""
        mod = _import_hook()
        state_dir = tmp_path / "state"
        counter_file = state_dir / "counters.json"
        state_dir.mkdir(parents=True)
        counter_file.write_text(
            '{"old-session-1":99,"old-session-2":50,"current":3}',
            encoding="utf-8",
        )

        stdin_data = json.dumps({"tool_name": "MultiEdit"})
        captured_stdout = StringIO()

        monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", "PreToolUse")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "current")
        monkeypatch.setattr("sys.stdin", StringIO(stdin_data))
        monkeypatch.setattr("sys.stdout", captured_stdout)

        with (
            patch.object(mod, "_COUNTER_FILE", counter_file),
            patch.object(mod, "_STATE_DIR", state_dir),
        ):
            mod.main()

        saved = json.loads(counter_file.read_text(encoding="utf-8"))
        assert list(saved.keys()) == ["current"]
        assert saved["current"] == 4
