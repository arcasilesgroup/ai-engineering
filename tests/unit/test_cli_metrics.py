"""Unit tests for ai_engineering.cli_commands.metrics module.

Tests the metrics collect CLI command which aggregates signal/event
data into a compact machine-readable JSON summary.
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
    return entry


class TestMetricsCollect:
    """Tests for `ai-eng metrics collect`."""

    def test_empty_audit_log(self, tmp_path: Path) -> None:
        """When no audit log exists, metrics returns zero counts."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.metrics._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["metrics", "collect"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["window_days"] == 30
        assert data["events"]["total"] == 0
        assert data["data_quality"] == "LOW"
        assert data["gate_health"]["pass_rate"] == 0.0

    def test_with_scan_and_build_events(self, tmp_path: Path) -> None:
        """Metrics correctly count scan_complete and build_complete events."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [
                _make_event(event="scan_complete", timestamp=now),
                _make_event(event="scan_complete", timestamp=now),
                _make_event(event="build_complete", timestamp=now),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.metrics._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["metrics", "collect"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["events"]["total"] == 3
        assert data["events"]["scan_complete"] == 2
        assert data["events"]["build_complete"] == 1

    def test_gate_result_events(self, tmp_path: Path) -> None:
        """Gate health is computed from gate_result events."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [
                _make_event(
                    event="gate_result",
                    detail={"result": "pass"},
                    timestamp=now,
                ),
                _make_event(
                    event="gate_result",
                    detail={"result": "fail", "failed_checks": ["lint", "test"]},
                    timestamp=now,
                ),
                _make_event(
                    event="gate_result",
                    detail={"result": "pass"},
                    timestamp=now,
                ),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.metrics._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["metrics", "collect"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["gate_health"]["pass_rate"] == pytest.approx(66.7, abs=0.1)
        assert data["gate_health"]["failed"] == 1

    def test_custom_days_window(self, tmp_path: Path) -> None:
        """--days flag changes the metrics window."""
        now = datetime.now(tz=UTC)
        old = now - timedelta(days=60)
        _write_audit_log(
            tmp_path,
            [
                _make_event(event="scan_complete", timestamp=old),
                _make_event(event="scan_complete", timestamp=now),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.metrics._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["metrics", "collect", "--days", "7"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["window_days"] == 7
        # Only the recent event should be in the window
        assert data["events"]["total"] == 1
        assert data["events"]["scan_complete"] == 1

    def test_deploy_and_session_metric_events(self, tmp_path: Path) -> None:
        """Deploy and session_metric events are counted correctly."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [
                _make_event(event="deploy_complete", timestamp=now),
                _make_event(event="session_metric", timestamp=now),
                _make_event(event="session_metric", timestamp=now),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.metrics._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["metrics", "collect"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["events"]["deploy_complete"] == 1
        assert data["events"]["session_metric"] == 2

    def test_generated_at_field(self, tmp_path: Path) -> None:
        """Output contains a generated_at timestamp."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.metrics._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["metrics", "collect"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "generated_at" in data
        # Should be parseable as an ISO timestamp
        datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))

    def test_most_failed_check(self, tmp_path: Path) -> None:
        """Most-failed check is identified from gate_result events."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [
                _make_event(
                    event="gate_result",
                    detail={"result": "fail", "failed_checks": ["lint"]},
                    timestamp=now,
                ),
                _make_event(
                    event="gate_result",
                    detail={"result": "fail", "failed_checks": ["lint", "test"]},
                    timestamp=now,
                ),
                _make_event(
                    event="gate_result",
                    detail={"result": "fail", "failed_checks": ["test"]},
                    timestamp=now,
                ),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.metrics._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["metrics", "collect"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # lint appears in 2 events, test appears in 2 events
        # Either could be the most_failed_check; both have count 2
        assert data["gate_health"]["most_failed_check"] in ("lint", "test")
        assert data["gate_health"]["most_failed_count"] >= 2

    def test_no_gate_failures(self, tmp_path: Path) -> None:
        """When all gates pass, most_failed_check is 'none'."""
        now = datetime.now(tz=UTC)
        _write_audit_log(
            tmp_path,
            [
                _make_event(
                    event="gate_result",
                    detail={"result": "pass"},
                    timestamp=now,
                ),
            ],
        )
        with patch(
            "ai_engineering.cli_commands.metrics._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["metrics", "collect"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["gate_health"]["most_failed_check"] == "none"
        assert data["gate_health"]["most_failed_count"] == 0
        assert data["gate_health"]["pass_rate"] == 100.0

    def test_output_is_valid_json(self, tmp_path: Path) -> None:
        """The output is well-formed JSON with expected top-level keys."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.metrics._project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["metrics", "collect"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data.keys()) == {
            "window_days",
            "generated_at",
            "data_quality",
            "events",
            "gate_health",
        }
        assert set(data["events"].keys()) == {
            "total",
            "scan_complete",
            "build_complete",
            "gate_result",
            "deploy_complete",
            "session_metric",
        }
        assert set(data["gate_health"].keys()) == {
            "pass_rate",
            "failed",
            "most_failed_check",
            "most_failed_count",
        }
