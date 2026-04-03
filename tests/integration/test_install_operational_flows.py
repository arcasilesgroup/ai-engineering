"""Integration tests for install-to-operational readiness flows."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering.installer import service
from ai_engineering.installer.phases import PhaseResult
from ai_engineering.installer.phases.pipeline import PipelineSummary
from ai_engineering.installer.phases.tools import ToolsPhase
from ai_engineering.installer.service import install, install_with_pipeline
from ai_engineering.state.service import load_install_state
from ai_engineering.vcs.protocol import VcsContext, VcsResult


class _StubProvider:
    def __init__(self, *, available: bool, auth_ok: bool, policy_ok: bool) -> None:
        self._available = available
        self._auth_ok = auth_ok
        self._policy_ok = policy_ok

    def is_available(self) -> bool:
        return self._available

    def check_auth(self, ctx: VcsContext) -> VcsResult:  # pragma: no cover - exercised in flow
        _ = ctx
        return VcsResult(success=self._auth_ok, output="auth")

    def apply_branch_policy(
        self,
        ctx: VcsContext,
        *,
        branch: str,
        required_checks: list[str],
    ) -> VcsResult:  # pragma: no cover - exercised in flow
        _ = (ctx, branch, required_checks)
        return VcsResult(success=self._policy_ok, output="policy")


def _patch_tooling(monkeypatch: object, *, available: bool = True) -> None:
    monkeypatch.setattr(
        service,
        "check_tools_for_stacks",
        lambda *args, **kwargs: SimpleNamespace(tools=[]),
    )
    monkeypatch.setattr(
        service,
        "ensure_tool",
        lambda tool, **_kw: SimpleNamespace(available=available, detail=f"{tool}-ok"),
    )


def test_install_operational_ready_github_cli(tmp_path: Path, monkeypatch: object) -> None:
    _patch_tooling(monkeypatch)
    monkeypatch.setattr(
        service,
        "get_provider",
        lambda target: _StubProvider(available=True, auth_ok=True, policy_ok=True),
    )

    result = install(tmp_path, vcs_provider="github")

    state_dir = tmp_path / ".ai-engineering" / "state"
    state = load_install_state(state_dir)

    assert result.readiness_status == "READY"
    assert state.operational_readiness.status == "READY"
    assert state.tooling.get("gh") is not None
    assert state.tooling["gh"].authenticated is True
    assert state.branch_policy.applied is True


def test_install_operational_ready_with_manual_steps_azure_fallback(
    tmp_path: Path,
    monkeypatch: object,
) -> None:
    _patch_tooling(monkeypatch)
    monkeypatch.setattr(
        service,
        "get_provider",
        lambda target: _StubProvider(available=False, auth_ok=False, policy_ok=False),
    )

    result = install(tmp_path, vcs_provider="azure_devops")

    state_dir = tmp_path / ".ai-engineering" / "state"
    state = load_install_state(state_dir)

    assert result.readiness_status == "READY WITH MANUAL STEPS"
    assert state.operational_readiness.status == "READY WITH MANUAL STEPS"
    assert state.branch_policy.applied is False
    assert state.branch_policy.manual_guide is not None
    assert "Manual Branch Policy Setup" in state.branch_policy.manual_guide


# ---------------------------------------------------------------------------
# install_with_pipeline tests
# ---------------------------------------------------------------------------


def test_pipeline_install_writes_operational_readiness(tmp_path: Path) -> None:
    """install_with_pipeline sets operational_readiness.status to non-pending."""
    _result, summary = install_with_pipeline(tmp_path, vcs_provider="github")

    state_dir = tmp_path / ".ai-engineering" / "state"
    state = load_install_state(state_dir)

    assert isinstance(summary, PipelineSummary)
    assert state.operational_readiness.status != "pending"


def test_pipeline_dry_run_does_not_write_state(tmp_path: Path) -> None:
    """install_with_pipeline in dry_run skips all file writes."""
    _result, summary = install_with_pipeline(tmp_path, dry_run=True)

    state_path = tmp_path / ".ai-engineering" / "state" / "install-state.json"
    assert not state_path.exists()
    assert summary.dry_run is True


def test_pipeline_auto_detects_repair_mode(tmp_path: Path) -> None:
    """Second call auto-detects REPAIR mode when state already exists."""
    install_with_pipeline(tmp_path)
    result, _summary = install_with_pipeline(tmp_path)
    assert result is not None


def test_pipeline_writes_ready_with_manual_steps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """READY WITH MANUAL STEPS is written when ToolsPhase reports missing tools."""

    def _execute_with_warning(self: ToolsPhase, plan: object, context: object) -> PhaseResult:
        r = PhaseResult(phase_name=self.name)
        r.warnings.append("Tool 'gh' not found.")
        return r

    monkeypatch.setattr(ToolsPhase, "execute", _execute_with_warning)

    install_with_pipeline(tmp_path, vcs_provider="github")

    state_dir = tmp_path / ".ai-engineering" / "state"
    state = load_install_state(state_dir)

    assert state.operational_readiness.status == "READY WITH MANUAL STEPS"
    assert len(state.operational_readiness.pending_steps) > 0
