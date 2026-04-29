"""Tests for spec-113 G-9 / D-113-12: branch-policy first-install grace period."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.runtime import branch_policy
from ai_engineering.state.models import InstallState


def _git_inside_main(_args: list[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
    """Stub _run_git to report inside-worktree=true and HEAD=main."""
    if _args[0] == "rev-parse":
        return subprocess.CompletedProcess(args=_args, returncode=0, stdout="true\n", stderr="")
    if _args[0] == "symbolic-ref":
        return subprocess.CompletedProcess(args=_args, returncode=0, stdout="main\n", stderr="")
    return subprocess.CompletedProcess(args=_args, returncode=1, stdout="", stderr="")


def _ctx_with_install_at(tmp_path: Path, installed_at: datetime | None) -> DoctorContext:
    state = InstallState(installed_at=installed_at) if installed_at is not None else None
    return DoctorContext(target=tmp_path, install_state=state)


def test_grace_period_suppresses_protected_branch_warn(tmp_path: Path) -> None:
    """Within 5 minutes of install, protected branch surface is OK."""
    fresh = datetime.now(tz=UTC) - timedelta(minutes=2)
    ctx = _ctx_with_install_at(tmp_path, fresh)
    with patch.object(branch_policy, "_run_git", side_effect=_git_inside_main):
        results = branch_policy.check(ctx)
    assert len(results) == 1
    assert results[0].status == CheckStatus.OK
    assert "grace period" in results[0].message
    assert "main" in results[0].message


def test_after_grace_period_warns_again(tmp_path: Path) -> None:
    """After 5 minutes the WARN comes back."""
    stale = datetime.now(tz=UTC) - timedelta(minutes=10)
    ctx = _ctx_with_install_at(tmp_path, stale)
    with patch.object(branch_policy, "_run_git", side_effect=_git_inside_main):
        results = branch_policy.check(ctx)
    assert results[0].status == CheckStatus.WARN
    assert "protected branch" in results[0].message


def test_no_install_state_uses_current_warn(tmp_path: Path) -> None:
    """When install_state is None, no grace period applies."""
    ctx = _ctx_with_install_at(tmp_path, None)
    with patch.object(branch_policy, "_run_git", side_effect=_git_inside_main):
        results = branch_policy.check(ctx)
    assert results[0].status == CheckStatus.WARN


def test_grace_period_only_protects_protected_branches(tmp_path: Path) -> None:
    """A feature branch within grace period is still OK (no protected-branch path)."""
    fresh = datetime.now(tz=UTC) - timedelta(seconds=30)
    ctx = _ctx_with_install_at(tmp_path, fresh)

    def _git_inside_feature(_args: list[str], _cwd: Path) -> subprocess.CompletedProcess[str]:
        if _args[0] == "rev-parse":
            return subprocess.CompletedProcess(args=_args, returncode=0, stdout="true\n", stderr="")
        if _args[0] == "symbolic-ref":
            return subprocess.CompletedProcess(
                args=_args, returncode=0, stdout="feat/spec-113\n", stderr=""
            )
        return subprocess.CompletedProcess(args=_args, returncode=1, stdout="", stderr="")

    with patch.object(branch_policy, "_run_git", side_effect=_git_inside_feature):
        results = branch_policy.check(ctx)
    assert results[0].status == CheckStatus.OK
    assert "feat/spec-113" in results[0].message
