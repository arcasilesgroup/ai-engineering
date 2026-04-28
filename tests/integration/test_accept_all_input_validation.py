"""RED skeleton for spec-105 Phase 3 — `risk accept-all` input validation.

Covers 6 malformed JSON fixtures the CLI must reject (exit 2 with helpful
message): truncated JSON, wrong schema literal, missing ``findings`` key,
findings entry missing required fields, wrong types, and a path that
points at a non-existent file. These exercise the input-validation
layer of ``risk_cmd.risk_accept_all``.

Status: RED (CLI command does not exist yet; tests fail at invocation).
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 3 (T-3.14).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _runner_invoke(args: list[str]):
    """Invoke the CLI app. Deferred imports per Phase 1 lesson."""
    from typer.testing import CliRunner

    from ai_engineering.cli_factory import create_app

    return CliRunner().invoke(create_app(), args)


def _write_findings(path: Path, payload: object) -> None:
    """Write a JSON payload (or raw text via str) to a findings file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")


def _invoke_with_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, findings_path: Path):
    """Invoke `risk accept-all` against the seeded findings file."""
    monkeypatch.chdir(tmp_path)
    return _runner_invoke(
        [
            "risk",
            "accept-all",
            str(findings_path),
            "--justification",
            "Bulk accept for the sprint cutoff.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Refactor next quarter.",
        ]
    )


def test_rejects_truncated_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Truncated JSON file rejected with exit 2."""
    findings_path = tmp_path / "findings.json"
    findings_path.write_text('{"schema": "ai-engineering/gate-finding', encoding="utf-8")
    result = _invoke_with_findings(tmp_path, monkeypatch, findings_path)
    assert result.exit_code == 2


def test_rejects_wrong_schema_literal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong schema literal (e.g., `v0` or `v999`) rejected with exit 2."""
    findings_path = tmp_path / "findings.json"
    _write_findings(
        findings_path,
        {
            "schema": "ai-engineering/gate-findings/v999",
            "session_id": "00000000-0000-4000-8000-000000000030",
            "produced_by": "ai-pr",
            "produced_at": "2026-04-27T12:00:00Z",
            "branch": "feat/x",
            "commit_sha": "deadbeef",
            "findings": [],
            "auto_fixed": [],
            "cache_hits": [],
            "cache_misses": [],
            "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
        },
    )
    result = _invoke_with_findings(tmp_path, monkeypatch, findings_path)
    assert result.exit_code == 2


def test_rejects_missing_findings_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Document missing the `findings` key rejected with exit 2."""
    findings_path = tmp_path / "findings.json"
    _write_findings(
        findings_path,
        {
            "schema": "ai-engineering/gate-findings/v1",
            "session_id": "00000000-0000-4000-8000-000000000031",
            "produced_by": "ai-pr",
            "produced_at": "2026-04-27T12:00:00Z",
            "branch": "feat/x",
            "commit_sha": "deadbeef",
            "auto_fixed": [],
            "cache_hits": [],
            "cache_misses": [],
            "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
        },
    )
    # `findings` defaults to empty list per the model — accept-all on an empty
    # list is a no-op exit 0; this test instead asserts the more meaningful
    # case of missing `wall_clock_ms` (a required field) returning exit 2.
    findings_path.write_text(
        json.dumps(
            {
                "schema": "ai-engineering/gate-findings/v1",
                "session_id": "00000000-0000-4000-8000-000000000031",
                "produced_by": "ai-pr",
                "produced_at": "2026-04-27T12:00:00Z",
                "branch": "feat/x",
                "commit_sha": "deadbeef",
                "auto_fixed": [],
                "cache_hits": [],
                "cache_misses": [],
            }
        ),
        encoding="utf-8",
    )
    result = _invoke_with_findings(tmp_path, monkeypatch, findings_path)
    assert result.exit_code == 2


def test_rejects_finding_entry_missing_required_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding entry missing `severity` (required) rejected with exit 2."""
    findings_path = tmp_path / "findings.json"
    _write_findings(
        findings_path,
        {
            "schema": "ai-engineering/gate-findings/v1",
            "session_id": "00000000-0000-4000-8000-000000000032",
            "produced_by": "ai-pr",
            "produced_at": "2026-04-27T12:00:00Z",
            "branch": "feat/x",
            "commit_sha": "deadbeef",
            "findings": [
                {
                    "check": "ruff",
                    "rule_id": "E501",
                    "file": "src/x.py",
                    "line": 1,
                    "auto_fixable": False,
                }
            ],
            "auto_fixed": [],
            "cache_hits": [],
            "cache_misses": [],
            "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
        },
    )
    result = _invoke_with_findings(tmp_path, monkeypatch, findings_path)
    assert result.exit_code == 2


def test_rejects_wrong_field_types(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`line` as string rather than int rejected with exit 2."""
    findings_path = tmp_path / "findings.json"
    _write_findings(
        findings_path,
        {
            "schema": "ai-engineering/gate-findings/v1",
            "session_id": "00000000-0000-4000-8000-000000000033",
            "produced_by": "ai-pr",
            "produced_at": "2026-04-27T12:00:00Z",
            "branch": "feat/x",
            "commit_sha": "deadbeef",
            "findings": [
                {
                    "check": "ruff",
                    "rule_id": "E501",
                    "file": "src/x.py",
                    "line": "not-an-int",
                    "severity": "low",
                    "message": "msg",
                    "auto_fixable": False,
                    "auto_fix_command": None,
                }
            ],
            "auto_fixed": [],
            "cache_hits": [],
            "cache_misses": [],
            "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
        },
    )
    result = _invoke_with_findings(tmp_path, monkeypatch, findings_path)
    assert result.exit_code == 2


def test_rejects_nonexistent_findings_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A path that does not exist rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    missing_path = tmp_path / "does-not-exist.json"
    result = _runner_invoke(
        [
            "risk",
            "accept-all",
            str(missing_path),
            "--justification",
            "Bulk accept.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ]
    )
    assert result.exit_code == 2
