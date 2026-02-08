"""Integration tests for command workflows with real git repositories."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ai_engineering.commands import workflows
from ai_engineering.state.defaults import decision_store_default
from ai_engineering.state.io import write_json


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)


def test_commit_workflow_creates_commit_on_feature_branch(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _git(temp_repo, "init")
    _git(temp_repo, "config", "user.name", "test")
    _git(temp_repo, "config", "user.email", "test@example.com")
    _git(temp_repo, "checkout", "-b", "feature/runtime")

    (temp_repo / "README.md").write_text("hello\n", encoding="utf-8")

    monkeypatch.setattr(workflows, "run_pre_commit", lambda: (True, ["ok"]))

    ok, notes = workflows.run_commit_workflow(message="feat: runtime commit", push=False)

    assert ok
    assert any("commit" in note.lower() for note in notes)
    log = _git(temp_repo, "log", "--oneline", "-1")
    assert "feat: runtime commit" in log.stdout


def test_pr_only_defer_persists_decision_without_upstream(temp_repo: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _git(temp_repo, "init")
    _git(temp_repo, "checkout", "-b", "feature/pr-only")

    state_root = temp_repo / ".ai-engineering" / "state"
    state_root.mkdir(parents=True)
    write_json(state_root / "decision-store.json", decision_store_default())
    (state_root / "audit-log.ndjson").write_text("", encoding="utf-8")

    monkeypatch.setattr(workflows, "has_remote_upstream", lambda _root: False)

    ok, notes = workflows.run_pr_only_workflow(
        title="Test PR",
        body="Body",
        mode="defer-pr",
        record_decision=True,
    )

    assert ok
    assert any("defer-pr selected" in note for note in notes)

    decision_store_text = (state_root / "decision-store.json").read_text(encoding="utf-8")
    assert "PR_ONLY_UNPUSHED_BRANCH_MODE" in decision_store_text
