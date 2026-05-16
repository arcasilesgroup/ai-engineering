"""Unit tests for ``ai-eng audit index`` (spec-120 T-B2).

Covers the CLI surface registered in
:mod:`ai_engineering.cli_commands.audit_cmd`:

* human single-line summary on success
* ``--json`` envelope mirrors :class:`IndexResult` fields
* ``--rebuild`` flag drops the schema and re-indexes from offset 0
* missing ``framework-events.ndjson`` is a soft-success (exit 0,
  empty result, no SQLite created)

Each test pins ``cwd`` to a fresh ``tmp_path`` so the project's real
``framework-events.ndjson`` is never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.state.audit_index import NDJSON_REL, index_path

runner = CliRunner()


def _seed_ndjson(project_root: Path, events: list[dict]) -> None:
    """Drop a tiny synthetic NDJSON under ``project_root``."""
    target = project_root / NDJSON_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(event, sort_keys=True) + "\n" for event in events)
    target.write_text(body, encoding="utf-8")


def _event(
    *,
    skill: str = "ai-brainstorm",
    span_id: str = "abcdef0123456789",
    input_tokens: int = 100,
    output_tokens: int = 50,
    total_tokens: int = 150,
) -> dict:
    """Minimal-but-complete synthetic event with a usage block."""
    return {
        "kind": "skill_invoked",
        "engine": "claude_code",
        "timestamp": "2026-05-04T01:00:00Z",
        "component": "hook.telemetry-skill",
        "outcome": "success",
        "correlationId": f"corr-{span_id}",
        "schemaVersion": "1.0",
        "project": "test-120",
        "spanId": span_id,
        "sessionId": "session-test-120",
        "detail": {
            "skill": skill,
            "genai": {
                "system": "anthropic",
                "request": {"model": "claude-sonnet-4-5"},
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost_usd": 0.001,
                },
            },
        },
    }


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Anchor cwd at ``tmp_path`` so the audit CLI sees a fresh root."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_index_human_output(project_root: Path) -> None:
    """Default invocation prints a one-line summary mentioning row counts."""
    _seed_ndjson(project_root, [_event(span_id=f"span-{i:016d}") for i in range(3)])
    result = runner.invoke(create_app(), ["audit", "index"])

    assert result.exit_code == 0, result.output
    assert "Indexed 3 rows" in result.output
    assert "rebuild=False" in result.output
    assert "ms" in result.output  # elapsed_ms surfaced
    assert index_path(project_root).exists()


def test_index_json_output(project_root: Path) -> None:
    """``--json`` emits a machine-readable envelope mirroring IndexResult."""
    _seed_ndjson(project_root, [_event(span_id=f"span-{i:016d}") for i in range(2)])
    result = runner.invoke(create_app(), ["audit", "index", "--json"])

    assert result.exit_code == 0, result.output
    # The output may include the global app banner suppressed by --json mode at
    # the app level; the audit-index subcommand keeps its own --json local.
    # Find the JSON object in the output.
    last_line = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("{")
    )
    payload = json.loads(last_line)
    assert payload["rows_indexed"] == 2
    assert payload["rows_total"] == 2
    assert payload["rebuilt"] is False
    assert payload["last_offset"] > 0
    assert "elapsed_ms" in payload


def test_index_with_rebuild_flag(project_root: Path) -> None:
    """``--rebuild`` drops the schema and re-reads from offset 0."""
    _seed_ndjson(project_root, [_event(span_id=f"span-{i:016d}") for i in range(3)])
    first = runner.invoke(create_app(), ["audit", "index"])
    assert first.exit_code == 0, first.output
    assert "Indexed 3 rows" in first.output

    # Second incremental run sees no new lines (0 rows indexed).
    second = runner.invoke(create_app(), ["audit", "index"])
    assert second.exit_code == 0, second.output
    assert "Indexed 0 rows" in second.output

    # Third run with --rebuild ingests all 3 again, with rebuild=True.
    third = runner.invoke(create_app(), ["audit", "index", "--rebuild"])
    assert third.exit_code == 0, third.output
    assert "Indexed 3 rows" in third.output
    assert "rebuild=True" in third.output


def test_index_handles_missing_ndjson(project_root: Path) -> None:
    """No NDJSON file -> soft success, no SQLite created, exit 0."""
    # NDJSON is intentionally absent.
    result = runner.invoke(create_app(), ["audit", "index"])
    assert result.exit_code == 0, result.output
    assert "Indexed 0 rows" in result.output
    assert not index_path(project_root).exists()
