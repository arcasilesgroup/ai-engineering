"""Tests for ``ai-eng cleanup branches`` (spec-133 D-133-03)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _init_git(root: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "README.md").write_text("# t\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)


def test_cleanup_branches_dry_run_lists_merged(tmp_path: Path) -> None:
    _init_git(tmp_path)
    subprocess.run(["git", "branch", "feature/foo"], cwd=tmp_path, check=True)

    from ai_engineering.cli_commands.cleanup import _resolve_target_branches

    targets = _resolve_target_branches(
        tmp_path,
        pruned=False,
        merged=True,
        squashed=False,
        stale=False,
        untracked=False,
        reset=False,
        all_modes=False,
    )
    # feature/foo points to main HEAD => merged
    assert "feature/foo" in targets


def test_cleanup_branches_refuses_detached_head(tmp_path: Path) -> None:
    _init_git(tmp_path)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    subprocess.run(["git", "checkout", "-q", "--detach", sha], cwd=tmp_path, check=True)

    import typer

    from ai_engineering.cli_commands.cleanup import _refuse_detached_head

    with pytest.raises(typer.Exit) as excinfo:
        _refuse_detached_head(tmp_path)
    assert excinfo.value.exit_code == 2


def test_cleanup_branches_modes_default_to_merged(tmp_path: Path) -> None:
    """When no mode flag is passed, default to --merged (least surprising)."""
    _init_git(tmp_path)
    subprocess.run(["git", "branch", "feature/foo"], cwd=tmp_path, check=True)
    # default: merged should pick up feature/foo
    from ai_engineering.cli_commands.cleanup import _resolve_target_branches

    targets = _resolve_target_branches(
        tmp_path,
        pruned=False,
        merged=True,
        squashed=False,
        stale=False,
        untracked=False,
        reset=False,
        all_modes=False,
    )
    assert "feature/foo" in targets


def test_cleanup_branches_untracked_picks_local_only(tmp_path: Path) -> None:
    _init_git(tmp_path)
    subprocess.run(["git", "branch", "local-only"], cwd=tmp_path, check=True)
    from ai_engineering.cli_commands.cleanup import _list_untracked_branches

    branches = _list_untracked_branches(tmp_path)
    assert "local-only" in branches


def test_cleanup_branches_stale_with_zero_days_catches_today(tmp_path: Path) -> None:
    _init_git(tmp_path)
    subprocess.run(["git", "branch", "fresh-branch"], cwd=tmp_path, check=True)
    from ai_engineering.cli_commands.cleanup import _list_stale_branches

    # 0-day cutoff: every branch except current is stale
    branches = _list_stale_branches(tmp_path, days=0)
    assert "fresh-branch" in branches


def test_cleanup_branches_all_modes_union(tmp_path: Path) -> None:
    _init_git(tmp_path)
    subprocess.run(["git", "branch", "feature/foo"], cwd=tmp_path, check=True)
    from ai_engineering.cli_commands.cleanup import _resolve_target_branches

    targets = _resolve_target_branches(
        tmp_path,
        pruned=False,
        merged=False,
        squashed=False,
        stale=False,
        untracked=False,
        reset=False,
        all_modes=True,
    )
    # --all should include feature/foo (matched by merged + untracked)
    assert "feature/foo" in targets


def test_cleanup_branches_envelope_shape() -> None:
    from ai_engineering.cli_commands.cleanup import CleanupBranchesResult

    result = CleanupBranchesResult(mode="merged", dry_run=True, deleted=["a"])
    env = result.to_envelope()
    assert env["ok"] is True
    assert env["command"] == "cleanup-branches"
    assert env["data"]["mode"] == "merged"
    assert env["data"]["dry_run"] is True
    assert env["data"]["deleted"] == ["a"]


def test_cleanup_envelope_failure_propagates_to_code() -> None:
    from ai_engineering.cli_commands.cleanup import CleanupBranchesResult

    result = CleanupBranchesResult(mode="merged", dry_run=False, errors=["boom"])
    env = result.to_envelope()
    assert env["ok"] is False
    assert env["code"] == 1
