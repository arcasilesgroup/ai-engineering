"""spec-201 sub-001 T-4.1/T-4.2: ``ai-eng audit verify --strict``.

`audit verify` is advisory by construction (D-107-10): it always exits 0
so installs, doctor flows and CI are never blocked by a chain break.
`--strict` is the opt-in gate on top of that — an integrity boundary is
allowed to fail closed, but only when the caller asked for it.

The trap this file exists to close: the command has **two** exit paths.
The `--json` branch calls `emit_success(...)` and then bare-`return`s,
and `emit_success` only writes to stdout — it does not exit. A test that
covers only the text path ships a flag that is silently broken in JSON
mode, which is the mode every agent surface uses. Every assertion below
is therefore run against both {clean, broken} x {text, --json}.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_commands.audit_cmd import _audit_verify_machine_readable
from ai_engineering.cli_factory import create_app
from ai_engineering.state.audit_chain import compute_entry_hash

runner = CliRunner()


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _events(count: int) -> list[dict]:
    entries: list[dict] = []
    prior: str | None = None
    for index in range(count):
        entry = {
            "kind": "framework_operation",
            "timestamp": f"2026-07-27T00:00:{index:02d}Z",
            "detail": {"operation": f"op-{index}"},
            "prev_event_hash": prior,
        }
        entries.append(entry)
        prior = compute_entry_hash(entry)
    return entries


def _seed_events(project_root: Path, *, broken: bool) -> Path:
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    entries = _events(3)
    if broken:
        entries[2]["prev_event_hash"] = "0" * 64
    path.write_text(
        "".join(json.dumps(e, sort_keys=True) + "\n" for e in entries),
        encoding="utf-8",
    )
    return path


# ── {clean, broken} x {text, --json} ─────────────────────────────────────


def test_strict_text_clean_exits_zero(project_root: Path) -> None:
    _seed_events(project_root, broken=False)

    result = runner.invoke(create_app(), ["audit", "verify", "--file", "events", "--strict"])

    assert result.exit_code == 0, result.output


def test_strict_text_broken_exits_nonzero(project_root: Path) -> None:
    _seed_events(project_root, broken=True)

    result = runner.invoke(create_app(), ["audit", "verify", "--file", "events", "--strict"])

    assert result.exit_code != 0


def test_strict_json_clean_exits_zero(project_root: Path) -> None:
    _seed_events(project_root, broken=False)

    result = runner.invoke(
        create_app(), ["--json", "audit", "verify", "--file", "events", "--strict"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output[result.output.index("{") :])
    assert payload["result"]["verdicts"][0]["ok"] is True


def test_strict_json_broken_exits_nonzero_and_still_emits_the_envelope(
    project_root: Path,
) -> None:
    """Trap 6: the JSON branch returns early -- it must gate *after* emitting."""
    _seed_events(project_root, broken=True)

    result = runner.invoke(
        create_app(), ["--json", "audit", "verify", "--file", "events", "--strict"]
    )

    assert result.exit_code != 0
    payload = json.loads(result.output[result.output.index("{") :])
    assert payload["result"]["verdicts"][0]["ok"] is False


# ── the default stays advisory (D-107-10 holds for existing callers) ─────


def test_default_text_broken_still_exits_zero(project_root: Path) -> None:
    _seed_events(project_root, broken=True)

    result = runner.invoke(create_app(), ["audit", "verify", "--file", "events"])

    assert result.exit_code == 0, result.output


def test_default_json_broken_still_exits_zero(project_root: Path) -> None:
    _seed_events(project_root, broken=True)

    result = runner.invoke(create_app(), ["--json", "audit", "verify", "--file", "events"])

    assert result.exit_code == 0, result.output


# ── strict across both ledgers, and the third copy of the verdict logic ──


def test_strict_all_gates_on_any_ledger(project_root: Path) -> None:
    """A break in either ledger fails the gate, not just the first one."""
    _seed_events(project_root, broken=False)
    decisions = project_root / ".ai-engineering" / "state" / "decision-store.json"
    rows = _events(2)
    rows[1]["prev_event_hash"] = "0" * 64
    decisions.write_text(
        json.dumps({"decisions": rows, "schemaVersion": "1.1"}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(create_app(), ["audit", "verify", "--strict"])

    assert result.exit_code != 0


def test_machine_readable_helper_reports_the_same_verdict(project_root: Path) -> None:
    """The third copy of the verdict logic must not drift from the command."""
    _seed_events(project_root, broken=True)

    payload = _audit_verify_machine_readable("events")

    assert payload["verdicts"][0]["ok"] is False
    assert payload["ok"] is False
