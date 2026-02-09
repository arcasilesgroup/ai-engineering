"""Unit tests for state I/O helpers."""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.state.io import append_ndjson


def test_append_ndjson_adds_timestamp_when_missing(tmp_path: Path) -> None:
    path = tmp_path / "audit-log.ndjson"

    append_ndjson(path, {"event": "x", "actor": "tester", "details": {}})

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "x"
    assert payload["actor"] == "tester"
    assert isinstance(payload.get("timestamp"), str)


def test_append_ndjson_keeps_existing_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "audit-log.ndjson"
    ts = "2026-02-09T00:00:00Z"

    append_ndjson(path, {"timestamp": ts, "event": "x", "actor": "tester", "details": {}})

    payload = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert payload["timestamp"] == ts
