"""Tests for the spec-182 governed-git advisory hook.

The hook is a NON-BLOCKING PreToolUse:Bash advisor: when the agent issues a
raw ``git commit`` / ``git push`` / ``gh pr create`` it ALLOWS the call and
injects a ``hookSpecificOutput`` nudge steering toward /ai-commit and /ai-pr.
It never denies (contrast: no-verify-guard.py).

Mirrors the load/ctx/event harness of ``test_spec_121_hooks.py``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS = REPO / ".ai-engineering" / "scripts" / "hooks"


def _load(name: str, path: Path):
    sys.path.insert(0, str(HOOKS))
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _ctx(project_root: Path, *, data: dict[str, Any], event_name: str = "PreToolUse"):
    from _lib.hook_context import HookContext

    return HookContext(
        engine="claude_code",
        project_root=project_root,
        session_id=data.get("session_id"),
        event_name=event_name,
        event_name_raw=event_name,
        data=data,
    )


def _events(project: Path) -> list[dict[str, Any]]:
    path = project / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _advisories(project: Path) -> list[dict[str, Any]]:
    return [e for e in _events(project) if e.get("component") == "hook.governed-git-advisor"]


@pytest.fixture
def mod():
    return _load("aieng_governed_git_advisor", HOOKS / "governed-git-advisor.py")


def _run(mod, project, monkeypatch, command, *, tool_name="Bash", extra_data=None):
    """Drive main() with a Bash command; return (parsed_stdout_or_None)."""
    data: dict[str, Any] = {"tool_name": tool_name, "tool_input": {"command": command}}
    if extra_data:
        data.update(extra_data)
    ctx = _ctx(project, data=data)
    monkeypatch.setattr(mod, "get_hook_context", lambda: ctx)
    return ctx


def _stdout_json(capsys) -> dict[str, Any] | None:
    out = capsys.readouterr().out.strip()
    if not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def _advisory_text(payload: dict[str, Any] | None) -> str | None:
    if not payload:
        return None
    hso = payload.get("hookSpecificOutput")
    if not isinstance(hso, dict):
        return None
    return hso.get("additionalContext")


# --- detection: the three governed verbs ------------------------------------


def test_git_commit_emits_advisory_envelope(mod, project, monkeypatch, capsys):
    _run(mod, project, monkeypatch, "git commit -m 'wip'")
    mod.main()
    payload = _stdout_json(capsys)
    assert payload is not None
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "allow"
    assert isinstance(hso["additionalContext"], str) and hso["additionalContext"]


def test_git_push_routes_to_ai_commit(mod, project, monkeypatch, capsys):
    _run(mod, project, monkeypatch, "git push origin main")
    mod.main()
    text = _advisory_text(_stdout_json(capsys))
    assert text is not None
    assert "/ai-commit" in text


def test_gh_pr_create_routes_to_ai_pr(mod, project, monkeypatch, capsys):
    _run(mod, project, monkeypatch, "gh pr create --fill")
    mod.main()
    text = _advisory_text(_stdout_json(capsys))
    assert text is not None
    assert "/ai-pr" in text


def test_advisory_names_all_governance_terms(mod, project, monkeypatch, capsys):
    # Goal acceptance: the nudge must name the concrete governance lost so a
    # later message simplification cannot silently gut the steer.
    for command in ("git commit -m x", "git push", "gh pr create"):
        _run(mod, project, monkeypatch, command)
        mod.main()
        text = _advisory_text(_stdout_json(capsys)) or ""
        for term in ("secret scan", "docs gate", "spec consolidation", "audit chain"):
            assert term in text, f"{term!r} missing from advisory for {command!r}"


# --- D-182-07 detection scope -----------------------------------------------


def test_compound_command_is_detected(mod, project, monkeypatch, capsys):
    _run(mod, project, monkeypatch, "git add . && git commit -m x && git push")
    mod.main()
    assert _advisory_text(_stdout_json(capsys)) is not None


def test_git_dash_c_path_prefix_is_detected(mod, project, monkeypatch, capsys):
    _run(mod, project, monkeypatch, "git -C /tmp/repo commit -m x")
    mod.main()
    assert _advisory_text(_stdout_json(capsys)) is not None


@pytest.mark.parametrize(
    "command",
    [
        "gh pr create --fill",
        "gh pr create -R owner/repo",
        "gh -R owner/repo pr create",
        "gh --repo owner/repo pr create",
        "gh --repo=owner/repo pr create",
    ],
)
def test_gh_pr_create_value_flag_forms_detected(mod, project, monkeypatch, capsys, command):
    # gh global value flags (-R/--repo) before the subcommand must not defeat
    # detection (symmetry with git's -C handling).
    _run(mod, project, monkeypatch, command)
    mod.main()
    text = _advisory_text(_stdout_json(capsys))
    assert text is not None and "/ai-pr" in text


def test_non_git_command_passes_through(mod, project, monkeypatch, capsys):
    # Hot-path pre-screen: a command with neither "git" nor "gh" never reaches
    # shlex and never nudges.
    _run(mod, project, monkeypatch, "ls -la && cat README.md")
    mod.main()
    assert _advisory_text(_stdout_json(capsys)) is None
    assert _advisories(project) == []


# --- no false positives -----------------------------------------------------


@pytest.mark.parametrize("command", ["git log", "git status", "git diff --stat", "git add ."])
def test_readonly_and_structural_git_passes_through(mod, project, monkeypatch, capsys, command):
    _run(mod, project, monkeypatch, command)
    mod.main()
    assert _advisory_text(_stdout_json(capsys)) is None
    assert _advisories(project) == []


def test_non_bash_tool_passes_through(mod, project, monkeypatch, capsys):
    _run(mod, project, monkeypatch, "git commit -m x", tool_name="Read")
    mod.main()
    assert _advisory_text(_stdout_json(capsys)) is None
    assert _advisories(project) == []


# --- ledger (D-182-05) ------------------------------------------------------


def test_detection_emits_ledger_event(mod, project, monkeypatch, capsys):
    _run(mod, project, monkeypatch, "git commit -m x")
    mod.main()
    advisories = _advisories(project)
    assert len(advisories) == 1
    detail = advisories[0]["detail"]
    assert detail["operation"] == "governed_git_advisory"
    assert detail["verb"] == "git commit"
    assert detail["session_seq"] in {"first", "repeat", "unknown"}


# --- D-182-04 toggle + fail-open --------------------------------------------


def test_disable_toggle_suppresses_advisory(mod, project, monkeypatch, capsys):
    monkeypatch.setenv("AIENG_GOVERNED_GIT_ADVISOR_DISABLED", "1")
    _run(mod, project, monkeypatch, "git commit -m x")
    mod.main()
    assert _advisory_text(_stdout_json(capsys)) is None
    assert _advisories(project) == []


def test_malformed_tool_input_does_not_raise(mod, project, monkeypatch, capsys):
    # tool_input is not a dict and not a JSON string → fail-open passthrough.
    ctx = _ctx(project, data={"tool_name": "Bash", "tool_input": ["not", "a", "dict"]})
    monkeypatch.setattr(mod, "get_hook_context", lambda: ctx)
    mod.main()  # must not raise
    assert _advisory_text(_stdout_json(capsys)) is None
