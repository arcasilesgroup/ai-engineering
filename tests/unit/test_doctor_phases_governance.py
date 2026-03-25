"""Unit tests for doctor/phases/governance.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.doctor.phases import governance

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a project directory with all governance artifacts present."""
    ai_eng = tmp_path / ".ai-engineering"
    ai_eng.mkdir()
    (ai_eng / "contexts").mkdir()
    (ai_eng / "state").mkdir()
    (ai_eng / "scripts" / "hooks").mkdir(parents=True)
    (ai_eng / "manifest.yml").write_text(
        "schema_version: '2.0'\nname: test\n",
        encoding="utf-8",
    )
    (ai_eng / "README.md").write_text("# AI Engineering\n", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# check() -- governance-dirs
# ---------------------------------------------------------------------------


class TestGovernanceDirs:
    def test_ok_when_all_present(self, project: Path):
        ctx = DoctorContext(target=project)
        results = governance.check(ctx)
        dirs_check = next(r for r in results if r.name == "governance-dirs")
        assert dirs_check.status == CheckStatus.OK

    def test_fail_when_ai_engineering_missing(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        results = governance.check(ctx)
        dirs_check = next(r for r in results if r.name == "governance-dirs")
        assert dirs_check.status == CheckStatus.FAIL
        assert ".ai-engineering" in dirs_check.message

    def test_fail_when_contexts_missing(self, tmp_path: Path):
        (tmp_path / ".ai-engineering").mkdir()
        (tmp_path / ".ai-engineering" / "state").mkdir()
        ctx = DoctorContext(target=tmp_path)
        results = governance.check(ctx)
        dirs_check = next(r for r in results if r.name == "governance-dirs")
        assert dirs_check.status == CheckStatus.FAIL
        assert "contexts" in dirs_check.message

    def test_fail_when_state_missing(self, tmp_path: Path):
        (tmp_path / ".ai-engineering").mkdir()
        (tmp_path / ".ai-engineering" / "contexts").mkdir()
        ctx = DoctorContext(target=tmp_path)
        results = governance.check(ctx)
        dirs_check = next(r for r in results if r.name == "governance-dirs")
        assert dirs_check.status == CheckStatus.FAIL
        assert "state" in dirs_check.message

    def test_fixable_flag_set(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        results = governance.check(ctx)
        dirs_check = next(r for r in results if r.name == "governance-dirs")
        assert dirs_check.fixable is True


# ---------------------------------------------------------------------------
# check() -- manifest-valid
# ---------------------------------------------------------------------------


class TestManifestValid:
    def test_ok_when_valid(self, project: Path):
        ctx = DoctorContext(target=project)
        results = governance.check(ctx)
        manifest_check = next(r for r in results if r.name == "manifest-valid")
        assert manifest_check.status == CheckStatus.OK

    def test_fail_when_missing(self, tmp_path: Path):
        (tmp_path / ".ai-engineering").mkdir(parents=True)
        ctx = DoctorContext(target=tmp_path)
        results = governance.check(ctx)
        manifest_check = next(r for r in results if r.name == "manifest-valid")
        assert manifest_check.status == CheckStatus.FAIL
        assert "not found" in manifest_check.message

    def test_ok_with_empty_yaml(self, tmp_path: Path):
        """Empty YAML produces defaults, which is valid."""
        ai_eng = tmp_path / ".ai-engineering"
        ai_eng.mkdir(parents=True)
        (ai_eng / "manifest.yml").write_text("", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path)
        results = governance.check(ctx)
        manifest_check = next(r for r in results if r.name == "manifest-valid")
        # load_manifest_config returns defaults for empty files
        assert manifest_check.status == CheckStatus.OK

    def test_fail_when_loader_raises(self, tmp_path: Path):
        ai_eng = tmp_path / ".ai-engineering"
        ai_eng.mkdir(parents=True)
        (ai_eng / "manifest.yml").write_text("valid: yaml\n", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path)
        with patch(
            "ai_engineering.doctor.phases.governance.load_manifest_config",
            side_effect=RuntimeError("boom"),
        ):
            results = governance.check(ctx)
        manifest_check = next(r for r in results if r.name == "manifest-valid")
        assert manifest_check.status == CheckStatus.FAIL
        assert "boom" in manifest_check.message


# ---------------------------------------------------------------------------
# check() -- governance-templates
# ---------------------------------------------------------------------------


class TestGovernanceTemplates:
    def test_ok_when_all_present(self, project: Path):
        ctx = DoctorContext(target=project)
        results = governance.check(ctx)
        tmpl_check = next(r for r in results if r.name == "governance-templates")
        assert tmpl_check.status == CheckStatus.OK

    def test_warn_when_readme_missing(self, project: Path):
        (project / ".ai-engineering" / "README.md").unlink()
        ctx = DoctorContext(target=project)
        results = governance.check(ctx)
        tmpl_check = next(r for r in results if r.name == "governance-templates")
        assert tmpl_check.status == CheckStatus.WARN
        assert "README.md" in tmpl_check.message

    def test_warn_when_hooks_dir_missing(self, tmp_path: Path):
        ai_eng = tmp_path / ".ai-engineering"
        ai_eng.mkdir()
        (ai_eng / "README.md").write_text("# AI Engineering\n", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path)
        results = governance.check(ctx)
        tmpl_check = next(r for r in results if r.name == "governance-templates")
        assert tmpl_check.status == CheckStatus.WARN
        assert "hooks" in tmpl_check.message

    def test_fixable_flag_set_on_warn(self, tmp_path: Path):
        ai_eng = tmp_path / ".ai-engineering"
        ai_eng.mkdir()
        ctx = DoctorContext(target=tmp_path)
        results = governance.check(ctx)
        tmpl_check = next(r for r in results if r.name == "governance-templates")
        assert tmpl_check.fixable is True


# ---------------------------------------------------------------------------
# fix() -- governance-dirs
# ---------------------------------------------------------------------------


class TestFixGovernanceDirs:
    def test_creates_missing_dirs(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="governance-dirs",
                status=CheckStatus.FAIL,
                message="Missing directories",
                fixable=True,
            )
        ]
        result = governance.fix(ctx, failed)
        assert len(result) == 1
        assert result[0].name == "governance-dirs"
        assert result[0].status == CheckStatus.FIXED
        assert (tmp_path / ".ai-engineering").is_dir()
        assert (tmp_path / ".ai-engineering" / "contexts").is_dir()
        assert (tmp_path / ".ai-engineering" / "state").is_dir()

    def test_dry_run_does_not_create(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="governance-dirs",
                status=CheckStatus.FAIL,
                message="Missing directories",
                fixable=True,
            )
        ]
        result = governance.fix(ctx, failed, dry_run=True)
        assert result[0].status == CheckStatus.FAIL
        assert "Would create" in result[0].message
        assert not (tmp_path / ".ai-engineering").exists()

    def test_already_fixed(self, project: Path):
        ctx = DoctorContext(target=project)
        failed = [
            CheckResult(
                name="governance-dirs",
                status=CheckStatus.FAIL,
                message="Missing directories",
                fixable=True,
            )
        ]
        result = governance.fix(ctx, failed)
        assert result[0].status == CheckStatus.OK


# ---------------------------------------------------------------------------
# fix() -- governance-templates
# ---------------------------------------------------------------------------


class TestFixGovernanceTemplates:
    def test_creates_missing_hooks_dir(self, tmp_path: Path):
        ai_eng = tmp_path / ".ai-engineering"
        ai_eng.mkdir()
        (ai_eng / "README.md").write_text("# AI\n", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="governance-templates",
                status=CheckStatus.WARN,
                message="Missing",
                fixable=True,
            )
        ]
        governance.fix(ctx, failed)
        assert (tmp_path / ".ai-engineering" / "scripts" / "hooks").is_dir()

    def test_dry_run_does_not_create(self, tmp_path: Path):
        (tmp_path / ".ai-engineering").mkdir()
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="governance-templates",
                status=CheckStatus.WARN,
                message="Missing",
                fixable=True,
            )
        ]
        result = governance.fix(ctx, failed, dry_run=True)
        assert result[0].status == CheckStatus.WARN
        assert "Would create" in result[0].message

    def test_only_files_missing_returns_warn(self, tmp_path: Path):
        """When dirs exist but files are missing, fix returns WARN (files need install)."""
        ai_eng = tmp_path / ".ai-engineering"
        ai_eng.mkdir()
        (ai_eng / "scripts" / "hooks").mkdir(parents=True)
        # README.md is still missing
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="governance-templates",
                status=CheckStatus.WARN,
                message="Missing",
                fixable=True,
            )
        ]
        result = governance.fix(ctx, failed)
        assert result[0].status == CheckStatus.WARN
        assert "requires install" in result[0].message


# ---------------------------------------------------------------------------
# fix() -- manifest-valid (non-fixable)
# ---------------------------------------------------------------------------


class TestFixManifestValid:
    def test_manifest_valid_not_fixed(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="manifest-valid",
                status=CheckStatus.FAIL,
                message="not found",
            )
        ]
        result = governance.fix(ctx, failed)
        assert len(result) == 1
        assert result[0].status == CheckStatus.FAIL
        assert result[0].name == "manifest-valid"


# ---------------------------------------------------------------------------
# check() returns exactly 3 results
# ---------------------------------------------------------------------------


class TestCheckReturnsAllResults:
    def test_check_returns_three_results(self, project: Path):
        ctx = DoctorContext(target=project)
        results = governance.check(ctx)
        assert len(results) == 3
        names = {r.name for r in results}
        assert names == {"governance-dirs", "manifest-valid", "governance-templates"}
