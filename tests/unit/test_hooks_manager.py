"""Unit tests for managed git hook generation and readiness."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.hooks import manager


def test_install_placeholder_hooks_writes_framework_managed_scripts(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    manager.install_placeholder_hooks(repo)

    for hook in manager.HOOKS:
        hook_path = repo / ".git" / "hooks" / hook
        assert hook_path.exists()
        content = hook_path.read_text(encoding="utf-8")
        assert "ai-engineering managed hook" in content
        assert "lefthook" not in content


def test_detect_hook_readiness_reports_conflict_for_lefthook_wrapper(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True)
    for hook in manager.HOOKS:
        path = hooks / hook
        path.write_text("#!/bin/sh\nlefthook run pre-commit\n", encoding="utf-8")
        path.chmod(0o755)

    payload = manager.detect_hook_readiness(repo)

    assert payload["installed"] is True
    assert payload["managedByFramework"] is False
    assert payload["conflictDetected"] is True
