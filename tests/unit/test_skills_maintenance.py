"""Unit tests for skills/service.py and maintenance/report.py.

Covers:
- SkillStatus eligibility logic.
- list_local_skill_status() with mocked filesystem and dependencies.
- StaleFile creation and fields.
- MaintenanceReport health_score calculation and warnings.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_engineering.maintenance.report import (
    MaintenanceReport,
    StaleFile,
)
from ai_engineering.skills.service import (
    SkillStatus,
    list_local_skill_status,
)

pytestmark = pytest.mark.unit


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
