"""Unit tests for release orchestrator high-level behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.release.orchestrator import (
    ReleaseConfig,
    ReleaseState,
    execute_release,
)
from ai_engineering.vcs.protocol import (
    CreateTagContext,
    PipelineStatusContext,
    VcsContext,
    VcsResult,
)

pytestmark = pytest.mark.unit


class _FakeProvider:
    def create_pr(self, ctx: VcsContext) -> VcsResult:
        del ctx
        return VcsResult(success=True, url="https://example/pr/1")

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
        return VcsResult(success=True)

    def get_pipeline_status(self, ctx: PipelineStatusContext) -> VcsResult:
        del ctx
        return VcsResult(success=True, output="[]")


class _FixedClock:
    def utcnow(self) -> datetime:
        return datetime(2026, 3, 2, tzinfo=UTC)


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
