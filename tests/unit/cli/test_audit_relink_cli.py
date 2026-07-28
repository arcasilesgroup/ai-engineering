"""spec-201 sub-001 T-1.3/T-1.4: ``ai-eng audit relink``.

The operator-facing repair verb for the two hash-chained ledgers. It is a
*write* verb on tamper-evidence, so the CLI contract pinned here is
deliberately narrow:

* ``--dry-run`` reports without touching a byte (the documented first step);
* ``--file`` targets one ledger, and an unknown value is a hard error
  rather than a silent default (unlike the read-only ``audit verify``);
* the repaired ledger verifies clean afterwards;
* the global ``--json`` flag emits a machine-readable envelope.

Each test pins ``cwd`` to a fresh ``tmp_path`` so the project's real
ledgers are never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.state.audit_chain import compute_entry_hash, verify_audit_chain

runner = CliRunner()


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Anchor cwd at ``tmp_path`` so the audit CLI sees a fresh root."""
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _entries(count: int, *, field: str) -> list[dict]:
    entries: list[dict] = []
    prior: str | None = None
    for index in range(count):
        entry = {
            "kind": "framework_operation",
            "timestamp": f"2026-07-27T00:00:{index:02d}Z",
            "detail": {"operation": f"op-{index}"},
            field: prior,
        }
        entries.append(entry)
        prior = compute_entry_hash(entry)
    return entries


def _seed_broken_events(project_root: Path) -> Path:
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    entries = _entries(4, field="prev_event_hash")
    entries[2]["prev_event_hash"] = "0" * 64
    path.write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in entries),
        encoding="utf-8",
    )
    return path


def _seed_broken_decisions(project_root: Path) -> Path:
    path = project_root / ".ai-engineering" / "state" / "decision-store.json"
    decisions = _entries(3, field="prevEventHash")
    decisions[1]["prevEventHash"] = "0" * 64
    path.write_text(
        json.dumps(
            {"active_decisions": [], "decisions": decisions, "schemaVersion": "1.1"},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_relink_events_repairs_the_chain(project_root: Path) -> None:
    """The default text path repairs the events ledger and exits 0."""
    path = _seed_broken_events(project_root)
    assert not verify_audit_chain(path, mode="ndjson").ok

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events"])

    assert result.exit_code == 0, result.output
    assert verify_audit_chain(path, mode="ndjson").ok
    assert "1" in result.output


def test_relink_decisions_repairs_the_chain(project_root: Path) -> None:
    """``--file decisions`` repairs the git-tracked ledger."""
    path = _seed_broken_decisions(project_root)

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "decisions"])

    assert result.exit_code == 0, result.output
    assert verify_audit_chain(path, mode="json_array").ok


def test_relink_file_filter_scopes_the_repair(project_root: Path) -> None:
    """``--file decisions`` leaves the events ledger untouched."""
    events = _seed_broken_events(project_root)
    _seed_broken_decisions(project_root)
    before = events.read_bytes()

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "decisions"])

    assert result.exit_code == 0, result.output
    assert events.read_bytes() == before


def test_relink_dry_run_writes_nothing(project_root: Path) -> None:
    """``--dry-run`` reports the count without touching the ledger."""
    path = _seed_broken_events(project_root)
    before = path.read_bytes()

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert path.read_bytes() == before
    assert not verify_audit_chain(path, mode="ndjson").ok


def test_relink_json_envelope(project_root: Path) -> None:
    """The global ``--json`` flag emits a machine-readable envelope."""
    _seed_broken_events(project_root)

    result = runner.invoke(create_app(), ["--json", "audit", "relink", "--file", "events"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output[result.output.index("{") :])
    assert payload["ok"] is True
    relinks = payload["result"]["relinks"]
    assert [r["file"] for r in relinks] == ["events"]
    assert relinks[0]["relinked"] == 1
    assert relinks[0]["written"] is True


def test_relink_json_dry_run_reports_written_false(project_root: Path) -> None:
    _seed_broken_events(project_root)

    result = runner.invoke(
        create_app(), ["--json", "audit", "relink", "--file", "events", "--dry-run"]
    )

    payload = json.loads(result.output[result.output.index("{") :])
    relinks = payload["result"]["relinks"]
    assert relinks[0]["relinked"] == 1
    assert relinks[0]["written"] is False


def test_relink_defaults_to_both_ledgers(project_root: Path) -> None:
    """With no ``--file`` the verb repairs both ledgers."""
    events = _seed_broken_events(project_root)
    decisions = _seed_broken_decisions(project_root)

    result = runner.invoke(create_app(), ["audit", "relink"])

    assert result.exit_code == 0, result.output
    assert verify_audit_chain(events, mode="ndjson").ok
    assert verify_audit_chain(decisions, mode="json_array").ok


def test_relink_rejects_unknown_file_filter(project_root: Path) -> None:
    """A write verb fails loud on a typo instead of defaulting to 'all'."""
    path = _seed_broken_events(project_root)
    before = path.read_bytes()

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "evnts"])

    assert result.exit_code == 2
    assert path.read_bytes() == before


def test_relink_missing_ledger_is_a_noop(project_root: Path) -> None:
    """A repo with no ledger yet exits 0 and creates nothing."""
    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events"])

    assert result.exit_code == 0, result.output
    assert not (project_root / ".ai-engineering" / "state" / "framework-events.ndjson").exists()


def test_relink_refuses_an_unparseable_ledger(project_root: Path) -> None:
    """A malformed ledger is reported (exit 1) and never rewritten."""
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    path.write_text('{"kind": "a"}\nnot json\n', encoding="utf-8")
    before = path.read_bytes()

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events"])

    assert result.exit_code == 1
    assert path.read_bytes() == before
