"""Tests for ``runtime-session-start.py`` — the SessionStart enrichment hook.

Pins two correctness contracts that earlier ad-hoc wiring missed:
  * ``trace-context.json`` is created with a valid 32-hex ``traceId``
    so subsequent spec-120 emit calls inside the session inherit a
    stable trace.
  * A ``framework_operation`` event with
    ``operation=session_started`` lands on the audit chain at session
    boot, with ``engine`` + ``session_id`` carried into ``detail``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-session-start.py"


@pytest.fixture
def hookmod(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_runtime_session_start", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_session_start", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _make_ctx(project_root: Path, *, data: dict[str, Any], event_name: str = "SessionStart"):
    from _lib.hook_context import HookContext

    return HookContext(
        engine="claude_code",
        project_root=project_root,
        session_id=data.get("session_id"),
        event_name=event_name,
        event_name_raw=event_name,
        data=data,
    )


def _read_events(project: Path) -> list[dict[str, Any]]:
    path = project / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def test_happy_path_initializes_trace_and_emits_event(
    hookmod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(
        project,
        data={"hook_event_name": "SessionStart", "session_id": "sess-X"},
    )
    monkeypatch.setattr(hookmod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(hookmod, "passthrough_stdin", lambda _data: None)

    hookmod.main()

    # Trace context file must exist with a valid traceId.
    trace_path = project / ".ai-engineering" / "state" / "runtime" / "trace-context.json"
    assert trace_path.exists(), "trace-context.json should be created at SessionStart"
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    trace_id = payload.get("traceId")
    assert isinstance(trace_id, str)
    # uuid4().hex form: 32 lowercase hex characters.
    assert len(trace_id) == 32
    assert all(c in "0123456789abcdef" for c in trace_id)

    # framework_operation event landed on the audit chain.
    events = _read_events(project)
    matching = [
        e
        for e in events
        if e.get("component") == "hook.runtime-session-start"
        and e.get("detail", {}).get("operation") == "session_started"
    ]
    assert matching, "expected exactly one session_started event"
    detail = matching[-1]["detail"]
    assert detail["engine"] == "claude_code"
    assert detail["session_id"] == "sess-X"
    assert detail.get("trace_id_initialized") == trace_id


def test_non_session_event_passes_through(
    hookmod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(
        project,
        data={"hook_event_name": "Stop"},
        event_name="Stop",
    )
    monkeypatch.setattr(hookmod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(hookmod, "passthrough_stdin", lambda _data: None)

    hookmod.main()

    # No trace-context written, no session_started event emitted.
    trace_path = project / ".ai-engineering" / "state" / "runtime" / "trace-context.json"
    assert not trace_path.exists()
    events = _read_events(project)
    assert all(
        e.get("detail", {}).get("operation") != "session_started"
        for e in events
        if e.get("component") == "hook.runtime-session-start"
    )


def test_instincts_count_logged_when_available(
    hookmod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the instincts cache loads cleanly, count is recorded in metadata."""
    ctx = _make_ctx(project, data={"hook_event_name": "SessionStart"})
    monkeypatch.setattr(hookmod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(hookmod, "passthrough_stdin", lambda _data: None)

    # Stub the lazy import inside _safe_count_instincts.
    fake_doc = {
        "corrections": [{"k": 1}, {"k": 2}],
        "recoveries": [{"k": 3}],
        "workflows": [],
    }
    import _lib.instincts as instincts_mod

    monkeypatch.setattr(instincts_mod, "_load_instincts_document", lambda _root: fake_doc)

    hookmod.main()

    events = _read_events(project)
    matching = [
        e
        for e in events
        if e.get("component") == "hook.runtime-session-start"
        and e.get("detail", {}).get("operation") == "session_started"
    ]
    assert matching, "expected session_started event"
    detail = matching[-1]["detail"]
    assert detail.get("instincts_count") == 3
