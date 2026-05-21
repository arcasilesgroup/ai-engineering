"""spec-148: ``ai-eng audit index`` is removed (files-only persistence).

There is no SQLite projection to build — framework-events.ndjson is the
single source of truth. The verb stays registered as a fail-loud stub
that exits non-zero with a clear message.
"""

from __future__ import annotations

from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app

runner = CliRunner()


def test_audit_index_removed_exits_nonzero() -> None:
    """`audit index` now exits non-zero with a 'removed' message."""
    result = runner.invoke(create_app(), ["audit", "index"])
    assert result.exit_code != 0
    assert "removed" in result.output.lower()


def test_audit_index_removed_with_rebuild_flag() -> None:
    """`audit index --rebuild` also hits the removed stub."""
    result = runner.invoke(create_app(), ["audit", "index", "--rebuild"])
    assert result.exit_code != 0
    assert "removed" in result.output.lower()
