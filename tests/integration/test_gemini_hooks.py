"""Integration tests for the Gemini CLI hook bridge (spec-112 T-2.5..T-2.8).

Gemini CLI hooks read stdin JSON and MUST return a JSON object on stdout
(per `geminicli.com/docs/hooks/`). The bridge in
``.ai-engineering/scripts/hooks/gemini-hook-bridge.py`` normalizes the
Gemini contract (``eventType: "BeforeTool"`` etc.) to a unified
``FrameworkEvent`` and writes the required ``{action: "continue"}``
response so Gemini does not block the IDE.

Three concerns covered:
1. BeforeTool → unified ``ide_hook`` event with engine=gemini AND a JSON
   response on stdout.
2. BeforeAgent matching ``/ai-`` → ``skill_invoked`` event (Gemini sends
   the prompt under ``prompt`` or ``userPrompt``).
3. Bridge is fail-open: malformed stdin still yields a JSON response so
   Gemini's parser does not error out.
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
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _bridge_path() -> Path:
    return HOOKS_ROOT / "gemini-hook-bridge.py"


def _run_bridge(project_root: Path, payload: dict) -> subprocess.CompletedProcess:
    env = os.environ | {
        "GEMINI_PROJECT_DIR": str(project_root),
        "AIENG_HOOK_ENGINE": "gemini",
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


def test_gemini_hook_returns_valid_json_response(tmp_path: Path) -> None:
    """BeforeTool → engine=gemini ide_hook event AND JSON stdout response."""
    project_root = _prepare(tmp_path)
    payload = {
        "eventType": "BeforeTool",
        "toolName": "Bash",
        "toolArgs": {"command": "ls"},
    }

    result = _run_bridge(project_root, payload)
    assert result.returncode == 0, f"bridge stderr: {result.stderr!r}"

    # 1. Stdout MUST be a JSON object with at least an `action` key.
    stripped = result.stdout.strip()
    assert stripped, "Gemini contract requires a JSON response on stdout"
    parsed = json.loads(stripped)
    assert isinstance(parsed, dict), "stdout must be a JSON object"
    assert parsed.get("action") in {"continue", "block"}, (
        f"action must be continue or block, got {parsed.get('action')!r}"
    )

    # 2. NDJSON event has engine=gemini.
    events = _read_events(project_root)
    assert events, "bridge must emit at least one event"
    ide_events = [e for e in events if e["kind"] == "ide_hook"]
    assert ide_events
    event = ide_events[0]
    assert event["engine"] == "gemini"
    assert event["component"] == "hook.gemini-bridge"
    assert event["detail"]["hook_kind"] == "pre-tool-use"


def test_gemini_before_agent_with_ai_prefix_emits_skill(tmp_path: Path) -> None:
    """BeforeAgent + prompt matching /ai- → skill_invoked + JSON response."""
    project_root = _prepare(tmp_path)
    payload = {
        "eventType": "BeforeAgent",
        "prompt": "/ai-plan migrate the auth module",
    }

    result = _run_bridge(project_root, payload)
    assert result.returncode == 0
    parsed = json.loads(result.stdout.strip())
    assert parsed.get("action") == "continue"

    events = _read_events(project_root)
    skill_events = [e for e in events if e["kind"] == "skill_invoked"]
    assert skill_events
    assert skill_events[0]["engine"] == "gemini"
    assert skill_events[0]["detail"]["skill"] == "ai-plan"


def test_gemini_bridge_is_fail_open_on_malformed_stdin(tmp_path: Path) -> None:
    """Malformed stdin still produces a continue response and exits 0."""
    project_root = _prepare(tmp_path)
    env = os.environ | {
        "GEMINI_PROJECT_DIR": str(project_root),
        "AIENG_HOOK_ENGINE": "gemini",
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
    assert result.returncode == 0
    parsed = json.loads(result.stdout.strip())
    assert parsed.get("action") == "continue"
