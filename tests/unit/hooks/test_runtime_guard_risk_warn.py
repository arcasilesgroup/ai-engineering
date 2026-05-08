"""Tests for the PRISM warn-level surfacing in ``runtime-guard.py``.

The runtime-guard PostToolUse hook reads the accumulated session risk
score from ``_lib/risk_accumulator`` and appends a one-line hint to the
``additionalContext`` payload when the score crosses the warn threshold
(10-30). Block / force_stop are owned by ``prompt-injection-guard.py``;
runtime-guard stays observational.

Pin three contracts:

1. **Warn score → hint emitted** — pre-write a risk-score.json with
   score=15, run the hook, assert stdout contains the warn marker.
2. **Silent score → no extra hint** — score=5, no warn marker in
   stdout.
3. **Disabled env var → check skipped** — score=15 +
   ``AIENG_RISK_ACCUMULATOR_DISABLED=1``, no warn marker.
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GUARD_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "runtime-guard.py"
RISK_REL = Path(".ai-engineering") / "runtime" / "risk-score.json"


def _load_guard(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / ".ai-engineering" / "scripts" / "hooks"))
    sys.modules.pop("aieng_runtime_guard", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_guard", GUARD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_runtime_guard"] = module
    spec.loader.exec_module(module)
    return module


def _seed_risk(project_root: Path, score: float) -> None:
    state = {
        "schemaVersion": "1.0",
        "session_id": "test",
        "score": score,
        "last_update_ts": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "events": [],
    }
    path = project_root / RISK_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


def _run_hook(monkeypatch, project_root: Path, payload: dict) -> str:
    """Run runtime-guard.main() with the given payload as stdin; return stdout."""
    monkeypatch.chdir(project_root)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_root))
    monkeypatch.setenv("CLAUDE_SESSION_ID", "test")
    monkeypatch.setenv("CLAUDE_HOOK_EVENT_NAME", payload.get("hook_event_name", ""))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    captured = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured)
    guard = _load_guard(monkeypatch)
    guard.main()
    return captured.getvalue()


def _post_tool_payload() -> dict:
    return {
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "echo hi"},
        "tool_response": "",
        "session_id": "test",
    }


def test_warn_score_writes_additionalcontext(tmp_path, monkeypatch):
    _seed_risk(tmp_path, score=15.0)
    out = _run_hook(monkeypatch, tmp_path, _post_tool_payload())
    assert "warn threshold" in out
    assert "15." in out


def test_silent_score_writes_no_warn_marker(tmp_path, monkeypatch):
    _seed_risk(tmp_path, score=5.0)
    out = _run_hook(monkeypatch, tmp_path, _post_tool_payload())
    assert "warn threshold" not in out


def test_disabled_env_skips_warn_check(tmp_path, monkeypatch):
    _seed_risk(tmp_path, score=15.0)
    monkeypatch.setenv("AIENG_RISK_ACCUMULATOR_DISABLED", "1")
    out = _run_hook(monkeypatch, tmp_path, _post_tool_payload())
    assert "warn threshold" not in out
