"""RED tests for the spec_lifecycle.py automation script (sub-spec sub-001).

Covers five public CLI verbs (`start_new`, `mark_shipped`, `archive`, `sweep`,
`status`) plus the one-shot `migrate_history` migration. Each verb is a
hexagonal composition of:

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
import sys
import time
from datetime import UTC
from pathlib import Path

import pytest

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
        assert elapsed < 0.5, f"start_new took {elapsed:.3f}s (>500ms budget)"


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
        assert elapsed < 0.5, f"mark_shipped took {elapsed:.3f}s (>500ms budget)"


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
        assert elapsed < 0.5, f"archive took {elapsed:.3f}s (>500ms budget)"


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
        assert elapsed < 0.5, f"sweep took {elapsed:.3f}s (>500ms budget)"


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
        assert elapsed < 0.5, f"status took {elapsed:.3f}s (>500ms budget)"


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
