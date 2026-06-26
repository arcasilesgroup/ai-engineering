"""RED tests for the spec_lifecycle.py automation script (sub-spec sub-001).

Covers public CLI verbs (`start_new`, `mark_shipped`, `archive`, `sweep`,
`status`, `consolidate_shipped`) plus the one-shot `migrate_history`
migration. Each verb is a hexagonal composition of:

- domain (pure FSM): ``LifecycleState`` enum, ``transition`` validator,
  ``SpecRecord`` dataclass.
- infra (filesystem): JSON sidecar at
  ``.ai-engineering/state/specs/<spec_id>.json`` (atomic via tempfile +
  ``os.replace`` under ``artifact_lock``); ``_history.md`` markdown
  projection (7-col header); NDJSON appender to
  ``.ai-engineering/state/framework-events.ndjson`` using event-kind
  ``framework_operation``.
- application (CLI): ``argparse`` dispatch, idempotent semantics, perf
  budget <500ms per atomic op.

The tests below are written **first** (RED) and must fail at every assertion
until the GREEN phase (T-2.1 / T-2.2 / T-2.3) implements the script. After
GREEN they must continue to enforce the contract.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Windows GitHub runners pay a ~2x penalty on subprocess + filesystem IO
# compared with ubuntu/macOS. Keep the POSIX hot-path budget tight at
# 0.5s; grant Windows 1.0s so genuine regressions still trip the
# assertion without flaking on the slower platform.
_PERF_BUDGET_S = 1.0 if sys.platform.startswith("win") else 0.5

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _module_path() -> Path:
    """Path to the spec_lifecycle.py script under test."""
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / ".ai-engineering" / "scripts" / "spec_lifecycle.py"


@pytest.fixture
def lifecycle():
    """Import the spec_lifecycle module by file path (script-style import)."""
    path = _module_path()
    if not path.exists():
        pytest.fail(
            f"spec_lifecycle.py missing at {path}; "
            "RED tests must drive its creation in T-2.1/T-2.2/T-2.3"
        )
    spec = importlib.util.spec_from_file_location("spec_lifecycle", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["spec_lifecycle"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """A tmp project root with the canonical ``.ai-engineering/`` skeleton."""
    (tmp_path / ".ai-engineering" / "specs").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "state" / "locks").mkdir(parents=True)
    # Seed a 5-col legacy _history.md so migration tests have something
    # to migrate. start_new must overwrite the header on first call if
    # not yet 7-col, but legacy data rows must be preserved verbatim.
    (tmp_path / ".ai-engineering" / "specs" / "_history.md").write_text(
        "# Spec History\n"
        "\n"
        "Completed specs. Details in git history.\n"
        "\n"
        "| ID | Title | Status | Created | Branch |\n"
        "|----|-------|--------|---------|--------|\n"
        "| 099 | Legacy row | done | 2026-04-02 | feat/legacy |\n",
        encoding="utf-8",
    )
    return tmp_path


def _events(project_root: Path) -> list[dict]:
    """Read the NDJSON event stream as a list of JSON objects."""
    p = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text().splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------


class TestDomain:
    """Pure FSM has zero filesystem effects."""

    def test_lifecycle_state_enum_has_six_states(self, lifecycle):
        """Six explicit states; closed enum (no INVALID sentinel)."""
        states = {s.name for s in lifecycle.LifecycleState}
        assert states == {
            "DRAFT",
            "APPROVED",
            "IN_PROGRESS",
            "SHIPPED",
            "ABANDONED",
            "ARCHIVED",
        }

    def test_legal_transitions_table_is_total_function(self, lifecycle):
        """LEGAL_TRANSITIONS maps every state to its allowed next states."""
        table = lifecycle.LEGAL_TRANSITIONS
        # Every state appears as a key (even if value is empty for terminals).
        for state in lifecycle.LifecycleState:
            assert state in table, f"state {state} missing from table"

    def test_transition_rejects_illegal_move(self, lifecycle):
        """SHIPPED → DRAFT must raise; FSM is the gate."""
        with pytest.raises(ValueError):
            lifecycle.transition(
                lifecycle.LifecycleState.SHIPPED,
                lifecycle.LifecycleState.DRAFT,
            )

    def test_transition_accepts_legal_move(self, lifecycle):
        """DRAFT → APPROVED is allowed."""
        result = lifecycle.transition(
            lifecycle.LifecycleState.DRAFT,
            lifecycle.LifecycleState.APPROVED,
        )
        assert result is lifecycle.LifecycleState.APPROVED


# ---------------------------------------------------------------------------
# start_new
# ---------------------------------------------------------------------------


class TestStartNew:
    def test_creates_sidecar_in_draft_state(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        assert record.state is lifecycle.LifecycleState.DRAFT
        assert record.slug == "my-feature"
        assert record.title == "My Feature"
        sidecar = project_root / ".ai-engineering" / "state" / "specs" / f"{record.spec_id}.json"
        assert sidecar.exists()

    def test_idempotent_same_slug(self, lifecycle, project_root):
        first = lifecycle.start_new("my-feature", "My Feature", project_root)
        second = lifecycle.start_new("my-feature", "My Feature", project_root)
        assert first.spec_id == second.spec_id  # no duplicate ID minted.

    def test_emits_framework_operation_event(self, lifecycle, project_root):
        lifecycle.start_new("my-feature", "My Feature", project_root)
        events = _events(project_root)
        assert any(
            e.get("kind") == "framework_operation"
            and e.get("detail", {}).get("operation") == "spec_started"
            for e in events
        )

    def test_perf_budget_under_500ms(self, lifecycle, project_root):
        start = time.monotonic()
        lifecycle.start_new("my-feature", "My Feature", project_root)
        elapsed = time.monotonic() - start
        assert elapsed < _PERF_BUDGET_S, (
            f"start_new took {elapsed:.3f}s (>{_PERF_BUDGET_S}s budget)"
        )


# ---------------------------------------------------------------------------
# mark_shipped
# ---------------------------------------------------------------------------


class TestMarkShipped:
    def test_moves_record_to_shipped(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        # Move through the legal chain DRAFT → APPROVED → IN_PROGRESS → SHIPPED.
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        shipped = lifecycle.status(record.spec_id, project_root)
        assert shipped.state is lifecycle.LifecycleState.SHIPPED
        assert shipped.pr == "PR-101"
        assert shipped.branch == "feat/x"
        assert shipped.shipped is not None

    def test_idempotent_when_already_shipped(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        # Second invocation must NOT raise; record stays SHIPPED.
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        assert (
            lifecycle.status(record.spec_id, project_root).state is lifecycle.LifecycleState.SHIPPED
        )

    def test_already_shipped_record_rematerializes_missing_history_row(
        self, lifecycle, project_root
    ):
        """Shared consolidation can call mark_shipped on an already-SHIPPED sidecar."""
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        history.write_text(
            "# Spec History\n\n"
            "Completed specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n",
            encoding="utf-8",
        )

        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)

        # Rows key on the canonical numeric spec_id (spec-153 D-153-01).
        row_prefix = f"| {record.spec_id} |"
        rows = [line for line in history.read_text().splitlines() if line.startswith(row_prefix)]
        assert len(rows) == 1
        assert f"| {record.spec_id} | My Feature | shipped |" in rows[0]
        assert "PR-101" in rows[0]

    def test_rejects_illegal_transition_from_archived(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        lifecycle.archive(record.spec_id, project_root)
        with pytest.raises(ValueError):
            lifecycle.mark_shipped(record.spec_id, "PR-202", "feat/y", project_root)

    def test_atomic_write_preserves_old_record_on_error(self, lifecycle, project_root, monkeypatch):
        """If write_state raises mid-flight the on-disk sidecar is unchanged."""
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        sidecar = project_root / ".ai-engineering" / "state" / "specs" / f"{record.spec_id}.json"
        before = sidecar.read_text()
        # Force os.replace to fail so atomic-write semantics kick in.
        import os as _os

        original = _os.replace

        def _boom(*args, **kwargs):
            raise OSError("simulated rename failure")

        monkeypatch.setattr(_os, "replace", _boom)
        with pytest.raises(OSError):
            lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        monkeypatch.setattr(_os, "replace", original)
        # File contents must be unchanged (tempfile not promoted).
        assert sidecar.read_text() == before

    def test_appends_to_history_seven_columns(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        history = (project_root / ".ai-engineering" / "specs" / "_history.md").read_text()
        # Header row carries all seven canonical column names.
        for col in ("ID", "Title", "Status", "Created", "Shipped", "PR", "Branch"):
            assert col in history
        # Data row carries the record values.
        assert "PR-101" in history
        assert "feat/x" in history

    def test_emits_framework_operation_event(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        events = _events(project_root)
        assert any(
            e.get("kind") == "framework_operation"
            and e.get("detail", {}).get("operation") == "spec_shipped"
            for e in events
        )

    def test_perf_budget_under_500ms(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        start = time.monotonic()
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        elapsed = time.monotonic() - start
        assert elapsed < _PERF_BUDGET_S, (
            f"mark_shipped took {elapsed:.3f}s (>{_PERF_BUDGET_S}s budget)"
        )

    def test_upserts_existing_history_row_for_same_spec_id(self, lifecycle, project_root):
        """A stale approved row is replaced, not duplicated, when a spec ships."""
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        # Stale rows key on the canonical numeric spec_id (spec-153 D-153-01).
        sid = record.spec_id
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        history.write_text(
            "# Spec History\n\n"
            "Completed specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n"
            f"| {sid} | My Feature | approved | 2026-05-01 | — | — | feat/old |\n"
            f"| {sid} | My Feature | approved | 2026-05-02 | — | — | feat/duplicate |\n",
            encoding="utf-8",
        )

        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)

        row_prefix = f"| {sid} |"
        rows = [line for line in history.read_text().splitlines() if line.startswith(row_prefix)]
        assert len(rows) == 1
        assert f"| {sid} | My Feature | shipped |" in rows[0]
        assert "PR-101" in rows[0]


# ---------------------------------------------------------------------------
# consolidate_shipped
# ---------------------------------------------------------------------------


class TestConsolidateShipped:
    def test_appends_missing_history_row_for_existing_shipped_sidecar(
        self, lifecycle, project_root
    ):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        # Simulate a stale history file while the sidecar is already shipped.
        history.write_text(
            "# Spec History\n\n"
            "Completed specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n",
            encoding="utf-8",
        )

        summary = lifecycle.consolidate_shipped(project_root)

        assert summary["consolidated"] == 1
        text = history.read_text()
        # Rows key on the canonical numeric spec_id (spec-153 D-153-01).
        assert f"| {record.spec_id} | My Feature | shipped |" in text
        assert "PR-101" in text

    def test_dry_run_reports_without_mutating_history(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        history.write_text(
            "# Spec History\n\n"
            "Completed specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n",
            encoding="utf-8",
        )
        before = history.read_text()

        summary = lifecycle.consolidate_shipped(project_root, dry_run=True)

        assert summary["would_consolidate"] == [record.spec_id]
        assert history.read_text() == before


# ---------------------------------------------------------------------------
# archive
# ---------------------------------------------------------------------------


class TestArchive:
    def test_moves_shipped_to_archived(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        lifecycle.archive(record.spec_id, project_root)
        assert (
            lifecycle.status(record.spec_id, project_root).state
            is lifecycle.LifecycleState.ARCHIVED
        )

    def test_idempotent(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        lifecycle.archive(record.spec_id, project_root)
        lifecycle.archive(record.spec_id, project_root)  # no raise.
        assert (
            lifecycle.status(record.spec_id, project_root).state
            is lifecycle.LifecycleState.ARCHIVED
        )

    def test_rejects_archive_from_draft(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        with pytest.raises(ValueError):
            lifecycle.archive(record.spec_id, project_root)

    def test_emits_framework_operation_event(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        lifecycle.archive(record.spec_id, project_root)
        events = _events(project_root)
        assert any(
            e.get("kind") == "framework_operation"
            and e.get("detail", {}).get("operation") == "spec_archived"
            for e in events
        )

    def test_perf_budget_under_500ms(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        start = time.monotonic()
        lifecycle.archive(record.spec_id, project_root)
        elapsed = time.monotonic() - start
        assert elapsed < _PERF_BUDGET_S, f"archive took {elapsed:.3f}s (>{_PERF_BUDGET_S}s budget)"


# ---------------------------------------------------------------------------
# sweep
# ---------------------------------------------------------------------------


class TestSweep:
    def test_drafts_older_than_14_days_become_abandoned(self, lifecycle, project_root):
        record = lifecycle.start_new("stale-feature", "Stale", project_root)
        # Backdate the sidecar's `created` to 30 days ago.
        sidecar = project_root / ".ai-engineering" / "state" / "specs" / f"{record.spec_id}.json"
        data = json.loads(sidecar.read_text())
        from datetime import datetime, timedelta

        old = datetime.now(UTC) - timedelta(days=30)
        data["created"] = old.isoformat()
        sidecar.write_text(json.dumps(data))
        result = lifecycle.sweep(project_root)
        assert result.get("abandoned", 0) >= 1
        assert (
            lifecycle.status(record.spec_id, project_root).state
            is lifecycle.LifecycleState.ABANDONED
        )

    def test_drafts_younger_than_14_days_untouched(self, lifecycle, project_root):
        record = lifecycle.start_new("fresh-feature", "Fresh", project_root)
        result = lifecycle.sweep(project_root)
        assert result.get("abandoned", 0) == 0
        assert (
            lifecycle.status(record.spec_id, project_root).state is lifecycle.LifecycleState.DRAFT
        )

    def test_idempotent_repeated_sweep(self, lifecycle, project_root):
        lifecycle.start_new("fresh-feature", "Fresh", project_root)
        first = lifecycle.sweep(project_root)
        second = lifecycle.sweep(project_root)
        # Two consecutive sweeps with no clock change must not duplicate work.
        assert first == second

    def test_emits_framework_operation_event(self, lifecycle, project_root):
        lifecycle.start_new("fresh-feature", "Fresh", project_root)
        lifecycle.sweep(project_root)
        events = _events(project_root)
        assert any(
            e.get("kind") == "framework_operation"
            and e.get("detail", {}).get("operation") == "spec_sweep"
            for e in events
        )

    def test_perf_budget_under_500ms(self, lifecycle, project_root):
        # Seed a couple of sidecars so the sweep has work to do.
        for slug in ("a", "b", "c"):
            lifecycle.start_new(slug, slug.upper(), project_root)
        start = time.monotonic()
        lifecycle.sweep(project_root)
        elapsed = time.monotonic() - start
        assert elapsed < _PERF_BUDGET_S, f"sweep took {elapsed:.3f}s (>{_PERF_BUDGET_S}s budget)"

    def _backdate(self, project_root, spec_id: str, *, days: int) -> None:
        from datetime import timedelta

        sidecar = project_root / ".ai-engineering" / "state" / "specs" / f"{spec_id}.json"
        data = json.loads(sidecar.read_text())
        data["created"] = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        sidecar.write_text(json.dumps(data))

    def test_stale_draft_with_ship_signal_is_not_abandoned(
        self, lifecycle, project_root, monkeypatch
    ):
        # A stale DRAFT whose archive dir proves it shipped must NOT be abandoned.
        record = lifecycle.start_new("ship-signal", "Ship Signal", project_root)
        self._backdate(project_root, record.spec_id, days=30)
        arch = (
            project_root / ".ai-engineering" / "specs" / "archive" / f"{record.spec_id}-ship-signal"
        )
        arch.mkdir(parents=True, exist_ok=True)
        (arch / "spec.md").write_text("# shipped\n", encoding="utf-8")
        # Off a git repo: branch detection returns None -> not protected.
        result = lifecycle.sweep(project_root)
        assert result.get("abandoned", 0) == 0
        assert result.get("skipped_shipped", 0) >= 1
        assert (
            lifecycle.status(record.spec_id, project_root).state
            is not lifecycle.LifecycleState.ABANDONED
        )

    def test_protected_branch_refuses_inplace_writes(self, lifecycle, project_root, monkeypatch):
        record = lifecycle.start_new("stale-on-main", "Stale On Main", project_root)
        self._backdate(project_root, record.spec_id, days=30)

        def _fake_run(cmd, *args, **kwargs):
            from subprocess import CompletedProcess

            argv = [str(c) for c in cmd]
            if "rev-parse" in argv and "--abbrev-ref" in argv:
                return CompletedProcess(argv, 0, stdout="main\n", stderr="")
            return CompletedProcess(argv, 0, stdout="", stderr="")

        monkeypatch.setattr(lifecycle.subprocess, "run", _fake_run)
        result = lifecycle.sweep(project_root)
        assert result.get("protected_branch") == "main"
        assert result.get("skipped") == "on-protected-branch"
        assert result.get("abandoned", 0) == 0
        # No mutation: the stale draft remains DRAFT.
        assert (
            lifecycle.status(record.spec_id, project_root).state is lifecycle.LifecycleState.DRAFT
        )

    def test_dry_run_mutates_nothing(self, lifecycle, project_root, monkeypatch):
        record = lifecycle.start_new("dry-stale", "Dry Stale", project_root)
        self._backdate(project_root, record.spec_id, days=30)
        result = lifecycle.sweep(project_root, dry_run=True)
        # Reports the would-be abandon but does NOT write.
        assert result.get("abandoned", 0) >= 1
        assert (
            lifecycle.status(record.spec_id, project_root).state is lifecycle.LifecycleState.DRAFT
        )


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_returns_record_for_known_spec(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        result = lifecycle.status(record.spec_id, project_root)
        assert result.spec_id == record.spec_id
        assert result.state is lifecycle.LifecycleState.DRAFT

    def test_raises_for_unknown_spec(self, lifecycle, project_root):
        with pytest.raises((KeyError, FileNotFoundError)):
            lifecycle.status("does-not-exist", project_root)

    def test_idempotent_read_only(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        before = (
            project_root / ".ai-engineering" / "state" / "specs" / f"{record.spec_id}.json"
        ).read_text()
        lifecycle.status(record.spec_id, project_root)
        after = (
            project_root / ".ai-engineering" / "state" / "specs" / f"{record.spec_id}.json"
        ).read_text()
        assert before == after, "status() must not mutate the sidecar"

    def test_perf_budget_under_500ms(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        start = time.monotonic()
        lifecycle.status(record.spec_id, project_root)
        elapsed = time.monotonic() - start
        assert elapsed < _PERF_BUDGET_S, f"status took {elapsed:.3f}s (>{_PERF_BUDGET_S}s budget)"


# ---------------------------------------------------------------------------
# migrate_history (one-shot CLI subcommand from T-3.4)
# ---------------------------------------------------------------------------


class TestMigrateHistory:
    def test_migrates_legacy_5col_to_7col(self, lifecycle, project_root):
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        # Fixture seeded a 5-col legacy table (ID, Title, Status, Created, Branch).
        lifecycle.migrate_history(project_root)
        text = history.read_text()
        # New header.
        for col in ("ID", "Title", "Status", "Created", "Shipped", "PR", "Branch"):
            assert col in text
        # Legacy row preserved verbatim (Title + Branch from fixture).
        assert "Legacy row" in text
        assert "feat/legacy" in text

    def test_idempotent(self, lifecycle, project_root):
        lifecycle.migrate_history(project_root)
        first = (project_root / ".ai-engineering" / "specs" / "_history.md").read_text()
        lifecycle.migrate_history(project_root)
        second = (project_root / ".ai-engineering" / "specs" / "_history.md").read_text()
        # Already-migrated tables must be byte-identical on second run.
        assert first == second

    def test_preserves_freeform_retro_sections(self, lifecycle, project_root):
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        # Append a free-form retro section below the table.
        history.write_text(
            history.read_text() + "\n\n## spec-099 retro\n\nLessons learned: write tests first.\n"
        )
        lifecycle.migrate_history(project_root)
        text = history.read_text()
        assert "## spec-099 retro" in text
        assert "Lessons learned: write tests first." in text


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------


class TestCLI:
    def test_status_subcommand_exits_zero_on_known_spec(self, lifecycle, project_root, capsys):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        rc = lifecycle.main(["status", record.spec_id, "--project-root", str(project_root)])
        assert rc == 0

    def test_unknown_subcommand_returns_nonzero(self, lifecycle, project_root):
        rc = lifecycle.main(["nope", "--project-root", str(project_root)])
        assert rc != 0

    def test_consolidate_shipped_subcommand_accepts_dry_run(self, lifecycle, project_root):
        rc = lifecycle.main(
            ["consolidate_shipped", "--dry-run", "--project-root", str(project_root)]
        )
        assert rc == 0


# ---------------------------------------------------------------------------
# Numeric canonical identity (spec-153 D-153-01 / D-153-05)
# ---------------------------------------------------------------------------

_NUMERIC_SPEC_ID = re.compile(r"^spec-\d+$")


def _seed_sidecar(project_root: Path, spec_id: str, *, slug: str, title: str) -> Path:
    """Write a minimal DRAFT sidecar directly (bypassing start_new)."""
    specs = project_root / ".ai-engineering" / "state" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    path = specs / f"{spec_id}.json"
    path.write_text(
        json.dumps(
            {
                "spec_id": spec_id,
                "slug": slug,
                "title": title,
                "state": "draft",
                "created": datetime.now(UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    return path


class TestNumericIdentity:
    def test_start_new_mints_numeric_spec_id_and_keeps_slug(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        assert _NUMERIC_SPEC_ID.match(record.spec_id), (
            f"spec_id {record.spec_id!r} must match ^spec-\\d+$"
        )
        assert record.slug == "my-feature"
        sidecar = project_root / ".ai-engineering" / "state" / "specs" / f"{record.spec_id}.json"
        assert sidecar.exists()

    def test_minted_number_is_max_history_plus_one(self, lifecycle, project_root):
        # Fixture history tops out at id 099 -> next number is 100.
        record = lifecycle.start_new("after-history", "After History", project_root)
        assert record.spec_id == "spec-100"

    def test_minted_number_scans_sidecar_ids_too(self, lifecycle, project_root):
        # A numeric sidecar above the history max wins the +1 race.
        _seed_sidecar(project_root, "spec-200", slug="prior", title="Prior")
        record = lifecycle.start_new("next-after-sidecar", "Next", project_root)
        assert record.spec_id == "spec-201"

    def test_minted_number_takes_max_across_history_and_sidecars(self, lifecycle, project_root):
        # history max is 099; a 150 sidecar must dominate.
        _seed_sidecar(project_root, "spec-150", slug="mid", title="Mid")
        record = lifecycle.start_new("dominant", "Dominant", project_root)
        assert record.spec_id == "spec-151"

    def test_first_spec_when_no_numbers_anywhere_is_spec_001(self, lifecycle, tmp_path):
        # No seeded _history.md and no sidecars -> default to 1.
        (tmp_path / ".ai-engineering" / "specs").mkdir(parents=True)
        (tmp_path / ".ai-engineering" / "state" / "specs").mkdir(parents=True)
        (tmp_path / ".ai-engineering" / "state" / "locks").mkdir(parents=True)
        record = lifecycle.start_new("very-first", "Very First", tmp_path)
        assert record.spec_id == "spec-001"

    def test_idempotent_same_slug_does_not_mint_new_number(self, lifecycle, project_root):
        first = lifecycle.start_new("my-feature", "My Feature", project_root)
        second = lifecycle.start_new("my-feature", "My Feature", project_root)
        assert first.spec_id == second.spec_id
        assert _NUMERIC_SPEC_ID.match(second.spec_id)
        # Only one sidecar exists for the slug; no spurious mint.
        specs = project_root / ".ai-engineering" / "state" / "specs"
        assert len(list(specs.glob("*.json"))) == 1

    def test_next_spec_number_helper_returns_int(self, lifecycle, project_root):
        # Fixture history tops out at 099 -> helper returns 100.
        assert lifecycle._next_spec_number(project_root) == 100


class TestLoadStateSlugFallback:
    def test_load_state_resolves_by_slug_when_id_non_numeric(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        # The sidecar now lives at spec-NNN.json; resolving by the slug must work.
        resolved = lifecycle._load_state(project_root, "my-feature")
        assert resolved.spec_id == record.spec_id
        assert resolved.slug == "my-feature"

    def test_load_state_resolves_by_numeric_id_directly(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        resolved = lifecycle._load_state(project_root, record.spec_id)
        assert resolved.spec_id == record.spec_id

    def test_load_state_raises_when_both_id_and_slug_miss(self, lifecycle, project_root):
        with pytest.raises(FileNotFoundError):
            lifecycle._load_state(project_root, "no-such-spec-or-slug")


class TestShippedRowEnumBinding:
    def test_freshly_shipped_row_status_cell_is_enum_value(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        shipped = lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        history = (project_root / ".ai-engineering" / "specs" / "_history.md").read_text()
        row = next(
            line for line in history.splitlines() if line.startswith(f"| {shipped.spec_id} |")
        )
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        # Column order: ID, Title, Status, Created, Shipped, PR, Branch.
        assert cells[2] == lifecycle.LifecycleState.SHIPPED.value


# ---------------------------------------------------------------------------
# migrate_ids (spec-153 D-153-01 / D-153-10)
# ---------------------------------------------------------------------------


class TestMigrateIds:
    def test_renames_slug_sidecar_to_numeric_via_title_match(self, lifecycle, project_root):
        # Seed a _history.md row whose title the slug sidecar will match.
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        history.write_text(
            "# Spec History\n\n"
            "Completed specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n"
            "| 077 | Cool Feature | done | 2026-03-26 | — | — | feat/cool |\n",
            encoding="utf-8",
        )
        _seed_sidecar(
            project_root, "cool-feature-slug", slug="cool-feature-slug", title="Cool Feature"
        )
        # A numeric sidecar must be left untouched.
        _seed_sidecar(project_root, "spec-077-extra", slug="spec-077-extra", title="Cool Feature")

        report = lifecycle.migrate_ids(project_root)

        specs = project_root / ".ai-engineering" / "state" / "specs"
        renamed = specs / "spec-077.json"
        assert renamed.exists(), "title-matched slug sidecar must be renamed to spec-077.json"
        assert not (specs / "cool-feature-slug.json").exists()
        data = json.loads(renamed.read_text())
        assert data["spec_id"] == "spec-077"
        assert data["slug"] == "cool-feature-slug"
        assert "cool-feature-slug" in {r["slug"] for r in report["renamed"]}

    def test_leaves_already_numeric_sidecar_untouched(self, lifecycle, project_root):
        _seed_sidecar(project_root, "spec-131", slug="spec-131", title="Already Numeric")
        lifecycle.migrate_ids(project_root)
        specs = project_root / ".ai-engineering" / "state" / "specs"
        assert (specs / "spec-131.json").exists()

    def test_unresolvable_sidecar_is_skipped_and_reported(self, lifecycle, project_root):
        _seed_sidecar(
            project_root,
            "totally-unmatched-slug",
            slug="totally-unmatched-slug",
            title="No History Row For This Title At All",
        )
        report = lifecycle.migrate_ids(project_root)
        specs = project_root / ".ai-engineering" / "state" / "specs"
        # Untouched on disk.
        assert (specs / "totally-unmatched-slug.json").exists()
        assert "totally-unmatched-slug" in report["unresolved"]

    def test_dry_run_does_not_mutate_disk(self, lifecycle, project_root):
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        history.write_text(
            "# Spec History\n\n"
            "Completed specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n"
            "| 077 | Cool Feature | done | 2026-03-26 | — | — | feat/cool |\n",
            encoding="utf-8",
        )
        _seed_sidecar(
            project_root, "cool-feature-slug", slug="cool-feature-slug", title="Cool Feature"
        )
        report = lifecycle.migrate_ids(project_root, dry_run=True)
        specs = project_root / ".ai-engineering" / "state" / "specs"
        assert (specs / "cool-feature-slug.json").exists(), "dry-run must not rename"
        assert not (specs / "spec-077.json").exists()
        assert "cool-feature-slug" in {r["slug"] for r in report["renamed"]}


# ---------------------------------------------------------------------------
# Snapshot-on-ship + working-buffer reset (spec-153 D-153-04 / D-153-06)
# ---------------------------------------------------------------------------

# The recognized placeholders the working buffers are reset to at the SHIPPED
# transition (spec-161 follow-up: spec.md and plan.md get their OWN marker, and
# the markers match the framework-wide idle-slot forms the gates recognize).
_SPEC_PLACEHOLDER = "# No active spec\n\nRun /ai-brainstorm to start one.\n"
_PLAN_PLACEHOLDER = "# No active plan\n\nRun /ai-plan after brainstorm approval.\n"
# Legacy lowercase-paren form a pre-fix consolidation wrote; still RECOGNIZED.
_LEGACY_PLACEHOLDER = "# (no active spec)\n\nRun /ai-brainstorm to start one.\n"


def _seed_working_buffers(
    project_root: Path, *, spec_body: str, plan_body: str
) -> tuple[Path, Path]:
    """Write ``specs/spec.md`` + ``specs/plan.md`` working buffers with real content."""
    specs = project_root / ".ai-engineering" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    spec_md = specs / "spec.md"
    plan_md = specs / "plan.md"
    spec_md.write_text(spec_body, encoding="utf-8")
    plan_md.write_text(plan_body, encoding="utf-8")
    return spec_md, plan_md


class TestSnapshotAndReset:
    """``mark_shipped`` snapshots the working buffers into a per-spec archive dir."""

    def test_mark_shipped_snapshots_buffers_into_per_spec_archive_dir(
        self, lifecycle, project_root
    ):
        record = lifecycle.start_new("cool-feature", "Cool Feature", project_root)
        spec_md, plan_md = _seed_working_buffers(
            project_root,
            spec_body="---\nspec: " + record.spec_id + "\n---\n# Cool Feature\n\nbody.\n",
            plan_body="---\nspec: " + record.spec_id + "\n---\n# Plan\n\nsteps.\n",
        )
        original_spec = spec_md.read_text()
        original_plan = plan_md.read_text()

        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)

        archive_dir = (
            project_root
            / ".ai-engineering"
            / "specs"
            / "archive"
            / f"{record.spec_id}-{record.slug}"
        )
        assert (archive_dir / "spec.md").read_text() == original_spec
        assert (archive_dir / "plan.md").read_text() == original_plan

    def test_mark_shipped_resets_working_buffers_to_placeholder(self, lifecycle, project_root):
        record = lifecycle.start_new("cool-feature", "Cool Feature", project_root)
        spec_md, plan_md = _seed_working_buffers(
            project_root,
            spec_body="# Cool Feature\n\nbody.\n",
            plan_body="# Plan\n\nsteps.\n",
        )

        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)

        assert spec_md.read_text() == _SPEC_PLACEHOLDER
        assert plan_md.read_text() == _PLAN_PLACEHOLDER

    def test_reset_placeholders_are_recognized_idle_markers(self, lifecycle, project_root):
        """spec-161 follow-up regression: the reset placeholders MUST be the
        framework-recognized idle markers (``# No active spec`` / ``# No active
        plan``) — the lowercase-paren form red the canonical-slot gate + spec_lint
        on main — and plan.md MUST get the PLAN marker, not the spec one."""
        record = lifecycle.start_new("cool-feature", "Cool Feature", project_root)
        spec_md, plan_md = _seed_working_buffers(
            project_root,
            spec_body="# Cool Feature\n\nbody.\n",
            plan_body="# Plan\n\nsteps.\n",
        )

        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)

        assert spec_md.read_text().startswith("# No active spec")
        assert plan_md.read_text().startswith("# No active plan")
        # Both written placeholders + the legacy paren form are recognized.
        assert lifecycle._buffer_is_placeholder(spec_md.read_text())
        assert lifecycle._buffer_is_placeholder(plan_md.read_text())
        assert lifecycle._buffer_is_placeholder(_LEGACY_PLACEHOLDER)

    def test_snapshot_is_idempotent_on_already_shipped_rerun(self, lifecycle, project_root):
        record = lifecycle.start_new("cool-feature", "Cool Feature", project_root)
        spec_md, _plan_md = _seed_working_buffers(
            project_root,
            spec_body="# Cool Feature\n\nbody.\n",
            plan_body="# Plan\n\nsteps.\n",
        )
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        archive_dir = (
            project_root
            / ".ai-engineering"
            / "specs"
            / "archive"
            / f"{record.spec_id}-{record.slug}"
        )
        snapshot_before = (archive_dir / "spec.md").read_text()

        # Re-running on an already-SHIPPED record must NOT clobber the snapshot
        # with the (now-placeholder) working buffer.
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)

        assert (archive_dir / "spec.md").read_text() == snapshot_before
        assert (archive_dir / "spec.md").read_text() != _SPEC_PLACEHOLDER
        assert spec_md.read_text() == _SPEC_PLACEHOLDER

    def test_mark_shipped_skips_snapshot_when_buffer_is_placeholder(self, lifecycle, project_root):
        record = lifecycle.start_new("cool-feature", "Cool Feature", project_root)
        # Seed the legacy paren placeholder a pre-fix consolidation would have
        # written — it must still be recognized and skipped (not re-snapshotted).
        _seed_working_buffers(
            project_root,
            spec_body=_LEGACY_PLACEHOLDER,
            plan_body=_LEGACY_PLACEHOLDER,
        )

        # Must not crash and must not create an archive snapshot of the placeholder.
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)

        archive_dir = (
            project_root
            / ".ai-engineering"
            / "specs"
            / "archive"
            / f"{record.spec_id}-{record.slug}"
        )
        assert not archive_dir.exists()
        assert (
            lifecycle.status(record.spec_id, project_root).state is lifecycle.LifecycleState.SHIPPED
        )

    def test_mark_shipped_skips_snapshot_when_buffer_absent(self, lifecycle, project_root):
        # The default project_root fixture has no spec.md/plan.md at all.
        record = lifecycle.start_new("cool-feature", "Cool Feature", project_root)

        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)

        archive_dir = (
            project_root
            / ".ai-engineering"
            / "specs"
            / "archive"
            / f"{record.spec_id}-{record.slug}"
        )
        assert not archive_dir.exists()
        assert (
            lifecycle.status(record.spec_id, project_root).state is lifecycle.LifecycleState.SHIPPED
        )

    def test_archive_verb_does_not_move_files(self, lifecycle, project_root):
        """ARCHIVED is a terminal marker only — no extra file movement (D-153-04)."""
        record = lifecycle.start_new("cool-feature", "Cool Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-101", "feat/x", project_root)
        # Drop a sentinel into the working buffer post-ship; archive() must leave it.
        spec_md = project_root / ".ai-engineering" / "specs" / "spec.md"
        spec_md.write_text("sentinel\n", encoding="utf-8")

        lifecycle.archive(record.spec_id, project_root)

        assert spec_md.read_text() == "sentinel\n"


# ---------------------------------------------------------------------------
# sweep — orphan reaper + manifest retention (spec-153 D-153-07 / D-153-08)
# ---------------------------------------------------------------------------


def _write_manifest_lifecycle(
    project_root: Path,
    *,
    draft_ttl_days: int | None = None,
    reap_orphans: bool | None = None,
) -> None:
    """Write a minimal ``manifest.yml`` carrying a ``lifecycle:`` block."""
    manifest = project_root / ".ai-engineering" / "manifest.yml"
    lines = ["version: 1", "lifecycle:"]
    if draft_ttl_days is not None:
        lines.append(f"  draft_ttl_days: {draft_ttl_days}")
    if reap_orphans is not None:
        lines.append(f"  reap_orphans: {'true' if reap_orphans else 'false'}")
    lines.append("  archive_layout: per-spec-dir")
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")


class TestSweepReaper:
    def test_reap_orphans_true_moves_stray_root_spec_into_archive(self, lifecycle, project_root):
        _write_manifest_lifecycle(project_root, reap_orphans=True)
        specs = project_root / ".ai-engineering" / "specs"
        stray = specs / "spec-999-foo.md"
        stray.write_text("# spec-999 foo\n\nstray orphan.\n", encoding="utf-8")

        result = lifecycle.sweep(project_root)

        moved = specs / "archive" / "spec-999-foo" / "spec.md"
        assert moved.exists(), "stray spec-999-foo.md must move into archive/spec-999-foo/spec.md"
        assert not stray.exists()
        assert result.get("reaped", 0) == 1

    def test_reap_leaves_canonical_buffers_and_dirs_untouched(self, lifecycle, project_root):
        _write_manifest_lifecycle(project_root, reap_orphans=True)
        specs = project_root / ".ai-engineering" / "specs"
        (specs / "spec.md").write_text("# active\n", encoding="utf-8")
        (specs / "plan.md").write_text("# plan\n", encoding="utf-8")
        (specs / "drafts").mkdir(parents=True, exist_ok=True)
        (specs / "drafts" / "spec-123-idea.md").write_text("# draft\n", encoding="utf-8")
        (specs / "archive").mkdir(parents=True, exist_ok=True)
        (specs / "archive" / "spec-100-old").mkdir(parents=True, exist_ok=True)
        (specs / "archive" / "spec-100-old" / "spec.md").write_text("# old\n", encoding="utf-8")

        lifecycle.sweep(project_root)

        # Canonical buffers + history untouched.
        assert (specs / "spec.md").read_text() == "# active\n"
        assert (specs / "plan.md").read_text() == "# plan\n"
        assert (specs / "_history.md").exists()
        # drafts/ and archive/ contents untouched.
        assert (specs / "drafts" / "spec-123-idea.md").read_text() == "# draft\n"
        assert (specs / "archive" / "spec-100-old" / "spec.md").read_text() == "# old\n"

    def test_reap_orphans_false_leaves_strays_alone(self, lifecycle, project_root):
        _write_manifest_lifecycle(project_root, reap_orphans=False)
        specs = project_root / ".ai-engineering" / "specs"
        stray = specs / "spec-999-foo.md"
        stray.write_text("# spec-999 foo\n", encoding="utf-8")

        result = lifecycle.sweep(project_root)

        assert stray.exists(), "reap_orphans=false must leave strays in place"
        assert not (specs / "archive" / "spec-999-foo" / "spec.md").exists()
        assert result.get("reaped", 0) == 0

    def test_sweep_reads_draft_ttl_days_from_manifest(self, lifecycle, project_root):
        # A 5-day TTL must abandon a 10-day-old draft that the default 14/30 window keeps.
        _write_manifest_lifecycle(project_root, draft_ttl_days=5, reap_orphans=False)
        record = lifecycle.start_new("borderline", "Borderline", project_root)
        sidecar = project_root / ".ai-engineering" / "state" / "specs" / f"{record.spec_id}.json"
        from datetime import datetime, timedelta

        data = json.loads(sidecar.read_text())
        data["created"] = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        sidecar.write_text(json.dumps(data))

        result = lifecycle.sweep(project_root)

        assert result.get("abandoned", 0) >= 1
        assert (
            lifecycle.status(record.spec_id, project_root).state
            is lifecycle.LifecycleState.ABANDONED
        )

    def test_sweep_fails_open_to_14_days_when_manifest_absent(self, lifecycle, project_root):
        # No manifest.yml in the fixture -> fail-open to a 14-day TTL.
        record = lifecycle.start_new("aging", "Aging", project_root)
        sidecar = project_root / ".ai-engineering" / "state" / "specs" / f"{record.spec_id}.json"
        from datetime import datetime, timedelta

        # 20 days old -> beyond the fail-open 14-day window -> abandoned.
        data = json.loads(sidecar.read_text())
        data["created"] = (datetime.now(UTC) - timedelta(days=20)).isoformat()
        sidecar.write_text(json.dumps(data))

        result = lifecycle.sweep(project_root)

        assert result.get("abandoned", 0) >= 1

    def test_sweep_event_detail_carries_reaped_count(self, lifecycle, project_root):
        _write_manifest_lifecycle(project_root, reap_orphans=True)
        specs = project_root / ".ai-engineering" / "specs"
        (specs / "spec-999-foo.md").write_text("# foo\n", encoding="utf-8")

        lifecycle.sweep(project_root)

        events = _events(project_root)
        sweep_events = [e for e in events if e.get("detail", {}).get("operation") == "spec_sweep"]
        assert sweep_events, "sweep must emit a spec_sweep event"
        assert sweep_events[-1]["detail"].get("reaped") == 1


# ---------------------------------------------------------------------------
# sweep — stale draft-brief retention (spec-153 follow-up: drafts/ TTL)
# ---------------------------------------------------------------------------


def _backdate_mtime(path: Path, *, days: int) -> None:
    """Set a file's atime+mtime to *days* in the past."""
    past = time.time() - days * 24 * 3600
    os.utime(path, (past, past))


class TestSweepDraftRetention:
    """``sweep`` reaps stale ``specs/drafts/*-brief.md`` past the draft TTL.

    Briefs feed ``/ai-brainstorm`` and otherwise accumulate unbounded. The
    manifest ``lifecycle.draft_ttl_days`` (default 30) + ``reap_orphans`` gate
    the reap; stale briefs are MOVED (never deleted) to
    ``specs/archive/drafts/<name>`` consistent with the orphan reaper.
    """

    def test_stale_brief_moved_to_archive_drafts_when_reap_enabled(self, lifecycle, project_root):
        _write_manifest_lifecycle(project_root, draft_ttl_days=30, reap_orphans=True)
        drafts = project_root / ".ai-engineering" / "specs" / "drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        stale = drafts / "old-idea-brief.md"
        stale.write_text("# old idea\n\nstale brief.\n", encoding="utf-8")
        _backdate_mtime(stale, days=45)

        result = lifecycle.sweep(project_root)

        moved = (
            project_root / ".ai-engineering" / "specs" / "archive" / "drafts" / "old-idea-brief.md"
        )
        assert moved.exists(), "stale brief must move into archive/drafts/"
        assert moved.read_text(encoding="utf-8") == "# old idea\n\nstale brief.\n"
        assert not stale.exists(), "the original brief must be moved, not copied"
        assert result.get("drafts_reaped", 0) == 1

    def test_recent_brief_left_untouched(self, lifecycle, project_root):
        _write_manifest_lifecycle(project_root, draft_ttl_days=30, reap_orphans=True)
        drafts = project_root / ".ai-engineering" / "specs" / "drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        fresh = drafts / "fresh-idea-brief.md"
        fresh.write_text("# fresh\n", encoding="utf-8")
        _backdate_mtime(fresh, days=3)

        result = lifecycle.sweep(project_root)

        assert fresh.exists(), "a recent brief must not be reaped"
        assert not (
            project_root
            / ".ai-engineering"
            / "specs"
            / "archive"
            / "drafts"
            / "fresh-idea-brief.md"
        ).exists()
        assert result.get("drafts_reaped", 0) == 0

    def test_reap_orphans_false_leaves_stale_briefs_alone(self, lifecycle, project_root):
        _write_manifest_lifecycle(project_root, draft_ttl_days=30, reap_orphans=False)
        drafts = project_root / ".ai-engineering" / "specs" / "drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        stale = drafts / "old-idea-brief.md"
        stale.write_text("# old\n", encoding="utf-8")
        _backdate_mtime(stale, days=90)

        result = lifecycle.sweep(project_root)

        assert stale.exists(), "reap_orphans=false must leave stale briefs in place"
        assert result.get("drafts_reaped", 0) == 0

    def test_fails_open_to_14_days_when_manifest_absent(self, lifecycle, project_root):
        # No manifest.yml in the fixture -> fail-open to 14-day TTL + reaping on.
        drafts = project_root / ".ai-engineering" / "specs" / "drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        stale = drafts / "ancient-brief.md"
        stale.write_text("# ancient\n", encoding="utf-8")
        _backdate_mtime(stale, days=20)  # > the fail-open 14-day window

        result = lifecycle.sweep(project_root)

        moved = (
            project_root / ".ai-engineering" / "specs" / "archive" / "drafts" / "ancient-brief.md"
        )
        assert moved.exists(), "fail-open 14d TTL must reap a 20-day-old brief"
        assert result.get("drafts_reaped", 0) == 1

    def test_only_brief_suffix_files_are_reaped(self, lifecycle, project_root):
        # A non-brief markdown file in drafts/ is NOT a brief; leave it alone.
        _write_manifest_lifecycle(project_root, draft_ttl_days=30, reap_orphans=True)
        drafts = project_root / ".ai-engineering" / "specs" / "drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        not_a_brief = drafts / "notes.md"
        not_a_brief.write_text("# scratch notes\n", encoding="utf-8")
        _backdate_mtime(not_a_brief, days=120)

        result = lifecycle.sweep(project_root)

        assert not_a_brief.exists(), "only *-brief.md files are reaped from drafts/"
        assert result.get("drafts_reaped", 0) == 0

    def test_sweep_event_detail_carries_drafts_reaped_count(self, lifecycle, project_root):
        _write_manifest_lifecycle(project_root, draft_ttl_days=30, reap_orphans=True)
        drafts = project_root / ".ai-engineering" / "specs" / "drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        stale = drafts / "stale-brief.md"
        stale.write_text("# stale\n", encoding="utf-8")
        _backdate_mtime(stale, days=60)

        lifecycle.sweep(project_root)

        events = _events(project_root)
        sweep_events = [e for e in events if e.get("detail", {}).get("operation") == "spec_sweep"]
        assert sweep_events, "sweep must emit a spec_sweep event"
        assert sweep_events[-1]["detail"].get("drafts_reaped") == 1

    def test_stale_brief_symlink_is_not_followed(self, lifecycle, project_root):
        # Security: a hostile symlink named *-brief.md must never be relocated
        # (mirrors the orphan reaper's symlink guard).
        _write_manifest_lifecycle(project_root, draft_ttl_days=30, reap_orphans=True)
        drafts = project_root / ".ai-engineering" / "specs" / "drafts"
        drafts.mkdir(parents=True, exist_ok=True)
        outside = project_root / "outside-secret.md"
        outside.write_text("secret\n", encoding="utf-8")
        link = drafts / "evil-brief.md"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            pytest.skip("platform cannot create symlinks without elevation")
        _backdate_mtime(outside, days=99)

        result = lifecycle.sweep(project_root)

        assert outside.exists(), "the symlink target must never be relocated"
        assert result.get("drafts_reaped", 0) == 0


# ---------------------------------------------------------------------------
# reconcile_merged — merged-branch backstop auto-marks SHIPPED (spec-153 D-153-03)
# ---------------------------------------------------------------------------


class _FakeGit:
    """Scripted ``subprocess.run`` replacement for git + gh classification.

    ``reconcile_merged`` mirrors ``/ai-branch-cleanup`` classification:
    a branch is "merged" when it appears in ``git branch --merged <default>``
    OR ``git diff <default>..<branch>`` is empty (squash-merge). PR numbers
    resolve via ``gh pr list --head <branch> --state merged --json number``.
    The fake routes on the command verb so the test never couples to exact
    flag ordering.
    """

    def __init__(
        self,
        *,
        merged_branches: set[str] | None = None,
        empty_diff_branches: set[str] | None = None,
        pr_for_branch: dict[str, int] | None = None,
        gh_available: bool = True,
    ) -> None:
        self.merged_branches = merged_branches or set()
        self.empty_diff_branches = empty_diff_branches or set()
        self.pr_for_branch = pr_for_branch or {}
        self.gh_available = gh_available

    def __call__(self, cmd, *args, **kwargs):
        from subprocess import CalledProcessError, CompletedProcess

        # Normalise to a plain list of strings.
        argv = [str(c) for c in cmd]

        def done(stdout: str = "", returncode: int = 0) -> CompletedProcess:
            return CompletedProcess(argv, returncode, stdout=stdout, stderr="")

        if argv[0] == "gh":
            if not self.gh_available:
                raise FileNotFoundError("gh")
            # gh pr list --head <branch> --state merged --json number
            head = argv[argv.index("--head") + 1] if "--head" in argv else ""
            num = self.pr_for_branch.get(head)
            if num is None:
                return done(stdout="[]")
            return done(stdout=json.dumps([{"number": num}]))

        if "git" in argv[0] or argv[0] == "git":
            # `git branch --merged <default>` -> newline list of branch names.
            if "branch" in argv and "--merged" in argv:
                lines = "".join(f"  {b}\n" for b in sorted(self.merged_branches))
                return done(stdout=lines)
            # `git diff <default>..<branch>` -> empty stdout when squash-merged.
            if "diff" in argv:
                rng = argv[-1]
                branch = rng.split("..")[-1]
                return done(stdout="" if branch in self.empty_diff_branches else "diffated\n")
            # Any other git call (rev-parse, etc.) succeeds quietly.
            return done()
        raise CalledProcessError(1, argv)


def _seed_branch_sidecar(
    project_root: Path,
    spec_id: str,
    *,
    slug: str,
    title: str,
    state: str,
    branch: str | None,
) -> Path:
    """Seed a sidecar in an arbitrary lifecycle state carrying an optional branch."""
    specs = project_root / ".ai-engineering" / "state" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    payload = {
        "spec_id": spec_id,
        "slug": slug,
        "title": title,
        "state": state,
        "created": datetime.now(UTC).isoformat(),
    }
    if branch is not None:
        payload["branch"] = branch
    path = specs / f"{spec_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class TestReconcileMerged:
    def test_marks_shipped_when_branch_is_merged(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-200",
            slug="merged-spec",
            title="Merged Spec",
            state="in_progress",
            branch="spec-200-merged-spec",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(
                merged_branches={"spec-200-merged-spec"},
                pr_for_branch={"spec-200-merged-spec": 600},
            ),
        )

        report = lifecycle.reconcile_merged(project_root)

        assert lifecycle.status("spec-200", project_root).state is lifecycle.LifecycleState.SHIPPED
        assert "spec-200" in {r["spec_id"] for r in report["shipped"]}

    def test_marks_shipped_on_squash_merge(self, lifecycle, project_root, monkeypatch):
        """A genuinely squash-merged branch (unique commits landed) is shipped.

        Detection now uses the hardened ``cleanup.py`` taxonomy (unique-commit
        count + cherry), not a naive empty-diff — so the fake models a real
        squash: positive unique commits whose synthetic patch lands on default.
        """
        _seed_branch_sidecar(
            project_root,
            "spec-201",
            slug="squashed-spec",
            title="Squashed Spec",
            state="approved",
            branch="spec-201-squashed-spec",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGitTaxonomy(
                merged_branches=set(),
                squashed_branches={"spec-201-squashed-spec"},
                unique_commit_counts={"spec-201-squashed-spec": 2},
                pr_for_branch={"spec-201-squashed-spec": 601},
            ),
        )

        lifecycle.reconcile_merged(project_root)

        shipped = lifecycle.status("spec-201", project_root)
        assert shipped.state is lifecycle.LifecycleState.SHIPPED
        assert shipped.pr == "601"

    def test_unmerged_branch_left_untouched(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-202",
            slug="active-spec",
            title="Active Spec",
            state="in_progress",
            branch="spec-202-active-spec",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set(), empty_diff_branches=set()),
        )

        report = lifecycle.reconcile_merged(project_root)

        assert (
            lifecycle.status("spec-202", project_root).state is lifecycle.LifecycleState.IN_PROGRESS
        )
        assert "spec-202" not in {r["spec_id"] for r in report["shipped"]}

    def test_sidecar_without_branch_is_skipped(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-203",
            slug="no-branch-spec",
            title="No Branch Spec",
            state="draft",
            branch=None,
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches={"anything"}),
        )

        report = lifecycle.reconcile_merged(project_root)

        assert lifecycle.status("spec-203", project_root).state is lifecycle.LifecycleState.DRAFT
        assert "spec-203" in {r["spec_id"] for r in report["skipped"]}

    def test_already_shipped_is_idempotent_noop(self, lifecycle, project_root, monkeypatch):
        record = lifecycle.start_new("done-spec", "Done Spec", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-1", "spec-done", project_root)
        # Stamp a branch on the now-SHIPPED sidecar so reconcile inspects it.
        sidecar = project_root / ".ai-engineering" / "state" / "specs" / f"{record.spec_id}.json"
        data = json.loads(sidecar.read_text())
        data["branch"] = "spec-done"
        sidecar.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches={"spec-done"}, pr_for_branch={"spec-done": 700}),
        )

        # Terminal SHIPPED records are skipped before any git classification.
        report = lifecycle.reconcile_merged(project_root)

        assert (
            lifecycle.status(record.spec_id, project_root).state is lifecycle.LifecycleState.SHIPPED
        )
        assert record.spec_id not in {r["spec_id"] for r in report["shipped"]}

    def test_gh_absent_fails_open_to_em_dash_pr(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-204",
            slug="no-gh-spec",
            title="No GH Spec",
            state="in_progress",
            branch="spec-204-no-gh-spec",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches={"spec-204-no-gh-spec"}, gh_available=False),
        )

        lifecycle.reconcile_merged(project_root)

        shipped = lifecycle.status("spec-204", project_root)
        assert shipped.state is lifecycle.LifecycleState.SHIPPED
        assert shipped.pr == "—"

    def test_reconcile_does_not_snapshot_unrelated_current_buffer(
        self, lifecycle, project_root, monkeypatch
    ):
        """Snapshot-safety guard (W4): marking an OLD spec must not clear the live buffer.

        ``reconcile_merged`` can mark a spec whose content is no longer in the
        working buffer (the buffer now holds a *different*, in-flight spec).
        ``_snapshot_and_reset`` snapshots only when ``spec.md`` frontmatter
        ``spec:`` equals the record being shipped — so the unrelated current
        buffer is left intact (no archive dir for the old spec, no reset).
        """
        # The live working buffer holds a DIFFERENT spec (spec-300), in flight.
        specs = project_root / ".ai-engineering" / "specs"
        specs.mkdir(parents=True, exist_ok=True)
        current_spec_body = "---\nspec: spec-300\n---\n# Current In-Flight Spec\n\nbody.\n"
        current_plan_body = "---\nspec: spec-300\n---\n# Current Plan\n\nsteps.\n"
        spec_md = specs / "spec.md"
        plan_md = specs / "plan.md"
        spec_md.write_text(current_spec_body, encoding="utf-8")
        plan_md.write_text(current_plan_body, encoding="utf-8")

        # An OLD merged spec (spec-205) whose content is gone from the buffer.
        _seed_branch_sidecar(
            project_root,
            "spec-205",
            slug="old-merged-spec",
            title="Old Merged Spec",
            state="in_progress",
            branch="spec-205-old-merged-spec",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(
                merged_branches={"spec-205-old-merged-spec"},
                pr_for_branch={"spec-205-old-merged-spec": 605},
            ),
        )

        lifecycle.reconcile_merged(project_root)

        # State transition + history row happen for the old spec ...
        assert lifecycle.status("spec-205", project_root).state is lifecycle.LifecycleState.SHIPPED
        history = (specs / "_history.md").read_text()
        assert "| spec-205 |" in history
        # ... but the unrelated current buffer is NOT snapshotted or cleared.
        assert spec_md.read_text() == current_spec_body
        assert plan_md.read_text() == current_plan_body
        old_archive = specs / "archive" / "spec-205-old-merged-spec"
        assert not old_archive.exists(), "old spec must NOT capture the unrelated buffer"

    def test_mark_shipped_via_pr_path_still_snapshots_matching_buffer(
        self, lifecycle, project_root
    ):
        """The /ai-pr path (buffer IS the shipping spec) still snapshots + resets.

        This pins the guard's other arm: when ``spec.md`` frontmatter ``spec:``
        equals the record being shipped, ``mark_shipped`` snapshots into the
        per-spec archive and resets the buffer (the W3 behavior is preserved).
        """
        record = lifecycle.start_new("matching-spec", "Matching Spec", project_root)
        specs = project_root / ".ai-engineering" / "specs"
        specs.mkdir(parents=True, exist_ok=True)
        spec_body = f"---\nspec: {record.spec_id}\n---\n# Matching Spec\n\nbody.\n"
        plan_body = f"---\nspec: {record.spec_id}\n---\n# Plan\n\nsteps.\n"
        spec_md = specs / "spec.md"
        plan_md = specs / "plan.md"
        spec_md.write_text(spec_body, encoding="utf-8")
        plan_md.write_text(plan_body, encoding="utf-8")

        lifecycle.mark_shipped(record.spec_id, "PR-9", "feat/match", project_root)

        archive_dir = specs / "archive" / f"{record.spec_id}-{record.slug}"
        assert (archive_dir / "spec.md").read_text() == spec_body
        assert (archive_dir / "plan.md").read_text() == plan_body
        assert spec_md.read_text() == _SPEC_PLACEHOLDER
        assert plan_md.read_text() == _PLAN_PLACEHOLDER


# ---------------------------------------------------------------------------
# reconcile_merged hardening — robust squash-merge classification +
# ledger-presence idempotency (spec-153 quality loop FINDING 1)
# ---------------------------------------------------------------------------


class _FakeGitTaxonomy:
    """Scripted git replacement modelling the squash-merge commit taxonomy.

    Mirrors ``cli_commands/cleanup.py:_list_squashed_branches`` exactly so the
    hardened ``_branch_is_merged`` can reuse that proven classification:

    - ``git branch --merged <default>``  -> true-merge / fast-forward list.
    - ``git rev-list --count <default>..<branch>`` -> count of UNIQUE commits on
      the branch (zero means at/behind ``default`` — NOT a squash-merge).
    - ``git merge-base <default> <branch>`` -> a synthetic base sha.
    - ``git rev-parse <branch>^{tree}``  -> the branch tree sha.
    - ``git commit-tree <tree> -p <base> -m _check`` -> a synthetic commit sha.
    - ``git cherry <default> <synthetic>`` -> a leading ``-`` when the synthetic
      patch already landed on ``default`` (squash-merged).

    ``squashed_branches`` is the set whose content actually landed under a
    squash commit; ``unique_commit_counts`` maps a branch to its unique-commit
    count (default 1 for a squashed branch, 0 otherwise unless overridden).
    """

    def __init__(
        self,
        *,
        merged_branches: set[str] | None = None,
        squashed_branches: set[str] | None = None,
        unique_commit_counts: dict[str, int] | None = None,
        pr_for_branch: dict[str, int] | None = None,
        gh_available: bool = True,
    ) -> None:
        self.merged_branches = merged_branches or set()
        self.squashed_branches = squashed_branches or set()
        self.unique_commit_counts = dict(unique_commit_counts or {})
        self.pr_for_branch = pr_for_branch or {}
        self.gh_available = gh_available

    def _unique_count(self, branch: str) -> int:
        if branch in self.unique_commit_counts:
            return self.unique_commit_counts[branch]
        # A squashed branch carries real unique commits whose content landed;
        # everything else defaults to zero (at/behind default).
        return 1 if branch in self.squashed_branches else 0

    def __call__(self, cmd, *args, **kwargs):
        from subprocess import CalledProcessError, CompletedProcess

        argv = [str(c) for c in cmd]

        def done(stdout: str = "", returncode: int = 0) -> CompletedProcess:
            return CompletedProcess(argv, returncode, stdout=stdout, stderr="")

        if argv[0] == "gh":
            if not self.gh_available:
                raise FileNotFoundError("gh")
            head = argv[argv.index("--head") + 1] if "--head" in argv else ""
            num = self.pr_for_branch.get(head)
            return done(stdout="[]" if num is None else json.dumps([{"number": num}]))

        if argv[0] == "git" or "git" in argv[0]:
            if "branch" in argv and "--merged" in argv:
                lines = "".join(f"  {b}\n" for b in sorted(self.merged_branches))
                return done(stdout=lines)
            if "rev-list" in argv and "--count" in argv:
                rng = argv[-1]
                branch = rng.split("..")[-1]
                return done(stdout=f"{self._unique_count(branch)}\n")
            if "merge-base" in argv:
                branch = argv[-1]
                return done(stdout=f"mergebase-{branch}\n")
            if "rev-parse" in argv:
                ref = argv[-1]
                branch = ref.split("^")[0]
                return done(stdout=f"tree-{branch}\n")
            if "commit-tree" in argv:
                # commit-tree <tree> -p <base> -m _check ; the tree is the token
                # immediately after ``commit-tree`` (robust to the ``-C <root>``
                # prefix git wraps the call in).
                tree = argv[argv.index("commit-tree") + 1]
                branch = tree[len("tree-") :] if tree.startswith("tree-") else tree
                return done(stdout=f"synthetic-{branch}\n")
            if "cherry" in argv:
                synthetic = argv[-1]
                branch = (
                    synthetic[len("synthetic-") :]
                    if synthetic.startswith("synthetic-")
                    else synthetic
                )
                # A leading "-" marks a patch already present on <default>.
                marker = "-" if branch in self.squashed_branches else "+"
                return done(stdout=f"{marker} {synthetic}\n")
            return done()
        raise CalledProcessError(1, argv)


class TestBranchIsMergedHardened:
    """``_branch_is_merged`` must demand real evidence, not just an empty diff."""

    def test_branch_at_or_behind_main_is_not_merged(self, lifecycle, project_root, monkeypatch):
        """Zero unique commits (fresh-cut / rebased-away / behind) is NOT merged.

        This is the empty-diff false-positive: ``git diff main..branch`` is empty
        for a branch with no unique commits, but its content never *landed* as a
        squash — it simply has nothing. The hardened classifier returns False.
        """
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGitTaxonomy(
                merged_branches=set(),
                squashed_branches=set(),
                unique_commit_counts={"spec-900-empty": 0},
            ),
        )
        assert lifecycle._branch_is_merged(project_root, "spec-900-empty", "main") is False

    def test_genuine_squash_merged_branch_is_merged(self, lifecycle, project_root, monkeypatch):
        """A branch whose unique commits landed under a squash IS merged."""
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGitTaxonomy(
                merged_branches=set(),
                squashed_branches={"spec-901-squashed"},
                unique_commit_counts={"spec-901-squashed": 3},
            ),
        )
        assert lifecycle._branch_is_merged(project_root, "spec-901-squashed", "main") is True

    def test_true_merge_branch_still_detected(self, lifecycle, project_root, monkeypatch):
        """A fast-forward / true-merge branch (in --merged) stays merged."""
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGitTaxonomy(merged_branches={"spec-902-ff"}),
        )
        assert lifecycle._branch_is_merged(project_root, "spec-902-ff", "main") is True

    def test_unmerged_branch_with_unique_commits_not_merged(
        self, lifecycle, project_root, monkeypatch
    ):
        """Unique commits that did NOT land (cherry shows ``+``) is NOT merged."""
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGitTaxonomy(
                merged_branches=set(),
                squashed_branches=set(),
                unique_commit_counts={"spec-903-live": 5},
            ),
        )
        assert lifecycle._branch_is_merged(project_root, "spec-903-live", "main") is False


class TestReconcileLedgerIdempotency:
    """``reconcile_merged`` must skip any spec already in the ledger (FINDING 1)."""

    def test_spec_already_in_ledger_is_skipped_even_if_branch_looks_merged(
        self, lifecycle, project_root, monkeypatch
    ):
        """A spec whose id is already a ledger row must NOT be re-shipped.

        Backstop idempotency against historical rows regardless of branch-
        detection accuracy: even when the branch classifies as merged, a spec
        already present in ``_history.md`` is skipped (no duplicate ledger row,
        no phantom re-ship with today's date).
        """
        # Seed a ledger that already carries a bare-numeric row for 136.
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        history.write_text(
            "# Spec History\n\n"
            "Completed specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n"
            "| 136 | Prune low-value surfaces | done | 2026-05-16 | 2026-05-16 | #514 | "
            "spec-136/prune |\n",
            encoding="utf-8",
        )
        # Sidecar is still APPROVED with a branch that classifies as merged.
        _seed_branch_sidecar(
            project_root,
            "spec-136",
            slug="spec-136-prune",
            title="Prune low-value surfaces",
            state="approved",
            branch="spec-136/prune",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGitTaxonomy(
                merged_branches={"spec-136/prune"},
                pr_for_branch={"spec-136/prune": 514},
            ),
        )

        report = lifecycle.reconcile_merged(project_root)

        # NOT re-shipped: the bare-numeric ledger row neutralizes the backstop.
        assert "spec-136" not in {r["spec_id"] for r in report["shipped"]}
        assert lifecycle.status("spec-136", project_root).state is (
            lifecycle.LifecycleState.APPROVED
        )
        # Ledger keeps exactly one row for 136 (no duplicate appended).
        rows = [ln for ln in history.read_text().splitlines() if ln.startswith("| 136 |")]
        assert len(rows) == 1
        # Skip report records the ledger-presence reason.
        assert "spec-136" in {r["spec_id"] for r in report["skipped"]}

    def test_spec_with_spec_prefixed_ledger_row_is_skipped(
        self, lifecycle, project_root, monkeypatch
    ):
        """The guard also matches when the ledger row is ``spec-NNN`` form."""
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        history.write_text(
            "# Spec History\n\n"
            "Completed specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n"
            "| spec-210 | Already Shipped | shipped | 2026-05-01 | 2026-05-01 | #1 | feat/x |\n",
            encoding="utf-8",
        )
        _seed_branch_sidecar(
            project_root,
            "spec-210",
            slug="already-shipped",
            title="Already Shipped",
            state="in_progress",
            branch="spec-210-already",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGitTaxonomy(merged_branches={"spec-210-already"}),
        )

        report = lifecycle.reconcile_merged(project_root)

        assert "spec-210" not in {r["spec_id"] for r in report["shipped"]}
        assert "spec-210" in {r["spec_id"] for r in report["skipped"]}

    def test_genuinely_unshipped_squash_merged_spec_is_still_shipped(
        self, lifecycle, project_root, monkeypatch
    ):
        """A real squash-merged spec absent from the ledger IS still marked."""
        _seed_branch_sidecar(
            project_root,
            "spec-211",
            slug="fresh-squash",
            title="Fresh Squash",
            state="in_progress",
            branch="spec-211-fresh",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGitTaxonomy(
                squashed_branches={"spec-211-fresh"},
                unique_commit_counts={"spec-211-fresh": 4},
                pr_for_branch={"spec-211-fresh": 711},
            ),
        )

        report = lifecycle.reconcile_merged(project_root)

        assert lifecycle.status("spec-211", project_root).state is (
            lifecycle.LifecycleState.SHIPPED
        )
        assert "spec-211" in {r["spec_id"] for r in report["shipped"]}

    def test_branch_at_main_is_not_phantom_shipped(self, lifecycle, project_root, monkeypatch):
        """A fresh-cut branch (zero unique commits) is never phantom-shipped.

        This is the core FINDING 1 fuel: an APPROVED spec with a branch sitting
        at/behind main must NOT be classified merged and must NOT get a ledger
        row with today's date.
        """
        _seed_branch_sidecar(
            project_root,
            "spec-212",
            slug="behind-main",
            title="Behind Main",
            state="approved",
            branch="spec-212-behind",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGitTaxonomy(
                merged_branches=set(),
                squashed_branches=set(),
                unique_commit_counts={"spec-212-behind": 0},
            ),
        )

        report = lifecycle.reconcile_merged(project_root)

        assert lifecycle.status("spec-212", project_root).state is (
            lifecycle.LifecycleState.APPROVED
        )
        assert "spec-212" in {r["spec_id"] for r in report["unmerged"]}
        assert "spec-212" not in {r["spec_id"] for r in report["shipped"]}


# ---------------------------------------------------------------------------
# orphan reaper — symlink safety (spec-153 quality loop FINDING 2)
# ---------------------------------------------------------------------------


class TestReaperSymlinkSafety:
    def test_symlink_in_specs_root_is_left_untouched(self, lifecycle, project_root):
        """A ``spec-*.md`` symlink in ``specs/`` root must not be followed/relocated.

        ``path.is_file()`` follows symlinks, so a malicious
        ``specs/spec-evil.md -> /outside`` would be relocated by the reaper. The
        reaper must skip symlinks outright (defense against escaping the tree).
        """
        _write_manifest_lifecycle(project_root, reap_orphans=True)
        specs = project_root / ".ai-engineering" / "specs"
        # A real outside target the symlink points at.
        outside = project_root / "outside-target.md"
        outside.write_text("# outside\n", encoding="utf-8")
        link = specs / "spec-evil.md"
        link.symlink_to(outside)

        result = lifecycle.sweep(project_root)

        # The symlink is left in place; nothing reaped; outside target intact.
        assert link.is_symlink(), "symlink must be left untouched by the reaper"
        assert outside.read_text() == "# outside\n"
        assert not (specs / "archive" / "spec-evil" / "spec.md").exists()
        assert result.get("reaped", 0) == 0


# ---------------------------------------------------------------------------
# placeholder marker recognition widening (spec-153 quality loop FINDING 4)
# ---------------------------------------------------------------------------


class TestPlaceholderMarkerWidening:
    def test_spec_reset_no_active_spec_marker_is_recognized_as_placeholder(self, lifecycle):
        """The framework-wide ``# No active spec`` marker counts as a placeholder.

        ``spec_reset.py`` writes ``# No active spec`` when it clears the buffer;
        ``_buffer_is_placeholder`` must recognize it (recognition-widening only)
        so a reset buffer is never snapshotted by ``mark_shipped``.
        """
        marker = "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n"
        assert lifecycle._buffer_is_placeholder(marker) is True

    def test_spec_reset_no_active_plan_marker_is_recognized_as_placeholder(self, lifecycle):
        """The ``# No active plan`` plan marker is also a placeholder."""
        marker = "# No active plan\n\nRun /ai-plan after brainstorm approval.\n"
        assert lifecycle._buffer_is_placeholder(marker) is True

    def test_own_placeholder_still_recognized(self, lifecycle):
        """The lifecycle's legacy paren placeholder is still recognized (no regression)."""
        assert lifecycle._buffer_is_placeholder(_LEGACY_PLACEHOLDER) is True

    def test_producer_markers_match_the_real_idle_slot_gate_prefix(self, lifecycle):
        """spec-161 follow-up: the markers ``mark_shipped`` WRITES must match the
        idle-slot gate's recognized prefix. The producer (``spec_lifecycle``) and
        the gate (``tools/spec_lint/cli.py``) hardcode the literal independently —
        couple them here so a future gate-constant rename can't silently
        re-introduce the red-main drift this fix closed (review finding testing-2).
        """
        repo_root = Path(__file__).resolve().parents[3]
        gate_src = (repo_root / "tools" / "spec_lint" / "cli.py").read_text(encoding="utf-8")
        gate_match = re.search(r'_IDLE_SLOT_PREFIX\s*=\s*"([^"]+)"', gate_src)
        assert gate_match, "could not locate _IDLE_SLOT_PREFIX in tools/spec_lint/cli.py"
        gate_prefix = gate_match.group(1)
        # The spec buffer marker MUST satisfy the spec_lint idle-slot gate prefix.
        assert lifecycle._SPEC_BUFFER_PLACEHOLDER.startswith(gate_prefix)
        # The plan buffer marker keys off the framework-wide plan marker the docs
        # gate (tests/docs/test_links.py) + manifest_coherence recognize.
        assert lifecycle._PLAN_BUFFER_PLACEHOLDER.startswith("# No active plan")
        # Both written markers must also satisfy the lifecycle's own recognizer.
        assert lifecycle._buffer_is_placeholder(lifecycle._SPEC_BUFFER_PLACEHOLDER)
        assert lifecycle._buffer_is_placeholder(lifecycle._PLAN_BUFFER_PLACEHOLDER)

    def test_real_spec_content_is_not_a_placeholder(self, lifecycle):
        """A real spec buffer is NOT a placeholder (no false widening)."""
        assert (
            lifecycle._buffer_is_placeholder("---\nspec: spec-001\n---\n# Real\n\nbody.\n") is False
        )

    def test_mark_shipped_does_not_snapshot_spec_reset_cleared_buffer(
        self, lifecycle, project_root
    ):
        """A ``spec_reset``-cleared buffer is not snapshotted on ship (FINDING 4)."""
        record = lifecycle.start_new("reset-spec", "Reset Spec", project_root)
        specs = project_root / ".ai-engineering" / "specs"
        specs.mkdir(parents=True, exist_ok=True)
        (specs / "spec.md").write_text(
            "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n", encoding="utf-8"
        )
        (specs / "plan.md").write_text(
            "# No active plan\n\nRun /ai-plan after brainstorm approval.\n", encoding="utf-8"
        )

        lifecycle.mark_shipped(record.spec_id, "PR-1", "feat/x", project_root)

        archive_dir = specs / "archive" / f"{record.spec_id}-{record.slug}"
        assert not archive_dir.exists(), "spec_reset-cleared buffer must not be snapshotted"


# ---------------------------------------------------------------------------
# migrate_ids — archive-dir slug resolution (spec-153 quality loop FINDING 5)
# ---------------------------------------------------------------------------


def _make_archive_dir(project_root: Path, dir_name: str) -> None:
    """Create an ``specs/archive/<dir_name>/`` directory with a spec.md."""
    d = project_root / ".ai-engineering" / "specs" / "archive" / dir_name
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.md").write_text(f"# {dir_name}\n", encoding="utf-8")


class TestMigrateIdsArchiveDirResolution:
    def test_slug_sidecar_resolves_via_unique_archive_dir(self, lifecycle, project_root):
        """An unresolved slug sidecar adopts the number of its UNIQUE archive dir.

        W3 created ``archive/spec-NNN-<slug>/`` dirs for shipped specs. When a
        slug sidecar has no ledger/frontmatter/prefix signal, a unique archive
        dir whose ``<slug>`` exactly matches is an authoritative source.
        """
        _make_archive_dir(project_root, "spec-150-notebooklm-async-tier3")
        _seed_sidecar(
            project_root,
            "notebooklm-async-tier3",
            slug="notebooklm-async-tier3",
            title="Async-first NotebookLM autonomous deep research",
        )

        report = lifecycle.migrate_ids(project_root)

        specs = project_root / ".ai-engineering" / "state" / "specs"
        assert (specs / "spec-150.json").exists()
        assert not (specs / "notebooklm-async-tier3.json").exists()
        data = json.loads((specs / "spec-150.json").read_text())
        assert data["spec_id"] == "spec-150"
        assert data["slug"] == "notebooklm-async-tier3"
        assert "notebooklm-async-tier3" in {r["slug"] for r in report["renamed"]}

    def test_slug_with_no_archive_dir_is_left_unresolved(self, lifecycle, project_root):
        """A slug with no matching archive dir is left untouched and reported.

        e.g. ``antigravity-gemini-cli-retirement`` (never shipped) -> no archive
        dir -> NEVER assigned a guessed number.
        """
        _make_archive_dir(project_root, "spec-150-notebooklm-async-tier3")
        _seed_sidecar(
            project_root,
            "antigravity-gemini-cli-retirement",
            slug="antigravity-gemini-cli-retirement",
            title="Antigravity-only Google surface after Gemini CLI retirement",
        )

        report = lifecycle.migrate_ids(project_root)

        specs = project_root / ".ai-engineering" / "state" / "specs"
        assert (specs / "antigravity-gemini-cli-retirement.json").exists()
        assert "antigravity-gemini-cli-retirement" in report["unresolved"]

    def test_ambiguous_archive_dirs_for_same_slug_left_unresolved(self, lifecycle, project_root):
        """Two archive dirs with the same slug suffix -> ambiguous -> unresolved.

        A guessed/ambiguous number is never assigned.
        """
        _make_archive_dir(project_root, "spec-148-files-only-persistence")
        _make_archive_dir(project_root, "spec-149-files-only-persistence")
        _seed_sidecar(
            project_root,
            "files-only-persistence",
            slug="files-only-persistence",
            title="Files-only persistence",
        )

        report = lifecycle.migrate_ids(project_root)

        specs = project_root / ".ai-engineering" / "state" / "specs"
        assert (specs / "files-only-persistence.json").exists()
        assert "files-only-persistence" in report["unresolved"]

    def test_archive_dir_with_different_slug_does_not_match(self, lifecycle, project_root):
        """An archive dir whose slug differs must NOT match (no partial match)."""
        # The 148 dir for a DIFFERENT slug must not capture this sidecar.
        _make_archive_dir(project_root, "spec-148-autopilot-manifest-prior-session")
        _seed_sidecar(
            project_root,
            "files-only-persistence",
            slug="files-only-persistence",
            title="Files-only persistence",
        )

        report = lifecycle.migrate_ids(project_root)

        specs = project_root / ".ai-engineering" / "state" / "specs"
        assert (specs / "files-only-persistence.json").exists()
        assert "files-only-persistence" in report["unresolved"]


# ---------------------------------------------------------------------------
# P1 — archive-blind numbering (spec-161 #574 Bug 1)
# ---------------------------------------------------------------------------


def _make_archive_spec_dir(project_root: Path, dir_name: str) -> None:
    """Create an empty ``specs/archive/<dir_name>/`` directory (no spec.md needed)."""
    (project_root / ".ai-engineering" / "specs" / "archive" / dir_name).mkdir(
        parents=True, exist_ok=True
    )


class TestNextSpecNumberArchiveAware:
    """``_next_spec_number`` must also scan archive ``spec-NNN-*`` dir names.

    Regression for #574 Bug 1: a shipped+archived spec whose sidecar was
    consolidated away (cleared) left its number invisible to the scanner, so
    ``start_new`` could re-mint an already-used (archived) number.
    """

    def test_archived_dir_number_dominates_next_mint(self, lifecycle, project_root):
        # Live sidecar max is 158; an archive dir carries 207 -> next is 208.
        _seed_sidecar(project_root, "spec-158", slug="live-max", title="Live Max")
        _make_archive_spec_dir(project_root, "spec-207-foo")
        assert lifecycle._next_spec_number(project_root) == 208

    def test_sidecar_only_case_still_passes(self, lifecycle, tmp_path):
        # No archive, no ledger: sidecar max + 1 (no regression).
        (tmp_path / ".ai-engineering" / "specs").mkdir(parents=True)
        (tmp_path / ".ai-engineering" / "state" / "specs").mkdir(parents=True)
        (tmp_path / ".ai-engineering" / "state" / "locks").mkdir(parents=True)
        _seed_sidecar(tmp_path, "spec-042", slug="only", title="Only")
        assert lifecycle._next_spec_number(tmp_path) == 43

    def test_ledger_only_case_still_passes(self, lifecycle, project_root):
        # The fixture ledger tops out at bare 099; no sidecars, no archive.
        assert lifecycle._next_spec_number(project_root) == 100

    def test_scan_unions_archive_with_sidecar_and_ledger(self, lifecycle, project_root):
        # Fixture ledger=099, sidecar=120, archive=207 -> union max 207, +1=208.
        _seed_sidecar(project_root, "spec-120", slug="mid", title="Mid")
        _make_archive_spec_dir(project_root, "spec-207-foo")
        nums = lifecycle._scan_spec_numbers(project_root)
        assert 99 in nums
        assert 120 in nums
        assert 207 in nums
        assert lifecycle._next_spec_number(project_root) == 208


# ---------------------------------------------------------------------------
# P2 — reconcile gh-classify with no local branch ref (spec-161 #574 Bug 2)
# ---------------------------------------------------------------------------


class TestReconcileGhClassify:
    """``reconcile_merged`` ships when ``gh`` reports a merged PR, even with no
    local branch ref (the merged branch was pruned)."""

    def test_gh_merged_pr_ships_without_local_branch_ref(
        self, lifecycle, project_root, monkeypatch
    ):
        _seed_branch_sidecar(
            project_root,
            "spec-220",
            slug="gh-merged",
            title="GH Merged",
            state="in_progress",
            branch="spec-220-gh-merged",
        )
        # ``_branch_is_merged`` would say False (no local branch ref), but the
        # gh PR query reports a merged PR -> ship.
        monkeypatch.setattr(lifecycle, "_branch_is_merged", lambda *a, **k: False)
        monkeypatch.setattr(
            lifecycle,
            "_pr_merged_via_gh",
            lambda root, branch: branch == "spec-220-gh-merged",
        )
        monkeypatch.setattr(lifecycle, "_resolve_merged_pr", lambda root, branch: "820")

        report = lifecycle.reconcile_merged(project_root)

        shipped = lifecycle.status("spec-220", project_root)
        assert shipped.state is lifecycle.LifecycleState.SHIPPED
        assert "spec-220" in {r["spec_id"] for r in report["shipped"]}

    def test_falls_back_to_branch_merged_when_gh_silent(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-221",
            slug="local-merged",
            title="Local Merged",
            state="in_progress",
            branch="spec-221-local-merged",
        )
        # gh returns nothing; the local-branch classifier says merged -> ship.
        monkeypatch.setattr(lifecycle, "_pr_merged_via_gh", lambda root, branch: False)
        monkeypatch.setattr(
            lifecycle,
            "_branch_is_merged",
            lambda root, branch, default: branch == "spec-221-local-merged",
        )
        monkeypatch.setattr(lifecycle, "_resolve_merged_pr", lambda root, branch: "821")

        report = lifecycle.reconcile_merged(project_root)

        assert lifecycle.status("spec-221", project_root).state is lifecycle.LifecycleState.SHIPPED
        assert "spec-221" in {r["spec_id"] for r in report["shipped"]}

    def test_unmerged_when_both_gh_and_branch_say_no(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-222",
            slug="not-merged",
            title="Not Merged",
            state="in_progress",
            branch="spec-222-not-merged",
        )
        monkeypatch.setattr(lifecycle, "_pr_merged_via_gh", lambda root, branch: False)
        monkeypatch.setattr(lifecycle, "_branch_is_merged", lambda *a, **k: False)

        report = lifecycle.reconcile_merged(project_root)

        assert (
            lifecycle.status("spec-222", project_root).state is lifecycle.LifecycleState.IN_PROGRESS
        )
        assert "spec-222" in {r["spec_id"] for r in report["unmerged"]}
        assert "spec-222" not in {r["spec_id"] for r in report["shipped"]}

    def test_ledger_idempotency_guard_still_precedes_gh(self, lifecycle, project_root, monkeypatch):
        """A spec already in the ledger is skipped before any gh/git work."""
        history = project_root / ".ai-engineering" / "specs" / "_history.md"
        history.write_text(
            "# Spec History\n\n"
            "Completed specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n"
            "| spec-223 | Already In Ledger | shipped | 2026-05-01 | 2026-05-01 | #1 | feat/x |\n",
            encoding="utf-8",
        )
        _seed_branch_sidecar(
            project_root,
            "spec-223",
            slug="in-ledger",
            title="Already In Ledger",
            state="in_progress",
            branch="spec-223-in-ledger",
        )
        # Even if gh would say merged, the ledger guard skips it first.
        called = {"gh": False}

        def _gh(root, branch):
            called["gh"] = True
            return True

        monkeypatch.setattr(lifecycle, "_pr_merged_via_gh", _gh)
        monkeypatch.setattr(lifecycle, "_branch_is_merged", lambda *a, **k: True)

        report = lifecycle.reconcile_merged(project_root)

        assert "spec-223" not in {r["spec_id"] for r in report["shipped"]}
        assert "spec-223" in {r["spec_id"] for r in report["skipped"]}
        assert called["gh"] is False, "ledger guard must precede any gh classification"
        rows = [ln for ln in history.read_text().splitlines() if ln.startswith("| spec-223 |")]
        assert len(rows) == 1


class TestPrMergedViaGh:
    """``_pr_merged_via_gh`` fail-open shape mirrors ``_resolve_merged_pr``."""

    def test_returns_true_when_gh_lists_a_merged_pr(self, lifecycle, project_root, monkeypatch):
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(pr_for_branch={"feat/x": 900}),
        )
        assert lifecycle._pr_merged_via_gh(project_root, "feat/x") is True

    def test_returns_false_when_gh_lists_nothing(self, lifecycle, project_root, monkeypatch):
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(pr_for_branch={}),
        )
        assert lifecycle._pr_merged_via_gh(project_root, "feat/x") is False

    def test_returns_false_when_gh_absent(self, lifecycle, project_root, monkeypatch):
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(gh_available=False),
        )
        assert lifecycle._pr_merged_via_gh(project_root, "feat/x") is False


# ---------------------------------------------------------------------------
# P3 — approve / start verbs + frontmatter status mirror (spec-161)
# ---------------------------------------------------------------------------


def _read_frontmatter_status(spec_md: Path) -> str | None:
    """Return the frontmatter ``status:`` value from a spec.md, or None."""
    in_fm = False
    for line in spec_md.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if in_fm and stripped.startswith("status:"):
            return stripped.split(":", 1)[1].strip()
    return None


class TestApproveVerb:
    def test_approve_moves_draft_to_approved(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        approved = lifecycle.approve(record.spec_id, project_root)
        assert approved.state is lifecycle.LifecycleState.APPROVED
        assert (
            lifecycle.status(record.spec_id, project_root).state
            is lifecycle.LifecycleState.APPROVED
        )

    def test_approve_emits_spec_approved_event(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.approve(record.spec_id, project_root)
        events = _events(project_root)
        assert any(
            e.get("kind") == "framework_operation"
            and e.get("detail", {}).get("operation") == "spec_approved"
            for e in events
        )

    def test_approve_is_idempotent_no_duplicate_event(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.approve(record.spec_id, project_root)
        lifecycle.approve(record.spec_id, project_root)  # no raise, no dup event.
        events = _events(project_root)
        approved = [e for e in events if e.get("detail", {}).get("operation") == "spec_approved"]
        assert len(approved) == 1
        assert (
            lifecycle.status(record.spec_id, project_root).state
            is lifecycle.LifecycleState.APPROVED
        )

    def test_approve_from_shipped_raises(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-1", "feat/x", project_root)
        with pytest.raises(ValueError):
            lifecycle.approve(record.spec_id, project_root)

    def test_approve_main_returns_one_on_illegal(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.mark_shipped(record.spec_id, "PR-1", "feat/x", project_root)
        rc = lifecycle.main(["approve", record.spec_id, "--project-root", str(project_root)])
        assert rc == 1

    def test_approve_main_exits_zero_on_draft(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        rc = lifecycle.main(["approve", record.spec_id, "--project-root", str(project_root)])
        assert rc == 0


class TestStartVerb:
    def test_start_moves_approved_to_in_progress(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.approve(record.spec_id, project_root)
        started = lifecycle.start(record.spec_id, project_root)
        assert started.state is lifecycle.LifecycleState.IN_PROGRESS

    def test_start_emits_distinct_event_kind(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.approve(record.spec_id, project_root)
        lifecycle.start(record.spec_id, project_root)
        events = _events(project_root)
        ops = {e.get("detail", {}).get("operation") for e in events}
        assert "spec_started_impl" in ops
        # Must not collide with the create-event start_new emits.
        assert "spec_started_impl" != "spec_started"

    def test_start_is_idempotent_no_duplicate_event(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.approve(record.spec_id, project_root)
        lifecycle.start(record.spec_id, project_root)
        lifecycle.start(record.spec_id, project_root)  # no raise, no dup event.
        events = _events(project_root)
        started = [e for e in events if e.get("detail", {}).get("operation") == "spec_started_impl"]
        assert len(started) == 1
        assert (
            lifecycle.status(record.spec_id, project_root).state
            is lifecycle.LifecycleState.IN_PROGRESS
        )

    def test_start_from_draft_raises(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        with pytest.raises(ValueError):
            lifecycle.start(record.spec_id, project_root)

    def test_start_main_exits_zero_on_approved(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.approve(record.spec_id, project_root)
        rc = lifecycle.main(["start", record.spec_id, "--project-root", str(project_root)])
        assert rc == 0

    def test_start_main_returns_one_from_draft(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        rc = lifecycle.main(["start", record.spec_id, "--project-root", str(project_root)])
        assert rc == 1


class TestFrontmatterStatusMirror:
    def _seed_spec_md(self, project_root: Path, *, spec_id: str, slug: str, status: str) -> Path:
        specs = project_root / ".ai-engineering" / "specs"
        specs.mkdir(parents=True, exist_ok=True)
        spec_md = specs / "spec.md"
        spec_md.write_text(
            f"---\nspec: {spec_id}\nslug: {slug}\nstatus: {status}\n---\n# Body\n\ntext.\n",
            encoding="utf-8",
        )
        return spec_md

    def test_approve_mirrors_status_to_approved(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        spec_md = self._seed_spec_md(
            project_root, spec_id=record.spec_id, slug=record.slug, status="draft"
        )
        lifecycle.approve(record.spec_id, project_root)
        assert _read_frontmatter_status(spec_md) == "approved"

    def test_start_mirrors_status_to_in_progress(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        spec_md = self._seed_spec_md(
            project_root, spec_id=record.spec_id, slug=record.slug, status="draft"
        )
        lifecycle.approve(record.spec_id, project_root)
        lifecycle.start(record.spec_id, project_root)
        assert _read_frontmatter_status(spec_md) == "in-progress"

    def test_mirror_matches_on_slug_when_spec_id_absent(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        specs = project_root / ".ai-engineering" / "specs"
        specs.mkdir(parents=True, exist_ok=True)
        spec_md = specs / "spec.md"
        spec_md.write_text(
            f"---\nslug: {record.slug}\nstatus: draft\n---\n# Body\n",
            encoding="utf-8",
        )
        lifecycle.approve(record.spec_id, project_root)
        assert _read_frontmatter_status(spec_md) == "approved"

    def test_mirror_does_not_fire_for_other_spec(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        spec_md = self._seed_spec_md(
            project_root, spec_id="spec-999", slug="other-slug", status="draft"
        )
        lifecycle.approve(record.spec_id, project_root)
        # Unrelated buffer must be left intact.
        assert _read_frontmatter_status(spec_md) == "draft"

    def test_mirror_preserves_other_lines_and_body(self, lifecycle, project_root):
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        specs = project_root / ".ai-engineering" / "specs"
        specs.mkdir(parents=True, exist_ok=True)
        spec_md = specs / "spec.md"
        body = (
            f"---\nspec: {record.spec_id}\nslug: {record.slug}\n"
            f"status: draft\ntitle: My Feature\n---\n# Body\n\nexact text.\n"
        )
        spec_md.write_text(body, encoding="utf-8")
        lifecycle.approve(record.spec_id, project_root)
        text = spec_md.read_text(encoding="utf-8")
        assert "title: My Feature" in text
        assert "# Body\n\nexact text.\n" in text
        assert "status: approved" in text
        assert "status: draft" not in text

    def test_mirror_is_fail_open_when_no_spec_md(self, lifecycle, project_root):
        # No spec.md present: approve must still succeed (best-effort mirror).
        record = lifecycle.start_new("my-feature", "My Feature", project_root)
        lifecycle.approve(record.spec_id, project_root)
        assert (
            lifecycle.status(record.spec_id, project_root).state
            is lifecycle.LifecycleState.APPROVED
        )


class TestApproveStartCLIHelp:
    def test_approve_help_exits_zero(self, lifecycle):
        rc = lifecycle.main(["approve", "--help"])
        assert rc == 0

    def test_start_help_exits_zero(self, lifecycle):
        rc = lifecycle.main(["start", "--help"])
        assert rc == 0


# ---------------------------------------------------------------------------
# slot_status (spec-167 D-167-05) — read-only live-slot occupancy query
# ---------------------------------------------------------------------------


class TestSlotStatus:
    """`slot_status` reports whether spec.md holds an un-shipped spec.

    Read-only and fail-open: it never mutates state and never raises, so
    /ai-brainstorm Step -1 can warn before clobbering the slot without the
    guard ever blocking interrogation.
    """

    def _write_buffer(self, project_root: Path, text: str) -> None:
        (project_root / ".ai-engineering" / "specs" / "spec.md").write_text(text, encoding="utf-8")

    def test_idle_slot_reports_unoccupied(self, lifecycle, project_root):
        """Placeholder buffer → occupied False, idle True, no spec id."""
        self._write_buffer(project_root, "# No active spec\n\nRun /ai-brainstorm to start one.\n")
        result = lifecycle.slot_status(project_root)
        assert result["occupied"] is False
        assert result["idle"] is True
        assert result["spec_id"] is None

    def test_missing_buffer_reports_idle(self, lifecycle, project_root):
        """No spec.md at all → treated as idle (fail-open), never raises."""
        result = lifecycle.slot_status(project_root)
        assert result["occupied"] is False
        assert result["idle"] is True

    def test_occupied_by_unshipped_spec_reports_state(self, lifecycle, project_root):
        """Real content + a DRAFT/APPROVED sidecar → occupied with state+slug."""
        record = lifecycle.start_new("feat-x", "Feat X", project_root)
        lifecycle.approve(record.spec_id, project_root)
        self._write_buffer(
            project_root,
            f"---\nspec: {record.spec_id}\nslug: feat-x\n"
            f"title: Feat X\nstatus: approved\n---\n\n# Feat X\n\nbody\n",
        )
        result = lifecycle.slot_status(project_root)
        assert result["occupied"] is True
        assert result["idle"] is False
        assert result["spec_id"] == record.spec_id
        assert result["state"] == "approved"
        assert result["slug"] == "feat-x"

    def test_occupied_by_shipped_spec_surfaces_shipped_state(self, lifecycle, project_root):
        """Content present but sidecar SHIPPED → state='shipped' so the
        consumer can treat the slot as safe-to-overwrite."""
        sidecar = project_root / ".ai-engineering" / "state" / "specs" / "spec-200.json"
        sidecar.parent.mkdir(parents=True, exist_ok=True)
        sidecar.write_text(
            json.dumps(
                {
                    "spec_id": "spec-200",
                    "slug": "shipped-x",
                    "title": "Shipped X",
                    "state": "shipped",
                    "created": "2026-01-01T00:00:00+00:00",
                }
            ),
            encoding="utf-8",
        )
        self._write_buffer(
            project_root,
            "---\nspec: spec-200\nslug: shipped-x\n---\n\n# Shipped X\n\nbody\n",
        )
        result = lifecycle.slot_status(project_root)
        assert result["occupied"] is True
        assert result["state"] == "shipped"

    def test_occupied_but_unresolvable_id_is_conservative(self, lifecycle, project_root):
        """Content present, no resolvable spec id → occupied True (warn),
        spec_id None. Conservative: never silently clobber."""
        self._write_buffer(project_root, "# Some heading\n\nreal content, no spec frontmatter\n")
        result = lifecycle.slot_status(project_root)
        assert result["occupied"] is True
        assert result["spec_id"] is None

    def test_result_is_json_serializable(self, lifecycle, project_root):
        """Output must round-trip through json.dumps (CLI prints it)."""
        self._write_buffer(project_root, "# No active spec\n\nRun /ai-brainstorm to start one.\n")
        json.dumps(lifecycle.slot_status(project_root))

    def test_slot_status_help_exits_zero(self, lifecycle):
        rc = lifecycle.main(["slot_status", "--help"])
        assert rc == 0

    def test_slot_status_cli_prints_json(self, lifecycle, project_root, capsys):
        """The CLI verb prints a JSON object to stdout and exits 0."""
        self._write_buffer(project_root, "# No active spec\n\nRun /ai-brainstorm to start one.\n")
        rc = lifecycle.main(["slot_status", "--project-root", str(project_root)])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["occupied"] is False


# ---------------------------------------------------------------------------
# check_ledger — ledger-consistency guard verb (spec-180 D-180-04)
# ---------------------------------------------------------------------------


def _seed_shipped_sidecar(
    project_root: Path,
    spec_id: str,
    *,
    slug: str,
    title: str,
    pr: str | None = None,
    branch: str | None = None,
    state: str = "shipped",
) -> Path:
    """Seed a sidecar in an arbitrary state with optional pr/branch metadata."""
    specs = project_root / ".ai-engineering" / "state" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "spec_id": spec_id,
        "slug": slug,
        "title": title,
        "state": state,
        "created": datetime.now(UTC).isoformat(),
    }
    if state == "shipped":
        payload["shipped"] = datetime.now(UTC).isoformat()
    if pr is not None:
        payload["pr"] = pr
    if branch is not None:
        payload["branch"] = branch
    path = specs / f"{spec_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _make_spec_archive_dir(project_root: Path, spec_id: str, slug: str) -> Path:
    """Create a ``specs/archive/<spec_id>-<slug>/`` dir with a spec.md."""
    d = project_root / ".ai-engineering" / "specs" / "archive" / f"{spec_id}-{slug}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "spec.md").write_text(f"# {spec_id}\n", encoding="utf-8")
    return d


class TestLedgerConsistencyGuard:
    """`check_ledger` flags structural inconsistencies between sidecars,
    archive dirs and slug↔id numbering. Read-only: never mutates state.
    """

    def _rules(self, result: dict, spec_id: str) -> set[str]:
        return {v["rule"] for v in result["violations"] if v["spec_id"] == spec_id}

    def test_shipped_with_null_pr_and_no_archive_is_flagged(self, lifecycle, project_root):
        _seed_shipped_sidecar(
            project_root, "spec-300", slug="ghost-ship", title="Ghost Ship", pr=None
        )
        result = lifecycle.check_ledger(project_root)
        assert "shipped-no-evidence" in self._rules(result, "spec-300")

    def test_shipped_with_archive_present_is_not_flagged(self, lifecycle, project_root):
        _seed_shipped_sidecar(
            project_root, "spec-301", slug="real-ship", title="Real Ship", pr=None
        )
        _make_spec_archive_dir(project_root, "spec-301", "real-ship")
        result = lifecycle.check_ledger(project_root)
        assert "shipped-no-evidence" not in self._rules(result, "spec-301")

    def test_shipped_with_pr_is_not_flagged(self, lifecycle, project_root):
        _seed_shipped_sidecar(project_root, "spec-302", slug="pr-ship", title="PR Ship", pr="900")
        result = lifecycle.check_ledger(project_root)
        assert "shipped-no-evidence" not in self._rules(result, "spec-302")

    def test_shipped_with_ledger_row_only_is_not_flagged(self, lifecycle, project_root):
        # Null PR, no archive — but a _history done-row is evidence enough.
        _seed_shipped_sidecar(project_root, "spec-320", slug="ledgered", title="Ledgered", pr=None)
        _write_history_done_row(project_root, "spec-320", "Ledgered", pr="—")
        result = lifecycle.check_ledger(project_root)
        assert "shipped-no-evidence" not in self._rules(result, "spec-320")

    def test_shipped_with_decision_ref_only_is_not_flagged(self, lifecycle, project_root):
        # Null PR, no archive, no ledger row — a live D-<num>- anchor is evidence.
        _seed_shipped_sidecar(project_root, "spec-154", slug="dec-only", title="Dec Only", pr=None)
        _write_decision_ref(project_root, "D-154-03")
        result = lifecycle.check_ledger(project_root)
        assert "shipped-no-evidence" not in self._rules(result, "spec-154")

    def test_shipped_with_zero_evidence_is_flagged(self, lifecycle, project_root):
        # Truly zero evidence: null PR, no archive, no ledger row, no decision ref.
        _seed_shipped_sidecar(project_root, "spec-321", slug="zero-ev", title="Zero Ev", pr=None)
        result = lifecycle.check_ledger(project_root)
        assert "shipped-no-evidence" in self._rules(result, "spec-321")

    def test_shipped_em_dash_pr_with_ledger_row_is_not_flagged(self, lifecycle, project_root):
        # The em-dash PR sentinel is not real evidence, but a ledger row is.
        _seed_shipped_sidecar(project_root, "spec-322", slug="dashed", title="Dashed", pr="—")
        _write_history_done_row(project_root, "spec-322", "Dashed", pr="—")
        result = lifecycle.check_ledger(project_root)
        assert "shipped-no-evidence" not in self._rules(result, "spec-322")

    def test_nonterminal_with_archive_dir_is_flagged(self, lifecycle, project_root):
        _seed_shipped_sidecar(project_root, "spec-303", slug="early", title="Early", state="draft")
        _make_spec_archive_dir(project_root, "spec-303", "early")
        result = lifecycle.check_ledger(project_root)
        assert "nonterminal-with-archive" in self._rules(result, "spec-303")

    def test_approved_with_archive_dir_is_flagged(self, lifecycle, project_root):
        _seed_shipped_sidecar(project_root, "spec-304", slug="appr", title="Appr", state="approved")
        _make_spec_archive_dir(project_root, "spec-304", "appr")
        result = lifecycle.check_ledger(project_root)
        assert "nonterminal-with-archive" in self._rules(result, "spec-304")

    def test_id_slug_numeric_mismatch_is_flagged(self, lifecycle, project_root):
        _seed_shipped_sidecar(
            project_root, "spec-158", slug="spec-159-renamed", title="Mismatch", pr="800"
        )
        result = lifecycle.check_ledger(project_root)
        assert "id-slug-mismatch" in self._rules(result, "spec-158")

    def test_id_slug_match_is_not_flagged(self, lifecycle, project_root):
        _seed_shipped_sidecar(
            project_root, "spec-159", slug="spec-159-renamed", title="Match", pr="801"
        )
        result = lifecycle.check_ledger(project_root)
        assert "id-slug-mismatch" not in self._rules(result, "spec-159")

    def test_inflight_draft_null_pr_is_clean(self, lifecycle, project_root):
        _seed_shipped_sidecar(project_root, "spec-305", slug="wip", title="WIP", state="draft")
        result = lifecycle.check_ledger(project_root)
        assert self._rules(result, "spec-305") == set()

    def test_inflight_approved_null_pr_is_clean(self, lifecycle, project_root):
        _seed_shipped_sidecar(project_root, "spec-306", slug="wip2", title="WIP2", state="approved")
        result = lifecycle.check_ledger(project_root)
        assert self._rules(result, "spec-306") == set()

    def test_inflight_in_progress_null_pr_is_clean(self, lifecycle, project_root):
        _seed_shipped_sidecar(
            project_root, "spec-307", slug="wip3", title="WIP3", state="in_progress"
        )
        result = lifecycle.check_ledger(project_root)
        assert self._rules(result, "spec-307") == set()

    def test_abandoned_null_pr_no_ship_is_clean(self, lifecycle, project_root):
        _seed_shipped_sidecar(
            project_root, "spec-308", slug="dead", title="Dead", state="abandoned"
        )
        result = lifecycle.check_ledger(project_root)
        assert self._rules(result, "spec-308") == set()

    def test_shipped_absent_from_history_is_not_flagged(self, lifecycle, project_root):
        # Shipped with archive evidence but no ledger row -> ledger absence is
        # NOT a check_ledger violation (that is consolidate_shipped's job).
        _seed_shipped_sidecar(project_root, "spec-309", slug="unrowed", title="Unrowed", pr="700")
        result = lifecycle.check_ledger(project_root)
        assert self._rules(result, "spec-309") == set()

    def test_checked_count_reflects_sidecars(self, lifecycle, project_root):
        _seed_shipped_sidecar(project_root, "spec-310", slug="a", title="A", pr="1")
        _seed_shipped_sidecar(project_root, "spec-311", slug="b", title="B", pr="2")
        result = lifecycle.check_ledger(project_root)
        assert result["checked"] == 2

    def test_result_is_json_serializable(self, lifecycle, project_root):
        _seed_shipped_sidecar(project_root, "spec-312", slug="ser", title="Ser", pr=None)
        json.dumps(lifecycle.check_ledger(project_root))

    def test_cli_exits_nonzero_when_violations_present(self, lifecycle, project_root, capsys):
        _seed_shipped_sidecar(project_root, "spec-313", slug="bad", title="Bad", pr=None)
        rc = lifecycle.main(["check_ledger", "--project-root", str(project_root)])
        assert rc != 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["violations"]

    def test_cli_exits_zero_when_clean(self, lifecycle, project_root, capsys):
        _seed_shipped_sidecar(project_root, "spec-314", slug="ok", title="OK", pr="500")
        rc = lifecycle.main(["check_ledger", "--project-root", str(project_root)])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["violations"] == []


# ---------------------------------------------------------------------------
# reconcile_all — 3-signal reconcile verb (spec-180 D-180-03)
# ---------------------------------------------------------------------------


def _write_history_done_row(
    project_root: Path, spec_id: str, title: str, *, pr: str = "500"
) -> None:
    """Append a ``done`` ledger row for ``spec_id`` to ``_history.md``.

    The PR cell (column 6) defaults to ``500`` but can be overridden (or set to
    the em-dash ``—`` sentinel) so backfill tests can exercise both branches.
    """
    history = project_root / ".ai-engineering" / "specs" / "_history.md"
    existing = (
        history.read_text(encoding="utf-8")
        if history.exists()
        else (
            "# Spec History\n\nCompleted specs. Details in git history.\n\n"
            "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
            "|----|-------|--------|---------|---------|----|--------|\n"
        )
    )
    existing += f"| {spec_id} | {title} | done | 2026-04-02 | 2026-04-03 | {pr} | feat/x |\n"
    history.write_text(existing, encoding="utf-8")


def _write_decision_ref(project_root: Path, anchor: str) -> Path:
    """Write a docs file carrying a live ``D-<NNN>-`` decision anchor."""
    docs = project_root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    p = docs / "ref.md"
    p.write_text(f"# Refs\n\nSee {anchor} for the rationale.\n", encoding="utf-8")
    return p


class TestReconcileAll:
    """`reconcile_all` classifies non-terminal sidecars SHIPPED when ANY of
    four signals hold (gh PR, ledger row, archive dir, live decision ref) and
    ABANDONED only when ALL signals are absent AND (superseded or stale).
    Terminal states are never downgraded; ``dry_run`` mutates nothing.
    """

    def _ship_ids(self, report: dict) -> set[str]:
        return {r["spec_id"] for r in report["shipped"]}

    def _abandon_ids(self, report: dict) -> set[str]:
        return {r["spec_id"] for r in report["abandoned"]}

    def test_gh_pr_signal_classifies_shipped(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-400",
            slug="gh-spec",
            title="GH Spec",
            state="in_progress",
            branch="spec-400-gh-spec",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(
                merged_branches={"spec-400-gh-spec"},
                pr_for_branch={"spec-400-gh-spec": 600},
            ),
        )
        report = lifecycle.reconcile_all(project_root)
        assert "spec-400" in self._ship_ids(report)
        assert lifecycle.status("spec-400", project_root).state is lifecycle.LifecycleState.SHIPPED

    def test_ledger_row_signal_classifies_shipped(self, lifecycle, project_root, monkeypatch):
        # Bundle-PR case: branch yields an EMPTY gh result, but the ledger row
        # still classifies the spec as shipped.
        _seed_branch_sidecar(
            project_root,
            "spec-401",
            slug="ledger-spec",
            title="Ledger Spec",
            state="in_progress",
            branch="spec-401-ledger-spec",
        )
        _write_history_done_row(project_root, "spec-401", "Ledger Spec", pr="#509")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set(), pr_for_branch={}),
        )
        report = lifecycle.reconcile_all(project_root)
        assert "spec-401" in self._ship_ids(report)
        assert lifecycle.status("spec-401", project_root).state is lifecycle.LifecycleState.SHIPPED
        # The PR is backfilled from the ledger row, not the em-dash sentinel.
        entry = next(r for r in report["shipped"] if r["spec_id"] == "spec-401")
        assert entry["pr"] == "#509"
        assert lifecycle.status("spec-401", project_root).pr == "#509"

    def test_bundle_pr_backfilled_from_ledger_when_gh_empty(
        self, lifecycle, project_root, monkeypatch
    ):
        # A bundle-merged spec: gh returns no PR for the branch, but the ledger
        # row carries the bundle PR (#586). reconcile_all must backfill it.
        _seed_branch_sidecar(
            project_root,
            "spec-410",
            slug="bundle-spec",
            title="Bundle Spec",
            state="in_progress",
            branch="spec-410-bundle-spec",
        )
        _write_history_done_row(project_root, "spec-410", "Bundle Spec", pr="#586")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set(), pr_for_branch={}),
        )
        report = lifecycle.reconcile_all(project_root)
        entry = next(r for r in report["shipped"] if r["spec_id"] == "spec-410")
        assert entry["pr"] == "#586"
        assert lifecycle.status("spec-410", project_root).pr == "#586"

    def test_ledger_row_without_pr_falls_back_to_em_dash(
        self, lifecycle, project_root, monkeypatch
    ):
        # Ledger row marks done but its PR cell is the em-dash placeholder.
        _seed_branch_sidecar(
            project_root,
            "spec-411",
            slug="no-pr-spec",
            title="No PR Spec",
            state="in_progress",
            branch=None,
        )
        _write_history_done_row(project_root, "spec-411", "No PR Spec", pr="—")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set(), pr_for_branch={}),
        )
        report = lifecycle.reconcile_all(project_root)
        entry = next(r for r in report["shipped"] if r["spec_id"] == "spec-411")
        assert entry["pr"] == "—"

    def test_gh_pr_wins_over_ledger_backfill(self, lifecycle, project_root, monkeypatch):
        # When the branch resolves a gh PR, that takes precedence over the
        # ledger row PR (the gh signal is the most direct evidence).
        _seed_branch_sidecar(
            project_root,
            "spec-412",
            slug="gh-wins",
            title="GH Wins",
            state="in_progress",
            branch="spec-412-gh-wins",
        )
        _write_history_done_row(project_root, "spec-412", "GH Wins", pr="#509")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(
                merged_branches={"spec-412-gh-wins"},
                pr_for_branch={"spec-412-gh-wins": 999},
            ),
        )
        report = lifecycle.reconcile_all(project_root)
        entry = next(r for r in report["shipped"] if r["spec_id"] == "spec-412")
        assert entry["pr"] == "999"

    def test_archive_dir_signal_classifies_shipped(self, lifecycle, project_root, monkeypatch):
        # No branch, no gh row -> archive dir alone classifies shipped.
        _seed_branch_sidecar(
            project_root,
            "spec-402",
            slug="arch-spec",
            title="Arch Spec",
            state="approved",
            branch=None,
        )
        _make_spec_archive_dir(project_root, "spec-402", "arch-spec")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set()),
        )
        report = lifecycle.reconcile_all(project_root)
        assert "spec-402" in self._ship_ids(report)

    def test_archive_dir_resolves_prefixed_slug(self, lifecycle, project_root):
        # spec-180 review hardening: a sidecar whose slug already carries the
        # ``spec-NNN-`` prefix (e.g. spec-133 ``spec-133-surface-primitive-rearch``)
        # has an archive dir named verbatim as the slug. ``group(2)`` is the bare
        # trailing slug and can never equal the prefixed slug, so this used to be
        # a silent blind spot. The verbatim ``child.name == slug`` fallback fixes it.
        slug = "spec-404-prefixed-rearch"
        archive = project_root / ".ai-engineering" / "specs" / "archive" / slug
        archive.mkdir(parents=True)
        assert lifecycle._resolve_via_archive_dir(project_root, slug) == "spec-404"

    def test_decision_ref_signal_classifies_shipped(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-403",
            slug="dec-spec",
            title="Dec Spec",
            state="in_progress",
            branch=None,
        )
        _write_decision_ref(project_root, "D-403-01")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set()),
        )
        report = lifecycle.reconcile_all(project_root)
        assert "spec-403" in self._ship_ids(report)

    def test_no_signal_and_stale_classifies_abandoned(self, lifecycle, project_root, monkeypatch):
        path = _seed_branch_sidecar(
            project_root,
            "spec-404",
            slug="dead-spec",
            title="Dead Spec",
            state="draft",
            branch=None,
        )
        # Backdate created far past the staleness threshold.
        from datetime import timedelta

        data = json.loads(path.read_text())
        data["created"] = (datetime.now(UTC) - timedelta(days=120)).isoformat()
        path.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set()),
        )
        report = lifecycle.reconcile_all(project_root)
        assert "spec-404" in self._abandon_ids(report)
        assert (
            lifecycle.status("spec-404", project_root).state is lifecycle.LifecycleState.ABANDONED
        )

    def test_no_signal_but_fresh_is_left_untouched(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-405",
            slug="fresh-spec",
            title="Fresh Spec",
            state="draft",
            branch=None,
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set()),
        )
        report = lifecycle.reconcile_all(project_root)
        assert "spec-405" not in self._ship_ids(report)
        assert "spec-405" not in self._abandon_ids(report)
        assert lifecycle.status("spec-405", project_root).state is lifecycle.LifecycleState.DRAFT

    def test_terminal_state_never_downgraded(self, lifecycle, project_root, monkeypatch):
        _seed_shipped_sidecar(project_root, "spec-406", slug="terminal", title="Terminal", pr="900")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set()),
        )
        report = lifecycle.reconcile_all(project_root)
        assert "spec-406" not in self._abandon_ids(report)
        assert lifecycle.status("spec-406", project_root).state is lifecycle.LifecycleState.SHIPPED

    def test_dry_run_mutates_nothing(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-407",
            slug="dry-spec",
            title="Dry Spec",
            state="in_progress",
            branch="spec-407-dry-spec",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(
                merged_branches={"spec-407-dry-spec"},
                pr_for_branch={"spec-407-dry-spec": 600},
            ),
        )
        report = lifecycle.reconcile_all(project_root, dry_run=True)
        assert "spec-407" in self._ship_ids(report)
        # State untouched on disk.
        assert (
            lifecycle.status("spec-407", project_root).state is lifecycle.LifecycleState.IN_PROGRESS
        )

    def test_dry_run_report_carries_evidence(self, lifecycle, project_root, monkeypatch):
        _seed_branch_sidecar(
            project_root,
            "spec-408",
            slug="ev-spec",
            title="Ev Spec",
            state="in_progress",
            branch=None,
        )
        _make_spec_archive_dir(project_root, "spec-408", "ev-spec")
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(merged_branches=set()),
        )
        report = lifecycle.reconcile_all(project_root, dry_run=True)
        entry = next(r for r in report["shipped"] if r["spec_id"] == "spec-408")
        assert "evidence" in entry
        assert entry["evidence"]

    def test_explicit_id_map_has_release_spec(self, lifecycle):
        assert (
            lifecycle._EXPLICIT_ID_MAP.get("ai-engineering-release-version-cicd-pypi") == "spec-143"
        )

    def test_live_decision_refs_helper_detects_anchor(self, lifecycle, project_root):
        _write_decision_ref(project_root, "D-180-04")
        assert lifecycle._live_decision_refs(project_root, "spec-180") is True

    def test_live_decision_refs_helper_no_false_positive(self, lifecycle, project_root):
        _write_decision_ref(project_root, "D-180-04")
        # spec-999 has no anchor anywhere.
        assert lifecycle._live_decision_refs(project_root, "spec-999") is False

    def test_cli_dry_run_flag(self, lifecycle, project_root, monkeypatch, capsys):
        _seed_branch_sidecar(
            project_root,
            "spec-409",
            slug="cli-spec",
            title="CLI Spec",
            state="in_progress",
            branch="spec-409-cli-spec",
        )
        monkeypatch.setattr(
            lifecycle.subprocess,
            "run",
            _FakeGit(
                merged_branches={"spec-409-cli-spec"},
                pr_for_branch={"spec-409-cli-spec": 600},
            ),
        )
        rc = lifecycle.main(["reconcile_all", "--dry-run", "--project-root", str(project_root)])
        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert "spec-409" in {r["spec_id"] for r in payload["shipped"]}
        # dry-run: no mutation.
        assert (
            lifecycle.status("spec-409", project_root).state is lifecycle.LifecycleState.IN_PROGRESS
        )
