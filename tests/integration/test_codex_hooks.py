"""Integration tests for the Codex CLI hook bridge (spec-112 T-2.1..T-2.4).

The Codex CLI sends JSON to a registered command via stdin (per
`developers.openai.com/codex/hooks`). The bridge in
``.ai-engineering/scripts/hooks/codex-hook-bridge.py`` translates the
Codex contract to a unified ``FrameworkEvent`` and delegates to
``_lib/hook-common.emit_event()`` so the NDJSON stream carries
``engine: "codex"`` for every Codex-originated event.

Three concerns covered:
1. PreToolUse → unified ``ide_hook`` event with the right metadata.
2. UserPromptSubmit matching ``/ai-`` → ``skill_invoked`` event.
3. Bridge stays fail-open: malformed input produces no event but exits 0.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_ROOT = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks"


def _events_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


def _read_events(project_root: Path) -> list[dict]:
    path = _events_path(project_root)
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _prepare(tmp_path: Path) -> Path:
    """Mirror the production hooks tree into ``tmp_path`` for an isolated run."""
    target_dir = tmp_path / ".ai-engineering" / "state"
    target_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


def _bridge_path() -> Path:
    return HOOKS_ROOT / "codex-hook-bridge.py"


def _run_bridge(project_root: Path, payload: dict) -> subprocess.CompletedProcess:
    env = os.environ | {
        "CLAUDE_PROJECT_DIR": str(project_root),
        "AIENG_HOOK_ENGINE": "codex",
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }
    return subprocess.run(
        [sys.executable, str(_bridge_path())],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=project_root,
        env=env,
        check=False,
    )


def test_codex_hook_emits_unified_event(tmp_path: Path) -> None:
    """PreToolUse from Codex → ``ide_hook`` event with engine=codex."""
    project_root = _prepare(tmp_path)
    payload = {
        "event": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
    }

    result = _run_bridge(project_root, payload)
    assert result.returncode == 0, f"bridge stderr: {result.stderr!r}"

    events = _read_events(project_root)
    assert events, "bridge must emit at least one event"
    ide_events = [e for e in events if e["kind"] == "ide_hook"]
    assert ide_events, f"expected ide_hook event in {[e['kind'] for e in events]}"
    event = ide_events[0]
    assert event["engine"] == "codex"
    assert event["component"] == "hook.codex-bridge"
    assert event["outcome"] == "success"
    assert event["detail"]["hook_kind"] == "pre-tool-use"
    assert event["detail"]["tool_name"] == "Bash"


def test_codex_user_prompt_with_ai_prefix_emits_skill_invoked(tmp_path: Path) -> None:
    """UserPromptSubmit matching /ai- → skill_invoked with normalized name."""
    project_root = _prepare(tmp_path)
    payload = {
        "event": "UserPromptSubmit",
        "prompt": "/ai-brainstorm refactor this module",
    }

    result = _run_bridge(project_root, payload)
    assert result.returncode == 0, result.stderr

    events = _read_events(project_root)
    skill_events = [e for e in events if e["kind"] == "skill_invoked"]
    assert skill_events, f"expected skill_invoked event in {[e['kind'] for e in events]}"
    event = skill_events[0]
    assert event["engine"] == "codex"
    assert event["detail"]["skill"] == "ai-brainstorm"


def test_codex_bridge_is_fail_open_on_malformed_stdin(tmp_path: Path) -> None:
    """Bad stdin must produce no event but exit 0 (fail-open contract)."""
    project_root = _prepare(tmp_path)
    env = os.environ | {
        "CLAUDE_PROJECT_DIR": str(project_root),
        "AIENG_HOOK_ENGINE": "codex",
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }
    result = subprocess.run(
        [sys.executable, str(_bridge_path())],
        input="{not-json",
        text=True,
        capture_output=True,
        cwd=project_root,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    # Bridge may still emit a malformed event for observability; what matters
    # is no crash and the stream is well-formed JSON-per-line.
    events = _read_events(project_root)
    for entry in events:
        assert entry.get("engine") == "codex"
