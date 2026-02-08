"""Unit tests for command contract workflows."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.commands import workflows
from ai_engineering.state.defaults import decision_store_default
from ai_engineering.state.io import write_json


def test_commit_workflow_blocks_on_protected_branch(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(workflows, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(workflows, "current_branch", lambda _root: "main")

    ok, notes = workflows.run_commit_workflow(message="test", push=False)

    assert not ok
    assert any("protected branch" in note for note in notes)


def test_pr_only_defer_when_unpushed(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    write_json(state / "decision-store.json", decision_store_default())
    (state / "audit-log.ndjson").write_text("", encoding="utf-8")

    monkeypatch.setattr(workflows, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(workflows, "current_branch", lambda _root: "feature/x")
    monkeypatch.setattr(workflows, "has_remote_upstream", lambda _root: False)

    ok, notes = workflows.run_pr_only_workflow(
        title="T",
        body="B",
        mode="defer-pr",
        record_decision=True,
    )

    assert ok
    assert any("defer-pr selected" in note for note in notes)


def test_pr_only_export_payload(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    write_json(state / "decision-store.json", decision_store_default())
    (state / "audit-log.ndjson").write_text("", encoding="utf-8")

    monkeypatch.setattr(workflows, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(workflows, "current_branch", lambda _root: "feature/y")
    monkeypatch.setattr(workflows, "has_remote_upstream", lambda _root: False)

    ok, notes = workflows.run_pr_only_workflow(
        title="Title",
        body="Body",
        mode="export-pr-payload",
        record_decision=False,
    )

    assert ok
    assert any("export-pr-payload" in note for note in notes)


def test_pr_only_attempt_anyway_returns_success_on_pr_error(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    write_json(state / "decision-store.json", decision_store_default())
    (state / "audit-log.ndjson").write_text("", encoding="utf-8")

    monkeypatch.setattr(workflows, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(workflows, "current_branch", lambda _root: "feature/z")
    monkeypatch.setattr(workflows, "has_remote_upstream", lambda _root: True)
    monkeypatch.setattr(workflows, "create_pr", lambda _root, _title, _body: (False, "error"))

    ok, notes = workflows.run_pr_only_workflow(
        title="Title",
        body="Body",
        mode="attempt-pr-anyway",
        record_decision=False,
    )

    assert ok
    assert any("continued" in note for note in notes)


def test_pr_workflow_enables_auto_complete(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    write_json(state / "decision-store.json", decision_store_default())
    (state / "audit-log.ndjson").write_text("", encoding="utf-8")

    monkeypatch.setattr(workflows, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(workflows, "current_branch", lambda _root: "feature/auto")
    monkeypatch.setattr(workflows, "run_pre_commit", lambda: (True, ["ok"]))
    monkeypatch.setattr(workflows, "run_pre_push", lambda: (True, ["ok"]))
    monkeypatch.setattr(workflows, "stage_all", lambda _root: None)
    monkeypatch.setattr(workflows, "has_staged_changes", lambda _root: True)
    monkeypatch.setattr(workflows, "create_commit", lambda _root, _m: (True, "commit created"))
    monkeypatch.setattr(workflows, "push_current_branch", lambda _root: (True, "push succeeded"))
    monkeypatch.setattr(workflows, "create_pr", lambda _root, _t, _b: (True, "pr created"))
    monkeypatch.setattr(
        workflows,
        "enable_pr_auto_complete",
        lambda _root: (True, "auto-complete enabled"),
    )

    ok, notes = workflows.run_pr_workflow(message="feat: x", title="T", body="B")

    assert ok
    assert any("auto-complete enabled" in note for note in notes)


def test_pr_only_enables_auto_complete_on_created_pr(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    state = tmp_path / ".ai-engineering" / "state"
    state.mkdir(parents=True)
    write_json(state / "decision-store.json", decision_store_default())
    (state / "audit-log.ndjson").write_text("", encoding="utf-8")

    monkeypatch.setattr(workflows, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(workflows, "current_branch", lambda _root: "feature/auto-pr-only")
    monkeypatch.setattr(workflows, "has_remote_upstream", lambda _root: True)
    monkeypatch.setattr(workflows, "create_pr", lambda _root, _t, _b: (True, "pr created"))
    monkeypatch.setattr(
        workflows,
        "enable_pr_auto_complete",
        lambda _root: (True, "auto-complete enabled"),
    )

    ok, notes = workflows.run_pr_only_workflow(
        title="Title",
        body="Body",
        mode="attempt-pr-anyway",
        record_decision=False,
    )

    assert ok
    assert any("auto-complete enabled" in note for note in notes)
