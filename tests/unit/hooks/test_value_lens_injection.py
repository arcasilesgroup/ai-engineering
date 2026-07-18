"""Client-Value Lens hook reinforcement (spec-186 D-186-05).

Two contracts, exercised by driving the real hook scripts as subprocesses
with JSON stdin (matching ``test_telemetry_skill.py`` style):

  * ``runtime-progressive-disclosure.py`` emits the Client-Value Lens
    reminder on EVERY ``UserPromptSubmit`` — including inputs that used to
    short-circuit to a bare passthrough (short prompt / no ranked skills).
  * ``runtime-session-start.py`` emits the one-shot lens contract at
    ``SessionStart``.

Both assertions pin the load-bearing adoption marker: the injected text
cites ``reference/value-lens.md``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS = REPO / ".ai-engineering" / "scripts" / "hooks"
DISCLOSURE_HOOK = HOOKS / "runtime-progressive-disclosure.py"
SESSION_START_HOOK = HOOKS / "runtime-session-start.py"


@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _run_hook(hook_path: Path, project_root: Path, *, event: str, payload: dict) -> str:
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_root)
    env["CLAUDE_HOOK_EVENT_NAME"] = event
    env["AIENG_HOOK_ENGINE"] = "claude_code"
    # Decouple from the hooks-manifest sha so the test does not depend on
    # re-pin ordering; we exercise main(), not integrity enforcement.
    env["AIENG_HOOK_INTEGRITY_MODE"] = "off"
    env.pop("CI", None)
    result = subprocess.run(
        [sys.executable, str(hook_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, f"hook exited {result.returncode}: {result.stderr}"
    return result.stdout


def test_user_prompt_submit_injects_lens_without_ranked_skills(project_root: Path) -> None:
    """A short prompt (<3 informative tokens) previously passed through with no
    additionalContext; the lens reminder must now ride on every event."""
    stdout = _run_hook(
        DISCLOSURE_HOOK,
        project_root,
        event="UserPromptSubmit",
        # "hi ok" tokenises to 2 words -> old code hit the _MIN_PROMPT_TOKENS
        # early-return with no skill ranking.
        payload={"prompt": "hi ok", "cwd": str(project_root)},
    )
    doc = json.loads(stdout)
    additional = doc["hookSpecificOutput"]["additionalContext"]
    assert doc["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "client-value-lens" in additional
    assert "reference/value-lens.md" in additional


def test_user_prompt_submit_lens_on_slash_command(project_root: Path) -> None:
    """Even an explicit slash command (no ranking performed) carries the lens."""
    stdout = _run_hook(
        DISCLOSURE_HOOK,
        project_root,
        event="UserPromptSubmit",
        payload={"prompt": "/some-command", "cwd": str(project_root)},
    )
    doc = json.loads(stdout)
    additional = doc["hookSpecificOutput"]["additionalContext"]
    assert "client-value-lens" in additional
    assert "value-lens.md" in additional


def test_session_start_emits_lens_contract(project_root: Path) -> None:
    stdout = _run_hook(
        SESSION_START_HOOK,
        project_root,
        event="SessionStart",
        payload={"hook_event_name": "SessionStart", "session_id": "sess-1"},
    )
    assert "client-value-lens" in stdout
    assert "reference/value-lens.md" in stdout
