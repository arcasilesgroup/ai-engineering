"""Tests for ``runtime-subagent-stop.py`` — the SubagentStop hook.

Covers three correctness contracts:
  * Happy path: ``subagent_type`` and ``duration_ms`` make it into the
    emitted ``framework_operation`` event.
  * Missing ``subagent_type``: defaults to the literal string
    ``"unknown"`` so downstream consumers never see ``None``.
  * Exception path: an ``emit_framework_operation`` failure must NOT
    raise — the hook contract is fail-open.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-subagent-stop.py"


@pytest.fixture
def hookmod(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_runtime_subagent_stop", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_subagent_stop", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _make_ctx(
    hookmod, project_root: Path, *, data: dict[str, Any], event_name: str = "SubagentStop"
):
    """Build a HookContext-shaped object the hook expects."""
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


def test_happy_path_captures_subagent_type_and_duration(
    hookmod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(
        hookmod,
        project,
        data={
            "hook_event_name": "SubagentStop",
            "session_id": "sess-A",
            "subagent_type": "ai-explore",
            "subagent_run_id": "run-42",
            "duration_ms": 1234,
        },
    )
    monkeypatch.setattr(hookmod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(hookmod, "passthrough_stdin", lambda _data: None)

    hookmod.main()

    events = _read_events(project)
    assert events, "expected at least one framework_operation event"
    last = events[-1]
    assert last["kind"] == "framework_operation"
    assert last["component"] == "hook.runtime-subagent-stop"
    detail = last["detail"]
    assert detail["operation"] == "subagent_stop"
    assert detail["subagent_type"] == "ai-explore"
    assert detail["duration_ms"] == 1234
    assert detail["subagent_run_id"] == "run-42"


def test_missing_subagent_type_defaults_to_unknown(
    hookmod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _make_ctx(
        hookmod,
        project,
        data={"hook_event_name": "SubagentStop", "session_id": "sess-B"},
    )
    monkeypatch.setattr(hookmod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(hookmod, "passthrough_stdin", lambda _data: None)

    hookmod.main()

    events = _read_events(project)
    assert events, "expected event even when subagent_type is missing"
    last = events[-1]
    assert last["detail"]["subagent_type"] == "unknown"
    # duration_ms is omitted when not present in the payload.
    assert "duration_ms" not in last["detail"]


def test_exception_path_is_silent(hookmod, project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If observability emit raises, the hook must NOT propagate."""
    ctx = _make_ctx(
        hookmod,
        project,
        data={"hook_event_name": "SubagentStop", "subagent_type": "ai-build"},
    )
    monkeypatch.setattr(hookmod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(hookmod, "passthrough_stdin", lambda _data: None)

    # Force the lazy observability import to raise from inside main().
    import _lib.observability as obs_mod

    def boom(*_a, **_kw) -> None:
        raise RuntimeError("synthetic emit failure")

    monkeypatch.setattr(obs_mod, "emit_framework_operation", boom)

    # Must not raise.
    hookmod.main()


def test_non_subagent_event_passes_through_silently(
    hookmod, project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the event_name is not SubagentStop, no framework_operation is emitted."""
    ctx = _make_ctx(
        hookmod,
        project,
        data={"hook_event_name": "Stop"},
        event_name="Stop",
    )
    monkeypatch.setattr(hookmod, "get_hook_context", lambda: ctx)
    monkeypatch.setattr(hookmod, "passthrough_stdin", lambda _data: None)

    hookmod.main()

    events = _read_events(project)
    # Must NOT have emitted a subagent_stop framework_operation.
    assert all(
        not (
            e.get("component") == "hook.runtime-subagent-stop"
            and e.get("detail", {}).get("operation") == "subagent_stop"
        )
        for e in events
    )
