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
    review = tmp_path / "review.md"
    review.write_text(
        "# Review\n\n## Backlog and Delivery Docs Pre-Merge Checklist\n"
        "- required gates: `unit` `integration` `e2e` `ruff` `ty` `gitleaks` `semgrep` `pip-audit`\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(gates, "DOC_CONTRACT_FILES", ("backlog.md", "review.md"))
    monkeypatch.setattr(gates, "DOC_CONTRACT_REVIEW_FILE", "review.md")

    ok, output = gates._run_docs_contract_check(tmp_path)

    assert not ok
    assert "missing '## Document Metadata'" in output


def test_docs_contract_check_passes_with_required_fields(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    metadata_block = (
        "## Document Metadata\n\n"
        "- Doc ID: TEST\n"
        "- Owner: team\n"
        "- Status: active\n"
        "- Last reviewed: 2026-02-09\n"
    )
    doc = tmp_path / "backlog.md"
    doc.write_text(
        f"# Backlog\n\n{metadata_block}- Source of truth: `backlog.md`\n",
        encoding="utf-8",
    )
    review = tmp_path / "review.md"
    review.write_text(
        "# Review\n\n"
        f"{metadata_block}"
        "- Source of truth: `review.md`\n\n"
        "## Backlog and Delivery Docs Pre-Merge Checklist\n"
        "- required gates: `unit` `integration` `e2e` `ruff` `ty` `gitleaks` `semgrep` `pip-audit`\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(gates, "DOC_CONTRACT_FILES", ("backlog.md", "review.md"))
    monkeypatch.setattr(gates, "DOC_CONTRACT_REVIEW_FILE", "review.md")

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


def test_attempt_uv_install_tries_brew(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import shutil

    installed = False

    def _which(cmd: str) -> str | None:
        if cmd == "brew":
            return "/usr/local/bin/brew"
        if cmd == "uv" and installed:
            return "/usr/local/bin/uv"
        return None

    monkeypatch.setattr(shutil, "which", _which)
    commands_run: list[list[str]] = []

    def _fake_run_raw(_root: Path, command: list[str]) -> tuple[bool, str]:
        nonlocal installed
        commands_run.append(command)
        installed = True
        return True, "ok"

    monkeypatch.setattr(gates, "_run_raw", _fake_run_raw)

    ok, _ = gates._attempt_uv_install(Path.cwd())

    assert ok
    assert commands_run[0] == ["brew", "install", "uv"]


def test_attempt_uv_install_fallback_curl(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import shutil

    monkeypatch.setattr(
        shutil,
        "which",
        lambda cmd: (
            "/usr/bin/curl" if cmd == "curl" else ("/usr/local/bin/uv" if cmd == "uv" else None)
        ),
    )
    commands_run: list[list[str]] = []

    def _fake_run_raw(_root: Path, command: list[str]) -> tuple[bool, str]:
        commands_run.append(command)
        return True, "ok"

    monkeypatch.setattr(gates, "_run_raw", _fake_run_raw)

    ok, _ = gates._attempt_uv_install(Path.cwd())

    assert ok
    assert any("curl" in " ".join(cmd) for cmd in commands_run)


def test_attempt_tool_remediation_handles_uv(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import shutil

    monkeypatch.setattr(gates, "_attempt_uv_install", lambda _root: (True, "installed"))
    monkeypatch.setattr(shutil, "which", lambda _cmd: "/usr/local/bin/uv")

    ok, msg = gates._attempt_tool_remediation(Path.cwd(), "uv")

    assert ok
    assert "auto-remediation installed uv" in msg


def test_attempt_tool_remediation_uv_failure(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import shutil

    monkeypatch.setattr(gates, "_attempt_uv_install", lambda _root: (False, "no manager"))
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)

    ok, msg = gates._attempt_tool_remediation(Path.cwd(), "uv")

    assert not ok
    assert "auto-remediation failed for uv" in msg
