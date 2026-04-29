"""Tests for `_lib/hook-common.run_hook_safe` duration instrumentation (spec-114 T-2.4..T-2.6).

`run_hook_safe` is the shared exception-safety wrapper imported by every
Python hook (telemetry-skill, prompt-injection-guard, instinct-observe,
auto-format, ...). Spec-114 G-2 extends it to wrap the main callable
with `time.perf_counter()` and emit a final hot-path heartbeat event
carrying `detail.duration_ms`.

The heartbeat event uses `kind: ide_hook` (existing wire-format) and
populates `detail.duration_ms` with an integer millisecond reading
≥ 0. The event also carries `detail.hook_kind` and `detail.outcome`
("success" or "failure") so `ai-eng doctor --check hot-path` can group
by hook + outcome.

We exercise the wrapper through a tmp-path NDJSON to keep the test
sealed (no shared state with the dogfood repo).
"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path
from typing import Any

import pytest

HOOK_COMMON_PATH = (
    Path(__file__).resolve().parents[3]
    / ".ai-engineering"
    / "scripts"
    / "hooks"
    / "_lib"
    / "hook-common.py"
)


@pytest.fixture
def hc(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Load the hook-common module by file path (filename uses a hyphen)."""
    spec = importlib.util.spec_from_file_location("aieng_hook_common_spec114", HOOK_COMMON_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "session-test-114")
    monkeypatch.setenv("CLAUDE_TRACE_ID", "trace-test-114")
    return tmp_path


def _read_events(project_root: Path) -> list[dict]:
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# ---------------------------------------------------------------------------
# T-2.4 RED — duration_ms injection on success
# ---------------------------------------------------------------------------


def test_emit_event_records_duration_ms(hc: Any, project_root: Path) -> None:
    """run_hook_safe emits a hot-path heartbeat event with detail.duration_ms."""

    def _work() -> None:
        time.sleep(0.01)  # ~10 ms — well below pre-commit budget but >0

    with pytest.raises(SystemExit) as exc:
        hc.run_hook_safe(_work, component="hook.test-114", hook_kind="pre-commit")
    assert exc.value.code == 0

    events = _read_events(project_root)
    # The wrapper must have written exactly one heartbeat event.
    heartbeats = [e for e in events if e.get("component") == "hook.test-114"]
    assert heartbeats, "run_hook_safe must emit a hot-path heartbeat event"

    heartbeat = heartbeats[-1]
    detail = heartbeat.get("detail", {})
    assert "duration_ms" in detail, "heartbeat detail must carry duration_ms"
    assert isinstance(detail["duration_ms"], int), "duration_ms must be integer ms"
    assert detail["duration_ms"] >= 0, "duration_ms must be non-negative"
    assert detail.get("hook_kind") == "pre-commit"
    assert detail.get("outcome") == "success"
    assert heartbeat.get("kind") == "ide_hook"
    assert heartbeat.get("engine") in {"claude_code", "codex", "gemini", "copilot"}


# ---------------------------------------------------------------------------
# T-2.4 — duration_ms is also recorded on failure paths
# ---------------------------------------------------------------------------


def test_emit_event_records_duration_ms_on_failure(hc: Any, project_root: Path) -> None:
    """When main() raises, run_hook_safe still emits the heartbeat with duration_ms."""

    def _work() -> None:
        time.sleep(0.005)
        raise RuntimeError("simulated failure")

    with pytest.raises(SystemExit) as exc:
        hc.run_hook_safe(_work, component="hook.test-114-fail", hook_kind="pre-push")
    assert exc.value.code == 0

    events = _read_events(project_root)
    heartbeats = [
        e
        for e in events
        if e.get("component") == "hook.test-114-fail" and e.get("kind") == "ide_hook"
    ]
    assert heartbeats, "failure path must still emit a heartbeat"
    detail = heartbeats[-1]["detail"]
    assert isinstance(detail["duration_ms"], int)
    assert detail["duration_ms"] >= 0
    assert detail["outcome"] == "failure"
    assert detail["hook_kind"] == "pre-push"


# ---------------------------------------------------------------------------
# T-2.4 — duration_ms is rounded (no float leakage)
# ---------------------------------------------------------------------------


def test_duration_ms_is_integer_milliseconds(hc: Any, project_root: Path) -> None:
    """The wrapper rounds perf_counter() readings to integer milliseconds."""

    def _work() -> None:
        # No sleep — duration may be sub-millisecond. The wrapper must still
        # produce an integer (rounded down to 0 if necessary).
        return None

    with pytest.raises(SystemExit):
        hc.run_hook_safe(_work, component="hook.test-114-round", hook_kind="post-tool-use")

    events = _read_events(project_root)
    heartbeat = next(e for e in events if e.get("component") == "hook.test-114-round")
    duration = heartbeat["detail"]["duration_ms"]
    assert isinstance(duration, int)
    assert duration >= 0
