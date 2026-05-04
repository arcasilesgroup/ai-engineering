"""Unit tests for ``ai-eng audit otel-export`` (spec-120 T-C5).

Covers the CLI surface registered in
:mod:`ai_engineering.cli_commands.audit_cmd`:

* default invocation prints OTLP/JSON to stdout
* ``--out path.json`` writes the envelope to disk and reports the path
* ``--trace`` is required (Typer enforces, exit non-zero)
* the emitted JSON is parseable

Each test pins ``cwd`` to a fresh ``tmp_path`` so the project's real
``framework-events.ndjson`` is never touched.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.state.audit_index import NDJSON_REL

runner = CliRunner()


def _hex16(seed: str) -> str:
    """Return a deterministic 16-hex span_id derived from ``seed``."""
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


def _hex32(seed: str) -> str:
    """Return a deterministic 32-hex trace_id derived from ``seed``."""
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def _seed_ndjson(project_root: Path, events: list[dict[str, Any]]) -> None:
    """Write ``events`` as canonical NDJSON under ``project_root``."""
    target = project_root / NDJSON_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(event, sort_keys=True) + "\n" for event in events)
    target.write_text(body, encoding="utf-8")


def _make_event(
    *,
    index: int,
    span_id: str,
    trace_id: str = "trace-otel",
    parent_span_id: str | None = None,
    kind: str = "skill_invoked",
    component: str = "hook.telemetry-skill",
    outcome: str = "success",
) -> dict[str, Any]:
    """Build a synthetic event suitable for the OTel exporter."""
    event: dict[str, Any] = {
        "kind": kind,
        "engine": "claude_code",
        "timestamp": f"2026-01-01T00:00:{index:02d}Z",
        "component": component,
        "outcome": outcome,
        "correlationId": f"corr-{index:04d}",
        "schemaVersion": "1.0",
        "project": "ai-engineering",
        "spanId": span_id,
        "traceId": _hex32(trace_id),
        "sessionId": "session-otel",
        "detail": {
            "skill": "ai-brainstorm",
            "genai": {
                "system": "anthropic",
                "request": {"model": "claude-sonnet-4-5"},
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "cost_usd": 0.001,
                },
            },
        },
    }
    if parent_span_id is not None:
        event["parentSpanId"] = parent_span_id
    return event


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Anchor cwd at ``tmp_path`` so the audit CLI sees a fresh root."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_export_to_stdout(project_root: Path) -> None:
    """Default invocation prints a valid OTLP envelope to stdout."""
    _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("a"))])
    runner.invoke(create_app(), ["audit", "index"])

    result = runner.invoke(
        create_app(),
        ["audit", "otel-export", "--trace", _hex32("trace-otel")],
    )
    assert result.exit_code == 0, result.output
    # JSON envelope occupies multiple lines; collapse to a single string.
    # Find the first '{' and last '}' to slice the JSON region. Banners may
    # sit before/after.
    text = result.output
    start = text.index("{")
    end = text.rindex("}")
    envelope = json.loads(text[start : end + 1])
    assert "resourceSpans" in envelope
    spans = envelope["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert len(spans) == 1
    assert spans[0]["name"] == "skill_invoked"


def test_export_to_file(project_root: Path) -> None:
    """``--out path.json`` writes the envelope to disk."""
    _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("a"))])
    runner.invoke(create_app(), ["audit", "index"])

    out_path = project_root / "exports" / "spans.json"
    result = runner.invoke(
        create_app(),
        [
            "audit",
            "otel-export",
            "--trace",
            _hex32("trace-otel"),
            "--out",
            str(out_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_path.exists()
    body = json.loads(out_path.read_text(encoding="utf-8"))
    assert "resourceSpans" in body
    assert "Wrote OTLP envelope" in result.output


def test_export_creates_parent_dirs(project_root: Path) -> None:
    """``--out`` creates intermediate parent directories on demand."""
    _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("a"))])
    runner.invoke(create_app(), ["audit", "index"])

    out_path = project_root / "deeply" / "nested" / "out" / "spans.json"
    result = runner.invoke(
        create_app(),
        [
            "audit",
            "otel-export",
            "--trace",
            _hex32("trace-otel"),
            "--out",
            str(out_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_path.exists()


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


def test_export_requires_trace(project_root: Path) -> None:
    """Calling without --trace exits non-zero (Typer-enforced)."""
    _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("a"))])
    runner.invoke(create_app(), ["audit", "index"])

    result = runner.invoke(create_app(), ["audit", "otel-export"])
    assert result.exit_code != 0


def test_exported_json_parses(project_root: Path) -> None:
    """The bytes written to ``--out`` parse as JSON without surprises."""
    _seed_ndjson(
        project_root,
        [
            _make_event(index=0, span_id=_hex16("root")),
            _make_event(
                index=1,
                span_id=_hex16("child"),
                parent_span_id=_hex16("root"),
            ),
        ],
    )
    runner.invoke(create_app(), ["audit", "index"])

    out_path = project_root / "spans.json"
    result = runner.invoke(
        create_app(),
        [
            "audit",
            "otel-export",
            "--trace",
            _hex32("trace-otel"),
            "--out",
            str(out_path),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert len(spans) == 2
    # Child span carries parentSpanId.
    child = next(s for s in spans if s["spanId"] == _hex16("child"))
    assert child["parentSpanId"] == _hex16("root")
    # Root span omits parentSpanId.
    root = next(s for s in spans if s["spanId"] == _hex16("root"))
    assert "parentSpanId" not in root


def test_export_missing_ndjson_emits_empty_envelope(project_root: Path) -> None:
    """No NDJSON at all -> empty envelope, exit 0 (soft success)."""
    result = runner.invoke(
        create_app(),
        ["audit", "otel-export", "--trace", _hex32("trace-otel")],
    )
    assert result.exit_code == 0, result.output
    text = result.output
    start = text.index("{")
    end = text.rindex("}")
    envelope = json.loads(text[start : end + 1])
    assert envelope["resourceSpans"][0]["scopeSpans"][0]["spans"] == []
