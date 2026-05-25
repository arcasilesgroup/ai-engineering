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
    ReleaseResult,
    ReleaseState,
    SubprocessRunner,
    SystemClock,
    _complete_release,
    _create_release_pr,
    _create_tag,
    _default_branch,
    _detect_state,
    _find_existing_pr_url,
    _monitor_pipeline,
    _parse_runs,
    _prepare_branch,
    _repo_slug,
    _run_release_readiness,
    _update_lockfile_version,
    _update_manifest,
    _validate,
    _version_from_git_ref,
    _wait_for_merge,
    execute_release,
)
from ai_engineering.state.defaults import default_install_state
from ai_engineering.state.service import save_install_state
from ai_engineering.vcs.protocol import (
    CreateTagContext,
    PipelineStatusContext,
    VcsContext,
    VcsResult,
)


class _FakeProvider:
    def __init__(self) -> None:
        self.tag_success = True
        self.pipeline_success = True
        self.pipeline_output = "[]"
        self.last_head_sha: str | None = None

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
        self.last_head_sha = ctx.head_sha
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


def _readiness_phase(
    verdict: str = "GO",
    *,
    success: bool = True,
    conditions: list[str] | None = None,
) -> PhaseResult:
    return PhaseResult(
        "readiness",
        success,
        verdict,
        details={
            "readiness": {
                "verdict": verdict,
                "conditions": conditions or [],
                "artifact_path": ".ai-engineering/runtime/release/0.2.0/release-readiness.json",
            }
        },
    )


def test_execute_release_returns_validation_errors(tmp_path: Path) -> None:
    # Arrange
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    # Act
    with patch("ai_engineering.release.orchestrator._validate", return_value=["boom"]):
        result = execute_release(config, provider)

    # Assert
    assert result.success is False
    assert result.errors == ["boom"]
    assert result.phases[0].phase == "validate"
    assert result.phases[0].success is False


def test_execute_release_dry_run_outputs_plan(tmp_path: Path) -> None:
    # Arrange
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, dry_run=True)
    provider = _FakeProvider()
    state = ReleaseState(
        release_branch="release/v0.2.0",
        local_branch_exists=False,
        remote_branch_exists=False,
        tag_exists=False,
        current_version="0.1.0",
    )

    # Act
    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    # Assert
    assert result.success is True
    assert any(phase.phase == "plan" and phase.skipped for phase in result.phases)
    assert result.dry_run_plan is not None
    assert result.dry_run_plan["old_version"] == "0.1.0"
    assert result.dry_run_plan["target_version"] == "0.2.0"
    assert result.dry_run_plan["release_branch"] == "release/v0.2.0"
    assert result.dry_run_plan["tag"] == "v0.2.0"
    assert "readiness gate" in result.dry_run_plan["readiness_gate"]
    assert "TestPyPI" in result.dry_run_plan["testpypi_stage"]
    assert "PyPI" in result.dry_run_plan["pypi_stage"]
    assert "release-packet.json" in result.dry_run_plan["release_packet_outputs"]


def test_execute_release_noops_when_tag_exists(tmp_path: Path) -> None:
    # Arrange
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()
    state = ReleaseState(
        release_branch="release/v0.2.0",
        local_branch_exists=False,
        remote_branch_exists=False,
        tag_exists=True,
        current_version="0.2.0",
    )

    # Act
    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch("ai_engineering.release.orchestrator._repo_slug", return_value="acme/repo"),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    # Assert
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
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    seq = [(True, ""), (False, ""), (True, "")]

    # Act
    with (
        patch("ai_engineering.release.orchestrator.run_git", side_effect=seq),
        patch("ai_engineering.release.orchestrator.detect_current_version", return_value="0.1.0"),
    ):
        state = _detect_state(cfg, _FakeProvider())

    # Assert
    assert state.local_branch_exists is True
    assert state.remote_branch_exists is False
    assert state.tag_exists is True
    assert state.current_version == "0.1.0"


def test_prepare_branch_returns_skip_when_branch_exists(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    # Act
    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")):
        phase = _prepare_branch(cfg, _FixedClock())

    # Assert
    assert phase.skipped is True


def test_prepare_branch_handles_checkout_failure(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    seq = [(False, ""), (False, "oops")]

    # Act
    with patch("ai_engineering.release.orchestrator.run_git", side_effect=seq):
        phase = _prepare_branch(cfg, _FixedClock())

    # Assert
    assert phase.success is False
    assert "Failed to create branch" in phase.output


def test_prepare_branch_handles_bump_failure(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    seq = [(False, ""), (True, "")]

    # Act
    with (
        patch("ai_engineering.release.orchestrator.run_git", side_effect=seq),
        patch(
            "ai_engineering.release.orchestrator.bump_python_version", side_effect=ValueError("x")
        ),
    ):
        phase = _prepare_branch(cfg, _FixedClock())

    # Assert
    assert phase.success is False
    assert phase.output == "x"


def test_prepare_branch_success_path(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    bump = type("Bump", (), {})()
    bump.old_version = "0.1.0"
    bump.new_version = "0.2.0"
    bump.files_modified = [
        tmp_path / "pyproject.toml",
        tmp_path / "src" / "ai_engineering" / "__version__.py",
    ]
    seq = [(False, ""), (True, ""), (True, ""), (True, "")]

    # Act
    with (
        patch("ai_engineering.release.orchestrator.run_git", side_effect=seq),
        patch("ai_engineering.release.orchestrator.bump_python_version", return_value=bump),
        patch("ai_engineering.release.orchestrator.promote_unreleased", return_value=True),
    ):
        phase = _prepare_branch(cfg, _FixedClock())

    # Assert
    assert phase.success is True
    assert "pyproject.toml" in phase.output


def test_create_release_pr_handles_existing_pr_url(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    class _P(_FakeProvider):
        def create_pr(self, ctx: VcsContext) -> VcsResult:
            del ctx
            return VcsResult(success=False, output="already")

    # Act
    with (
        patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")),
        patch(
            "ai_engineering.release.orchestrator._find_existing_pr_url",
            return_value="https://x/pr/1",
        ),
    ):
        phase = _create_release_pr(cfg, _P(), _Runner())

    # Assert
    assert phase.success is True
    assert phase.skipped is True


def test_create_release_pr_auto_complete_failure(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    class _P(_FakeProvider):
        def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
            del ctx
            return VcsResult(success=False, output="bad")

    # Act
    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "")):
        phase = _create_release_pr(cfg, _P(), _Runner())

    # Assert
    assert phase.success is False
    assert "Auto-complete failed" in phase.output


def test_wait_for_merge_github_success(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    runner = _Runner(ok=True, out='{"mergedAt":"now","url":"https://x/pr/1"}')

    # Act
    with patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 1]):
        phase = _wait_for_merge(cfg, _FakeProvider(), 5, runner)

    # Assert
    assert phase.success is True


def test_wait_for_merge_non_github_success(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    class _P(_FakeProvider):
        def provider_name(self) -> str:
            return "azure_devops"

    seq = [(True, ""), (False, ""), (True, "")]

    # Act
    with (
        patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 1]),
        patch("ai_engineering.release.orchestrator.run_git", side_effect=seq),
        patch("ai_engineering.release.orchestrator._version_from_git_ref", return_value="0.2.0"),
    ):
        phase = _wait_for_merge(cfg, _P(), 5, _Runner())

    # Assert
    assert phase.success is True


def test_create_tag_failure_and_success_paths(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    # Act / Assert — failure path
    seq_fail_checkout = [(False, ""), (True, ""), (False, "no")]
    with patch("ai_engineering.release.orchestrator.run_git", side_effect=seq_fail_checkout):
        phase = _create_tag(cfg, provider)
    assert phase.success is False

    # Act / Assert — success path
    seq_success = [(False, ""), (True, ""), (True, ""), (True, ""), (True, "abc123\n")]
    with patch("ai_engineering.release.orchestrator.run_git", side_effect=seq_success):
        phase_ok = _create_tag(cfg, provider)
    assert phase_ok.success is True


def test_update_manifest_skips_when_missing(tmp_path: Path) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    phase = _update_manifest(cfg, _FixedClock())
    assert phase.skipped is True


def test_update_manifest_updates_release_fields(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    state_dir = tmp_path / ".ai-engineering" / "state"
    save_install_state(state_dir, default_install_state())

    # Act
    phase = _update_manifest(cfg, _FixedClock())

    # Assert
    assert phase.success is True


def test_monitor_pipeline_success_and_failure(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    # Act / Assert — failure path
    with patch("ai_engineering.release.orchestrator.run_git", return_value=(False, "bad")):
        phase = _monitor_pipeline(cfg, provider, 1)
    assert phase.success is False

    # Act / Assert — success path
    provider.pipeline_output = (
        '[{"status":"completed","conclusion":"success","url":"https://x/run"}]'
    )
    with (
        patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "abc\n")),
        patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 1]),
    ):
        phase_ok = _monitor_pipeline(cfg, provider, 5)
    assert phase_ok.success is True


def test_monitor_pipeline_uses_threaded_sha_when_tag_is_remote_only(tmp_path: Path) -> None:
    """Regression (v0.8.1): the tag ref is created remote-only via the GitHub API, so a
    local ``git rev-parse v<version>`` fails. Monitor must use the SHA threaded from
    _create_tag instead of re-deriving it locally.
    """
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()
    provider.pipeline_output = (
        '[{"status":"completed","conclusion":"success","url":"https://x/run"}]'
    )
    local_rev_parse_fails = (
        False,
        "fatal: ambiguous argument 'v0.2.0': unknown revision or path not in the working tree.",
    )

    # Act / Assert — without the threaded SHA, the local lookup fails (the v0.8.1 symptom)
    with patch("ai_engineering.release.orchestrator.run_git", return_value=local_rev_parse_fails):
        broken = _monitor_pipeline(cfg, provider, 1)
    assert broken.success is False
    assert "Unable to read tag SHA" in broken.output

    # Act / Assert — with the threaded SHA, monitor never touches the local tag
    with (
        patch("ai_engineering.release.orchestrator.run_git", return_value=local_rev_parse_fails),
        patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 1]),
    ):
        fixed = _monitor_pipeline(cfg, provider, 5, tagged_sha="deadbeefcafe")
    assert fixed.success is True
    assert fixed.output == "https://x/run"
    assert provider.last_head_sha == "deadbeefcafe"


def test_monitor_pipeline_fallback_resolves_tag_via_refs_namespace(tmp_path: Path) -> None:
    """The resume-flow fallback must resolve the local tag through the
    ``refs/tags/`` namespace with ``--verify --quiet`` — the same safe form used
    by _validate/_create_tag — not a bare ``rev-parse v<version>`` that can match
    a branch or a partial SHA (0.8.2 release-robustness fix).
    """
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()
    captured: list[list[str]] = []

    def capture_run_git(args: list[str], _root: Path) -> tuple[bool, str]:
        captured.append(args)
        return (False, "")

    with patch("ai_engineering.release.orchestrator.run_git", side_effect=capture_run_git):
        _monitor_pipeline(cfg, provider, 1)

    assert captured == [["rev-parse", "--verify", "--quiet", "refs/tags/v0.2.0"]]


def test_create_tag_exposes_tagged_sha_in_details(tmp_path: Path) -> None:
    """_create_tag threads the freshly tagged commit SHA via PhaseResult.details so
    _monitor_pipeline can avoid a (failing) local tag lookup."""
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()

    # Act — fresh-tag success path (mirrors test_create_tag_failure_and_success_paths)
    seq_success = [(False, ""), (True, ""), (True, ""), (True, ""), (True, "abc123\n")]
    with patch("ai_engineering.release.orchestrator.run_git", side_effect=seq_success):
        phase = _create_tag(cfg, provider)

    # Assert
    assert phase.success is True
    assert phase.details.get("tagged_sha") == "abc123"


def test_complete_release_threads_tag_sha_into_monitor(tmp_path: Path) -> None:
    """_complete_release passes the SHA from _create_tag straight into _monitor_pipeline
    rather than letting monitor re-derive it from a local tag that does not exist."""
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    provider = _FakeProvider()
    result = ReleaseResult(success=True, phases=[], version="0.2.0", tag_name="v0.2.0")
    captured: dict[str, object] = {}

    def fake_monitor(_cfg, _provider, _timeout, tagged_sha=None):
        captured["tagged_sha"] = tagged_sha
        return PhaseResult("monitor", True, "https://example/release/v0.2.0")

    # Act
    with (
        patch(
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase(),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_tag",
            return_value=PhaseResult(
                "tag", True, "v0.2.0 created (abc123)", details={"tagged_sha": "abc123def456"}
            ),
        ),
        patch(
            "ai_engineering.release.orchestrator._update_manifest",
            return_value=PhaseResult("manifest", True, "ok"),
        ),
        patch("ai_engineering.release.orchestrator._release_url_for_tag", return_value=""),
        patch("ai_engineering.release.orchestrator._monitor_pipeline", side_effect=fake_monitor),
        patch("ai_engineering.release.orchestrator.emit_deploy_event"),
    ):
        ok = _complete_release(cfg, provider, _FixedClock(), result, [])

    # Assert
    assert ok is True
    assert captured["tagged_sha"] == "abc123def456"


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
    # Arrange
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=True)
    provider = _FakeProvider()
    state = ReleaseState(
        release_branch="release/v0.2.0",
        local_branch_exists=False,
        remote_branch_exists=False,
        tag_exists=False,
        current_version="0.1.0",
    )

    # Act
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
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase(),
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
        patch("ai_engineering.release.orchestrator.emit_deploy_event"),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    # Assert
    assert result.success is True
    assert result.pr_url == "https://example/pr/1"
    assert result.release_url == "https://example/release/v0.2.0"
    assert [phase.phase for phase in result.phases][3:6] == [
        "wait-for-merge",
        "readiness",
        "tag",
    ]


def test_run_release_readiness_writes_runtime_artifact(tmp_path: Path, monkeypatch) -> None:
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    class _Report:
        verdict = "GO"
        allows_release = True

        def __init__(self) -> None:
            self.conditions: list[str] = []

        def to_dict(self) -> dict[str, object]:
            return {
                "version": "0.2.0",
                "verdict": "GO",
                "conditions": [],
                "dimensions": {"security": {"status": "PASS"}},
                "artifact_path": str(tmp_path / "ignored.json"),
            }

    monkeypatch.setattr("ai_engineering.release.orchestrator.verify_release", lambda *_: _Report())

    phase = _run_release_readiness(cfg)

    assert phase.success is True
    assert phase.details["readiness"]["verdict"] == "GO"
    readiness_path = (
        tmp_path / ".ai-engineering" / "runtime" / "release" / "0.2.0" / "release-readiness.json"
    )
    assert readiness_path.is_file()


def test_execute_release_readiness_runs_after_merge_before_tag(tmp_path: Path) -> None:
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=True)
    provider = _FakeProvider()
    state = ReleaseState("release/v0.2.0", False, False, False, "0.1.0")
    calls: list[str] = []

    def wait_phase(*_args) -> PhaseResult:
        calls.append("wait")
        return PhaseResult("wait-for-merge", True, "merged")

    def readiness_phase(_config: ReleaseConfig) -> PhaseResult:
        calls.append("readiness")
        return _readiness_phase()

    def tag_phase(_config: ReleaseConfig, _provider: _FakeProvider) -> PhaseResult:
        calls.append("tag")
        return PhaseResult("tag", True, "ok")

    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", True, "pyproject.toml"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", True, "https://example/pr/1"),
        ),
        patch("ai_engineering.release.orchestrator._wait_for_merge", side_effect=wait_phase),
        patch(
            "ai_engineering.release.orchestrator._run_release_readiness",
            side_effect=readiness_phase,
        ),
        patch("ai_engineering.release.orchestrator._create_tag", side_effect=tag_phase),
        patch(
            "ai_engineering.release.orchestrator._update_manifest",
            return_value=PhaseResult("manifest", True, "ok"),
        ),
        patch(
            "ai_engineering.release.orchestrator._monitor_pipeline",
            return_value=PhaseResult("monitor", True, "https://example/release/v0.2.0"),
        ),
        patch("ai_engineering.release.orchestrator.emit_deploy_event"),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    assert result.success is True
    assert calls == ["wait", "readiness", "tag"]


def test_execute_release_blocks_tag_on_readiness_no_go(tmp_path: Path) -> None:
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=True)
    provider = _FakeProvider()
    state = ReleaseState("release/v0.2.0", False, False, False, "0.1.0")

    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", True, "pyproject.toml"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", True, "https://example/pr/1"),
        ),
        patch(
            "ai_engineering.release.orchestrator._wait_for_merge",
            return_value=PhaseResult("wait-for-merge", True, "merged"),
        ),
        patch(
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase("NO-GO", success=False),
        ),
        patch("ai_engineering.release.orchestrator._create_tag") as tag,
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    assert result.success is False
    assert result.phases[-1].phase == "readiness"
    assert result.errors == ["NO-GO"]
    tag.assert_not_called()


def test_execute_release_conditional_readiness_proceeds_and_records_conditions(
    tmp_path: Path,
) -> None:
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=True)
    provider = _FakeProvider()
    state = ReleaseState("release/v0.2.0", False, False, False, "0.1.0")

    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", True, "pyproject.toml"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", True, "https://example/pr/1"),
        ),
        patch(
            "ai_engineering.release.orchestrator._wait_for_merge",
            return_value=PhaseResult("wait-for-merge", True, "merged"),
        ),
        patch(
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase("CONDITIONAL GO", conditions=["accepted via D-143-09"]),
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
        patch("ai_engineering.release.orchestrator.emit_deploy_event"),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    assert result.success is True
    assert result.readiness is not None
    assert result.readiness["verdict"] == "CONDITIONAL GO"
    assert result.readiness["conditions"] == ["accepted via D-143-09"]


def test_validate_collects_branch_provider_and_changelog_errors(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")

    class _P(_FakeProvider):
        def is_available(self) -> bool:
            return False

    # Act
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

    # Assert
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
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)

    # Act
    with (
        patch("ai_engineering.release.orchestrator.time.time", side_effect=[0, 20]),
        patch("ai_engineering.release.orchestrator.time.sleep"),
    ):
        phase = _wait_for_merge(cfg, _FakeProvider(), 10, _Runner(ok=True, out="not-json"))

    # Assert
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
    # Arrange
    runner = SubprocessRunner()

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    # Act / Assert — success path
    with patch("subprocess.run", return_value=_Proc()):
        ok, out = runner.run(["echo", "x"], tmp_path)
    assert ok is True
    assert "ok" in out

    # Act / Assert — not found path
    with patch("subprocess.run", side_effect=FileNotFoundError):
        ok2, out2 = runner.run(["missing"], tmp_path)
    assert ok2 is False
    assert "Command not found" in out2

    # Act / Assert — timeout path
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
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase(),
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
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase(),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_tag",
            return_value=PhaseResult("tag", True, "ok"),
        ),
        patch(
            "ai_engineering.release.orchestrator._update_manifest",
            return_value=PhaseResult("manifest", False, "m-fail"),
        ),
        patch("ai_engineering.release.orchestrator.emit_deploy_event"),
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
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase(),
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
        patch("ai_engineering.release.orchestrator.emit_deploy_event"),
    ):
        r3 = execute_release(cfg, provider)
    assert r3.success is False


def test_execute_release_no_wait_skips_tag(tmp_path: Path) -> None:
    """Without --wait, tag phase must be skipped (not called)."""
    # Arrange
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=False)
    provider = _FakeProvider()
    state = ReleaseState(
        release_branch="release/v0.2.0",
        local_branch_exists=False,
        remote_branch_exists=False,
        tag_exists=False,
        current_version="0.1.0",
    )

    # Act — _create_tag is NOT patched; if called, it would hit real git and fail
    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch(
            "ai_engineering.release.orchestrator._prepare_branch",
            return_value=PhaseResult("prepare", True, "pyproject.toml"),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_release_pr",
            return_value=PhaseResult("pr", True, "https://example/pr/1"),
        ),
        patch("ai_engineering.release.orchestrator._repo_slug", return_value="acme/repo"),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    # Assert
    assert result.success is True
    tag_phases = [p for p in result.phases if p.phase == "tag"]
    assert len(tag_phases) == 1
    assert tag_phases[0].skipped is True
    assert "deferred" in tag_phases[0].output.lower()


def test_parse_runs_and_helpers_extra_branches(tmp_path: Path) -> None:
    assert _parse_runs("prefix [broken]") == []

    with patch(
        "ai_engineering.release.orchestrator.run_git",
        return_value=(True, "[project]\nname='x'\n"),
    ):
        assert _version_from_git_ref(tmp_path, "origin/main") is None

    with patch("ai_engineering.release.orchestrator.run_git", return_value=(True, "[1]")):
        assert _find_existing_pr_url(tmp_path, "release/v0.2.0", _FakeProvider(), _Runner()) == ""


# --- Idempotent resume: bump already merged, tag still missing ------------------


def _write_post_promotion_changelog(tmp_path: Path, version: str) -> None:
    """Write a CHANGELOG in the post-promotion state: empty [Unreleased], [version] present."""
    (tmp_path / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## [Unreleased]\n\n## [{version}] - 2026-01-01\n\n### Added\n- thing\n",
        encoding="utf-8",
    )


def test_validate_resume_skips_version_and_changelog_gate(tmp_path: Path) -> None:
    """current == target (bump merged) must skip the greater-than gate AND the
    changelog gate so a post-merge rerun can resume to tag instead of failing."""
    # Arrange — CHANGELOG already promoted (empty [Unreleased], [0.2.0] present)
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    _write_post_promotion_changelog(tmp_path, "0.2.0")

    # Act — tag absent (so no early return), branch main, clean tree, version equal
    with (
        patch(
            "ai_engineering.release.orchestrator.run_git",
            side_effect=[(False, ""), (True, "")],
        ),
        patch("ai_engineering.release.orchestrator.current_branch", return_value="main"),
        patch("ai_engineering.release.orchestrator.detect_current_version", return_value="0.2.0"),
    ):
        errors = _validate(cfg, _FakeProvider())

    # Assert — no errors despite empty [Unreleased] and existing [0.2.0] section
    assert errors == []


def test_validate_still_blocks_downgrade(tmp_path: Path) -> None:
    """current > target is a genuine downgrade and must still error."""
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n### Added\n- x\n", encoding="utf-8"
    )

    # Act
    with (
        patch(
            "ai_engineering.release.orchestrator.run_git",
            side_effect=[(False, ""), (True, "")],
        ),
        patch("ai_engineering.release.orchestrator.current_branch", return_value="main"),
        patch("ai_engineering.release.orchestrator.detect_current_version", return_value="0.3.0"),
    ):
        errors = _validate(cfg, _FakeProvider())

    # Assert
    assert any("must be greater than current" in e for e in errors)


def test_execute_release_resume_creates_tag_when_bump_already_merged(tmp_path: Path) -> None:
    """When the bump is already on main and the tag is missing, skip
    prepare/PR/wait-for-merge and proceed straight to readiness -> tag -> monitor."""
    # Arrange — current_version equals target, tag absent
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=True)
    provider = _FakeProvider()
    state = ReleaseState("release/v0.2.0", False, False, tag_exists=False, current_version="0.2.0")

    # Act
    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch("ai_engineering.release.orchestrator._prepare_branch") as prepare,
        patch("ai_engineering.release.orchestrator._create_release_pr") as create_pr,
        patch("ai_engineering.release.orchestrator._wait_for_merge") as wait,
        patch(
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase(),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_tag",
            return_value=PhaseResult("tag", True, "v0.2.0 created"),
        ),
        patch(
            "ai_engineering.release.orchestrator._update_manifest",
            return_value=PhaseResult("manifest", True, "ok"),
        ),
        patch(
            "ai_engineering.release.orchestrator._monitor_pipeline",
            return_value=PhaseResult("monitor", True, "https://example/release/v0.2.0"),
        ),
        patch("ai_engineering.release.orchestrator.emit_deploy_event"),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    # Assert — pre-merge phases skipped (not invoked), completion phases ran
    assert result.success is True
    prepare.assert_not_called()
    create_pr.assert_not_called()
    wait.assert_not_called()
    assert [phase.phase for phase in result.phases] == [
        "validate",
        "prepare",
        "pr",
        "wait-for-merge",
        "readiness",
        "tag",
        "manifest",
        "monitor",
    ]
    by_phase = {phase.phase: phase for phase in result.phases}
    assert by_phase["prepare"].skipped is True
    assert by_phase["pr"].skipped is True
    assert by_phase["wait-for-merge"].skipped is True
    assert by_phase["tag"].skipped is False
    assert by_phase["tag"].success is True


def test_execute_release_resume_completes_even_without_wait_flag(tmp_path: Path) -> None:
    """Resume finishes (tag + monitor) even without --wait: there is no merge to
    wait for once the bump has landed, so the deferred-tag path must not apply."""
    # Arrange
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=False)
    provider = _FakeProvider()
    state = ReleaseState("release/v0.2.0", False, False, tag_exists=False, current_version="0.2.0")

    # Act — _prepare_branch/_create_release_pr must not be called
    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch("ai_engineering.release.orchestrator._prepare_branch") as prepare,
        patch("ai_engineering.release.orchestrator._create_release_pr") as create_pr,
        patch(
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase(),
        ),
        patch(
            "ai_engineering.release.orchestrator._create_tag",
            return_value=PhaseResult("tag", True, "v0.2.0 created"),
        ),
        patch(
            "ai_engineering.release.orchestrator._update_manifest",
            return_value=PhaseResult("manifest", True, "ok"),
        ),
        patch(
            "ai_engineering.release.orchestrator._monitor_pipeline",
            return_value=PhaseResult("monitor", True, "https://example/release/v0.2.0"),
        ),
        patch("ai_engineering.release.orchestrator.emit_deploy_event"),
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    # Assert — tag actually created (not deferred)
    assert result.success is True
    prepare.assert_not_called()
    create_pr.assert_not_called()
    tag_phases = [phase for phase in result.phases if phase.phase == "tag"]
    assert len(tag_phases) == 1
    assert tag_phases[0].skipped is False
    assert "deferred" not in tag_phases[0].output.lower()


def test_execute_release_resume_blocks_on_readiness_no_go(tmp_path: Path) -> None:
    """Resume path still honors the readiness gate: NO-GO stops before tagging."""
    # Arrange
    config = ReleaseConfig(version="0.2.0", project_root=tmp_path, wait=True)
    provider = _FakeProvider()
    state = ReleaseState("release/v0.2.0", False, False, tag_exists=False, current_version="0.2.0")

    # Act
    with (
        patch("ai_engineering.release.orchestrator._validate", return_value=[]),
        patch("ai_engineering.release.orchestrator._detect_state", return_value=state),
        patch("ai_engineering.release.orchestrator._prepare_branch"),
        patch("ai_engineering.release.orchestrator._create_release_pr"),
        patch(
            "ai_engineering.release.orchestrator._run_release_readiness",
            return_value=_readiness_phase("NO-GO", success=False),
        ),
        patch("ai_engineering.release.orchestrator._create_tag") as tag,
    ):
        result = execute_release(config, provider, clock=_FixedClock())

    # Assert
    assert result.success is False
    assert result.errors == ["NO-GO"]
    assert result.phases[-1].phase == "readiness"
    tag.assert_not_called()


# --- Secondary: uv.lock project pin stays consistent with the bump --------------


_LOCK_FIXTURE = (
    (
        "version = 1\n"
        "revision = 3\n\n"
        "[[package]]\n"
        'name = "ai-engineering"\n'
        'version = "0.1.0"\n'
        'source = {{ editable = "." }}\n'
        "dependencies = [\n"
        '    {{ name = "click" }},\n'
        "]\n\n"
        "[[package]]\n"
        'name = "click"\n'
        'version = "8.3.3"\n'
    )
    .replace("{{", "{")
    .replace("}}", "}")
)


def test_update_lockfile_version_updates_editable_root_pin(tmp_path: Path) -> None:
    # Arrange
    lock = tmp_path / "uv.lock"
    lock.write_text(_LOCK_FIXTURE, encoding="utf-8")

    # Act
    result = _update_lockfile_version(tmp_path, "0.2.0")

    # Assert — only the editable-root pin moved
    text = lock.read_text(encoding="utf-8")
    assert result == lock
    assert 'version = "0.2.0"\nsource = { editable = "." }' in text
    # lockfile-format `version = 1` line and dependency pins untouched
    assert text.startswith("version = 1\n")
    assert 'name = "click"\nversion = "8.3.3"' in text


def test_update_lockfile_version_missing_file_returns_none(tmp_path: Path) -> None:
    assert _update_lockfile_version(tmp_path, "0.2.0") is None


def test_update_lockfile_version_without_editable_root_raises(tmp_path: Path) -> None:
    # Arrange — a lockfile with no editable root pin
    lock = tmp_path / "uv.lock"
    lock.write_text(
        'version = 1\n\n[[package]]\nname = "click"\nversion = "8.3.3"\n', encoding="utf-8"
    )

    # Act / Assert
    with pytest.raises(ValueError, match=r"uv\.lock"):
        _update_lockfile_version(tmp_path, "0.2.0")


def test_prepare_branch_updates_uv_lock_and_lists_it(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    bump = type("Bump", (), {})()
    bump.old_version = "0.1.0"
    bump.new_version = "0.2.0"
    bump.files_modified = [tmp_path / "pyproject.toml"]
    # show-ref (absent), checkout -b, add, commit
    seq = [(False, ""), (True, ""), (True, ""), (True, "")]

    # Act
    with (
        patch("ai_engineering.release.orchestrator.run_git", side_effect=seq),
        patch("ai_engineering.release.orchestrator.bump_python_version", return_value=bump),
        patch("ai_engineering.release.orchestrator.promote_unreleased", return_value=True),
        patch(
            "ai_engineering.release.orchestrator._update_lockfile_version",
            return_value=tmp_path / "uv.lock",
        ),
    ):
        phase = _prepare_branch(cfg, _FixedClock())

    # Assert — uv.lock listed among the bumped files
    assert phase.success is True
    assert "uv.lock" in phase.output


def test_prepare_branch_propagates_lockfile_error(tmp_path: Path) -> None:
    # Arrange
    cfg = ReleaseConfig(version="0.2.0", project_root=tmp_path)
    bump = type("Bump", (), {})()
    bump.files_modified = [tmp_path / "pyproject.toml"]

    # Act — lock update fails after a successful bump
    with (
        patch("ai_engineering.release.orchestrator.run_git", side_effect=[(False, ""), (True, "")]),
        patch("ai_engineering.release.orchestrator.bump_python_version", return_value=bump),
        patch(
            "ai_engineering.release.orchestrator._update_lockfile_version",
            side_effect=ValueError("Unable to update project version in uv.lock"),
        ),
    ):
        phase = _prepare_branch(cfg, _FixedClock())

    # Assert
    assert phase.success is False
    assert "uv.lock" in phase.output
