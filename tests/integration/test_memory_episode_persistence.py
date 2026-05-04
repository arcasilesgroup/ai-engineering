"""Smoke test: memory-stop hook actually writes episode rows.

Pre-fix (P0.1 in 2026-05-04 harness audit), ``memory-stop.py`` shelled to
``sys.executable`` which under Claude Code resolved to a host python3
without ``typer`` installed; the ``memory.cli`` subprocess failed silently
and zero episodes were ever written despite tens of thousands of framework
events. This test pins the new resolver path: prefer ``<project>/.venv``
python; fall back to ``sys.executable`` only with a telemetry breadcrumb.
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
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "memory-stop.py"
MEMORY_DIR = REPO / ".ai-engineering" / "scripts" / "memory"


def _seed_events(events_path: Path, session_id: str, count: int = 5) -> None:
    """Write `count` framework_event lines for `session_id` so build_episode
    has something to summarize."""
    events_path.parent.mkdir(parents=True, exist_ok=True)
    base = "2026-05-04T10:00:00Z"
    lines = []
    for i in range(count):
        lines.append(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "timestamp": base,
                    "project": events_path.parents[2].name,
                    "engine": "claude_code",
                    "kind": "ide_hook",
                    "outcome": "success",
                    "component": f"hook.test-{i}",
                    "correlationId": uuid4().hex,
                    "sessionId": session_id,
                    "detail": {
                        "hook_kind": "PostToolUse",
                        "tool_name": "Bash",
                    },
                },
                sort_keys=True,
            )
        )
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_synthetic_project(tmp_path: Path, *, link_venv: bool) -> tuple[Path, str]:
    """Create a temp project with .ai-engineering/state and (optionally) a
    .venv/bin/python symlinked to the test runner's own python.

    Returns (project_root, session_id).
    """
    project_root = tmp_path / "synthetic"
    state = project_root / ".ai-engineering" / "state"
    state.mkdir(parents=True)

    session_id = "synthetic-session-" + uuid4().hex[:8]
    _seed_events(state / "framework-events.ndjson", session_id, count=8)

    # Empty checkpoint so episodic.build_episode has the optional path covered.
    (state / "runtime").mkdir(parents=True, exist_ok=True)
    (state / "runtime" / "checkpoint.json").write_text(
        json.dumps({"session_id": session_id, "active_specs": ["test-spec"]}),
        encoding="utf-8",
    )

    if link_venv:
        venv_bin = project_root / ".venv" / "bin"
        venv_bin.mkdir(parents=True, exist_ok=True)
        target = venv_bin / "python"
        target.symlink_to(sys.executable)

    return project_root, session_id


def _run_hook(project_root: Path, payload: dict) -> tuple[int, str, str]:
    """Invoke memory-stop.py with the synthetic Stop payload."""
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_root),
        "CLAUDE_HOOK_EVENT_NAME": "Stop",
        "AIENG_HOOK_INTEGRITY_MODE": "off",
    }
    proc = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
        cwd=str(project_root),
    )
    return proc.returncode, proc.stdout, proc.stderr


@pytest.mark.skipif(
    not (MEMORY_DIR / "cli.py").exists(),
    reason="memory module not present (skipped on branches without spec-118)",
)
@pytest.mark.skipif(
    not (REPO / ".venv" / "bin" / "python").exists(),
    reason="repo .venv missing; integration test requires a working venv",
)
def test_memory_stop_writes_episode_against_real_venv() -> None:
    """End-to-end: run the hook against the real repo so the resolver
    picks up the actual ``.venv/bin/python`` (which has typer + sqlite-vec
    installed). Synthetic tmp-projects with symlinked venv pythons don't
    carry the parent's site-packages, so this test runs in-place against
    the canonical repo venv and cleans up its own row.

    The test seeds a unique sessionId into framework-events.ndjson, runs
    the hook, asserts the episode row exists, then deletes it. NDJSON
    growth is unavoidable (audit chain is append-only) but bounded.
    """
    session_id = "integration-test-" + uuid4().hex[:12]

    # Append events for our unique session to the real NDJSON. The hook
    # filters by sessionId so we won't disturb existing data.
    events_path = REPO / ".ai-engineering" / "state" / "framework-events.ndjson"
    db_path = REPO / ".ai-engineering" / "state" / "memory.db"

    base_event = {
        "schemaVersion": "1.0",
        "timestamp": "2026-05-04T10:00:00Z",
        "project": "ai-engineering",
        "engine": "claude_code",
        "kind": "ide_hook",
        "outcome": "success",
        "component": "test.memory-stop-integration",
        "detail": {"hook_kind": "PostToolUse", "tool_name": "Bash"},
    }
    appended_lines = []
    for i in range(3):
        ev = dict(base_event)
        ev["correlationId"] = uuid4().hex
        ev["sessionId"] = session_id
        ev["component"] = f"test.memory-stop-integration-{i}"
        appended_lines.append(json.dumps(ev, sort_keys=True))

    pre_size = events_path.stat().st_size if events_path.exists() else 0
    with events_path.open("a", encoding="utf-8") as fh:
        for line in appended_lines:
            fh.write(line + "\n")

    payload = {
        "session_id": session_id,
        "transcript_path": "/tmp/none.jsonl",
        "hook_event_name": "Stop",
        "stop_hook_active": False,
    }

    try:
        code, stdout, stderr = _run_hook(REPO, payload)
        assert code == 0, f"hook nonzero: {code}\nstderr: {stderr}"

        assert db_path.exists(), "memory.db not present at repo root"

        conn = sqlite3.connect(db_path)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM episodes WHERE session_id = ?",
                (session_id,),
            ).fetchone()[0]
        finally:
            conn.close()
        assert count >= 1, (
            f"episodes table did not gain a row for session {session_id}; "
            f"hook stdout={stdout!r} stderr={stderr!r}"
        )
    finally:
        # Clean up our episode row + truncate NDJSON back to pre-test size
        # so we don't leave test pollution in the canonical audit log.
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("DELETE FROM episodes WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
        except Exception:
            pass
        # Truncate NDJSON to exactly the pre-append size. Best-effort: if
        # other test runs interleaved, our lines are still uniquely tagged
        # by the random session_id and a final cleanup pass would purge them.
        try:
            with events_path.open("rb+") as fh:
                fh.truncate(pre_size)
        except OSError:
            pass


@pytest.mark.skipif(
    not (MEMORY_DIR / "cli.py").exists(),
    reason="memory module not present",
)
def test_memory_stop_resolver_picks_venv_when_present(tmp_path: Path) -> None:
    """Direct unit-style: the resolver returns the venv python when the
    .venv/bin/python is executable."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("memstop", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    project_root, _ = _build_synthetic_project(tmp_path, link_venv=True)
    exe, source = mod._resolve_python_executable(project_root)
    assert source == "venv"
    assert exe == str(project_root / ".venv" / "bin" / "python")


def test_memory_stop_resolver_falls_back_to_sys_executable(tmp_path: Path) -> None:
    """Without a .venv, the resolver falls back to sys.executable. The
    hook will additionally emit a ``framework_operation`` breadcrumb so
    the broken-by-default state is visible in telemetry."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("memstop2", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    project_root = tmp_path / "no-venv"
    project_root.mkdir()
    exe, source = mod._resolve_python_executable(project_root)
    assert source == "sys_executable"
    assert exe == sys.executable
