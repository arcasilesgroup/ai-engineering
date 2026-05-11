"""Tests for ``_lib.hook_context`` ``agent_kind`` field (spec-131 sub-004 T-4.A).

`HookContext.agent_kind` distinguishes a Claude Code main-thread invocation
from a Task-tool sub-agent dispatch. Sub-agent posture unlocks the
positive-allow-list lane in `prompt-injection-guard.py` (T-4.B).

Detection heuristic (deliberately defensive — defaults to ``"main"`` when
no signal fires so a misclassified main-thread call never bypasses the
IOC scan):

* ``ctx.data["parent_session_id"]`` set -> ``"subagent"``.
* ``ctx.data["parent_session"]`` set (alias) -> ``"subagent"``.
* ``ctx.data["is_subagent"]`` is True (Codex bridge flag) -> ``"subagent"``.
* ``ctx.data["transcript_path"]`` basename starts with ``"subagent-"`` ->
  ``"subagent"``.
* otherwise -> ``"main"``.
"""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_CONTEXT_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "hook_context.py"


@pytest.fixture
def hc():
    """Load ``_lib/hook_context.py`` under a fresh module name."""
    sys.modules.pop("aieng_lib_hook_context_subagent", None)
    spec = importlib.util.spec_from_file_location(
        "aieng_lib_hook_context_subagent", HOOK_CONTEXT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_lib_hook_context_subagent"] = module
    spec.loader.exec_module(module)
    return module


def _stub_stdin(monkeypatch: pytest.MonkeyPatch, payload: str) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))


def test_agent_kind_field_exists(hc) -> None:
    """``HookContext`` exposes ``agent_kind`` as a dataclass field."""
    fields = {f.name for f in __import__("dataclasses").fields(hc.HookContext)}
    assert "agent_kind" in fields


def test_parent_session_id_marks_subagent(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_stdin(monkeypatch, '{"parent_session_id": "abc-123"}')
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    ctx = hc.get_hook_context()
    assert ctx.agent_kind == "subagent"


def test_parent_session_alias_marks_subagent(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_stdin(monkeypatch, '{"parent_session": "abc-123"}')
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    ctx = hc.get_hook_context()
    assert ctx.agent_kind == "subagent"


def test_is_subagent_flag_marks_subagent(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_stdin(monkeypatch, '{"is_subagent": true}')
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    ctx = hc.get_hook_context()
    assert ctx.agent_kind == "subagent"


def test_transcript_path_basename_marks_subagent(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_stdin(
        monkeypatch,
        '{"transcript_path": "/tmp/.claude/projects/x/subagent-deadbeef.jsonl"}',
    )
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    ctx = hc.get_hook_context()
    assert ctx.agent_kind == "subagent"


def test_no_signal_defaults_to_main(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_stdin(monkeypatch, '{"session_id": "xyz"}')
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    ctx = hc.get_hook_context()
    assert ctx.agent_kind == "main"


def test_malformed_transcript_path_defaults_to_main(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive: a non-string ``transcript_path`` value must not crash."""
    _stub_stdin(monkeypatch, '{"transcript_path": 42}')
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    ctx = hc.get_hook_context()
    assert ctx.agent_kind == "main"


def test_empty_stdin_defaults_to_main(hc, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_stdin(monkeypatch, "")
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    ctx = hc.get_hook_context()
    assert ctx.agent_kind == "main"
