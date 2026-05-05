"""Unit tests for skills/service.py and maintenance/report.py.

Covers:
- SkillStatus eligibility logic.
- list_local_skill_status() with mocked filesystem and dependencies.
- StaleFile creation and fields.
- MaintenanceReport health_score calculation and warnings.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.maintenance.report import (
    MaintenanceReport,
    StaleFile,
    TaskScorecard,
    build_task_scorecard,
)
from ai_engineering.skills.service import (
    SkillStatus,
    list_local_skill_status,
)
from ai_engineering.state.io import append_ndjson, write_json_model
from ai_engineering.state.models import (
    FrameworkEvent,
    TaskLedger,
    TaskLedgerTask,
    TaskLifecycleState,
)

# ---------------------------------------------------------------------------
# SkillStatus
# ---------------------------------------------------------------------------


class TestSkillStatus:
    """Tests for SkillStatus eligibility logic."""

    def test_eligible_when_no_missing_deps(self) -> None:
        status = SkillStatus(name="test", file_path="skills/test.md", eligible=True)
        assert status.eligible is True
        assert status.missing_bins == []
        assert status.missing_env == []

    def test_not_eligible_when_missing_bins_present(self) -> None:
        status = SkillStatus(
            name="test",
            file_path="skills/test.md",
            eligible=False,
            missing_bins=["ruff"],
        )
        assert status.eligible is False
        assert "ruff" in status.missing_bins

    def test_with_all_missing_types(self) -> None:
        status = SkillStatus(
            name="complex",
            file_path="skills/complex.md",
            eligible=False,
            missing_bins=["ruff"],
            missing_any_bins=["gh", "az"],
            missing_env=["API_KEY"],
            missing_config=["providers.primary"],
            missing_os=["linux"],
            errors=["missing-frontmatter"],
        )
        assert status.eligible is False
        assert status.missing_bins == ["ruff"]
        assert status.missing_any_bins == ["gh", "az"]
        assert status.missing_env == ["API_KEY"]
        assert status.missing_config == ["providers.primary"]
        assert status.missing_os == ["linux"]
        assert status.errors == ["missing-frontmatter"]


# ---------------------------------------------------------------------------
# list_local_skill_status() — mocked
# ---------------------------------------------------------------------------


class TestListLocalSkillStatus:
    """Tests for list_local_skill_status() with mocked filesystem."""

    def test_empty_skills_dir_returns_empty(self, tmp_path: Path) -> None:
        """When .ai-engineering/skills does not exist, returns empty list."""
        result = list_local_skill_status(tmp_path)
        assert result == []

    def test_returns_statuses_for_skill_files(self, tmp_path: Path) -> None:
        """Parses skill frontmatter and returns SkillStatus list."""
        skills_dir = tmp_path / ".ai-engineering" / "skills" / "dev"
        skills_dir.mkdir(parents=True)

        skill_file = skills_dir / "sample.md"
        skill_file.write_text(
            "---\nname: sample\nversion: 1.0.0\ncategory: dev\n---\n\n# Sample\n",
            encoding="utf-8",
        )

        # Create manifest.yml (required by the function)
        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.write_text("{}\n", encoding="utf-8")

        result = list_local_skill_status(tmp_path)
        assert len(result) == 1
        assert result[0].name == "sample"
        assert result[0].eligible is True

    @patch("ai_engineering.skills.service.shutil.which", return_value=None)
    def test_skill_with_missing_binary(self, mock_which: MagicMock, tmp_path: Path) -> None:
        """When a required binary is missing, skill is not eligible."""
        skills_dir = tmp_path / ".ai-engineering" / "skills" / "dev"
        skills_dir.mkdir(parents=True)

        skill_file = skills_dir / "needs-binary.md"
        skill_file.write_text(
            "---\nname: needs-binary\nversion: 1.0.0\ncategory: dev\n"
            "requires:\n  bins: [missing-tool]\n---\n\n# Needs Binary\n",
            encoding="utf-8",
        )

        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.write_text("{}\n", encoding="utf-8")

        result = list_local_skill_status(tmp_path)
        assert len(result) == 1
        assert result[0].eligible is False
        assert "missing-tool" in result[0].missing_bins

    @patch.dict("os.environ", {}, clear=True)
    def test_skill_with_env_requirement(self, tmp_path: Path) -> None:
        """When a required env var is missing, skill is not eligible."""
        skills_dir = tmp_path / ".ai-engineering" / "skills" / "dev"
        skills_dir.mkdir(parents=True)

        skill_file = skills_dir / "needs-env.md"
        skill_file.write_text(
            "---\nname: needs-env\nversion: 1.0.0\ncategory: dev\n"
            "requires:\n  env: [MISSING_ENV_VAR]\n---\n\n# Needs Env\n",
            encoding="utf-8",
        )

        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.write_text("{}\n", encoding="utf-8")

        result = list_local_skill_status(tmp_path)
        assert len(result) == 1
        assert result[0].eligible is False
        assert "MISSING_ENV_VAR" in result[0].missing_env

    def test_skills_dir_exists_but_empty(self, tmp_path: Path) -> None:
        """When skills dir exists but has no .md files, returns empty list."""
        skills_dir = tmp_path / ".ai-engineering" / "skills"
        skills_dir.mkdir(parents=True)

        manifest = tmp_path / ".ai-engineering" / "manifest.yml"
        manifest.write_text("{}\n", encoding="utf-8")

        result = list_local_skill_status(tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# StaleFile
# ---------------------------------------------------------------------------


class TestStaleFile:
    """Tests for StaleFile dataclass."""

    def test_creation_and_fields(self) -> None:
        now = datetime.now(tz=UTC)
        stale = StaleFile(path=Path("standards/core.md"), last_modified=now, age_days=95)
        assert stale.path == Path("standards/core.md")
        assert stale.last_modified == now
        assert stale.age_days == 95


# ---------------------------------------------------------------------------
# MaintenanceReport
# ---------------------------------------------------------------------------


class TestMaintenanceReport:
    """Tests for MaintenanceReport health_score and properties."""

    def test_health_score_zero_governance_files(self) -> None:
        """When total_governance_files is 0, health_score is 0.0."""
        report = MaintenanceReport(
            generated_at=datetime.now(tz=UTC),
            total_governance_files=0,
        )
        assert report.health_score == 0.0

    def test_health_score_no_stale_files(self) -> None:
        """When no files are stale, health_score is 1.0."""
        report = MaintenanceReport(
            generated_at=datetime.now(tz=UTC),
            total_governance_files=10,
            stale_files=[],
        )
        assert report.health_score == 1.0

    def test_health_score_half_stale(self) -> None:
        """When half files are stale, health_score is 0.5."""
        now = datetime.now(tz=UTC)
        stale_files = [
            StaleFile(path=Path(f"file{i}.md"), last_modified=now, age_days=100) for i in range(5)
        ]
        report = MaintenanceReport(
            generated_at=now,
            total_governance_files=10,
            stale_files=stale_files,
        )
        assert report.health_score == pytest.approx(0.5)

    def test_health_score_all_stale(self) -> None:
        """When all files are stale, health_score is 0.0."""
        now = datetime.now(tz=UTC)
        stale_files = [
            StaleFile(path=Path(f"file{i}.md"), last_modified=now, age_days=100) for i in range(10)
        ]
        report = MaintenanceReport(
            generated_at=now,
            total_governance_files=10,
            stale_files=stale_files,
        )
        assert report.health_score == pytest.approx(0.0)

    def test_empty_defaults(self) -> None:
        """Default values for lists and counters."""
        report = MaintenanceReport(generated_at=datetime.now(tz=UTC))
        assert report.stale_files == []
        assert report.total_governance_files == 0
        assert report.total_state_files == 0
        assert report.recent_framework_events == 0
        assert report.install_manifest_version == ""
        assert report.warnings == []
        assert report.risk_active == 0
        assert report.risk_expiring == 0
        assert report.risk_expired == 0

    def test_warnings_list(self) -> None:
        """Warnings can be appended and read back."""
        report = MaintenanceReport(
            generated_at=datetime.now(tz=UTC),
            warnings=["Framework not installed", "Stale decision-store"],
        )
        assert len(report.warnings) == 2
        assert "Framework not installed" in report.warnings
        assert "Stale decision-store" in report.warnings

    def test_task_scorecard_is_serialized_and_rendered(self) -> None:
        report = MaintenanceReport(
            generated_at=datetime(2025, 1, 1, tzinfo=UTC),
            task_scorecard=TaskScorecard(
                total_tasks=3,
                resolved_tasks=1,
                open_tasks=2,
                retry_tasks=2,
                rework_tasks=1,
                verification_tax_events=1,
                drift_events=1,
            ),
        )

        data = report.to_dict()
        markdown = report.to_markdown()

        assert data["task_scorecard"] == {
            "total_tasks": 3,
            "resolved_tasks": 1,
            "open_tasks": 2,
            "retry_tasks": 2,
            "rework_tasks": 1,
            "verification_tax_events": 1,
            "drift_events": 1,
            "resolution_score": pytest.approx(1 / 3, rel=1e-3),
        }
        assert "## Task Scorecard" in markdown
        assert "Retrying tasks: 2" in markdown
        assert "Verification tax events: 1" in markdown


@pytest.mark.skip(reason="Spec-123 removed task-ledger surface from work_plane")
def test_build_task_scorecard_derives_counts_from_task_ledger_and_framework_events(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / ".ai-engineering" / "specs" / "task-ledger.json"
    write_json_model(
        ledger_path,
        TaskLedger(
            tasks=[
                TaskLedgerTask(
                    id="HX-05-T-A",
                    title="Resolved task",
                    status=TaskLifecycleState.DONE,
                    ownerRole="Build",
                    writeScope=["src/**"],
                ),
                TaskLedgerTask(
                    id="HX-05-T-B",
                    title="Retrying task",
                    status=TaskLifecycleState.IN_PROGRESS,
                    ownerRole="Build",
                    writeScope=["src/**"],
                ),
                TaskLedgerTask(
                    id="HX-05-T-C",
                    title="Reworked task",
                    status=TaskLifecycleState.REVIEW,
                    ownerRole="Build",
                    writeScope=["src/**"],
                ),
            ]
        ),
    )
    events_path = tmp_path / ".ai-engineering" / "state" / "framework-events.ndjson"

    def _append_event(
        *,
        correlation_id: str,
        kind: str,
        detail: dict[str, object],
        component: str = "state.task-ledger",
        outcome: str = "success",
    ) -> None:
        append_ndjson(
            events_path,
            FrameworkEvent.model_validate(
                {
                    "schemaVersion": "1.0",
                    "timestamp": "2026-05-01T12:00:00Z",
                    "project": "demo-project",
                    "engine": "ai_engineering",
                    "kind": kind,
                    "outcome": outcome,
                    "component": component,
                    "correlationId": correlation_id,
                    "detail": detail,
                }
            ),
        )

    _append_event(
        correlation_id="task-a-1",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-A",
            "lifecycle_phase": "planned",
            "artifact_refs": [],
        },
    )
    _append_event(
        correlation_id="task-a-2",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-A",
            "lifecycle_phase": "in-progress",
            "artifact_refs": ["handoffs/a.md"],
        },
    )
    _append_event(
        correlation_id="task-a-3",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-A",
            "lifecycle_phase": "verify",
            "artifact_refs": ["evidence/a.md"],
        },
    )
    _append_event(
        correlation_id="task-a-4",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-A",
            "lifecycle_phase": "done",
            "artifact_refs": ["evidence/a.md"],
        },
    )
    _append_event(
        correlation_id="task-b-1",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-B",
            "lifecycle_phase": "planned",
            "artifact_refs": [],
        },
    )
    _append_event(
        correlation_id="task-b-2",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-B",
            "lifecycle_phase": "in-progress",
            "artifact_refs": ["handoffs/b.md"],
        },
    )
    _append_event(
        correlation_id="task-b-3",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-B",
            "lifecycle_phase": "verify",
            "artifact_refs": ["evidence/b.md"],
        },
    )
    _append_event(
        correlation_id="task-b-4",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-B",
            "lifecycle_phase": "in-progress",
            "artifact_refs": ["evidence/b.md"],
        },
    )
    _append_event(
        correlation_id="task-b-5",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-B",
            "lifecycle_phase": "in-progress",
            "artifact_refs": ["evidence/b.md", "evidence/b-green.md"],
        },
    )
    _append_event(
        correlation_id="task-c-1",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-C",
            "lifecycle_phase": "planned",
            "artifact_refs": [],
        },
    )
    _append_event(
        correlation_id="task-c-2",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-C",
            "lifecycle_phase": "in-progress",
            "artifact_refs": ["handoffs/c.md"],
        },
    )
    _append_event(
        correlation_id="task-c-3",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-C",
            "lifecycle_phase": "done",
            "artifact_refs": ["evidence/c.md"],
        },
    )
    _append_event(
        correlation_id="task-c-4",
        kind="task_trace",
        detail={
            "task_id": "HX-05-T-C",
            "lifecycle_phase": "in-progress",
            "artifact_refs": ["evidence/c.md", "evidence/c-rework.md"],
        },
    )
    _append_event(
        correlation_id="drift-1",
        kind="control_outcome",
        component="guard",
        outcome="failure",
        detail={"category": "governance", "control": "guard-drift", "drifted": 2},
    )

    scorecard = build_task_scorecard(tmp_path)

    assert scorecard.total_tasks == 3
    assert scorecard.resolved_tasks == 1
    assert scorecard.open_tasks == 2
    assert scorecard.retry_tasks == 2
    assert scorecard.rework_tasks == 1
    assert scorecard.verification_tax_events == 1
    assert scorecard.drift_events == 1
    assert scorecard.resolution_score == pytest.approx(1 / 3, rel=1e-3)


def test_build_task_scorecard_reads_under_framework_events_lock(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[Path, str]] = []

    @contextmanager
    def _lock_spy(project_root: Path, artifact_name: str):
        calls.append((project_root, artifact_name))
        yield project_root / ".ai-engineering" / "state" / "locks" / f"{artifact_name}.lock"

    monkeypatch.setattr("ai_engineering.maintenance.report.artifact_lock", _lock_spy)

    ledger_path = tmp_path / ".ai-engineering" / "specs" / "task-ledger.json"
    write_json_model(
        ledger_path,
        TaskLedger(
            tasks=[
                TaskLedgerTask(
                    id="HX-05-T-4.2",
                    title="Read scorecard snapshot",
                    status=TaskLifecycleState.DONE,
                    ownerRole="Build",
                    writeScope=["src/**"],
                )
            ]
        ),
    )

    build_task_scorecard(tmp_path)

    assert calls == [(tmp_path, "framework-events")]
