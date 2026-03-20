"""Integration tests for install-to-operational readiness flows."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ai_engineering.installer import service
from ai_engineering.installer.service import install
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import InstallManifest
from ai_engineering.vcs.protocol import VcsContext, VcsResult

pytestmark = pytest.mark.integration


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
        lambda stacks: SimpleNamespace(tools=[]),
    )
    monkeypatch.setattr(
        service,
        "ensure_tool",
        lambda tool: SimpleNamespace(available=available, detail=f"{tool}-ok"),
    )


def test_install_operational_ready_github_cli(tmp_path: Path, monkeypatch: object) -> None:
    _patch_tooling(monkeypatch)
    monkeypatch.setattr(
        service,
        "get_provider",
        lambda target: _StubProvider(available=True, auth_ok=True, policy_ok=True),
    )

    result = install(tmp_path, vcs_provider="github")

    manifest = read_json_model(
        tmp_path / ".ai-engineering" / "state" / "install-manifest.json",
        InstallManifest,
    )

    assert result.readiness_status == "READY"
    assert manifest.operational_readiness.status == "READY"
    assert manifest.tooling_readiness.gh.mode == "cli"
    assert manifest.tooling_readiness.gh.authenticated is True
    assert manifest.branch_policy.applied is True


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

    manifest = read_json_model(
        tmp_path / ".ai-engineering" / "state" / "install-manifest.json",
        InstallManifest,
    )

    assert result.readiness_status == "READY WITH MANUAL STEPS"
    assert manifest.operational_readiness.status == "READY WITH MANUAL STEPS"
    assert manifest.tooling_readiness.az.mode == "api"
    assert manifest.tooling_readiness.az.authenticated is False
    assert manifest.branch_policy.applied is False
    assert manifest.branch_policy.manual_guide
    assert "Manual Branch Policy Setup" in manifest.branch_policy.manual_guide
