"""spec-148: ``ai-eng audit query`` is removed (files-only persistence).

Arbitrary SQL over the audit log required the SQLite projection, which no
longer exists. The verb stays registered as a fail-loud stub that exits
non-zero and points at the NDJSON-backed replacements (`audit tokens` /
`audit replay`).
"""

from __future__ import annotations

from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()


def test_audit_query_removed_exits_nonzero() -> None:
    """A SELECT invocation now exits non-zero with a 'removed' message."""
    result = runner.invoke(create_app(), ["audit", "query", "SELECT 1"])
    assert result.exit_code != 0
    assert "removed" in result.output.lower()


def test_audit_query_removed_points_to_replacements() -> None:
    """The error names the NDJSON-backed replacements."""
    result = runner.invoke(create_app(), ["audit", "query", "SELECT * FROM events"])
    assert result.exit_code != 0
    out = result.output.lower()
    assert "audit tokens" in out or "audit replay" in out or "ndjson" in out


def test_audit_query_removed_without_arg() -> None:
    """Even with no SQL argument the stub exits non-zero."""
    result = runner.invoke(create_app(), ["audit", "query"])
    assert result.exit_code != 0
