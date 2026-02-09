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


def test_docs_contract_check_requires_metadata(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    doc = tmp_path / "backlog.md"
    doc.write_text("# Backlog\n", encoding="utf-8")

    monkeypatch.setattr(gates, "DOC_CONTRACT_FILES", ("backlog.md",))

    ok, output = gates._run_docs_contract_check(tmp_path)

    assert not ok
    assert "missing '## Update Metadata'" in output


def test_docs_contract_check_passes_with_required_fields(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    document_metadata = (
        "## Document Metadata\n\n"
        "- Doc ID: TEST\n"
        "- Owner: team\n"
        "- Status: active\n"
        "- Last reviewed: 2026-02-09\n"
    )
    update_metadata = (
        "## Update Metadata\n\n"
        "- Rationale: keep docs aligned\n"
        "- Expected gain: deterministic checks\n"
        "- Potential impact: none\n"
    )
    doc = tmp_path / "backlog.md"
    doc.write_text(
        f"# Backlog\n\n{document_metadata}- Source of truth: `backlog.md`\n\n{update_metadata}",
        encoding="utf-8",
    )

    monkeypatch.setattr(gates, "DOC_CONTRACT_FILES", ("backlog.md",))

    ok, output = gates._run_docs_contract_check(tmp_path)

    assert ok
    assert "passed" in output


def test_pre_commit_reports_docs_contract_failure(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gates, "repo_root", lambda: Path.cwd())
    monkeypatch.setattr(gates, "current_branch", lambda _root: "feature/x")
    monkeypatch.setattr(gates, "discover_protected_branches", lambda _root: {"main", "master"})
    monkeypatch.setattr(gates, "_run_tool", lambda _root, _tool, _args: (True, "ok"))
    monkeypatch.setattr(gates, "_run_docs_contract_check", lambda _root: (False, "docs missing"))

    ok, messages = gates.run_pre_commit()

    assert not ok
    assert any("docs-contract" in message for message in messages)


def test_run_tool_attempts_auto_remediation(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gates, "_tool_path", lambda _root, _tool: None)
    monkeypatch.setattr(
        gates, "_attempt_tool_remediation", lambda _root, _tool: (False, "install failed")
    )

    ok, output = gates._run_tool(Path.cwd(), "ruff", ["check", "src"])

    assert not ok
    assert "missing required tool" in output


def test_pre_push_surfaces_missing_tool_failure(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(gates, "repo_root", lambda: Path.cwd())
    monkeypatch.setattr(gates, "current_branch", lambda _root: "feature/x")
    monkeypatch.setattr(gates, "discover_protected_branches", lambda _root: {"main", "master"})

    def _fake_run_tool(_root: Path, tool: str, _args: list[str]) -> tuple[bool, str]:
        if tool == "semgrep":
            return False, "missing required tool: semgrep; auto-remediation failed"
        return True, "ok"

    monkeypatch.setattr(gates, "_run_tool", _fake_run_tool)

    ok, messages = gates.run_pre_push()

    assert not ok
    assert any("semgrep" in message for message in messages)
