"""Tests for the Ralph Loop convergence path inside ``runtime-stop.py``.

The Ralph loop is the convergence-driven reinjection orchestration:
:func:`_ralph_convergence_loop` runs convergence checks and decides
whether to stamp ``ralph-resume.json`` and emit a ``decision: block``
JSON to stdout.

Pinned contracts:

* **Converged.** Convergence reports no failures → resume state is
  cleared and a ``ralph_converged`` framework_operation event lands
  on the audit chain. Caller MUST passthrough stdin (return False).
* **Default observe-only.** When ``AIENG_RALPH_BLOCK`` is unset,
  unconverged → telemetry only (``ralph_reinject``); stdout stays
  empty and the caller passes through normally.
* **Block-enabled.** When ``AIENG_RALPH_BLOCK=1`` and unconverged,
  the function writes ``decision:block`` JSON to stdout and returns
  True so the caller skips ``passthrough_stdin``.
* **Max retries.** Once retries reach ``_RALPH_MAX_RETRIES`` the next
  call emits ``framework_error`` (``ralph_max_retries_exceeded``) and
  returns False without writing more JSON. Resume state is removed
  so the next ``/ai-start`` cycle starts cold.
* **Disable env var.** ``AIENG_RALPH_DISABLED=1`` short-circuits to
  False before any convergence call.

Each test reloads the module after toggling env vars so the module-
level ``_RALPH_BLOCK_ENABLED`` / ``_RALPH_DISABLED`` are read fresh.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNTIME_STOP_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-stop.py"
RESUME_REL = Path(".ai-engineering") / "state" / "runtime" / "ralph-resume.json"
EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


def _load_module(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_runtime_stop_ralph", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_stop_ralph", RUNTIME_STOP_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_runtime_stop_ralph"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Project root with the runtime + state dirs preallocated."""
    (tmp_path / ".ai-engineering" / "state" / "runtime").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _read_events(project: Path) -> list[dict]:
    """Parse framework-events.ndjson into a list of dicts (oldest first)."""
    path = project / EVENTS_REL
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


class _FakeResult:
    """Stand-in for ConvergenceResult — duck-typed (frozen dataclass cmp not needed)."""

    def __init__(self, *, converged: bool, failures: list[str] | None = None) -> None:
        self.converged = converged
        self.failures = failures or []
        self.duration_ms = 1


def test_converged_clears_resume_state_and_emits_event(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Converged convergence sweep: resume state goes away, telemetry lands."""
    rstop = _load_module(monkeypatch)
    # Pre-write a resume state so we can verify it gets deleted.
    resume_path = project / RESUME_REL
    resume_path.write_text(json.dumps({"retries": 1, "active": True}), encoding="utf-8")

    monkeypatch.setattr(
        rstop, "check_convergence", lambda _root, fast=True: _FakeResult(converged=True)
    )

    reinjected = rstop._ralph_convergence_loop(
        project,
        session_id="sess-1",
        correlation_id="corr-1",
        last_prompt="do work",
    )
    assert reinjected is False
    # Resume state should have been deleted.
    assert not resume_path.exists()
    # ralph_converged framework_operation event should be on the audit chain.
    events = _read_events(project)
    converged_events = [
        e for e in events if (e.get("detail") or {}).get("operation") == "ralph_converged"
    ]
    assert len(converged_events) >= 1


def test_unconverged_observe_only_when_block_disabled(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Default behavior (no AIENG_RALPH_BLOCK): no stdout JSON, only telemetry."""
    monkeypatch.delenv("AIENG_RALPH_BLOCK", raising=False)
    monkeypatch.delenv("AIENG_RALPH_DISABLED", raising=False)
    rstop = _load_module(monkeypatch)
    # Sanity: the module must have read the env state correctly at import.
    assert rstop._RALPH_BLOCK_ENABLED is False
    assert rstop._RALPH_DISABLED is False

    monkeypatch.setattr(
        rstop,
        "check_convergence",
        lambda _root, fast=True: _FakeResult(converged=False, failures=["ruff check: 1 issue"]),
    )

    # Capture stdout to confirm it stays empty.
    buf = io.StringIO()
    monkeypatch.setattr(rstop.sys, "stdout", buf)

    reinjected = rstop._ralph_convergence_loop(
        project,
        session_id="sess-2",
        correlation_id="corr-2",
        last_prompt="finish work",
    )
    assert reinjected is False
    assert buf.getvalue() == ""

    # ralph_reinject framework_operation event must still land.
    events = _read_events(project)
    reinject_events = [
        e for e in events if (e.get("detail") or {}).get("operation") == "ralph_reinject"
    ]
    assert len(reinject_events) >= 1


def test_unconverged_writes_additionalcontext_when_block_enabled(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With AIENG_RALPH_BLOCK=1 + unconverged → ``decision:block`` JSON on stdout."""
    monkeypatch.setenv("AIENG_RALPH_BLOCK", "1")
    monkeypatch.delenv("AIENG_RALPH_DISABLED", raising=False)
    rstop = _load_module(monkeypatch)
    assert rstop._RALPH_BLOCK_ENABLED is True

    monkeypatch.setattr(
        rstop,
        "check_convergence",
        lambda _root, fast=True: _FakeResult(converged=False, failures=["ruff check: 2 issues"]),
    )

    buf = io.StringIO()
    monkeypatch.setattr(rstop.sys, "stdout", buf)

    reinjected = rstop._ralph_convergence_loop(
        project,
        session_id="sess-3",
        correlation_id="corr-3",
        last_prompt="resume",
    )
    assert reinjected is True
    payload = json.loads(buf.getvalue())
    assert payload["decision"] == "block"
    assert "additionalContext" in payload
    assert "convergence not reached" in payload["additionalContext"].lower() or (
        "ralph loop" in payload["additionalContext"].lower()
    )


def test_max_retries_exceeded_emits_framework_error_and_stops(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the retry counter is at the budget, the loop emits framework_error
    (``ralph_max_retries_exceeded``), deletes the resume state, and returns False
    without further reinjection."""
    monkeypatch.setenv("AIENG_RALPH_BLOCK", "1")  # would otherwise reinject
    monkeypatch.delenv("AIENG_RALPH_DISABLED", raising=False)
    rstop = _load_module(monkeypatch)

    # Pre-stamp a resume state already at max.
    resume_path = project / RESUME_REL
    resume_path.write_text(
        json.dumps({"retries": rstop._RALPH_MAX_RETRIES, "active": True}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        rstop,
        "check_convergence",
        lambda _root, fast=True: _FakeResult(converged=False, failures=["pytest -x: 1 failure"]),
    )

    buf = io.StringIO()
    monkeypatch.setattr(rstop.sys, "stdout", buf)

    reinjected = rstop._ralph_convergence_loop(
        project,
        session_id="sess-4",
        correlation_id="corr-4",
        last_prompt="give up gracefully",
    )
    assert reinjected is False
    # No reinjection JSON should have hit stdout.
    assert buf.getvalue() == ""
    # Resume state cleared so /ai-start does not loop forever.
    assert not resume_path.exists()
    # ralph_max_retries_exceeded framework_error must be present.
    events = _read_events(project)
    err_events = [
        e
        for e in events
        if (e.get("detail") or {}).get("error_code") == "ralph_max_retries_exceeded"
    ]
    assert len(err_events) >= 1


def test_disabled_via_env_var(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``AIENG_RALPH_DISABLED=1`` must short-circuit before any convergence run."""
    monkeypatch.setenv("AIENG_RALPH_DISABLED", "1")
    rstop = _load_module(monkeypatch)
    assert rstop._RALPH_DISABLED is True

    sentinel = {"called": False}

    def _boom(*_args, **_kwargs):
        sentinel["called"] = True
        raise AssertionError("convergence must not run when disabled")

    monkeypatch.setattr(rstop, "check_convergence", _boom)

    reinjected = rstop._ralph_convergence_loop(
        project,
        session_id="sess-5",
        correlation_id="corr-5",
        last_prompt="off",
    )
    assert reinjected is False
    assert sentinel["called"] is False
