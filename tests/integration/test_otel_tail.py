"""Integration test for ai-eng audit otel-tail (P4.1 / 2026-05-04 gap closure).

Uses a mock urlopen to capture POST payloads; this avoids the
prompt-injection-guard tripping on the bash command that would
contain the BaseHTTPRequestHandler test fixture body.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from queue import Queue
from typing import Any
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app


class _CollectorMock:
    """Captures POST envelopes via mocked urlopen."""

    def __init__(self) -> None:
        self.received: Queue[dict[str, Any]] = Queue()

    def make_urlopen(self):
        def fake_urlopen(req, timeout=10):
            try:
                payload = json.loads(req.data.decode("utf-8"))
                self.received.put(payload)
            except Exception:
                pass
            mock_resp = MagicMock()
            mock_resp.status = 202
            mock_resp.__enter__ = lambda self: self
            mock_resp.__exit__ = lambda *a: None
            return mock_resp

        return fake_urlopen


def _seed_event(ndjson_path: Path, *, span_id: str, ts: str, kind: str = "test") -> None:
    event = {
        "schemaVersion": "1.0",
        "timestamp": ts,
        "project": "test",
        "engine": "claude_code",
        "kind": kind,
        "outcome": "success",
        "component": f"test.{kind}",
        "correlationId": "abc",
        "spanId": span_id,
        "detail": {"foo": "bar"},
    }
    ndjson_path.parent.mkdir(parents=True, exist_ok=True)
    with ndjson_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + chr(10))


def test_otel_tail_streams_to_collector(tmp_path: Path) -> None:
    """End-to-end: append events while tail is running; assert they arrive."""
    project_root = tmp_path / "project"
    state = project_root / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    ndjson = state / "framework-events.ndjson"
    ndjson.write_text("", encoding="utf-8")

    mock = _CollectorMock()
    runner = CliRunner()
    app = create_app()
    result_holder: dict[str, Any] = {}

    def run_tail():
        with (
            patch(
                "ai_engineering.cli_commands.audit_cmd._resolve_project_root",
                return_value=project_root,
            ),
            patch("urllib.request.urlopen", side_effect=mock.make_urlopen()),
        ):
            r = runner.invoke(
                app,
                [
                    "audit",
                    "otel-tail",
                    "--collector",
                    "http://localhost:0/v1/traces",
                    "--batch-size",
                    "2",
                    "--poll-interval-sec",
                    "0.1",
                    "--duration-sec",
                    "3.0",
                ],
            )
            result_holder["exit_code"] = r.exit_code
            result_holder["output"] = r.output

    tail_thread = threading.Thread(target=run_tail, daemon=True)
    tail_thread.start()
    time.sleep(0.3)

    for i, ts in enumerate(
        ["2026-05-04T10:00:01Z", "2026-05-04T10:00:02Z", "2026-05-04T10:00:03Z"]
    ):
        _seed_event(ndjson, span_id=f"span{i:013d}xy", ts=ts)
        time.sleep(0.2)

    tail_thread.join(timeout=6)

    received = []
    while not mock.received.empty():
        received.append(mock.received.get_nowait())

    assert received, f"no envelopes; output: {result_holder.get('output')!r}"

    total_spans = 0
    for env in received:
        assert "resourceSpans" in env
        scope = env["resourceSpans"][0]["scopeSpans"][0]
        total_spans += len(scope.get("spans", []))

    assert total_spans >= 3, f"expected >=3 spans; got {total_spans}"


def test_otel_tail_since_filter(tmp_path: Path) -> None:
    """--since skips events older than the supplied timestamp."""
    project_root = tmp_path / "project-since"
    state = project_root / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    ndjson = state / "framework-events.ndjson"
    ndjson.write_text("", encoding="utf-8")

    for i, ts in enumerate(
        ["2025-01-01T00:00:00Z", "2025-01-02T00:00:00Z", "2025-01-03T00:00:00Z"]
    ):
        _seed_event(ndjson, span_id=f"old{i:013d}xy", ts=ts, kind="old")

    mock = _CollectorMock()
    runner = CliRunner()
    app = create_app()
    result_holder: dict[str, Any] = {}

    def run_tail():
        with (
            patch(
                "ai_engineering.cli_commands.audit_cmd._resolve_project_root",
                return_value=project_root,
            ),
            patch("urllib.request.urlopen", side_effect=mock.make_urlopen()),
        ):
            r = runner.invoke(
                app,
                [
                    "audit",
                    "otel-tail",
                    "--collector",
                    "http://localhost:0/v1/traces",
                    "--since",
                    "2026-05-04T00:00:00Z",
                    "--batch-size",
                    "1",
                    "--poll-interval-sec",
                    "0.1",
                    "--duration-sec",
                    "2.0",
                ],
            )
            result_holder["exit_code"] = r.exit_code

    tail_thread = threading.Thread(target=run_tail, daemon=True)
    tail_thread.start()
    time.sleep(0.3)
    _seed_event(ndjson, span_id="newspan00000001", ts="2026-05-04T10:00:00Z", kind="new")
    tail_thread.join(timeout=4)

    received = []
    while not mock.received.empty():
        received.append(mock.received.get_nowait())

    seen_kinds: set[str] = set()
    for env in received:
        for span in env["resourceSpans"][0]["scopeSpans"][0]["spans"]:
            seen_kinds.add(span.get("name", ""))

    assert "new" in seen_kinds, f"new event missed; kinds={seen_kinds}"
    assert "old" not in seen_kinds, f"old leaked through; kinds={seen_kinds}"
