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

# The placeholder both working buffers are reset to at the SHIPPED transition.
_PLACEHOLDER = "# (no active spec)\n\nRun /ai-brainstorm to start one.\n"


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

        assert spec_md.read_text() == _PLACEHOLDER
        assert plan_md.read_text() == _PLACEHOLDER

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
        assert (archive_dir / "spec.md").read_text() != _PLACEHOLDER
        assert spec_md.read_text() == _PLACEHOLDER

    def test_mark_shipped_skips_snapshot_when_buffer_is_placeholder(self, lifecycle, project_root):
        record = lifecycle.start_new("cool-feature", "Cool Feature", project_root)
        _seed_working_buffers(
            project_root,
            spec_body=_PLACEHOLDER,
            plan_body=_PLACEHOLDER,
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
        assert spec_md.read_text() == _PLACEHOLDER
        assert plan_md.read_text() == _PLACEHOLDER


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
        """The lifecycle's own placeholder is still a placeholder (no regression)."""
        assert lifecycle._buffer_is_placeholder(_PLACEHOLDER) is True

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
