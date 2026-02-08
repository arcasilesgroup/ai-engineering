"""Unit tests for governance gate policy behavior."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.policy import gates


def test_pre_commit_blocks_on_protected_branch(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gates, "repo_root", lambda: Path.cwd())
    monkeypatch.setattr(gates, "current_branch", lambda _root: "main")
    monkeypatch.setattr(gates, "discover_protected_branches", lambda _root: {"main", "master"})

    ok, messages = gates.run_pre_commit()

    assert not ok
    assert any("protected branch" in message for message in messages)


def test_pre_push_blocks_on_protected_branch(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gates, "repo_root", lambda: Path.cwd())
    monkeypatch.setattr(gates, "current_branch", lambda _root: "master")
    monkeypatch.setattr(gates, "discover_protected_branches", lambda _root: {"main", "master"})

    ok, messages = gates.run_pre_push()

    assert not ok
    assert any("protected branch" in message for message in messages)


def test_pre_commit_passes_when_tools_pass(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gates, "repo_root", lambda: Path.cwd())
    monkeypatch.setattr(gates, "current_branch", lambda _root: "feature/x")
    monkeypatch.setattr(gates, "discover_protected_branches", lambda _root: {"main", "master"})
    monkeypatch.setattr(gates, "_run_tool", lambda _root, _tool, _args: (True, "ok"))

    ok, messages = gates.run_pre_commit()

    assert ok
    assert "passed" in messages[0]


def test_commit_msg_requires_message(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gates, "repo_root", lambda: Path.cwd())
    monkeypatch.setattr(gates, "current_branch", lambda _root: "feature/x")
    monkeypatch.setattr(gates, "discover_protected_branches", lambda _root: {"main", "master"})
    message_file = tmp_path / "COMMIT_EDITMSG"
    message_file.write_text("\n", encoding="utf-8")

    ok, messages = gates.run_commit_msg(message_file)

    assert not ok
    assert any("cannot be empty" in message for message in messages)


def test_pre_push_reports_remediation_for_failures(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gates, "repo_root", lambda: Path.cwd())
    monkeypatch.setattr(gates, "current_branch", lambda _root: "feature/x")
    monkeypatch.setattr(gates, "discover_protected_branches", lambda _root: {"main", "master"})
    monkeypatch.setattr(gates, "_run_tool", lambda _root, _tool, _args: (False, "failure"))

    ok, messages = gates.run_pre_push()

    assert not ok
    assert any("remediation:" in message for message in messages)


def test_gate_requirements_includes_stages(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gates, "discover_protected_branches", lambda _root: {"main", "release"})

    payload = gates.gate_requirements(Path.cwd())

    assert "stages" in payload
    stages = payload["stages"]
    assert isinstance(stages, dict)
    assert "pre-commit" in stages
    assert "pre-push" in stages
