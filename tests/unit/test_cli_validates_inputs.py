"""RED skeleton for spec-105 Phase 3 — `ai-eng risk *` input validation.

Covers 8 edge cases the CLI must reject (exit 2 with helpful message):
1. empty justification (zero chars)
2. whitespace-only justification (no real content)
3. missing required `--spec` flag
4. invalid `--severity` value
5. malformed `--expires-at` value
6. missing `--finding-id`
7. NULL/empty/whitespace `rule_id` in accept-all input (OQ-1: skip with warning,
   exit 0 if rest OK, telemetry ``category=risk-acceptance,
   control=invalid-rule-id-skipped``)
8. invalid `--accepted-by` actor format

Status: RED (CLI commands do not exist yet; tests fail at invocation).
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 3 (T-3.14) once ``risk_cmd.py`` validation lands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.spec_105_red


def _runner_invoke(args: list[str]):
    """Invoke the CLI app. Deferred imports per Phase 1 lesson."""
    from typer.testing import CliRunner

    from ai_engineering.cli_factory import create_app

    return CliRunner().invoke(create_app(), args)


def test_rejects_empty_justification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty `--justification` is rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "E501",
            "--severity",
            "low",
            "--justification",
            "",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ]
    )
    assert result.exit_code == 2


def test_rejects_whitespace_only_justification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Whitespace-only `--justification` is rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "E501",
            "--severity",
            "low",
            "--justification",
            "   \t\n   ",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ]
    )
    assert result.exit_code == 2


def test_rejects_missing_spec_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing `--spec` flag is rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "E501",
            "--severity",
            "low",
            "--justification",
            "Accept this finding for the sprint cutoff.",
            "--follow-up",
            "Plan.",
        ]
    )
    assert result.exit_code == 2


def test_rejects_invalid_severity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid `--severity` value rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "E501",
            "--severity",
            "ultra-mega",
            "--justification",
            "Accept this finding.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ]
    )
    assert result.exit_code == 2


def test_rejects_malformed_expires_at(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Malformed `--expires-at` value rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "E501",
            "--severity",
            "low",
            "--justification",
            "Accept this finding.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
            "--expires-at",
            "not-a-date",
        ]
    )
    assert result.exit_code == 2


def test_rejects_missing_finding_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing `--finding-id` flag rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    result = _runner_invoke(
        [
            "risk",
            "accept",
            "--severity",
            "low",
            "--justification",
            "Accept this finding.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ]
    )
    assert result.exit_code == 2


def test_skips_findings_with_null_or_whitespace_rule_id_in_accept_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OQ-1: NULL/empty/whitespace `rule_id` in accept-all input is skipped.

    The CLI must skip such findings with a warning message, emit a
    telemetry event ``category=risk-acceptance,
    control=invalid-rule-id-skipped`` per skipped finding, and return
    exit 0 (not 2) provided the remaining findings parse cleanly.
    """
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    findings_path = state_dir / "gate-findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "schema": "ai-engineering/gate-findings/v1",
                "session_id": "00000000-0000-4000-8000-000000000020",
                "produced_by": "ai-pr",
                "produced_at": "2026-04-27T12:00:00Z",
                "branch": "feat/spec-101-installer-robustness",
                "commit_sha": "deadbeef",
                "findings": [
                    {
                        "check": "ruff",
                        "rule_id": "",
                        "file": "src/long.py",
                        "line": 120,
                        "column": None,
                        "severity": "low",
                        "message": "missing rule id",
                        "auto_fixable": False,
                        "auto_fix_command": None,
                    },
                    {
                        "check": "ruff",
                        "rule_id": "E501",
                        "file": "src/long.py",
                        "line": 120,
                        "column": None,
                        "severity": "low",
                        "message": "line too long",
                        "auto_fixable": True,
                        "auto_fix_command": "ruff check --fix src/long.py",
                    },
                ],
                "auto_fixed": [],
                "cache_hits": [],
                "cache_misses": [],
                "wall_clock_ms": {"wave1_fixers": 0, "wave2_checkers": 0, "total": 0},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = _runner_invoke(
        [
            "risk",
            "accept-all",
            str(findings_path),
            "--justification",
            "Accept everything for the sprint.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ]
    )
    assert result.exit_code == 0, result.output

    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    # Only the well-formed E501 finding should produce a DEC entry.
    assert len(store["decisions"]) == 1
    assert store["decisions"][0]["context"] == "finding:E501"

    events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
    assert events_path.exists()
    events = [
        json.loads(ln) for ln in events_path.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    assert any(
        e.get("detail", {}).get("category") == "risk-acceptance"
        and e.get("detail", {}).get("control") == "invalid-rule-id-skipped"
        for e in events
    )


def test_rejects_invalid_actor_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid `--accepted-by` actor (non-email-like) rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "E501",
            "--severity",
            "low",
            "--justification",
            "Accept this finding.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
            "--accepted-by",
            "not a valid actor with spaces",
        ]
    )
    assert result.exit_code == 2
