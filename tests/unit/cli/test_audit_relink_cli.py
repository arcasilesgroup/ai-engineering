"""spec-201 sub-001 T-1.3/T-1.4: ``ai-eng audit relink``.

The operator-facing repair verb for the two hash-chained ledgers. It is a
*write* verb on tamper-evidence, so the CLI contract pinned here is
deliberately narrow:

* it is report-only until ``--write`` (spec-201 H9): the default invocation
  cannot consume tamper-evidence;
* ``--write`` leaves a ``<name>.bak`` beside each ledger it rewrites and
  records the repair as an ``audit_relink`` ``framework_operation``;
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


def _relink_events(project_root: Path) -> dict:
    """Return the ``audit_relink`` event recorded in the events ledger."""
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not path.exists():
        return {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if (event.get("detail") or {}).get("operation") == "audit_relink":
            return event
    return {}


def test_relink_events_repairs_the_chain(project_root: Path) -> None:
    """``--write`` repairs the events ledger and exits 0."""
    path = _seed_broken_events(project_root)
    assert not verify_audit_chain(path, mode="ndjson").ok

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events", "--write"])

    assert result.exit_code == 0, result.output
    assert verify_audit_chain(path, mode="ndjson").ok
    assert "1" in result.output


def test_relink_decisions_repairs_the_chain(project_root: Path) -> None:
    """``--file decisions`` repairs the git-tracked ledger."""
    path = _seed_broken_decisions(project_root)

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "decisions", "--write"])

    assert result.exit_code == 0, result.output
    assert verify_audit_chain(path, mode="json_array").ok


def test_relink_file_filter_scopes_the_repair(project_root: Path) -> None:
    """``--file decisions`` never re-stamps the events ledger.

    The events ledger does gain the ``audit_relink`` record — that is where the
    audit chain lives — so the assertion is on the seeded entries: every one of
    them, including the break, must survive byte-identical.
    """
    events = _seed_broken_events(project_root)
    _seed_broken_decisions(project_root)
    seeded = events.read_text(encoding="utf-8").splitlines()

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "decisions", "--write"])

    assert result.exit_code == 0, result.output
    after = events.read_text(encoding="utf-8").splitlines()
    assert after[: len(seeded)] == seeded
    assert not verify_audit_chain(events, mode="ndjson").ok, "the events break must survive"


def test_relink_without_write_reports_and_writes_nothing(project_root: Path) -> None:
    """The DEFAULT invocation cannot consume tamper-evidence (spec-201 H9).

    Doctor FAILs, the operator pastes the printed remedy — and before this the
    chain was silently re-stamped with no record, no backup and no prompt. The
    default now reports; ``--write`` is the deliberate second step.
    """
    path = _seed_broken_events(project_root)
    before = path.read_bytes()

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events"])

    assert result.exit_code == 0, result.output
    assert path.read_bytes() == before
    assert not verify_audit_chain(path, mode="ndjson").ok
    assert not list(path.parent.glob("*.bak"))
    assert not _relink_events(project_root)


def test_relink_write_leaves_a_backup_beside_the_ledger(project_root: Path) -> None:
    """``framework-events.ndjson`` is gitignored: the .bak is the only way back."""
    path = _seed_broken_events(project_root)
    before = path.read_bytes()

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events", "--write"])

    assert result.exit_code == 0, result.output
    backup = path.with_name(path.name + ".bak")
    assert backup.is_file()
    assert backup.read_bytes() == before, "the backup must hold the PRE-repair bytes"


def test_relink_write_records_the_repair_in_the_chain(project_root: Path) -> None:
    """A repair that leaves no trace is indistinguishable from a clean chain."""
    _seed_broken_events(project_root)

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events", "--write"])

    assert result.exit_code == 0, result.output
    event = _relink_events(project_root)
    assert event, "no audit_relink event recorded"
    recorded = event["detail"]["files"][0]
    assert recorded["file"] == "events"
    assert recorded["chain_ok_before"] is False
    assert recorded["first_break_index_before"] == 2
    assert recorded["relinked"] == 1
    assert recorded["entries_after"] == 4
    assert recorded["backup"] == "framework-events.ndjson.bak"


def test_relink_json_envelope(project_root: Path) -> None:
    """The global ``--json`` flag emits a machine-readable envelope."""
    _seed_broken_events(project_root)

    result = runner.invoke(
        create_app(), ["--json", "audit", "relink", "--file", "events", "--write"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output[result.output.index("{") :])
    assert payload["ok"] is True
    assert payload["result"]["event_recorded"] is True
    assert payload["result"]["backups"] == {"events": "framework-events.ndjson.bak"}
    relinks = payload["result"]["relinks"]
    assert [r["file"] for r in relinks] == ["events"]
    assert relinks[0]["relinked"] == 1
    assert relinks[0]["written"] is True


def test_relink_json_report_only_reports_written_false(project_root: Path) -> None:
    _seed_broken_events(project_root)

    result = runner.invoke(create_app(), ["--json", "audit", "relink", "--file", "events"])

    payload = json.loads(result.output[result.output.index("{") :])
    assert payload["result"]["dry_run"] is True
    relinks = payload["result"]["relinks"]
    assert relinks[0]["relinked"] == 1
    assert relinks[0]["written"] is False


def test_relink_defaults_to_both_ledgers(project_root: Path) -> None:
    """With no ``--file`` the verb repairs both ledgers."""
    events = _seed_broken_events(project_root)
    decisions = _seed_broken_decisions(project_root)

    result = runner.invoke(create_app(), ["audit", "relink", "--write"])

    assert result.exit_code == 0, result.output
    assert verify_audit_chain(events, mode="ndjson").ok
    assert verify_audit_chain(decisions, mode="json_array").ok


def test_relink_rejects_unknown_file_filter(project_root: Path) -> None:
    """A write verb fails loud on a typo instead of defaulting to 'all'."""
    path = _seed_broken_events(project_root)
    before = path.read_bytes()

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "evnts", "--write"])

    assert result.exit_code == 2
    assert path.read_bytes() == before


def test_relink_missing_ledger_is_a_noop(project_root: Path) -> None:
    """A repo with no ledger yet exits 0 and creates nothing."""
    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events", "--write"])

    assert result.exit_code == 0, result.output
    assert not (project_root / ".ai-engineering" / "state" / "framework-events.ndjson").exists()


def test_relink_refuses_an_unparseable_ledger(project_root: Path) -> None:
    """A malformed ledger is reported (exit 1) and never rewritten."""
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    path.write_text('{"kind": "a"}\nnot json\n', encoding="utf-8")
    before = path.read_bytes()

    result = runner.invoke(create_app(), ["audit", "relink", "--file", "events", "--write"])

    assert result.exit_code == 1
    assert path.read_bytes() == before
