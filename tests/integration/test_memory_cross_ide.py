"""Pin: every IDE mirror wires the canonical memory hooks.

P1.2 from the 2026-05-04 harness audit: only Claude Code wired
``memory-stop.py`` and ``memory-session-start.py``; Codex, Gemini, and
Copilot had memory effectively disabled, defeating the cross-IDE story
spec-118 was meant to deliver.

This file pins the IDE configs and invokes the Copilot adapters with a
synthetic Stop payload to confirm an episode lands in memory.db.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# IDE config drift pins — fast unit-style assertions.
# ---------------------------------------------------------------------------


def _hook_names_for_event(config: dict, event: str, key: str) -> list[str]:
    """Flatten command basenames for a given event (`hooks[event][i].hooks[].command`)."""
    out: list[str] = []
    for entry in config.get("hooks", {}).get(event, []) or []:
        for hook in entry.get("hooks", []) or []:
            cmd = hook.get(key, "")
            if isinstance(cmd, str) and cmd:
                # last segment, strip args after first space
                tail = cmd.rstrip().split("/")[-1].split()[0]
                out.append(tail)
    return out


def test_codex_wires_memory_stop_and_session_start() -> None:
    config = json.loads((REPO / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    stop_cmds = _hook_names_for_event(config, "Stop", "command")
    session_start_cmds = _hook_names_for_event(config, "SessionStart", "command")
    assert "memory-stop.py" in stop_cmds, f"Codex Stop missing memory-stop.py; got {stop_cmds}"
    assert "memory-session-start.py" in session_start_cmds, (
        f"Codex SessionStart missing memory-session-start.py; got {session_start_cmds}"
    )


def test_gemini_wires_memory_hooks() -> None:
    config = json.loads((REPO / ".gemini" / "settings.json").read_text(encoding="utf-8"))
    after_agent_names = [
        h.get("name", "")
        for entry in config.get("hooks", {}).get("AfterAgent", [])
        for h in entry.get("hooks", [])
    ]
    before_agent_names = [
        h.get("name", "")
        for entry in config.get("hooks", {}).get("BeforeAgent", [])
        for h in entry.get("hooks", [])
    ]
    assert "memory-stop" in after_agent_names, (
        f"Gemini AfterAgent missing memory-stop; got {after_agent_names}"
    )
    assert "memory-session-start" in before_agent_names, (
        f"Gemini BeforeAgent missing memory-session-start; got {before_agent_names}"
    )


def test_copilot_wires_memory_hooks() -> None:
    config = json.loads((REPO / ".github" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    session_end_bash = [
        h.get("bash", "").rsplit("/", 1)[-1] for h in config.get("hooks", {}).get("sessionEnd", [])
    ]
    session_start_bash = [
        h.get("bash", "").rsplit("/", 1)[-1]
        for h in config.get("hooks", {}).get("sessionStart", [])
    ]
    assert "copilot-memory-stop.sh" in session_end_bash, (
        f"Copilot sessionEnd missing copilot-memory-stop.sh; got {session_end_bash}"
    )
    assert "copilot-memory-session-start.sh" in session_start_bash, (
        f"Copilot sessionStart missing copilot-memory-session-start.sh; got {session_start_bash}"
    )


def test_copilot_memory_wrappers_exist_and_executable() -> None:
    """The four Copilot wrappers must exist on disk and shell scripts must
    be executable. Bash + PowerShell halves keep the cross-IDE coverage matrix."""
    hooks_dir = REPO / ".ai-engineering" / "scripts" / "hooks"
    expected = (
        "copilot-memory-stop.sh",
        "copilot-memory-stop.ps1",
        "copilot-memory-session-start.sh",
        "copilot-memory-session-start.ps1",
    )
    for name in expected:
        path = hooks_dir / name
        assert path.is_file(), f"Missing Copilot wrapper: {path}"
        if name.endswith(".sh"):
            assert os.access(path, os.X_OK), f"Wrapper not executable: {path}"


# ---------------------------------------------------------------------------
# Smoke: invoke the Copilot bash wrapper with a synthetic Stop payload
# and assert an episode lands. Mirrors the SS-01 integration approach
# (uses the real repo venv so typer + sqlite-vec are available).
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (REPO / ".venv" / "bin" / "python").exists(),
    reason="repo .venv missing; Copilot smoke test requires a working venv",
)
@pytest.mark.skipif(
    sys.platform == "win32",
    reason="bash wrapper smoke test runs on POSIX; PS1 covered by static drift pin",
)
def test_copilot_memory_stop_writes_episode() -> None:
    """End-to-end: invoke copilot-memory-stop.sh with a synthetic Stop
    payload and confirm an episode row lands in memory.db."""
    session_id = "copilot-cross-ide-" + uuid4().hex[:12]
    events_path = REPO / ".ai-engineering" / "state" / "framework-events.ndjson"
    db_path = REPO / ".ai-engineering" / "state" / "memory.db"

    # Seed events for the unique session so build_episode has something to summarize.
    base = {
        "schemaVersion": "1.0",
        "timestamp": "2026-05-04T10:00:00Z",
        "project": "ai-engineering",
        "engine": "github_copilot",
        "kind": "ide_hook",
        "outcome": "success",
        "component": "test.copilot-memory-stop",
        "detail": {"hook_kind": "PostToolUse", "tool_name": "edit"},
    }
    appended = []
    for i in range(3):
        ev = dict(base)
        ev["correlationId"] = uuid4().hex
        ev["sessionId"] = session_id
        ev["component"] = f"test.copilot-memory-stop-{i}"
        appended.append(json.dumps(ev, sort_keys=True))
    pre_size = events_path.stat().st_size if events_path.exists() else 0
    with events_path.open("a", encoding="utf-8") as fh:
        for line in appended:
            fh.write(line + "\n")

    payload = {
        "sessionId": session_id,
        "session_id": session_id,
        "hookEventName": "sessionEnd",
    }
    wrapper = REPO / ".ai-engineering" / "scripts" / "hooks" / "copilot-memory-stop.sh"
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(REPO),
        "AIENG_HOOK_INTEGRITY_MODE": "off",
    }

    try:
        proc = subprocess.run(
            ["/bin/bash", str(wrapper)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
            cwd=str(REPO),
        )
        assert proc.returncode == 0, f"copilot-memory-stop.sh exit {proc.returncode}: {proc.stderr}"

        conn = sqlite3.connect(db_path)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
        finally:
            conn.close()
        assert count >= 1, (
            f"Copilot wrapper did not write an episode for {session_id}; "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    finally:
        # Clean up
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM episodes WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass
        try:
            with events_path.open("rb+") as fh:
                fh.truncate(pre_size)
        except OSError:
            pass
