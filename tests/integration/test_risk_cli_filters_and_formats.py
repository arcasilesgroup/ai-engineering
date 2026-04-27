"""Filter and formatter coverage for ``cli_commands/risk_cmd.py``.

Exercises real surface that the per-command happy-path E2Es in
``test_risk_cli_per_command.py`` skip:

* ``risk list --format markdown`` -- markdown table renderer.
* ``risk list --format table`` -- default human renderer.
* ``risk list --severity ...`` and ``--expires-within ...`` filters.
* ``risk show --format json``.
* ``risk show <missing-id>`` error path.
* Validation errors: empty ``--spec``, empty ``--follow-up``, empty
  ``--finding-id``, malformed ``--expires-at``, invalid ``--accepted-by``.
* ``--accepted-by`` actor override.
* ``risk renew``/``risk resolve``/``risk revoke`` against an unknown DEC ID.

These are real branches behind user-facing behavior, not coverage padding.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()


def _accept_one(tmp_path: Path, *, finding_id: str = "X", severity: str = "low") -> str:
    """Run ``risk accept`` once and return the persisted DEC ID."""
    app = create_app()
    result = runner.invoke(
        app,
        [
            "risk",
            "accept",
            "--finding-id",
            finding_id,
            "--severity",
            severity,
            "--justification",
            "Filter-and-format coverage seed.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan refactor.",
        ],
    )
    assert result.exit_code == 0, result.output
    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    return store["decisions"][-1]["id"]


def test_risk_list_markdown_renders_pipe_separated_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--format markdown`` emits a pipe-separated table with the DEC ID."""
    monkeypatch.chdir(tmp_path)
    dec_id = _accept_one(tmp_path, finding_id="MD-1")
    app = create_app()
    result = runner.invoke(app, ["risk", "list", "--format", "markdown"])
    assert result.exit_code == 0, result.output
    assert "| DEC ID | Status | Severity | Finding | Expires |" in result.output
    assert dec_id in result.output


def test_risk_list_table_renders_human_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Default ``--format table`` prints a header and one entry per decision."""
    monkeypatch.chdir(tmp_path)
    _accept_one(tmp_path, finding_id="TBL-1")
    app = create_app()
    result = runner.invoke(app, ["risk", "list", "--format", "table"])
    assert result.exit_code == 0, result.output
    assert "Risk acceptances" in result.output
    assert "TBL-1" in result.output


def test_risk_list_severity_filter_excludes_other_levels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--severity medium`` returns only medium-severity decisions."""
    monkeypatch.chdir(tmp_path)
    _accept_one(tmp_path, finding_id="LOW-1", severity="low")
    _accept_one(tmp_path, finding_id="MED-1", severity="medium")
    app = create_app()
    result = runner.invoke(app, ["risk", "list", "--severity", "medium", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert all(d.get("severity") == "medium" for d in payload)
    assert any(d.get("findingId") == "MED-1" for d in payload)


def test_risk_list_expires_within_filters_to_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--expires-within`` keeps decisions whose expiry lands inside the window."""
    monkeypatch.chdir(tmp_path)
    _accept_one(tmp_path, finding_id="EXP-1")
    app = create_app()
    result = runner.invoke(app, ["risk", "list", "--expires-within", "365", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    # Default TTL puts low-severity acceptances within the year window.
    assert any(d.get("findingId") == "EXP-1" for d in payload)


def test_risk_list_status_all_includes_revoked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--status all`` keeps non-active entries in the listing."""
    monkeypatch.chdir(tmp_path)
    dec_id = _accept_one(tmp_path, finding_id="ALL-1")
    app = create_app()
    revoke = runner.invoke(app, ["risk", "revoke", dec_id, "--reason", "no longer needed"])
    assert revoke.exit_code == 0, revoke.output
    result = runner.invoke(app, ["risk", "list", "--status", "all", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    statuses = {d.get("status") for d in payload}
    assert "revoked" in statuses


def test_risk_show_json_returns_full_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``risk show --format json`` returns the canonical Decision payload."""
    monkeypatch.chdir(tmp_path)
    dec_id = _accept_one(tmp_path, finding_id="SHOW-1")
    app = create_app()
    result = runner.invoke(app, ["risk", "show", dec_id, "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload.get("id") == dec_id
    assert payload.get("findingId") == "SHOW-1"


def test_risk_show_unknown_dec_returns_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unknown DEC ID surfaces exit-1 with a descriptive error."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["risk", "show", "DEC-MISSING"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_risk_show_invalid_format_returns_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unsupported ``--format`` value rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["risk", "show", "DEC-X", "--format", "yaml"])
    assert result.exit_code == 2


def test_risk_list_invalid_format_returns_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unsupported ``--format`` value on list rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["risk", "list", "--format", "yaml"])
    assert result.exit_code == 2


def test_risk_list_invalid_status_returns_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unsupported ``--status`` value rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["risk", "list", "--status", "purgatory"])
    assert result.exit_code == 2


def test_risk_renew_unknown_dec_returns_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Renewing an unknown DEC surfaces exit 1 from the lifecycle helper."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(
        app,
        [
            "risk",
            "renew",
            "DEC-MISSING",
            "--justification",
            "Need another quarter.",
            "--spec",
            "spec-105",
        ],
    )
    assert result.exit_code == 1


def test_risk_resolve_unknown_dec_returns_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolving an unknown DEC surfaces exit 1."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(
        app,
        ["risk", "resolve", "DEC-MISSING", "--note", "fix landed in PR-9"],
    )
    assert result.exit_code == 1


def test_risk_revoke_unknown_dec_returns_exit_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Revoking an unknown DEC surfaces exit 1."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(app, ["risk", "revoke", "DEC-MISSING", "--reason", "obsolete"])
    assert result.exit_code == 1


def test_risk_accept_rejects_empty_spec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty ``--spec`` is rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(
        app,
        [
            "risk",
            "accept",
            "--finding-id",
            "S",
            "--severity",
            "low",
            "--justification",
            "Reasoning for the spec edge case.",
            "--spec",
            "   ",
            "--follow-up",
            "Plan.",
        ],
    )
    assert result.exit_code == 2


def test_risk_accept_rejects_empty_follow_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty ``--follow-up`` is rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(
        app,
        [
            "risk",
            "accept",
            "--finding-id",
            "S",
            "--severity",
            "low",
            "--justification",
            "Reasoning for the follow-up edge case.",
            "--spec",
            "spec-105",
            "--follow-up",
            "   ",
        ],
    )
    assert result.exit_code == 2


def test_risk_accept_rejects_empty_finding_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty ``--finding-id`` is rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(
        app,
        [
            "risk",
            "accept",
            "--finding-id",
            "   ",
            "--severity",
            "low",
            "--justification",
            "Reasoning for the finding-id edge case.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
        ],
    )
    assert result.exit_code == 2


def test_risk_accept_rejects_malformed_expires_at(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-ISO-8601 ``--expires-at`` is rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(
        app,
        [
            "risk",
            "accept",
            "--finding-id",
            "T",
            "--severity",
            "low",
            "--justification",
            "Reasoning for the expires-at edge case.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
            "--expires-at",
            "tomorrow",
        ],
    )
    assert result.exit_code == 2


def test_risk_accept_with_explicit_actor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``--accepted-by`` overrides the git-derived default actor."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(
        app,
        [
            "risk",
            "accept",
            "--finding-id",
            "ACT-1",
            "--severity",
            "low",
            "--justification",
            "Actor override path coverage.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
            "--accepted-by",
            "spec105-tester",
        ],
    )
    assert result.exit_code == 0, result.output
    store_path = tmp_path / ".ai-engineering" / "state" / "decision-store.json"
    store = json.loads(store_path.read_text(encoding="utf-8"))
    assert store["decisions"][0].get("acceptedBy") == "spec105-tester"


def test_risk_accept_rejects_invalid_actor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``--accepted-by`` with whitespace/prose is rejected with exit 2."""
    monkeypatch.chdir(tmp_path)
    app = create_app()
    result = runner.invoke(
        app,
        [
            "risk",
            "accept",
            "--finding-id",
            "ACT-2",
            "--severity",
            "low",
            "--justification",
            "Invalid actor exit-2 path coverage.",
            "--spec",
            "spec-105",
            "--follow-up",
            "Plan.",
            "--accepted-by",
            "the security team",
        ],
    )
    assert result.exit_code == 2
