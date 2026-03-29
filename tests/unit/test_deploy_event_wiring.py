"""Unit tests for release orchestrator deploy event wiring.

Verifies that the release orchestrator uses ``emit_deploy_event`` from
``state.audit`` instead of an internal ``_log_audit_event`` function.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_engineering.release import orchestrator as orchestrator_module
from ai_engineering.release.orchestrator import (
    ReleaseConfig,
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeClock:
    def utcnow(self) -> datetime:
        return datetime(2025, 6, 1, tzinfo=UTC)


class _FakeRunner:
    def run(self, cmd: list[str], cwd: Path, timeout: int = 60) -> tuple[bool, str]:
        return True, ""


class _FakeProvider:
    def __init__(self) -> None:
        self.tag_result = VcsResult(success=True, output="v9.9.9 created")

    def is_available(self) -> bool:
        return True

    def provider_name(self) -> str:
        return "github"

    def check_auth(self, ctx: VcsContext) -> VcsResult:
        return VcsResult(success=True)

    def create_pr(self, ctx: VcsContext) -> VcsResult:
        return VcsResult(success=True, url="https://example/pr/1")

    def find_open_pr(self, ctx: VcsContext) -> VcsResult:
        return VcsResult(success=True, output="")

    def update_pr(self, ctx: VcsContext, *, pr_number: str, title: str = "") -> VcsResult:
        return VcsResult(success=True)

    def enable_auto_complete(self, ctx: VcsContext) -> VcsResult:
        return VcsResult(success=True)

    def create_tag(self, ctx: CreateTagContext) -> VcsResult:
        return self.tag_result

    def get_pipeline_status(self, ctx: PipelineStatusContext) -> VcsResult:
        return VcsResult(success=False, output="no runs")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLogAuditEventRemoved:
    """Verify that the old _log_audit_event function no longer exists."""

    def test_no_log_audit_event_function(self) -> None:
        """_log_audit_event should not be present in the orchestrator module."""
        assert not hasattr(orchestrator_module, "_log_audit_event")

    def test_no_log_audit_event_in_source(self) -> None:
        """The source file should not contain 'def _log_audit_event'."""
        source_path = Path(orchestrator_module.__file__)
        source = source_path.read_text(encoding="utf-8")
        assert "def _log_audit_event" not in source


class TestEmitDeployEventWiring:
    """Verify emit_deploy_event is called during release execution."""

    def _setup_project(self, tmp_path: Path) -> ReleaseConfig:
        """Create minimal project structure for a release dry-run bypass."""
        state_dir = tmp_path / ".ai-engineering" / "state"
        state_dir.mkdir(parents=True)
        save_install_state(state_dir, default_install_state())
        # Create CHANGELOG.md with [Unreleased] section
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text(
            "# Changelog\n\n## [Unreleased]\n\n- feature\n",
            encoding="utf-8",
        )
        # Create pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\nversion = "0.0.1"\n',
            encoding="utf-8",
        )
        return ReleaseConfig(
            version="9.9.9",
            project_root=tmp_path,
            wait=True,
        )

    @patch("ai_engineering.release.orchestrator.emit_deploy_event")
    def test_tag_creation_emits_deploy_event(
        self,
        mock_emit: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Tag creation phase should call emit_deploy_event with strategy='tag'."""
        config = self._setup_project(tmp_path)
        provider = _FakeProvider()

        # Patch git operations to simulate a successful release flow
        with (
            patch(
                "ai_engineering.release.orchestrator.current_branch",
                return_value="main",
            ),
            patch(
                "ai_engineering.release.orchestrator.run_git",
                return_value=(True, "abc123def456"),
            ),
            patch(
                "ai_engineering.release.orchestrator._validate",
                return_value=[],
            ),
            patch(
                "ai_engineering.release.orchestrator._detect_state",
                return_value=MagicMock(
                    release_branch="release/v9.9.9",
                    local_branch_exists=False,
                    remote_branch_exists=False,
                    tag_exists=False,
                    current_version="0.0.1",
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._prepare_branch",
                return_value=MagicMock(
                    phase="prepare",
                    success=True,
                    output="pyproject.toml",
                    skipped=False,
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._create_release_pr",
                return_value=MagicMock(
                    phase="pr",
                    success=True,
                    output="https://example/pr/1",
                    skipped=False,
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._wait_for_merge",
                return_value=MagicMock(
                    phase="wait-for-merge",
                    success=True,
                    output="merged",
                    skipped=False,
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._create_tag",
                return_value=MagicMock(
                    phase="tag",
                    success=True,
                    output="v9.9.9 created",
                    skipped=False,
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._update_manifest",
                return_value=MagicMock(
                    phase="manifest",
                    success=True,
                    output="updated",
                    skipped=False,
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._monitor_pipeline",
                return_value=MagicMock(
                    phase="monitor",
                    success=True,
                    output="https://example/run/1\nCompleted",
                    skipped=False,
                ),
            ),
        ):
            result = execute_release(config, provider, clock=_FakeClock(), runner=_FakeRunner())

        assert result.success
        # With wait=True, emit is called twice (tag + pipeline). Check tag call exists.
        tag_calls = [
            c
            for c in mock_emit.call_args_list
            if c.kwargs.get("strategy") == "tag" or (len(c.args) > 3 and c.args[3] == "tag")
        ]
        assert len(tag_calls) >= 1

    @patch("ai_engineering.release.orchestrator.emit_deploy_event")
    def test_pipeline_completion_emits_deploy_event(
        self,
        mock_emit: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Pipeline monitoring should call emit_deploy_event with strategy='pipeline'."""
        config = self._setup_project(tmp_path)
        config.wait = True
        provider = _FakeProvider()

        with (
            patch(
                "ai_engineering.release.orchestrator._validate",
                return_value=[],
            ),
            patch(
                "ai_engineering.release.orchestrator._detect_state",
                return_value=MagicMock(
                    release_branch="release/v9.9.9",
                    local_branch_exists=False,
                    remote_branch_exists=False,
                    tag_exists=False,
                    current_version="0.0.1",
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._prepare_branch",
                return_value=MagicMock(
                    phase="prepare", success=True, output="pyproject.toml", skipped=False
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._create_release_pr",
                return_value=MagicMock(
                    phase="pr", success=True, output="https://example/pr/1", skipped=False
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._wait_for_merge",
                return_value=MagicMock(
                    phase="wait-for-merge", success=True, output="merged", skipped=False
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._create_tag",
                return_value=MagicMock(
                    phase="tag", success=True, output="v9.9.9 created", skipped=False
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._update_manifest",
                return_value=MagicMock(
                    phase="manifest", success=True, output="updated", skipped=False
                ),
            ),
            patch(
                "ai_engineering.release.orchestrator._monitor_pipeline",
                return_value=MagicMock(
                    phase="monitor",
                    success=True,
                    output="https://example/actions/runs/1",
                    skipped=False,
                ),
            ),
        ):
            result = execute_release(config, provider, clock=_FakeClock(), runner=_FakeRunner())

        assert result.success
        # Two calls: one for tag creation, one for pipeline completion
        assert mock_emit.call_count == 2
        tag_call = mock_emit.call_args_list[0]
        assert tag_call.kwargs["strategy"] == "tag"
        assert tag_call.kwargs["version"] == "9.9.9"
        assert tag_call.kwargs["environment"] == "production"

        pipeline_call = mock_emit.call_args_list[1]
        assert pipeline_call.kwargs["strategy"] == "pipeline"
        assert pipeline_call.kwargs["version"] == "9.9.9"
        assert pipeline_call.kwargs["result"] == "https://example/actions/runs/1"
