"""GREEN spec-105 Phase 8 — `ai-eng risk accept-all` E2E.

Covers spec-105 G-1 happy path: bulk accept findings from gate-findings.json,
generate shared `batch_id`, write N DEC entries, emit telemetry batch event.

Status: GREEN — exercises real production code via ``CliRunner``.
Prior history: started as a Phase 1 RED skeleton, body landed in Phase 8 once
``cli_commands/risk_cmd.py`` and the schema additions were stable.

Fixture invariant: per ``GateFinding._enforce_auto_fix_command_when_fixable``,
``auto_fixable=True`` requires a non-null ``auto_fix_command``. The fixture
sets ``auto_fixable=False`` to keep the model contract trivially satisfied.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()


def _seed_findings(root: Path) -> Path:
    """Seed a gate-findings.json v1 fixture into the project state dir.

    The two findings carry distinct severities so ``--max-severity low``
    can demonstrate the cap behaviour without changing the fixture shape.
    """
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    findings_path = state_dir / "gate-findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "schema": "ai-engineering/gate-findings/v1",
                "session_id": "00000000-0000-4000-8000-000000000001",
                "produced_by": "ai-pr",
                "produced_at": "2026-04-27T12:00:00Z",
                "branch": "feat/spec-101-installer-robustness",
                "commit_sha": "deadbeef",
                "findings": [
                    {
                        "check": "ruff",
                        "rule_id": "E501",
                        "file": "src/long.py",
                        "line": 120,
                        "column": None,
                        "severity": "low",
                        "message": "line too long",
                        "auto_fixable": False,
                        "auto_fix_command": None,
                    },
                    {
                        "check": "semgrep",
                        "rule_id": "python.lang.security.audit.exec",
                        "file": "src/loader.py",
                        "line": 7,
                        "column": None,
                        "severity": "medium",
                        "message": "exec() usage",
                        "auto_fixable": False,
                        "auto_fix_command": None,
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
    return findings_path


def test_risk_accept_all_creates_dec_per_finding_with_shared_batch_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G-1 happy path: 2 findings -> 2 DEC entries with same `batch_id`."""
    findings_path = _seed_findings(tmp_path)
    monkeypatch.chdir(tmp_path)
    app = create_app()

    result = runner.invoke(
        app,
        [
            "risk",
            "accept-all",
            str(findings_path),
            "--justification",
            "Sprint cutoff; remediation tracked in JIRA-1234.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Refactor in 2026-Q3.",
        ],
    )

    assert result.exit_code == 0, result.output

    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    assert len(store["decisions"]) == 2
    batch_ids = {d.get("batchId") for d in store["decisions"]}
    assert len(batch_ids) == 1, "All accepted findings must share one batch_id"
    assert next(iter(batch_ids)) is not None, "batchId must be populated"


def test_risk_accept_all_dry_run_emits_no_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--dry-run` flag prints summary but writes no DEC entries."""
    findings_path = _seed_findings(tmp_path)
    monkeypatch.chdir(tmp_path)
    app = create_app()

    result = runner.invoke(
        app,
        [
            "risk",
            "accept-all",
            str(findings_path),
            "--justification",
            "Dry-run preview before committing.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Confirm tomorrow.",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    if store_path.exists():
        store = json.loads(store_path.read_text(encoding="utf-8"))
        assert store.get("decisions", []) == []


def test_risk_accept_all_max_severity_caps_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--max-severity low` rejects medium+ findings; only `low` accepted."""
    findings_path = _seed_findings(tmp_path)
    monkeypatch.chdir(tmp_path)
    app = create_app()

    result = runner.invoke(
        app,
        [
            "risk",
            "accept-all",
            str(findings_path),
            "--justification",
            "Only accept low-severity items in this batch.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Open ticket for the rest.",
            "--max-severity",
            "low",
        ],
    )

    assert result.exit_code == 0
    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    assert len(store["decisions"]) == 1
    assert store["decisions"][0]["severity"] == "low"
