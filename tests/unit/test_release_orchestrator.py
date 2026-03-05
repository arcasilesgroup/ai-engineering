"""Unit tests for release orchestrator behavior and helper branches."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.release.orchestrator import (
    PhaseResult,
    ReleaseConfig,
    ReleaseState,
    SubprocessRunner,
    SystemClock,
    _create_release_pr,
    _create_tag,
    _default_branch,
    _detect_state,
    _find_existing_pr_url,
    _monitor_pipeline,
    _parse_runs,
    _prepare_branch,
    _repo_slug,
    _update_manifest,
    _validate,
    _version_from_git_ref,
    _wait_for_merge,
    execute_release,
)
from ai_engineering.state.defaults import default_install_manifest
from ai_engineering.state.io import write_json_model
from ai_engineering.vcs.protocol import (
    CreateTagContext,
    PipelineStatusContext,
    VcsContext,
    VcsResult,
)

pytestmark = pytest.mark.unit


class _FakeProvider:
    def __init__(self) -> None:
        self.tag_success = True
        self.pipeline_success = True
        self.pipeline_output = "[]"

    def create_pr(self, ctx: VcsContext) -> VcsResult:
        del ctx
        return VcsResult(success=True, url="https://example/pr/1")

    def find_open_pr(self, ctx: VcsContext) -> VcsResult:
        del ctx
        return VcsResult(success=True, output="")

    def update_pr(self, ctx: VcsContext, *, pr_number: str, title: str = "") -> VcsResult:
        del ctx, pr_number, title
        return VcsResult(success=True)

    def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
        del ctx
        return VcsResult(success=True)

    def is_available(self) -> bool:
        return True

    def provider_name(self) -> str:
        return "github"

    def check_auth(self, ctx: VcsContext) -> VcsResult:
        del ctx
        return VcsResult(success=True)

    def apply_branch_policy(
        self, ctx: VcsContext, *, branch: str, required_checks: list[str]
    ) -> VcsResult:
        del ctx, branch, required_checks
        return VcsResult(success=True)

    def post_pr_review(self, ctx: VcsContext, *, body: str) -> VcsResult:
        del ctx, body
        return VcsResult(success=True)

    def create_tag(self, ctx: CreateTagContext) -> VcsResult:
        del ctx
        return VcsResult(success=self.tag_success, output="ok" if self.tag_success else "bad")

    def get_pipeline_status(self, ctx: PipelineStatusContext) -> VcsResult:
        del ctx
        return VcsResult(success=self.pipeline_success, output=self.pipeline_output)


class _FixedClock:
    def utcnow(self) -> datetime:
        return datetime(2026, 3, 2, tzinfo=UTC)


class _Runner:
    def __init__(self, *, ok: bool = True, out: str = "") -> None:
        self.ok = ok
        self.out = out

    def run(self, cmd: list[str], cwd: Path, timeout: int = 60) -> tuple[bool, str]:
        del cmd, cwd, timeout
        return self.ok, self.out


def test_execute_release_returns_validation_errors(tmp_path: Path) -> None:
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    with patch("ai_engineering.release.orchestrator._validate", return_value=["boom"]):
        result = execute_release(config, provider)

    assert result.success is False
    assert result.errors == ["boom"]
    assert result.phases[0].phase == "validate"
    assert result.phases[0].success is False


def test_execute_release_dry_run_outputs_plan(tmp_path: Path) -> None:
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, dry_run=True)
    provider = _FakeProvider()

    state = ReleaseState(
        release_branch="release/v0.2.0",
        local_branch_exists=False,
        remote_branch_exists=False,
        tag_exists=False,
        current_version="0.1.0",
    )
    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    assert result.success is True
    assert any(phase.phase == "plan" and phase.skipped for phase in result.phases)


def test_execute_release_noops_when_tag_exists(tmp_path: Path) -> None:
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    state = ReleaseState(
        release_branch="release/v0.2.0",
        local_branch_exists=False,
        remote_branch_exists=False,
        tag_exists=True,
        current_version="0.2.0",
    )
    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch("ai_engineering.release.orchestrator._repo_slug", return_value="acme/repo"),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    assert result.success is True
    assert result.release_url.endswith("/releases/tag/v0.2.0")
    assert any(phase.phase == "tag" and phase.skipped for phase in result.phases)


def test_validate_invalid_semver_short_circuit(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="bad", project_root=tmp_path)
    errors = _validate(cfg, _FakeProvider())
    assert errors == ["Invalid semver version: bad"]


def test_validate_returns_empty_when_tag_exists(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")):
        errors = _validate(cfg, _FakeProvider())
    assert errors == []


def test_detect_state_reads_refs_and_current_version(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    seq = [(True, ""), (False, ""), (True, "")]
    with (
        patch("ai_engineering.release.orchestrator.run_git", side_effect=seq),
        patch("ai_engineering.release.orchestrator.detect_current_version", return_value="0.1.0"),
    ):
        state = _detect_state(cfg, _FakeProvider())
    assert state.local_branch_exists is True
    assert state.remote_branch_exists is False
    assert state.tag_exists is True
    assert state.current_version == "0.1.0"


def test_prepare_branch_returns_skip_when_branch_exists(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")):
        phase = _prepare_branch(cfg, _FixedClock())
    assert phase.skipped is True


def test_prepare_branch_handles_checkout_failure(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    seq = [(False, ""), (False, "oops")]
    with patch("ai_engineering.release.orchestrator.run_git", side_effect=seq):
        phase = _prepare_branch(cfg, _FixedClock())
    assert phase.success is False
    assert "Failed to create branch" in phase.output


def test_prepare_branch_handles_bump_failure(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    seq = [(False, ""), (True, "")]
    with (
        patch("ai_engineering.release.orchestrator.run_git", side_effect=seq),
        patch(
            "ai_engineering.release.orchestrator.bump_python_version", side_effect=ValueError("x")
        ),
    ):
        phase = _prepare_branch(cfg, _FixedClock())
    assert phase.success is False
    assert phase.output == "x"


def test_prepare_branch_success_path(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    bump = type("Bump", (), {})()
    bump.old_version = "0.1.0"
    bump.new_version = "0.2.0"
    bump.files_modified = [
        tmp_path / "pyproject.toml",
        tmp_path / "src" / "ai_engineering" / "__version__.py",
    ]

    seq = [(False, ""), (True, ""), (True, ""), (True, "")]
    with (
        patch("ai_engineering.release.orchestrator.run_git", side_effect=seq),
        patch("ai_engineering.release.orchestrator.bump_python_version", return_value=bump),
        patch("ai_engineering.release.orchestrator.promote_unreleased", return_value=True),
    ):
        phase = _prepare_branch(cfg, _FixedClock())
    assert phase.success is True
    assert "pyproject.toml" in phase.output


def test_create_release_pr_handles_existing_pr_url(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    class _P(_FakeProvider):
        def create_pr(self, ctx: VcsContext) -> VcsResult:
            del ctx
            return VcsResult(success=False, output="already")

    with (
        patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")),
        patch(
            "ai_engineering.release.orchestrator._find_existing_pr_url",
            return_value="https://x/pr/1",
        ),
    ):
        phase = _create_release_pr(cfg, _P(), _Runner())
    assert phase.success is True
    assert phase.skipped is True


def test_create_release_pr_auto_complete_failure(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    class _P(_FakeProvider):
        def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
            del ctx
            return VcsResult(success=False, output="bad")

    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")):
        phase = _create_release_pr(cfg, _P(), _Runner())
    assert phase.success is False
    assert "Auto-complete failed" in phase.output


def test_wait_for_merge_github_success(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    runner = _Runner(ok=True, out='{"mergedAt":"now","url":"https://x/pr/1"}')
    with patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 1]):
        phase = _wait_for_merge(cfg, _FakeProvider(), 5, runner)
    assert phase.success is True


def test_wait_for_merge_non_github_success(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    class _P(_FakeProvider):
        def provider_name(self) -> str:
            return "azure_devops"

    seq = [(True, ""), (False, ""), (True, "")]
    with (
        patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 1]),
        patch("ai_engineering.release.orchestrator.run_git", side_effect=seq),
        patch("ai_engineering.release.orchestrator._version_from_git_ref", return_value="0.2.0"),
    ):
        phase = _wait_for_merge(cfg, _P(), 5, _Runner())
    assert phase.success is True


def test_create_tag_failure_and_success_paths(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    seq_fail_checkout = [(False, ""), (True, ""), (False, "no")]
    with patch("ai_engineering.release.orchestrator.run_git", side_effect=seq_fail_checkout):
        phase = _create_tag(cfg, provider)
    assert phase.success is False

    seq_success = [(False, ""), (True, ""), (True, ""), (True, ""), (True, "abc123\n")]
    with patch("ai_engineering.release.orchestrator.run_git", side_effect=seq_success):
        phase_ok = _create_tag(cfg, provider)
    assert phase_ok.success is True


def test_update_manifest_skips_when_missing(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    phase = _update_manifest(cfg, _FixedClock())
    assert phase.skipped is True


def test_update_manifest_updates_release_fields(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    manifest_path = tmp_path / ".ai-engineering" / "state" / "install-manifest.json"
    write_json_model(manifest_path, default_install_manifest())
    phase = _update_manifest(cfg, _FixedClock())
    assert phase.success is True


def test_monitor_pipeline_success_and_failure(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    with patch("ai_engineering.release.orchestrator.run_git", return_value=(False, "bad")):
        phase = _monitor_pipeline(cfg, provider, 1)
    assert phase.success is False

    provider.pipeline_output = (
        '[{"status":"completed","conclusion":"success","url":"https://x/run"}]'
    )
    with (
        patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "abc\n")),
        patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 1]),
    ):
        phase_ok = _monitor_pipeline(cfg, provider, 5)
    assert phase_ok.success is True


def test_parse_runs_handles_valid_and_embedded_json() -> None:
    assert _parse_runs("") == []
    assert _parse_runs("[]") == []
    assert len(_parse_runs('[{"a":1}]')) == 1
    assert len(_parse_runs('noise [{"a":1}] more')) == 1


def test_version_from_git_ref_and_repo_slug(tmp_path: Path) -> None:
    with patch(
        "ai_engineering.release.orchestrator.run_git",
        return_value=(True, '[project]\nversion = "0.9.0"\n'),
    ):
        assert _version_from_git_ref(tmp_path, "origin/main") == "0.9.0"

    with patch(
        "ai_engineering.release.orchestrator.run_git",
        return_value=(True, "git@github.com:acme/repo.git\n"),
    ):
        assert _repo_slug(tmp_path) == "acme/repo"


def test_find_existing_pr_url_and_default_branch(tmp_path: Path) -> None:
    runner = _Runner(ok=True, out='[{"url":"https://x/pr/2"}]')
    assert (
        _find_existing_pr_url(tmp_path, "release/v0.2.0", _FakeProvider(), runner)
        == "https://x/pr/2"
    )

    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")):
        assert _default_branch(tmp_path) == "main"
    with patch("ai_engineering.release.orchestrator.run_git", return_value=(False, "")):
        assert _default_branch(tmp_path) == "master"


def test_execute_release_wait_path_success(tmp_path: Path) -> None:
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=True)
    provider = _FakeProvider()
    state = ReleaseState(
        release_branch="release/v0.2.0",
        local_branch_exists=False,
        remote_branch_exists=False,
        tag_exists=False,
        current_version="0.1.0",
    )
    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult(
                "prepare", True, "pyproject.toml\nsrc/ai_engineering/__version__.py"
            ),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", True, "https://example/pr/1"),
        ),
        patch(
            "ai_engineering.release.orchestrator._wait_for_merge",
            return_value=PhaseResult("wait-for-merge", True, "https://example/pr/1"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_tag",
            return_value=PhaseResult("tag", True, "ok"),
        ),
        patch(
            "ai_engineering.release.orchestrator._update_manifest",
            return_value=PhaseResult("manifest", True, "ok"),
        ),
        patch(
            "ai_engineering.release.orchestrator._monitor_pipeline",
            return_value=PhaseResult("monitor", True, "https://example/release/v0.2.0"),
        ),
        patch("ai_engineering.release.orchestrator._log_audit_event"),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    assert result.success is True
    assert result.pr_url == "https://example/pr/1"
    assert result.release_url == "https://example/release/v0.2.0"


def test_validate_collects_branch_provider_and_changelog_errors(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

    class _P(_FakeProvider):
        def is_available(self) -> bool:
            return False

    with (
        patch(
            "ai_engineering.release.orchestrator.run_git", side_effect=[(False, ""), (False, "x")]
        ),
        patch("ai_engineering.release.orchestrator.current_branch", return_value="feature/x"),
        patch("ai_engineering.release.orchestrator.detect_current_version", return_value="0.1.0"),
        patch("ai_engineering.release.orchestrator.compare_versions", return_value=-1),
        patch(
            "ai_engineering.release.orchestrator.validate_changelog", return_value=["bad changelog"]
        ),
    ):
        errors = _validate(cfg, _P())

    assert any("main/master" in e for e in errors)
    assert any("Unable to check git status" in e for e in errors)
    assert any("VCS provider unavailable" in e for e in errors)
    assert "bad changelog" in errors


def test_prepare_branch_promote_add_commit_error_paths(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    bump = type("Bump", (), {})()
    bump.files_modified = [
        tmp_path / "pyproject.toml",
        tmp_path / "src" / "ai_engineering" / "__version__.py",
    ]

    with (
        patch("ai_engineering.release.orchestrator.run_git", side_effect=[(False, ""), (True, "")]),
        patch("ai_engineering.release.orchestrator.bump_python_version", return_value=bump),
        patch("ai_engineering.release.orchestrator.promote_unreleased", return_value=False),
    ):
        p1 = _prepare_branch(cfg, _FixedClock())
    assert p1.success is False

    with (
        patch(
            "ai_engineering.release.orchestrator.run_git",
            side_effect=[(False, ""), (True, ""), (False, "add-fail")],
        ),
        patch("ai_engineering.release.orchestrator.bump_python_version", return_value=bump),
        patch("ai_engineering.release.orchestrator.promote_unreleased", return_value=True),
    ):
        p2 = _prepare_branch(cfg, _FixedClock())
    assert "git add failed" in p2.output

    with (
        patch(
            "ai_engineering.release.orchestrator.run_git",
            side_effect=[(False, ""), (True, ""), (True, ""), (False, "commit-fail")],
        ),
        patch("ai_engineering.release.orchestrator.bump_python_version", return_value=bump),
        patch("ai_engineering.release.orchestrator.promote_unreleased", return_value=True),
    ):
        p3 = _prepare_branch(cfg, _FixedClock())
    assert "git commit failed" in p3.output


def test_create_release_pr_push_create_and_default_output(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    class _PFails(_FakeProvider):
        def create_pr(self, ctx: VcsContext) -> VcsResult:
            del ctx
            return VcsResult(success=False, output="boom")

    with patch("ai_engineering.release.orchestrator.run_git", return_value=(False, "push-fail")):
        p1 = _create_release_pr(cfg, _PFails(), _Runner())
    assert "git push failed" in p1.output

    with (
        patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")),
        patch("ai_engineering.release.orchestrator._find_existing_pr_url", return_value=""),
    ):
        p2 = _create_release_pr(cfg, _PFails(), _Runner())
    assert "PR creation failed" in p2.output

    class _PNoUrl(_FakeProvider):
        def create_pr(self, ctx: VcsContext) -> VcsResult:
            del ctx
            return VcsResult(success=True, url="")

    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")):
        p3 = _create_release_pr(cfg, _PNoUrl(), _Runner())
    assert p3.output == "PR created"


def test_wait_for_merge_github_timeout(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    with (
        patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 20]),
        patch("ai_engineering.release.orchestrator.time.sleep"),
    ):
        phase = _wait_for_merge(cfg, _FakeProvider(), 10, _Runner(ok=True, out="not-json"))
    assert phase.success is False


def test_create_tag_paths_for_exists_pull_sha_and_provider_errors(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")):
        exists_phase = _create_tag(cfg, provider)
    assert exists_phase.skipped is True

    with patch(
        "ai_engineering.release.orchestrator.run_git",
        side_effect=[(False, ""), (True, ""), (True, ""), (False, "pull")],
    ):
        pull_phase = _create_tag(cfg, provider)
    assert pull_phase.success is False

    with patch(
        "ai_engineering.release.orchestrator.run_git",
        side_effect=[(False, ""), (True, ""), (True, ""), (True, ""), (False, "sha")],
    ):
        sha_phase = _create_tag(cfg, provider)
    assert sha_phase.success is False

    class _PExists(_FakeProvider):
        def create_tag(self, ctx: CreateTagContext) -> VcsResult:
            del ctx
            return VcsResult(success=False, output="reference already exists")

    with patch(
        "ai_engineering.release.orchestrator.run_git",
        side_effect=[(False, ""), (True, ""), (True, ""), (True, ""), (True, "abc\n")],
    ):
        tag_exists = _create_tag(cfg, _PExists())
    assert tag_exists.skipped is True

    class _PFail(_FakeProvider):
        def create_tag(self, ctx: CreateTagContext) -> VcsResult:
            del ctx
            return VcsResult(success=False, output="boom")

    with patch(
        "ai_engineering.release.orchestrator.run_git",
        side_effect=[(False, ""), (True, ""), (True, ""), (True, ""), (True, "abc\n")],
    ):
        tag_fail = _create_tag(cfg, _PFail())
    assert tag_fail.success is False


def test_monitor_pipeline_timeout_and_completed_failure(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    provider.pipeline_output = "[]"
    with (
        patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "abc\n")),
        patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 20]),
        patch("ai_engineering.release.orchestrator.time.sleep"),
    ):
        timeout_phase = _monitor_pipeline(cfg, provider, 10)
    assert timeout_phase.success is False

    provider.pipeline_output = '[{"status":"completed","conclusion":"failure","url":"u"}]'
    with (
        patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "abc\n")),
        patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 1]),
    ):
        fail_phase = _monitor_pipeline(cfg, provider, 10)
    assert fail_phase.success is False


def test_parse_runs_and_lookup_helpers_extra_paths(tmp_path: Path) -> None:
    assert _parse_runs("not-json") == []
    assert _parse_runs("{}") == []

    with patch("ai_engineering.release.orchestrator.run_git", return_value=(False, "")):
        assert _version_from_git_ref(tmp_path, "origin/main") is None
        assert _repo_slug(tmp_path) == ""

    with patch(
        "ai_engineering.release.orchestrator.run_git",
        return_value=(True, "https://example.com/nope\n"),
    ):
        assert _repo_slug(tmp_path) == ""

    class _Az(_FakeProvider):
        def provider_name(self) -> str:
            return "azure_devops"

    assert _find_existing_pr_url(tmp_path, "release/v0.2.0", _Az(), _Runner()) == ""
    assert (
        _find_existing_pr_url(tmp_path, "release/v0.2.0", _FakeProvider(), _Runner(ok=False)) == ""
    )
    assert (
        _find_existing_pr_url(
            tmp_path,
            "release/v0.2.0",
            _FakeProvider(),
            _Runner(ok=True, out="not-json"),
        )
        == ""
    )
    assert (
        _find_existing_pr_url(
            tmp_path, "release/v0.2.0", _FakeProvider(), _Runner(ok=True, out="[]")
        )
        == ""
    )


def test_system_clock_returns_utc_timezone() -> None:
    now = SystemClock().utcnow()
    assert now.tzinfo is UTC


def test_subprocess_runner_success_not_found_and_timeout(tmp_path: Path) -> None:
    runner = SubprocessRunner()

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    with patch("subprocess.run", return_value=_Proc()):
        ok, out = runner.run(["echo", "x"], tmp_path)
    assert ok is True
    assert "ok" in out

    with patch("subprocess.run", side_effect=FileNotFoundError):
        ok2, out2 = runner.run(["missing"], tmp_path)
    assert ok2 is False
    assert "Command not found" in out2

    with patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd=["sleep", "1"], timeout=1),
    ):
        ok3, out3 = runner.run(["sleep", "1"], tmp_path)
    assert ok3 is False
    assert "Command timed out" in out3


def test_execute_release_phase_failures_cover_early_returns(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=True)
    provider = _FakeProvider()
    state = ReleaseState("release/v0.2.0", False, False, False, "0.1.0")

    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", False, "prep-fail"),
        ),
    ):
        r1 = execute_release(cfg, provider)
    assert r1.success is False

    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", True, "x"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", False, "pr-fail"),
        ),
    ):
        r2 = execute_release(cfg, provider)
    assert r2.success is False

    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", True, "x"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", True, "u"),
        ),
        patch(
            "ai_engineering.release.orchestrator._wait_for_merge",
            return_value=PhaseResult("wait-for-merge", False, "wait-fail"),
        ),
    ):
        r3 = execute_release(cfg, provider)
    assert r3.success is False


def test_execute_release_tag_manifest_and_monitor_failures(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=True)
    provider = _FakeProvider()
    state = ReleaseState("release/v0.2.0", False, False, False, "0.1.0")

    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", True, "x"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", True, "u"),
        ),
        patch(
            "ai_engineering.release.orchestrator._wait_for_merge",
            return_value=PhaseResult("wait-for-merge", True, "u"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_tag",
            return_value=PhaseResult("tag", False, "tag-fail"),
        ),
    ):
        r1 = execute_release(cfg, provider)
    assert r1.success is False

    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", True, "x"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", True, "u"),
        ),
        patch(
            "ai_engineering.release.orchestrator._wait_for_merge",
            return_value=PhaseResult("wait-for-merge", True, "u"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_tag",
            return_value=PhaseResult("tag", True, "ok"),
        ),
        patch(
            "ai_engineering.release.orchestrator._update_manifest",
            return_value=PhaseResult("manifest", False, "m-fail"),
        ),
        patch("ai_engineering.release.orchestrator._log_audit_event"),
    ):
        r2 = execute_release(cfg, provider)
    assert r2.success is False

    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", True, "x"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", True, "u"),
        ),
        patch(
            "ai_engineering.release.orchestrator._wait_for_merge",
            return_value=PhaseResult("wait-for-merge", True, "u"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_tag",
            return_value=PhaseResult("tag", True, "ok"),
        ),
        patch(
            "ai_engineering.release.orchestrator._update_manifest",
            return_value=PhaseResult("manifest", True, "ok"),
        ),
        patch(
            "ai_engineering.release.orchestrator._monitor_pipeline",
            return_value=PhaseResult("monitor", False, "mon-fail"),
        ),
        patch("ai_engineering.release.orchestrator._log_audit_event"),
    ):
        r3 = execute_release(cfg, provider)
    assert r3.success is False


def test_parse_runs_and_helpers_extra_branches(tmp_path: Path) -> None:
    assert _parse_runs("prefix [broken]") == []

    with patch(
        "ai_engineering.release.orchestrator.run_git",
        return_value=(True, "[project]\nname='x'\n"),
    ):
        assert _version_from_git_ref(tmp_path, "origin/main") is None

    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "[1]")):
        assert _find_existing_pr_url(tmp_path, "release/v0.2.0", _FakeProvider(), _Runner()) == ""
