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

    def test_marks_shipped_on_squash_merge_empty_diff(self, lifecycle, project_root, monkeypatch):
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
            _FakeGit(
                merged_branches=set(),
                empty_diff_branches={"spec-201-squashed-spec"},
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
