"""Unit tests for ``ai-eng audit replay`` (spec-120 T-C5).

Covers the CLI surface registered in
:mod:`ai_engineering.cli_commands.audit_cmd`:

* default human output is indented text
* ``--json`` emits a JSON envelope with ``trees`` and ``tokens``
* exactly one of ``--session`` / ``--trace`` is required
* both flags simultaneously is an error
* the SQLite index is auto-built when missing or stale

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
from ai_engineering.state.audit_index import NDJSON_REL, index_path

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
    parent_span_id: str | None = None,
    session_id: str = "session-replay",
    trace_id: str = "trace-replay",
    kind: str = "skill_invoked",
    component: str = "hook.telemetry-skill",
    outcome: str = "success",
) -> dict[str, Any]:
    """Build a minimal-but-complete synthetic event."""
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
        "sessionId": session_id,
        "traceId": _hex32(trace_id),
        "detail": {
            "skill": "ai-brainstorm",
            "genai": {
                "system": "anthropic",
                "request": {"model": "claude-sonnet-4-5"},
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
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


def test_replay_session_indented(project_root: Path) -> None:
    """Default invocation prints an indented tree + tokens footer."""
    span_root = _hex16("root")
    span_a = _hex16("A")
    _seed_ndjson(
        project_root,
        [
            _make_event(index=0, span_id=span_root),
            _make_event(index=1, span_id=span_a, parent_span_id=span_root),
        ],
    )
    # Pre-build so we don't depend on auto-build for this test.
    runner.invoke(create_app(), ["audit", "index"])

    result = runner.invoke(
        create_app(),
        ["audit", "replay", "--session", "session-replay"],
    )
    assert result.exit_code == 0, result.output
    # Two lines for the two events, plus the footer.
    lines = [line for line in result.output.splitlines() if line.strip()]
    body_lines = [line for line in lines if not line.startswith("---")]
    assert len(body_lines) >= 2
    # The child line carries leading indentation.
    indented = [line for line in body_lines if line.startswith("  ")]
    assert indented, f"Expected an indented child line in {result.output!r}"
    # Footer present with the cumulative tokens.
    assert "Tokens:" in result.output
    assert "input=20" in result.output
    assert "output=10" in result.output
    assert "total=30" in result.output


def test_replay_json_output(project_root: Path) -> None:
    """``--json`` emits a JSON envelope with both ``trees`` and ``tokens``."""
    span_root = _hex16("root")
    span_a = _hex16("A")
    _seed_ndjson(
        project_root,
        [
            _make_event(index=0, span_id=span_root),
            _make_event(index=1, span_id=span_a, parent_span_id=span_root),
        ],
    )
    runner.invoke(create_app(), ["audit", "index"])

    result = runner.invoke(
        create_app(),
        ["audit", "replay", "--session", "session-replay", "--json"],
    )
    assert result.exit_code == 0, result.output
    # Find the JSON envelope in the output (banners may precede it).
    last_json = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("{")
    )
    payload = json.loads(last_json)
    assert "trees" in payload
    assert "tokens" in payload
    assert len(payload["trees"]) == 1
    assert payload["trees"][0]["span_id"] == span_root
    assert payload["trees"][0]["children"][0]["span_id"] == span_a
    assert payload["tokens"]["total_tokens"] == 30


def test_replay_trace_filter(project_root: Path) -> None:
    """``--trace`` filter selects only the matching trace's events."""
    span_a = _hex16("A")
    span_b = _hex16("B")
    _seed_ndjson(
        project_root,
        [
            _make_event(index=0, span_id=span_a, trace_id="trace-A"),
            _make_event(index=1, span_id=span_b, trace_id="trace-B"),
        ],
    )
    runner.invoke(create_app(), ["audit", "index"])

    result = runner.invoke(
        create_app(),
        ["audit", "replay", "--trace", _hex32("trace-A"), "--json"],
    )
    assert result.exit_code == 0, result.output
    last_json = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("{")
    )
    payload = json.loads(last_json)
    assert len(payload["trees"]) == 1
    assert payload["trees"][0]["span_id"] == span_a


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


def test_replay_requires_session_or_trace(project_root: Path) -> None:
    """Calling with neither --session nor --trace exits non-zero."""
    _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("only"))])
    runner.invoke(create_app(), ["audit", "index"])

    # ``mix_stderr=False`` is rejected by older Typer; merge streams via
    # ``CliRunner()`` default and read combined ``output``.
    result = runner.invoke(create_app(), ["audit", "replay"])
    assert result.exit_code != 0
    assert "exactly one" in result.output.lower()


def test_replay_rejects_both_session_and_trace(project_root: Path) -> None:
    """Calling with both --session and --trace exits non-zero."""
    _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("only"))])
    runner.invoke(create_app(), ["audit", "index"])

    result = runner.invoke(
        create_app(),
        [
            "audit",
            "replay",
            "--session",
            "session-replay",
            "--trace",
            _hex32("trace-replay"),
        ],
    )
    assert result.exit_code != 0
    assert "exactly one" in result.output.lower()


# ---------------------------------------------------------------------------
# Auto-build behaviour
# ---------------------------------------------------------------------------


def test_replay_auto_builds_index(project_root: Path) -> None:
    """No SQLite present -> the CLI builds one on demand before walking."""
    _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("auto"))])
    # Index intentionally NOT pre-built.
    assert not index_path(project_root).exists()

    result = runner.invoke(
        create_app(),
        ["audit", "replay", "--session", "session-replay"],
    )
    assert result.exit_code == 0, result.output
    # The auto-build should have created the SQLite file.
    assert index_path(project_root).exists()
    # And the rendered output should include at least the kind cell.
    assert "skill_invoked" in result.output


def test_replay_handles_empty_session(project_root: Path) -> None:
    """A session with zero matching rows prints '(no events)'."""
    _seed_ndjson(project_root, [_make_event(index=0, span_id=_hex16("only"))])
    runner.invoke(create_app(), ["audit", "index"])

    result = runner.invoke(
        create_app(),
        ["audit", "replay", "--session", "no-such-session"],
    )
    assert result.exit_code == 0, result.output
    assert "(no events)" in result.output


def test_replay_missing_ndjson_returns_empty(project_root: Path) -> None:
    """No NDJSON at all -> '(no events)' on stdout, exit 0."""
    # No NDJSON, no SQLite.
    result = runner.invoke(
        create_app(),
        ["audit", "replay", "--session", "session-replay"],
    )
    assert result.exit_code == 0, result.output
    assert "(no events)" in result.output


def test_replay_missing_ndjson_json_mode(project_root: Path) -> None:
    """No NDJSON at all in JSON mode emits an empty trees envelope."""
    result = runner.invoke(
        create_app(),
        ["audit", "replay", "--session", "session-replay", "--json"],
    )
    assert result.exit_code == 0, result.output
    last_json = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("{")
    )
    payload = json.loads(last_json)
    assert payload == {
        "trees": [],
        "tokens": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        },
    }
