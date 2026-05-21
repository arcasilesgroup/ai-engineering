"""Unit tests for ai_engineering.cli_commands.decisions_cmd module.

Covers the four canonical decision subcommands -- ``list``, ``record``,
``expire-check``, ``backfill`` -- against the canonical
``decision-store.json`` (spec-148 P2 files-only). Seeds and assertions go
through the same file-backed ``decision_store_io`` adapter the CLI uses.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ai_engineering.cli_factory import create_app
from ai_engineering.state.decision_store_io import (
    list_decision_rows as list_decisions,
)
from ai_engineering.state.decision_store_io import (
    upsert_decision_rows_raw,
)

runner = CliRunner()


def _seed_decision(root: Path, **overrides: object) -> dict[str, object]:
    """Seed one decision row into ``decision-store.json`` under *root*."""
    row: dict[str, object] = {
        "decision_id": "DEC-001",
        "spec_id": "spec-001",
        "status": "active",
        "title": "Test decision",
        "rationale": None,
        "context": "test context",
    }
    row.update(overrides)
    upsert_decision_rows_raw(root, [row])
    return row


class TestDecisionList:
    """Tests for `ai-eng decision list` against decision-store.json."""

    def test_empty_store_no_db(self, tmp_path: Path) -> None:
        """When no decision store exists, report empty + the backfill hint."""
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        assert result.exit_code == 0
        assert "empty" in result.output.lower()
        assert "backfill" in result.output.lower()

    def test_lists_single_decision(self, tmp_path: Path) -> None:
        _seed_decision(tmp_path)

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        assert result.exit_code == 0
        assert "DEC-001" in result.output
        assert "spec-001" in result.output
        assert "active" in result.output
        assert "Test decision" in result.output
        assert "1 total" in result.output

    def test_lists_multiple_decisions_sorted(self, tmp_path: Path) -> None:
        _seed_decision(tmp_path, decision_id="DEC-002", title="Second")
        _seed_decision(tmp_path, decision_id="DEC-001", title="First")

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "list"])

        assert result.exit_code == 0
        assert "DEC-001" in result.output
        assert "DEC-002" in result.output
        assert "2 total" in result.output
        # Sorted ascending: DEC-001 appears before DEC-002.
        assert result.output.index("DEC-001") < result.output.index("DEC-002")


class TestDecisionExpireCheck:
    """`expire-check` flags decisions whose ``expires_at`` is past or near."""

    def test_empty_store_reports_no_decisions(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        assert result.exit_code == 0
        assert "no active decisions" in result.output.lower()

    def test_decisions_without_expiry_are_within_validity(self, tmp_path: Path) -> None:
        _seed_decision(tmp_path)

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        assert result.exit_code == 0
        assert "within validity" in result.output.lower()

    def test_flags_expired_and_expiring_soon(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime, timedelta

        past = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
        soon = (datetime.now(tz=UTC) + timedelta(days=3)).isoformat()
        _seed_decision(tmp_path, decision_id="DEC-EXPIRED", expires_at=past)
        _seed_decision(tmp_path, decision_id="DEC-SOON", expires_at=soon)

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        assert result.exit_code == 0
        assert "expired" in result.output.lower()
        assert "DEC-EXPIRED" in result.output
        assert "expiring soon" in result.output.lower()
        assert "DEC-SOON" in result.output

    def test_non_active_decisions_skipped(self, tmp_path: Path) -> None:
        from datetime import UTC, datetime, timedelta

        past = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
        _seed_decision(
            tmp_path,
            decision_id="DEC-REVOKED",
            status="revoked",
            expires_at=past,
        )

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "expire-check"])

        assert result.exit_code == 0
        # Revoked decisions are excluded; status='active' filter applies.
        assert "no active decisions" in result.output.lower()


class TestDecisionRecord:
    """Tests for `ai-eng decision record` writing to decision-store.json."""

    def test_record_creates_new_decision(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "decision",
                    "record",
                    "d-test-001",
                    "--context",
                    "test context",
                    "--decision",
                    "test decision",
                    "--spec",
                    "spec-034",
                ],
            )

        assert result.exit_code == 0
        assert "Recorded" in result.output
        assert "d-test-001" in result.output
        rows = list_decisions(tmp_path)
        assert len(rows) == 1
        assert rows[0]["decision_id"] == "d-test-001"
        assert rows[0]["spec_id"] == "spec-034"
        assert rows[0]["status"] == "active"
        assert rows[0]["title"] == "test decision"

    def test_record_rejects_duplicate_id(self, tmp_path: Path) -> None:
        _seed_decision(tmp_path)

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(
                app,
                [
                    "decision",
                    "record",
                    "DEC-001",
                    "--context",
                    "dup",
                    "--decision",
                    "dup",
                ],
            )

        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_record_emits_framework_event(self, tmp_path: Path) -> None:
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            runner.invoke(
                app,
                [
                    "decision",
                    "record",
                    "d-test-005",
                    "--context",
                    "ctx",
                    "--decision",
                    "dec",
                ],
            )

        events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"
        assert events_path.exists()
        line = events_path.read_text().strip()
        event = json.loads(line)
        assert event["kind"] == "control_outcome"
        assert event["detail"]["control"] == "decision-record"
        assert event["detail"]["decision_id"] == "d-test-005"


class TestDecisionBackfill:
    """Tests for `ai-eng decision backfill` markdown scanning."""

    def _write_markdown(self, root: Path) -> None:
        specs_dir = root / ".ai-engineering" / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        (specs_dir / "spec-200-example.md").write_text(
            "## Decisions\n\n"
            "D-200-01: First decision in this spec.\n"
            "D-200-02: Second decision in this spec.\n",
            encoding="utf-8",
        )
        (root / "CHANGELOG.md").write_text(
            "# Changelog\n- D-201-01 ships in changelog only.\n",
            encoding="utf-8",
        )
        (root / "CONSTITUTION.md").write_text(
            "# Constitution\n\nno decision ids here.\n",
            encoding="utf-8",
        )
        (root / "CLAUDE.md").write_text(
            "# CLAUDE.md\nD-200-01 reference (should not override spec source).\n",
            encoding="utf-8",
        )

    def test_dry_run_lists_candidates_without_writing(self, tmp_path: Path) -> None:
        self._write_markdown(tmp_path)

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            result = runner.invoke(app, ["decision", "backfill", "--dry-run"])

        assert result.exit_code == 0
        assert "D-200-01" in result.output
        assert "D-200-02" in result.output
        assert "D-201-01" in result.output
        assert "Dry run" in result.output
        # Dry-run does not populate decision-store.json.
        assert list_decisions(tmp_path) == []

    def test_writes_and_dedups_via_upsert(self, tmp_path: Path) -> None:
        self._write_markdown(tmp_path)

        with patch(
            "ai_engineering.cli_commands.decisions_cmd.find_project_root",
            return_value=tmp_path,
        ):
            app = create_app()
            first = runner.invoke(app, ["decision", "backfill"])
            assert first.exit_code == 0
            rows_after_first = {r["decision_id"]: r for r in list_decisions(tmp_path)}

            # Idempotent re-run keeps the row count stable.
            second = runner.invoke(app, ["decision", "backfill"])
            assert second.exit_code == 0
            rows_after_second = {r["decision_id"]: r for r in list_decisions(tmp_path)}

        assert {"D-200-01", "D-200-02", "D-201-01"} <= rows_after_first.keys()
        assert rows_after_first.keys() == rows_after_second.keys()

        # Spec source wins over CLAUDE.md fallback for D-200-01 title.
        assert "First decision" in (rows_after_first["D-200-01"]["title"] or "")
        # Spec ID is parsed from the regex (`D-200-01` -> `spec-200`).
        assert rows_after_first["D-200-01"]["spec_id"] == "spec-200"
        # Changelog-only ID still landed.
        assert rows_after_first["D-201-01"]["spec_id"] == "spec-201"
