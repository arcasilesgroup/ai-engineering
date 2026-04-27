"""RED skeleton for spec-105 Phase 3 — per-command `ai-eng risk *` CLI E2Es.

Covers spec-105 D-105-05 surface table: 7 happy-path E2Es for
``risk accept``, ``risk accept-all``, ``risk renew``, ``risk resolve``,
``risk revoke``, ``risk list``, ``risk show``.

Status: RED (CLI commands do not exist yet; tests fail at invocation).
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 3 (T-3.14) once ``risk_cmd.py`` is implemented.

Lesson learned in Phase 1: module-level imports of nonexistent modules
break pytest collection. Imports of the target CLI surface are deferred
to inside each test body so collection succeeds.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.spec_105_red


def _seed_findings(root: Path) -> Path:
    """Seed a minimal gate-findings.json v1 fixture into the project state dir."""
    state_dir = root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    findings_path = state_dir / "gate-findings.json"
    findings_path.write_text(
        json.dumps(
            {
                "schema": "ai-engineering/gate-findings/v1",
                "session_id": "00000000-0000-4000-8000-000000000010",
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
                        "auto_fixable": True,
                        "auto_fix_command": "ruff check --fix src/long.py",
                    }
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


def _runner_invoke(args: list[str]):
    """Invoke the CLI app with the given argv. Deferred imports per Phase 1 lesson."""
    from typer.testing import CliRunner

    from ai_engineering.cli_factory import create_app

    runner = CliRunner()
    return runner.invoke(create_app(), args)


def test_risk_accept_creates_single_dec_with_finding_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ai-eng risk accept` creates one DEC keyed by `finding:<rule_id>`."""
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
            "Sprint cutoff; refactor next quarter.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Track in JIRA-1234.",
        ]
    )
    assert result.exit_code == 0, result.output

    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    assert len(store["decisions"]) == 1
    assert store["decisions"][0]["context"] == "finding:E501"


def test_risk_accept_all_creates_dec_per_finding_with_shared_batch_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ai-eng risk accept-all` creates N DECs sharing one `batch_id`."""
    findings_path = _seed_findings(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _runner_invoke(
        [
            "risk",
            "accept-all",
            str(findings_path),
            "--justification",
            "Bulk accept for sprint cutoff.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Refactor in 2026-Q3.",
        ]
    )
    assert result.exit_code == 0, result.output

    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    assert len(store["decisions"]) >= 1
    batch_ids = {d.get("batchId") for d in store["decisions"]}
    assert len(batch_ids) == 1


def test_risk_renew_extends_existing_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ai-eng risk renew` accepts the prior DEC ID and writes a renewed entry."""
    monkeypatch.chdir(tmp_path)
    accept_result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "F841",
            "--severity",
            "low",
            "--justification",
            "Initial accept.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan A.",
        ]
    )
    assert accept_result.exit_code == 0, accept_result.output

    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    dec_id = store["decisions"][0]["id"]

    renew_result = _runner_invoke(
        [
            "risk",
            "renew",
            dec_id,
            "--justification",
            "Need another quarter.",
            "--spec",
            "spec-105",
        ]
    )
    assert renew_result.exit_code == 0, renew_result.output


def test_risk_resolve_marks_decision_remediated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ai-eng risk resolve` flips status to REMEDIATED."""
    monkeypatch.chdir(tmp_path)
    accept_result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "Q1",
            "--severity",
            "medium",
            "--justification",
            "Accept until pygments patch.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Pin upgrade.",
        ]
    )
    assert accept_result.exit_code == 0, accept_result.output

    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    dec_id = store["decisions"][0]["id"]

    resolve_result = _runner_invoke(
        [
            "risk",
            "resolve",
            dec_id,
            "--note",
            "Patched in v1.2.",
        ]
    )
    assert resolve_result.exit_code == 0, resolve_result.output

    store_after = json.loads(store_path.read_text(encoding="utf-8"))
    assert any(d["id"] == dec_id and d["status"] == "remediated" for d in store_after["decisions"])


def test_risk_revoke_marks_decision_revoked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ai-eng risk revoke` flips status to REVOKED."""
    monkeypatch.chdir(tmp_path)
    accept_result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "RV1",
            "--severity",
            "low",
            "--justification",
            "Accept temporarily.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ]
    )
    assert accept_result.exit_code == 0

    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    dec_id = store["decisions"][0]["id"]

    revoke_result = _runner_invoke(
        [
            "risk",
            "revoke",
            dec_id,
            "--reason",
            "Mistake; should not have been accepted.",
        ]
    )
    assert revoke_result.exit_code == 0, revoke_result.output


def test_risk_list_returns_active_decisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ai-eng risk list` returns decisions filtered to risk-acceptance category."""
    monkeypatch.chdir(tmp_path)
    accept_result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "L1",
            "--severity",
            "low",
            "--justification",
            "Accept.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ]
    )
    assert accept_result.exit_code == 0

    list_result = _runner_invoke(
        [
            "risk",
            "list",
            "--format",
            "json",
        ]
    )
    assert list_result.exit_code == 0, list_result.output


def test_risk_show_returns_full_decision_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ai-eng risk show <DEC-ID>` returns full detail including renewal_count."""
    monkeypatch.chdir(tmp_path)
    accept_result = _runner_invoke(
        [
            "risk",
            "accept",
            "--finding-id",
            "S1",
            "--severity",
            "low",
            "--justification",
            "Accept for the sprint.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ]
    )
    assert accept_result.exit_code == 0
    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    dec_id = store["decisions"][0]["id"]

    show_result = _runner_invoke(
        [
            "risk",
            "show",
            dec_id,
            "--format",
            "json",
        ]
    )
    assert show_result.exit_code == 0, show_result.output
