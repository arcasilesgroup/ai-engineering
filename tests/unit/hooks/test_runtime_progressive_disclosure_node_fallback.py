"""Tests for the node-missing telemetry in runtime-progressive-disclosure.

spec-131 sub-004 T-4.G: when ``ctx.event_name == "UserPromptSubmit"``
and ``ctx.data`` is empty, the upstream Claude Code shim likely failed
(operator sees ``/bin/sh: node: command not found``). Our hook emits a
single ``framework_error`` with ``error_code: upstream_hook_node_missing``
so the audit chain captures the symptom, then exits 0 (passthrough). The
fix in Claude Code's harness is out of our purview; we just stop dropping
the signal on the floor.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-progressive-disclosure.py"


@pytest.fixture
def hook():
    """Load ``runtime-progressive-disclosure.py`` under a fresh module name."""
    sys.modules.pop("aieng_runtime_progressive_disclosure", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_progressive_disclosure", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_runtime_progressive_disclosure"] = module
    spec.loader.exec_module(module)
    return module


def test_helper_exists(hook) -> None:
    """The emitter helper MUST be exposed at module scope."""
    assert hasattr(hook, "_emit_node_missing")


def test_empty_data_on_user_prompt_submit_emits_event(
    hook, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Empty stdin payload + UserPromptSubmit -> emit upstream_hook_node_missing."""
    events: list[dict] = []

    def _capture(project_root: Path, event: dict) -> bool:
        events.append(event)
        return True

    monkeypatch.setattr(hook, "emit_event", _capture)
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", "UserPromptSubmit")
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))

    hook.main()

    matches = [
        e for e in events if e.get("detail", {}).get("error_code") == "upstream_hook_node_missing"
    ]
    assert matches, f"expected upstream_hook_node_missing event; got {events!r}"


def test_normal_payload_does_not_emit_node_event(
    hook, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Non-empty payload -> normal flow, no node-missing event."""
    events: list[dict] = []

    def _capture(project_root: Path, event: dict) -> bool:
        events.append(event)
        return True

    monkeypatch.setattr(hook, "emit_event", _capture)
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", "UserPromptSubmit")
    monkeypatch.setattr(
        sys, "stdin", io.StringIO(json.dumps({"prompt": "hello world this is a test prompt"}))
    )

    hook.main()

    matches = [
        e for e in events if e.get("detail", {}).get("error_code") == "upstream_hook_node_missing"
    ]
    assert not matches, f"unexpected upstream_hook_node_missing event: {matches!r}"


def test_empty_data_on_other_event_does_not_emit(
    hook, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Empty data on a non-UserPromptSubmit event -> no node-missing event."""
    events: list[dict] = []

    def _capture(project_root: Path, event: dict) -> bool:
        events.append(event)
        return True

    monkeypatch.setattr(hook, "emit_event", _capture)
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "claude_code")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", "PostToolUse")
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))

    hook.main()

    matches = [
        e for e in events if e.get("detail", {}).get("error_code") == "upstream_hook_node_missing"
    ]
    assert not matches, "non-UserPromptSubmit events must not emit node-missing telemetry"
