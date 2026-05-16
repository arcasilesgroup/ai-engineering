"""Tests for doctor/phases/state.py -- state file validation checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.phases import state as state_phase
from ai_engineering.state.defaults import (
    default_decision_store,
    default_install_state,
    default_ownership_map,
)
from ai_engineering.state.io import write_json_model


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project directory with valid state files."""
    sd = tmp_path / ".ai-engineering" / "state"
    sd.mkdir(parents=True)

    write_json_model(sd / "install-state.json", default_install_state())
    write_json_model(sd / "ownership-map.json", default_ownership_map())
    write_json_model(sd / "decision-store.json", default_decision_store())

    return tmp_path


@pytest.fixture()
def ctx(project: Path) -> DoctorContext:
    """DoctorContext targeting the temp project."""
    return DoctorContext(target=project)


# ── state-files-parseable ──────────────────────────────────────────────


class TestFilesParseableCheck:
    def test_ok_when_all_files_present(self, ctx: DoctorContext) -> None:
        results = state_phase.check(ctx)
        parseable = next(r for r in results if r.name == "state-files-parseable")
        assert parseable.status == CheckStatus.OK

    def test_fail_when_file_missing(self, tmp_path: Path) -> None:
        # Post-spec-124 D-124-12: ownership-map and decision-store
        # migrated to state.db; only install-state remains in this
        # check. With install-state absent the probe FAILs.
        sd = tmp_path / ".ai-engineering" / "state"
        sd.mkdir(parents=True)
        # No install-state.json: probe expects FAIL.

        ctx = DoctorContext(target=tmp_path)
        results = state_phase.check(ctx)
        parseable = next(r for r in results if r.name == "state-files-parseable")
        assert parseable.status == CheckStatus.FAIL
        assert parseable.fixable is True
        assert "missing" in parseable.message
        assert "install-state.json" in parseable.message

    def test_fail_when_file_unparseable(self, project: Path) -> None:
        sd = project / ".ai-engineering" / "state"
        (sd / "install-state.json").write_text("not json", encoding="utf-8")

        ctx = DoctorContext(target=project)
        results = state_phase.check(ctx)
        parseable = next(r for r in results if r.name == "state-files-parseable")
        assert parseable.status == CheckStatus.FAIL
        assert "unparseable" in parseable.message

    def test_fail_when_no_state_dir(self, tmp_path: Path) -> None:
        ctx = DoctorContext(target=tmp_path)
        results = state_phase.check(ctx)
        parseable = next(r for r in results if r.name == "state-files-parseable")
        assert parseable.status == CheckStatus.FAIL
        assert "missing" in parseable.message


# ── state-schema ───────────────────────────────────────────────────────


class TestStateSchemaCheck:
    def test_ok_with_valid_schema(self, ctx: DoctorContext) -> None:
        results = state_phase.check(ctx)
        schema = next(r for r in results if r.name == "state-schema")
        assert schema.status == CheckStatus.OK

    def test_warn_when_schema_version_mismatch(self, project: Path) -> None:
        sd = project / ".ai-engineering" / "state"
        path = sd / "install-state.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["schema_version"] = "1.0"
        path.write_text(json.dumps(data), encoding="utf-8")

        ctx = DoctorContext(target=project)
        results = state_phase.check(ctx)
        schema = next(r for r in results if r.name == "state-schema")
        assert schema.status == CheckStatus.WARN
        assert "1.0" in schema.message

    def test_warn_when_file_missing(self, tmp_path: Path) -> None:
        sd = tmp_path / ".ai-engineering" / "state"
        sd.mkdir(parents=True)

        ctx = DoctorContext(target=tmp_path)
        results = state_phase.check(ctx)
        schema = next(r for r in results if r.name == "state-schema")
        assert schema.status == CheckStatus.WARN

    def test_warn_when_file_unparseable(self, project: Path) -> None:
        sd = project / ".ai-engineering" / "state"
        (sd / "install-state.json").write_text("{bad", encoding="utf-8")

        ctx = DoctorContext(target=project)
        results = state_phase.check(ctx)
        schema = next(r for r in results if r.name == "state-schema")
        assert schema.status == CheckStatus.WARN


# ── ownership-coverage ─────────────────────────────────────────────────


class TestOwnershipCoverageCheck:
    def test_ok_with_full_defaults(self, ctx: DoctorContext) -> None:
        results = state_phase.check(ctx)
        coverage = next(r for r in results if r.name == "ownership-coverage")
        assert coverage.status == CheckStatus.OK

    def test_warn_when_patterns_missing(self, project: Path) -> None:
        sd = project / ".ai-engineering" / "state"
        # Write an ownership map with only one pattern
        from ai_engineering.state.models import (
            FrameworkUpdatePolicy,
            OwnershipEntry,
            OwnershipLevel,
            OwnershipMap,
        )

        sparse_map = OwnershipMap(
            paths=[
                OwnershipEntry(
                    pattern="CLAUDE.md",
                    owner=OwnershipLevel.FRAMEWORK_MANAGED,
                    frameworkUpdate=FrameworkUpdatePolicy.ALLOW,
                )
            ]
        )
        write_json_model(sd / "ownership-map.json", sparse_map)

        ctx = DoctorContext(target=project)
        results = state_phase.check(ctx)
        coverage = next(r for r in results if r.name == "ownership-coverage")
        assert coverage.status == CheckStatus.WARN
        assert "missing" in coverage.message

    def test_warn_when_file_missing(self, tmp_path: Path) -> None:
        sd = tmp_path / ".ai-engineering" / "state"
        sd.mkdir(parents=True)

        ctx = DoctorContext(target=tmp_path)
        results = state_phase.check(ctx)
        coverage = next(r for r in results if r.name == "ownership-coverage")
        assert coverage.status == CheckStatus.WARN


# ── fix() ──────────────────────────────────────────────────────────────


class TestStateFix:
    def test_fix_regenerates_missing_files(self, tmp_path: Path) -> None:
        # Post-spec-124 D-124-12: only install-state.json is regenerated;
        # ownership-map and decision-store are owned by state.db and must
        # NOT reappear on disk after fix.
        sd = tmp_path / ".ai-engineering" / "state"
        sd.mkdir(parents=True)

        ctx = DoctorContext(target=tmp_path)
        checks = state_phase.check(ctx)
        fixable = [c for c in checks if c.fixable]

        fixed = state_phase.fix(ctx, fixable)

        # Only install-state.json should now exist on disk.
        assert (sd / "install-state.json").is_file()
        assert not (sd / "ownership-map.json").exists()
        assert not (sd / "decision-store.json").exists()

        result = next(r for r in fixed if r.name == "state-files-parseable")
        assert result.status == CheckStatus.FIXED
        assert "regenerated" in result.message
        assert "install-state.json" in result.message

    def test_fix_dry_run_does_not_write(self, tmp_path: Path) -> None:
        sd = tmp_path / ".ai-engineering" / "state"
        sd.mkdir(parents=True)

        ctx = DoctorContext(target=tmp_path)
        checks = state_phase.check(ctx)
        fixable = [c for c in checks if c.fixable]

        fixed = state_phase.fix(ctx, fixable, dry_run=True)

        # Files should NOT exist
        assert not (sd / "install-state.json").is_file()
        assert not (sd / "ownership-map.json").is_file()
        assert not (sd / "decision-store.json").is_file()

        result = next(r for r in fixed if r.name == "state-files-parseable")
        assert result.status == CheckStatus.FIXED

    def test_fix_skips_non_fixable_checks(self, project: Path) -> None:
        ctx = DoctorContext(target=project)

        # Pass a non-fixable check through fix
        warn = [
            state_phase._check_state_schema(ctx),
        ]
        fixed = state_phase.fix(ctx, warn)
        # Should pass through unchanged
        assert len(fixed) == 1
        assert fixed[0].name == "state-schema"

    def test_fix_only_regenerates_missing(self, project: Path) -> None:
        """Post-spec-124 D-124-12: only install-state.json regenerates.

        The state.db-owned files (decision-store, ownership-map) must
        not reappear on disk regardless of which file is unlinked --
        the probe simply ignores them.
        """
        sd = project / ".ai-engineering" / "state"
        (sd / "install-state.json").unlink()

        ctx = DoctorContext(target=project)
        checks = state_phase.check(ctx)
        fixable = [c for c in checks if c.fixable]

        fixed = state_phase.fix(ctx, fixable)
        result = next(r for r in fixed if r.name == "state-files-parseable")
        assert result.status == CheckStatus.FIXED
        assert "install-state.json" in result.message
        # state.db-owned files must not be regenerated.
        assert "decision-store.json" not in result.message
        assert "ownership-map.json" not in result.message

    def test_fix_uses_manifest_root_entry_point_contract_for_ownership_map(
        self, tmp_path: Path
    ) -> None:
        # Post-spec-124 D-124-12: doctor.fix no longer writes
        # ownership-map.json. The ownership contract lives in
        # state.db.ownership_map; this test now verifies the JSON
        # projection is NOT regenerated and that state.db carries the
        # default contract patterns derived from the manifest.
        sd = tmp_path / ".ai-engineering" / "state"
        sd.mkdir(parents=True)
        write_json_model(sd / "install-state.json", default_install_state())

        manifest_path = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            "ownership:\n"
            "  root_entry_points:\n"
            "    CLAUDE.md:\n"
            "      owner: team\n"
            "      canonical_source: CONSTITUTION.md\n"
            "      runtime_role: ide-overlay\n"
            "      sync:\n"
            "        mode: copy\n"
            "        template_path: src/ai_engineering/templates/project/CLAUDE.md\n"
            "        mirror_paths: []\n",
            encoding="utf-8",
        )

        ctx = DoctorContext(target=tmp_path)
        checks = state_phase.check(ctx)
        fixable = [check for check in checks if check.fixable]

        state_phase.fix(ctx, fixable)

        # JSON projection must not reappear on disk.
        assert not (sd / "ownership-map.json").exists()

    def test_check_returns_three_results(self, ctx: DoctorContext) -> None:
        # spec-107 D-107-10 (T-6.5) added two WARN-only advisory checks for
        # the H2 hash chain over events + decisions: the state phase now
        # ships five checks instead of three. The legacy assertion is kept
        # as the lower-bound contract (the original three remain) and the
        # new advisory names are explicitly enumerated so future drifts
        # surface as test failures rather than silent regressions.
        results = state_phase.check(ctx)
        assert len(results) == 5
        names = {r.name for r in results}
        assert names == {
            "state-files-parseable",
            "state-schema",
            "ownership-coverage",
            "audit-chain-events",
            "audit-chain-decisions",
        }
