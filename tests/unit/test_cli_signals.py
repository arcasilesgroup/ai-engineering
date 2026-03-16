"""Unit tests for ai_engineering.cli_commands.signals_cmd module.

Tests the signals emit and signals query CLI commands using the
Typer CLI runner with temporary audit log files.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

pytestmark = pytest.mark.unit

runner = CliRunner()


def _write_audit_log(root: Path, entries: list[dict]) -> None:
    """Write entries as NDJSON to the audit-log.ndjson file."""
    log_path = root / ".ai-engineering" / "state" / "audit-log.ndjson"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(e, default=str) for e in entries]
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_event(
    event: str = "scan_complete",
    actor: str = "cli",
    detail: dict | str | None = None,
    timestamp: datetime | None = None,
    spec: str | None = None,
) -> dict:
    """Build a minimal audit event dict."""
    ts = (timestamp or datetime.now(tz=UTC)).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry: dict = {
        "event": event,
        "actor": actor,
        "timestamp": ts,
    }
    if detail is not None:
        entry["detail"] = detail
    if spec is not None:
        entry["spec"] = spec
    return entry


class TestSignalsEmit:
    """Tests for `ai-eng signals emit`."""

    def test_emit_basic_event(self, tmp_path: Path) -> None:
        """Emit a simple event and verify it was written to the audit log."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "scan_complete"],
            )
        assert result.exit_code == 0
        assert "Emitted: scan_complete by cli" in result.output

        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        assert log_path.exists()
        content = log_path.read_text(encoding="utf-8").strip()
        entry = json.loads(content)
        assert entry["event"] == "scan_complete"
        assert entry["actor"] == "cli"

    def test_emit_with_actor(self, tmp_path: Path) -> None:
        """Emit with custom --actor flag."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "gate_result", "--actor", "build-agent"],
            )
        assert result.exit_code == 0
        assert "Emitted: gate_result by build-agent" in result.output

    def test_emit_with_detail_json(self, tmp_path: Path) -> None:
        """Emit with --detail JSON payload."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        detail = json.dumps({"result": "pass", "score": 100})
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "gate_result", "--detail", detail],
            )
        assert result.exit_code == 0

        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["detail"]["result"] == "pass"
        assert entry["detail"]["score"] == 100

    def test_emit_with_spec(self, tmp_path: Path) -> None:
        """Emit with --spec associates the event to a spec."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "build_complete", "--spec", "spec-042"],
            )
        assert result.exit_code == 0

        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        assert entry["spec"] == "spec-042"

    def test_emit_invalid_detail_json(self, tmp_path: Path) -> None:
        """Invalid JSON in --detail produces exit code 1."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "scan_complete", "--detail", "NOT JSON"],
            )
        assert result.exit_code != 0

    def test_emit_empty_detail_becomes_none(self, tmp_path: Path) -> None:
        """Emit with empty detail JSON {} stores no detail (None)."""
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                ["signals", "emit", "scan_complete", "--detail", "{}"],
            )
        assert result.exit_code == 0

        log_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        entry = json.loads(log_path.read_text(encoding="utf-8").strip())
        # detail is {} which is falsy, so model gets detail=None → excluded from dump
        assert "detail" not in entry


class TestSignalsQuery:
    """Tests for `ai-eng signals query`."""

    def test_no_events_found(self, tmp_path: Path) -> None:
        """When no audit log exists, report no events."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["signals", "query"])
        assert result.exit_code == 0
        assert "No events found" in result.output

    def test_query_shows_events(self, tmp_path: Path) -> None:
        """Query returns events from the audit log."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [
                _make_event(event="scan_complete", actor="agent1", timestamp=now),
                _make_event(event="gate_result", actor="agent2", timestamp=now),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["signals", "query"])
        assert result.exit_code == 0
        assert "Events" in result.output
        assert "scan_complete" in result.output
        assert "gate_result" in result.output

    def test_query_filter_by_type(self, tmp_path: Path) -> None:
        """Query with --type filters to matching events only."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [
                _make_event(event="scan_complete", timestamp=now),
                _make_event(event="gate_result", timestamp=now),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["signals", "query", "--type", "gate_result"])
        assert result.exit_code == 0
        assert "gate_result" in result.output
        # scan_complete should not appear in the event lines
        event_lines = [line for line in result.output.split("\n") if "scan_complete" in line]
        assert len(event_lines) == 0

    def test_query_limit(self, tmp_path: Path) -> None:
        """Query with --limit restricts the number of events shown."""
        now = datetime.now(tz=UTC)
        events = [_make_event(event=f"event_{i}", timestamp=now) for i in range(10)]
        _write_audit_log(tmp_path, events)
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["signals", "query", "--limit", "3"])
        assert result.exit_code == 0
        assert "3 shown" in result.output

    def test_query_days_filter(self, tmp_path: Path) -> None:
        """Query with --days filters out old events."""
        now = datetime.now(tz=UTC)
        old = now - timedelta(days=60)
        _write_audit_log(
            tmp_path,
            [
                _make_event(event="old_event", timestamp=old),
                _make_event(event="new_event", timestamp=now),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["signals", "query", "--days", "7"])
        assert result.exit_code == 0
        assert "new_event" in result.output
        # old_event should be filtered out
        assert "old_event" not in result.output

    def test_query_with_dict_detail(self, tmp_path: Path) -> None:
        """Events with dict details show a JSON summary."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [_make_event(detail={"result": "pass"}, timestamp=now)],
        )
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["signals", "query"])
        assert result.exit_code == 0
        assert "result" in result.output

    def test_query_with_string_detail(self, tmp_path: Path) -> None:
        """Events with string details show the string."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [_make_event(detail="some detail text", timestamp=now)],
        )
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["signals", "query"])
        assert result.exit_code == 0
        assert "some detail text" in result.output

    def test_query_with_no_detail(self, tmp_path: Path) -> None:
        """Events without detail don't add extra text."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [_make_event(timestamp=now)],
        )
        with patch(
            "ai_engineering.cli_commands.signals_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["signals", "query"])
        assert result.exit_code == 0
        assert "scan_complete" in result.output
