"""Integration tests for ``ai-eng maintenance reset-events`` (spec-114 G-5/G-6).

The reset-events subcommand is a one-shot gated archive operation:

* It moves the live ``framework-events.ndjson`` to a gzipped archive whose
  name matches D-114-05 (``framework-events.ndjson.legacy-<ISO>.gz``, with
  ``T`` and ``-`` only -- no ``:`` -- for cross-OS filesystem safety).
* It writes a fresh empty file with exactly one seed event matching
  D-114-06 (``framework_operation`` with ``component=maintenance.reset-events``,
  ``detail.reset_reason="spec-114 G-5"``, ``detail.previous_archive=<path>``).
* It refuses to run unless **both** gates pass:
    Gate 1 (R-1 mitigation): spec-110 commits exist in ``git log origin/main``.
    Gate 2 (R-8 mitigation): no ``legacy hash location detected`` log lines
    have been emitted in the last 24 h (i.e. no live readers still on the
    pre-spec-110 ``detail.prev_event_hash`` location).

Tests use :class:`typer.testing.CliRunner` so the gate-mock surface is the
:func:`ai_engineering.cli_commands.maintenance._spec_110_in_main` helper
(monkeypatched per test). Subprocess invocation is rejected on purpose:
mocking ``git log origin/main`` across a subprocess would require a stub
git binary on PATH, which makes the suite flaky on Windows runners and
adds a layer of indirection over a behaviour the helper already isolates.
"""

from __future__ import annotations

import gzip
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_commands import maintenance as maintenance_module
from ai_engineering.cli_factory import create_app

runner = CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _events_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


def _seed_event(
    *,
    timestamp: str,
    component: str = "test.fixture",
    kind: str = "framework_operation",
    engine: str = "ai_engineering",
    detail: dict | None = None,
) -> dict:
    """Build a schema-valid fixture event."""
    return {
        "kind": kind,
        "engine": engine,
        "timestamp": timestamp,
        "component": component,
        "outcome": "success",
        "correlationId": "00000000-0000-4000-8000-000000000001",
        "schemaVersion": "1.0",
        "project": "fixture",
        "detail": detail or {},
    }


def _write_events(project_root: Path, events: list[dict]) -> Path:
    path = _events_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, sort_keys=True, default=str) + "\n")
    return path


def _make_project(tmp_path: Path) -> Path:
    """Lay down the minimum scaffolding the resolver needs."""
    (tmp_path / ".ai-engineering").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# T-3.1 -- archive + fresh seed
# ---------------------------------------------------------------------------


def test_reset_archives_and_creates_fresh_ndjson(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reset moves NDJSON to ``.legacy-<ISO>.gz`` and writes a single seed event."""
    project = _make_project(tmp_path)
    original_event = _seed_event(
        timestamp="2026-04-29T12:00:00Z",
        component="fixture.original",
        detail={"note": "predates the reset"},
    )
    events_path = _write_events(project, [original_event])
    original_bytes = events_path.read_bytes()

    monkeypatch.setattr(maintenance_module, "_spec_110_in_main", lambda _root: True)

    app = create_app()
    result = runner.invoke(
        app,
        ["maintenance", "reset-events", "--target", str(project)],
    )

    assert result.exit_code == 0, result.stdout

    archives = sorted(
        (project / ".ai-engineering" / "state").glob("framework-events.ndjson.legacy-*.gz")
    )
    assert len(archives) == 1, f"expected one archive, found {archives}"
    archive = archives[0]
    # D-114-05 naming: framework-events.ndjson.legacy-YYYY-MM-DDTHH-MM-SS.gz
    assert re.fullmatch(
        r"framework-events\.ndjson\.legacy-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.gz",
        archive.name,
    ), f"archive name {archive.name} does not match D-114-05"
    assert ":" not in archive.name, "archive name must not contain ':' (cross-OS safety)"

    with gzip.open(archive, "rb") as gz:
        archived_bytes = gz.read()
    assert archived_bytes == original_bytes

    fresh_text = events_path.read_text(encoding="utf-8")
    fresh_lines = [line for line in fresh_text.splitlines() if line.strip()]
    assert len(fresh_lines) == 1, f"expected exactly 1 seed event, got {len(fresh_lines)}"
    seed = json.loads(fresh_lines[0])

    # D-114-06 contract.
    assert seed["kind"] == "framework_operation"
    assert seed["engine"] == "ai_engineering"
    assert seed["component"] == "maintenance.reset-events"
    assert seed["outcome"] == "success"
    assert seed["detail"]["reset_reason"] == "spec-114 G-5"
    assert seed["detail"]["previous_archive"] == archive.name
    # Seed is the first event in the new chain -- pointer must be null.
    assert seed.get("prev_event_hash") is None


# ---------------------------------------------------------------------------
# T-3.2 -- refuse when spec-110 not yet merged into main
# ---------------------------------------------------------------------------


def test_reset_refuses_without_spec_110_in_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reset exits non-zero when spec-110 commits are absent from origin/main."""
    project = _make_project(tmp_path)
    _write_events(project, [_seed_event(timestamp="2026-04-29T11:00:00Z")])

    monkeypatch.setattr(maintenance_module, "_spec_110_in_main", lambda _root: False)

    app = create_app()
    result = runner.invoke(
        app,
        ["maintenance", "reset-events", "--target", str(project)],
    )

    assert result.exit_code != 0, result.stdout
    combined = (result.stdout or "") + (result.stderr or "")
    assert "spec-110" in combined.lower()
    # No archive should have been produced.
    archives = list(
        (project / ".ai-engineering" / "state").glob("framework-events.ndjson.legacy-*.gz")
    )
    assert archives == []


# ---------------------------------------------------------------------------
# T-3.3 -- refuse when legacy reads are still happening within 24 h
# ---------------------------------------------------------------------------


def test_reset_refuses_with_recent_legacy_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reset refuses when the dual-read warning fired within the last 24 h."""
    project = _make_project(tmp_path)
    recent = (datetime.now(tz=UTC) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    legacy_marker = _seed_event(
        timestamp=recent,
        component="state.audit_chain",
        detail={"message": "legacy hash location detected at line 7"},
    )
    _write_events(project, [legacy_marker])

    # Spec-110 is in main; the legacy-read gate is the one we want to trip.
    monkeypatch.setattr(maintenance_module, "_spec_110_in_main", lambda _root: True)

    app = create_app()
    result = runner.invoke(
        app,
        ["maintenance", "reset-events", "--target", str(project)],
    )

    assert result.exit_code != 0, result.stdout
    combined = (result.stdout or "") + (result.stderr or "")
    assert "legacy" in combined.lower()
    archives = list(
        (project / ".ai-engineering" / "state").glob("framework-events.ndjson.legacy-*.gz")
    )
    assert archives == []


# ---------------------------------------------------------------------------
# T-3.4 -- ``--print-eligible-date`` returns now + 14 days
# ---------------------------------------------------------------------------


def test_reset_print_eligible_date(tmp_path: Path) -> None:
    """``--print-eligible-date`` prints today + 14d and exits 0 without side effects."""
    project = _make_project(tmp_path)
    _write_events(project, [_seed_event(timestamp="2026-04-29T10:00:00Z")])

    app = create_app()
    result = runner.invoke(
        app,
        ["maintenance", "reset-events", "--target", str(project), "--print-eligible-date"],
    )

    assert result.exit_code == 0, result.stdout
    today = datetime.now(tz=UTC).date()
    expected = today + timedelta(days=14)
    assert expected.isoformat() in result.stdout
    # No archive, no mutation.
    archives = list(
        (project / ".ai-engineering" / "state").glob("framework-events.ndjson.legacy-*.gz")
    )
    assert archives == []
    # Original NDJSON is untouched.
    text = _events_path(project).read_text(encoding="utf-8")
    assert "fixture" in text
