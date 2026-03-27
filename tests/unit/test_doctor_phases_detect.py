"""Unit tests for doctor/phases/detect.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.config.manifest import ManifestConfig, ProvidersConfig
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.doctor.phases import detect
from ai_engineering.state.models import InstallState

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal project directory with valid install-state.json."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    state = InstallState(
        schema_version="2.0",
        vcs_provider="github",
        operational_readiness={"status": "ready"},
    )
    (state_dir / "install-state.json").write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture()
def valid_state() -> InstallState:
    """A valid InstallState for context injection."""
    return InstallState(
        schema_version="2.0",
        vcs_provider="github",
        operational_readiness={"status": "ready"},
    )


# ---------------------------------------------------------------------------
# check() -- install-state-exists
# ---------------------------------------------------------------------------


class TestInstallStateExists:
    def test_ok_when_present_and_valid(self, project: Path):
        ctx = DoctorContext(target=project)
        results = detect.check(ctx)
        exists_check = next(r for r in results if r.name == "install-state-exists")
        assert exists_check.status == CheckStatus.OK

    def test_fail_when_missing(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        results = detect.check(ctx)
        exists_check = next(r for r in results if r.name == "install-state-exists")
        assert exists_check.status == CheckStatus.FAIL
        assert "not found" in exists_check.message

    def test_fail_when_invalid_json(self, tmp_path: Path):
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        (state_dir / "install-state.json").write_text("not json", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path)
        results = detect.check(ctx)
        exists_check = next(r for r in results if r.name == "install-state-exists")
        assert exists_check.status == CheckStatus.FAIL
        assert "not parseable" in exists_check.message


# ---------------------------------------------------------------------------
# check() -- install-state-coherent
# ---------------------------------------------------------------------------


class TestInstallStateCoherent:
    def test_ok_when_coherent(self, project: Path, valid_state: InstallState):
        ctx = DoctorContext(target=project, install_state=valid_state)
        results = detect.check(ctx)
        coherent_check = next(r for r in results if r.name == "install-state-coherent")
        assert coherent_check.status == CheckStatus.OK

    def test_fail_when_no_install_state(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path, install_state=None)
        results = detect.check(ctx)
        coherent_check = next(r for r in results if r.name == "install-state-coherent")
        assert coherent_check.status == CheckStatus.FAIL
        assert "No install state" in coherent_check.message

    def test_fail_on_wrong_schema_version(self, project: Path):
        state = InstallState(
            schema_version="1.0",
            operational_readiness={"status": "ready"},
        )
        ctx = DoctorContext(target=project, install_state=state)
        results = detect.check(ctx)
        coherent_check = next(r for r in results if r.name == "install-state-coherent")
        assert coherent_check.status == CheckStatus.FAIL
        assert "schema_version" in coherent_check.message

    def test_fail_on_pending_readiness(self, project: Path):
        state = InstallState(
            schema_version="2.0",
            operational_readiness={"status": "pending"},
        )
        ctx = DoctorContext(target=project, install_state=state)
        results = detect.check(ctx)
        coherent_check = next(r for r in results if r.name == "install-state-coherent")
        assert coherent_check.status == CheckStatus.FAIL
        assert "pending" in coherent_check.message

    def test_fail_both_problems(self, project: Path):
        state = InstallState(
            schema_version="1.0",
            operational_readiness={"status": "pending"},
        )
        ctx = DoctorContext(target=project, install_state=state)
        results = detect.check(ctx)
        coherent_check = next(r for r in results if r.name == "install-state-coherent")
        assert coherent_check.status == CheckStatus.FAIL
        assert "schema_version" in coherent_check.message
        assert "pending" in coherent_check.message


# ---------------------------------------------------------------------------
# check() -- detection-current
# ---------------------------------------------------------------------------


class TestDetectionCurrent:
    def test_ok_when_vcs_matches_github(self, project: Path, valid_state: InstallState):
        ctx = DoctorContext(target=project, install_state=valid_state)
        with patch("ai_engineering.doctor.phases.detect._detect_vcs_from_remote") as mock:
            mock.return_value = "github"
            results = detect.check(ctx)
        current_check = next(r for r in results if r.name == "detection-current")
        assert current_check.status == CheckStatus.OK

    def test_warn_on_mismatch(self, project: Path, valid_state: InstallState):
        ctx = DoctorContext(target=project, install_state=valid_state)
        with patch("ai_engineering.doctor.phases.detect._detect_vcs_from_remote") as mock:
            mock.return_value = "azure_devops"
            results = detect.check(ctx)
        current_check = next(r for r in results if r.name == "detection-current")
        assert current_check.status == CheckStatus.WARN
        assert "mismatch" in current_check.message.lower()

    def test_warn_when_no_remote(self, project: Path, valid_state: InstallState):
        ctx = DoctorContext(target=project, install_state=valid_state)
        with patch("ai_engineering.doctor.phases.detect._detect_vcs_from_remote") as mock:
            mock.return_value = None
            results = detect.check(ctx)
        current_check = next(r for r in results if r.name == "detection-current")
        assert current_check.status == CheckStatus.WARN

    def test_warn_when_no_install_state(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path, install_state=None)
        results = detect.check(ctx)
        current_check = next(r for r in results if r.name == "detection-current")
        assert current_check.status == CheckStatus.WARN


# ---------------------------------------------------------------------------
# _detect_vcs_from_remote() unit tests
# ---------------------------------------------------------------------------


class TestDetectVcsFromRemote:
    def test_github_url(self, tmp_path: Path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "https://github.com/org/repo.git\n"
            result = detect._detect_vcs_from_remote(tmp_path)
        assert result == "github"

    def test_azure_devops_url(self, tmp_path: Path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "https://dev.azure.com/org/project/_git/repo\n"
            result = detect._detect_vcs_from_remote(tmp_path)
        assert result == "azure_devops"

    def test_no_remote_returns_none(self, tmp_path: Path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            result = detect._detect_vcs_from_remote(tmp_path)
        assert result is None

    def test_timeout_returns_none(self, tmp_path: Path):
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 5)):
            result = detect._detect_vcs_from_remote(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# fix() -- returns failed unchanged
# ---------------------------------------------------------------------------


class TestDetectFix:
    def test_returns_failed_unchanged(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="install-state-exists",
                status=CheckStatus.FAIL,
                message="missing",
            )
        ]
        result = detect.fix(ctx, failed)
        assert len(result) == 1
        assert result[0].name == "install-state-exists"
        assert result[0].status == CheckStatus.FAIL

    def test_returns_new_list_not_same_reference(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="install-state-exists",
                status=CheckStatus.FAIL,
                message="missing",
            )
        ]
        result = detect.fix(ctx, failed)
        assert result is not failed


# ---------------------------------------------------------------------------
# check() -- stack-drift
# ---------------------------------------------------------------------------


class TestStackDrift:
    def test_ok_when_stacks_match(self, project: Path, valid_state: InstallState):
        manifest = ManifestConfig(providers=ProvidersConfig(stacks=["python"]))
        ctx = DoctorContext(target=project, install_state=valid_state, manifest_config=manifest)
        with (
            patch(
                "ai_engineering.doctor.phases.detect._detect_vcs_from_remote",
                return_value="github",
            ),
            patch(
                "ai_engineering.doctor.phases.detect.detect_stacks",
                return_value=["python"],
            ),
        ):
            results = detect.check(ctx)
        drift = next(r for r in results if r.name == "stack-drift")
        assert drift.status == CheckStatus.OK

    def test_warn_extra_in_manifest(self, project: Path, valid_state: InstallState):
        manifest = ManifestConfig(providers=ProvidersConfig(stacks=["python", "rust"]))
        ctx = DoctorContext(target=project, install_state=valid_state, manifest_config=manifest)
        with (
            patch(
                "ai_engineering.doctor.phases.detect._detect_vcs_from_remote",
                return_value="github",
            ),
            patch(
                "ai_engineering.doctor.phases.detect.detect_stacks",
                return_value=["python"],
            ),
        ):
            results = detect.check(ctx)
        drift = next(r for r in results if r.name == "stack-drift")
        assert drift.status == CheckStatus.WARN
        assert "in manifest but not detected" in drift.message
        assert "rust" in drift.message

    def test_warn_missing_from_manifest(self, project: Path, valid_state: InstallState):
        manifest = ManifestConfig(providers=ProvidersConfig(stacks=["python"]))
        ctx = DoctorContext(target=project, install_state=valid_state, manifest_config=manifest)
        with (
            patch(
                "ai_engineering.doctor.phases.detect._detect_vcs_from_remote",
                return_value="github",
            ),
            patch(
                "ai_engineering.doctor.phases.detect.detect_stacks",
                return_value=["python", "typescript"],
            ),
        ):
            results = detect.check(ctx)
        drift = next(r for r in results if r.name == "stack-drift")
        assert drift.status == CheckStatus.WARN
        assert "detected but not in manifest" in drift.message
        assert "typescript" in drift.message

    def test_warn_empty_manifest_stacks(self, project: Path, valid_state: InstallState):
        manifest = ManifestConfig(providers=ProvidersConfig(stacks=[]))
        ctx = DoctorContext(target=project, install_state=valid_state, manifest_config=manifest)
        with (
            patch(
                "ai_engineering.doctor.phases.detect._detect_vcs_from_remote",
                return_value="github",
            ),
        ):
            results = detect.check(ctx)
        drift = next(r for r in results if r.name == "stack-drift")
        assert drift.status == CheckStatus.WARN
        assert "empty" in drift.message

    def test_warn_no_manifest_config(self, project: Path, valid_state: InstallState):
        ctx = DoctorContext(target=project, install_state=valid_state, manifest_config=None)
        with patch(
            "ai_engineering.doctor.phases.detect._detect_vcs_from_remote",
            return_value="github",
        ):
            results = detect.check(ctx)
        drift = next(r for r in results if r.name == "stack-drift")
        assert drift.status == CheckStatus.WARN
        assert "No manifest config" in drift.message


# ---------------------------------------------------------------------------
# check() returns exactly 4 results
# ---------------------------------------------------------------------------


class TestCheckReturnsAllResults:
    def test_check_returns_four_results(self, project: Path, valid_state: InstallState):
        manifest = ManifestConfig(providers=ProvidersConfig(stacks=["python"]))
        ctx = DoctorContext(target=project, install_state=valid_state, manifest_config=manifest)
        with (
            patch(
                "ai_engineering.doctor.phases.detect._detect_vcs_from_remote",
                return_value="github",
            ),
            patch(
                "ai_engineering.doctor.phases.detect.detect_stacks",
                return_value=["python"],
            ),
        ):
            results = detect.check(ctx)
        assert len(results) == 4
        names = {r.name for r in results}
        assert names == {
            "install-state-exists",
            "install-state-coherent",
            "detection-current",
            "stack-drift",
        }
