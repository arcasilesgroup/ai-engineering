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


def test_cleanup_branches_resolver_merged_mode(tmp_path: Path) -> None:
    """The resolver returns merged branches when --merged is set explicitly."""
    _init_git(tmp_path)
    subprocess.run(["git", "branch", "feature/foo"], cwd=tmp_path, check=True)
    # explicit --merged should pick up feature/foo
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


def test_cleanup_branches_no_flag_is_plan_only_deletes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-149-02: no mode flag must NOT delete (plan-only). Destructive default removed.

    Previously a bare ``cleanup branches`` set ``merged=True`` and deleted. Now a
    no-flag invocation computes a plan and deletes nothing; the operator must pass
    an explicit mode flag (or ``--dry-run``) to act.
    """
    _init_git(tmp_path)
    subprocess.run(["git", "branch", "feature/foo"], cwd=tmp_path, check=True)

    import ai_engineering.cli_commands.cleanup as cl

    monkeypatch.setattr(cl, "resolve_project_root", lambda _target=None: tmp_path)
    deleted_calls: list[list[str]] = []

    def _spy_delete(
        root: Path, branches: list[str], **kwargs: object
    ) -> tuple[list[str], list[str]]:
        deleted_calls.append(list(branches))
        return [], []

    monkeypatch.setattr(cl, "delete_branches", _spy_delete)

    # No mode flag, not --dry-run: must compute a plan but delete nothing.
    cl.cleanup_branches_cmd()

    assert deleted_calls == [], "no-flag invocation must not call delete_branches (plan-only)"
    out = subprocess.run(
        ["git", "branch", "--format=%(refname:short)"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert "feature/foo" in out


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
