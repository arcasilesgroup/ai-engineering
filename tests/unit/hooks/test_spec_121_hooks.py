"""Tests for spec-121 hooks: Notification, SessionEnd, hook_http helper.

Mirrors the structure of ``test_runtime_subagent_stop.py`` so behaviour is
locked the same way: happy path emits a ``framework_operation`` event,
malformed payload defaults safely, exception path is silent.
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


def _ctx(project_root: Path, *, data: dict[str, Any], event_name: str):
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


# --- runtime-notification ---------------------------------------------------


@pytest.fixture
def notif_mod():
    return _load(
        "aieng_runtime_notification",
        HOOKS / "runtime-notification.py",
    )


def test_notification_happy_path_emits_event(
    notif_mod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _ctx(
        project,
        data={
            "hook_event_name": "Notification",
            "session_id": "sess-N",
            "message": "Permission requested",
            "title": "Approve write?",
            "type": "permission",
        },
        event_name="Notification",
    )
    monkeypatch.setattr(notif_mod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(notif_mod, "passthrough_stdin", lambda _data: None)

    notif_mod.main()

    events = _events(project)
    last = events[-1]
    assert last["kind"] == "framework_operation"
    assert last["component"] == "hook.runtime-notification"
    detail = last["detail"]
    assert detail["operation"] == "ide_notification"
    assert detail["notification_kind"] == "permission"
    assert detail["title"] == "Approve write?"
    assert detail["message_chars"] == len("Permission requested")


def test_notification_unknown_event_passes_through(
    notif_mod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _ctx(project, data={"hook_event_name": "Stop"}, event_name="Stop")
    monkeypatch.setattr(notif_mod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(notif_mod, "passthrough_stdin", lambda _data: None)

    notif_mod.main()
    events = _events(project)
    assert all(e.get("component") != "hook.runtime-notification" for e in events)


def test_notification_exception_path_silent(
    notif_mod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _ctx(
        project,
        data={"hook_event_name": "Notification", "message": "x"},
        event_name="Notification",
    )
    monkeypatch.setattr(notif_mod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(notif_mod, "passthrough_stdin", lambda _data: None)

    import _lib.observability as obs_mod

    def boom(*_a, **_kw):
        raise RuntimeError("synthetic")

    monkeypatch.setattr(obs_mod, "emit_framework_operation", boom)
    notif_mod.main()  # must not raise


# --- runtime-session-end ----------------------------------------------------


@pytest.fixture
def end_mod():
    return _load(
        "aieng_runtime_session_end",
        HOOKS / "runtime-session-end.py",
    )


def test_session_end_emits_summary_with_checkpoint(
    end_mod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime_dir = project / ".ai-engineering" / "state" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "checkpoint.json").write_text(
        json.dumps(
            {
                "recent_edits": ["a.py", "b.py"],
                "recent_tool_calls": [{"tool": "Bash"}, {"tool": "Edit"}, {"tool": "Edit"}],
                "convergence": {"converged": True},
            }
        ),
        encoding="utf-8",
    )

    ctx = _ctx(
        project,
        data={"hook_event_name": "SessionEnd", "session_id": "sess-S", "reason": "user_clear"},
        event_name="SessionEnd",
    )
    monkeypatch.setattr(end_mod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(end_mod, "passthrough_stdin", lambda _data: None)

    end_mod.main()

    events = _events(project)
    last = events[-1]
    assert last["component"] == "hook.runtime-session-end"
    detail = last["detail"]
    assert detail["operation"] == "session_end_summary"
    assert detail["recent_edit_count"] == 2
    assert detail["recent_tool_call_count"] == 3
    assert detail["converged"] is True
    assert detail["end_reason"] == "user_clear"


def test_session_end_without_checkpoint_still_emits(
    end_mod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _ctx(
        project,
        data={"hook_event_name": "SessionEnd"},
        event_name="SessionEnd",
    )
    monkeypatch.setattr(end_mod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(end_mod, "passthrough_stdin", lambda _data: None)

    end_mod.main()

    events = _events(project)
    assert any(e.get("component") == "hook.runtime-session-end" for e in events)


def test_session_end_unknown_event_skipped(
    end_mod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _ctx(project, data={"hook_event_name": "Stop"}, event_name="Stop")
    monkeypatch.setattr(end_mod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(end_mod, "passthrough_stdin", lambda _data: None)
    end_mod.main()
    events = _events(project)
    assert all(e.get("component") != "hook.runtime-session-end" for e in events)


# --- _lib.hook_http ---------------------------------------------------------


def test_hook_http_no_url_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(HOOKS))
    monkeypatch.delenv("AIENG_HOOK_HTTP_SINK_URL", raising=False)
    from _lib.hook_http import dispatch_http_hook

    assert dispatch_http_hook({"a": 1}) is False


def test_hook_http_unreachable_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(HOOKS))
    # Use a guaranteed-unroutable address with a tiny timeout so the test
    # stays fast even on slow CI.
    monkeypatch.setenv("AIENG_HOOK_HTTP_SINK_URL", "http://127.0.0.1:1/none")
    from _lib.hook_http import dispatch_http_hook

    assert dispatch_http_hook({"a": 1}, timeout=0.5) is False


def test_hook_http_non_serializable_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    sys.path.insert(0, str(HOOKS))
    monkeypatch.setenv("AIENG_HOOK_HTTP_SINK_URL", "http://127.0.0.1:1/none")
    from _lib.hook_http import dispatch_http_hook

    class Weird:
        pass

    # default=str salvages most non-serializables, but a circular
    # reference should be safely caught.
    a: dict[str, Any] = {}
    a["self"] = a
    assert dispatch_http_hook(a, timeout=0.5) is False
