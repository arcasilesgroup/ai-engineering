"""Unit tests for ``ai-eng audit tokens`` (spec-120 T-B4).

Covers:

* ``--by skill`` / ``--by agent`` / ``--by session`` produce non-empty
  tabular output sourced from the matching rollup view.
* Invalid ``--by`` exits with code 2 and a clear error.
* ``--json`` emits a JSON array with the rollup columns.

Each test pins ``cwd`` to a fresh ``tmp_path`` so the project's real
``framework-events.ndjson`` is never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.state.audit_index import NDJSON_REL

runner = CliRunner()


def _seed_ndjson(project_root: Path, events: list[dict]) -> None:
    """Drop a tiny synthetic NDJSON under ``project_root``."""
    target = project_root / NDJSON_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(json.dumps(event, sort_keys=True) + "\n" for event in events)
    target.write_text(body, encoding="utf-8")


def _skill_event(*, skill: str, span_id: str, total_tokens: int) -> dict:
    """Synthetic ``skill_invoked`` event with a usage block."""
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
                    "input_tokens": total_tokens // 3,
                    "output_tokens": total_tokens - (total_tokens // 3),
                    "total_tokens": total_tokens,
                    "cost_usd": 0.001,
                },
            },
        },
    }


def _agent_event(*, agent: str, span_id: str, total_tokens: int) -> dict:
    """Synthetic ``agent_dispatched`` event with a usage block."""
    return {
        "kind": "agent_dispatched",
        "engine": "claude_code",
        "timestamp": "2026-05-04T01:00:00Z",
        "component": "hook.observability",
        "outcome": "success",
        "correlationId": f"corr-{span_id}",
        "schemaVersion": "1.0",
        "project": "test-120",
        "spanId": span_id,
        "sessionId": "session-test-120",
        "detail": {
            "agent": agent,
            "genai": {
                "system": "anthropic",
                "request": {"model": "claude-sonnet-4-5"},
                "usage": {
                    "input_tokens": total_tokens // 2,
                    "output_tokens": total_tokens - (total_tokens // 2),
                    "total_tokens": total_tokens,
                    "cost_usd": 0.002,
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


def _seed_mixed_corpus(project_root: Path) -> None:
    """Seed a small mix of skill / agent events across two skills."""
    events = [
        _skill_event(skill="ai-brainstorm", span_id="span-skill-aa-0001", total_tokens=300),
        _skill_event(skill="ai-brainstorm", span_id="span-skill-aa-0002", total_tokens=600),
        _skill_event(skill="ai-plan", span_id="span-skill-pp-0001", total_tokens=900),
        _agent_event(agent="ai-explore", span_id="span-agent-xx-0001", total_tokens=1200),
        _agent_event(agent="ai-explore", span_id="span-agent-xx-0002", total_tokens=400),
    ]
    _seed_ndjson(project_root, events)
    runner.invoke(create_app(), ["audit", "index"])


def test_tokens_by_skill(project_root: Path) -> None:
    """Skill rollup lists every distinct skill with summed tokens."""
    _seed_mixed_corpus(project_root)
    result = runner.invoke(create_app(), ["audit", "tokens", "--by", "skill"])
    assert result.exit_code == 0, result.output
    # Both skills must appear in the table.
    assert "ai-brainstorm" in result.output
    assert "ai-plan" in result.output
    # Sums: brainstorm = 900, plan = 900.
    assert "900" in result.output


def test_tokens_by_agent(project_root: Path) -> None:
    """Agent rollup lists ``ai-explore`` summed across both dispatches."""
    _seed_mixed_corpus(project_root)
    result = runner.invoke(create_app(), ["audit", "tokens", "--by", "agent"])
    assert result.exit_code == 0, result.output
    assert "ai-explore" in result.output
    # Sum: 1200 + 400 = 1600.
    assert "1600" in result.output


def test_tokens_by_session(project_root: Path) -> None:
    """Session rollup groups every event by ``sessionId``."""
    _seed_mixed_corpus(project_root)
    result = runner.invoke(create_app(), ["audit", "tokens", "--by", "session"])
    assert result.exit_code == 0, result.output
    assert "session-test-120" in result.output
    # Sum: 300 + 600 + 900 + 1200 + 400 = 3400.
    assert "3400" in result.output


def test_tokens_invalid_by_exits_nonzero(project_root: Path) -> None:
    """``--by garbage`` exits with code 2 and points to the valid set."""
    _seed_mixed_corpus(project_root)
    result = runner.invoke(create_app(), ["audit", "tokens", "--by", "garbage"])
    assert result.exit_code == 2, result.output
    assert "skill" in result.output  # mentions the valid set
    assert "agent" in result.output
    assert "session" in result.output


def test_tokens_json_output(project_root: Path) -> None:
    """``--json`` emits a JSON array of dicts with the rollup columns."""
    _seed_mixed_corpus(project_root)
    result = runner.invoke(
        create_app(),
        ["audit", "tokens", "--by", "skill", "--json"],
    )
    assert result.exit_code == 0, result.output
    last_json = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("[")
    )
    payload = json.loads(last_json)
    assert isinstance(payload, list)
    assert len(payload) == 2
    skills = {row["skill"]: row["total_tokens"] for row in payload}
    assert skills == {"ai-brainstorm": 900, "ai-plan": 900}


def test_tokens_missing_index_returns_empty(project_root: Path) -> None:
    """With no NDJSON + no SQLite, ``audit tokens`` returns ``(no rows)``."""
    result = runner.invoke(create_app(), ["audit", "tokens", "--by", "skill"])
    assert result.exit_code == 0, result.output
    assert "(no rows)" in result.output


def test_tokens_missing_index_returns_empty_json(project_root: Path) -> None:
    """No NDJSON + ``--json`` -> ``[]`` on stdout."""
    result = runner.invoke(create_app(), ["audit", "tokens", "--by", "skill", "--json"])
    assert result.exit_code == 0, result.output
    last_line = next(
        line for line in reversed(result.output.splitlines()) if line.strip().startswith("[")
    )
    assert last_line.strip() == "[]"
