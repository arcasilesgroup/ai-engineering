"""Integration tests for the SessionEnd rotation throttle (spec-139 M6.T5).

Exercises ``.ai-engineering/scripts/hooks/runtime-rotate-throttled.py``
end-to-end in a tmp_path repo:

1. First SessionEnd → throttle wrapper invokes ``runtime_rotate.py``,
   touches the ``.rotate-lastrun`` sentinel.
2. Second SessionEnd within the throttle window → wrapper skips
   (sentinel mtime unchanged, ``runtime_rotate.py`` NOT re-invoked).
3. AIENG_RUNTIME_ROTATE_THROTTLE_SEC override is honoured — a 1-second
   throttle lets a second call past the gate.

Why not parametrize across engines?
-----------------------------------
The wrapper has no engine-specific behaviour (it shells out to
``runtime_rotate.py`` regardless of ``AIENG_HOOK_ENGINE``); the cross-IDE
wiring is asserted separately in ``test_hook_wiring_parity.py``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOKS = REPO / ".ai-engineering" / "scripts" / "hooks"
WRAPPER = HOOKS / "runtime-rotate-throttled.py"
RUNTIME_ROTATE = REPO / ".ai-engineering" / "scripts" / "runtime_rotate.py"


def _load_wrapper():
    sys.path.insert(0, str(HOOKS))
    sys.modules.pop("aieng_runtime_rotate_throttled", None)
    spec = importlib.util.spec_from_file_location("aieng_runtime_rotate_throttled", WRAPPER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Build a minimal project tree that mirrors the canonical layout.

    Plants a copy (preferring a symlink when the host supports them) of
    the real ``runtime_rotate.py`` under ``tmp_path/.ai-engineering/scripts/``
    so the throttle wrapper's ``Path.is_file()`` check passes and the
    subprocess invocation runs against a realistic path. Windows runners
    without Developer Mode (the default for GitHub Actions ``windows-latest``)
    cannot create symlinks without elevation; fall back to ``shutil.copy2``
    so the integration test stays green there too. The wrapper only needs
    a valid script at the resolved path — symlink vs copy is functionally
    equivalent.
    """
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "scripts").mkdir(parents=True, exist_ok=True)
    planted = tmp_path / ".ai-engineering" / "scripts" / "runtime_rotate.py"
    try:
        planted.symlink_to(RUNTIME_ROTATE)
    except (OSError, NotImplementedError):
        # Windows without Developer Mode raises ``OSError: [WinError 1314]``
        # (A required privilege is not held by the client). Fall back to a
        # plain copy — the wrapper's contract is that the script EXISTS at
        # the resolved path, not that it is a symlink.
        shutil.copy2(RUNTIME_ROTATE, planted)
    return tmp_path


@pytest.fixture
def wrapper_mod():
    return _load_wrapper()


def _run_wrapper_in_project(
    project_root: Path, *, throttle_sec: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Invoke the wrapper as a subprocess against ``project_root``."""
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project_root)
    env["CLAUDE_HOOK_EVENT_NAME"] = "SessionEnd"
    env["AIENG_HOOK_ENGINE"] = "claude_code"
    # Disable integrity enforcement for the test because the wrapper
    # lives at the canonical repo path (not the tmp project).
    env["AIENG_HOOK_INTEGRITY_MODE"] = "off"
    if throttle_sec is not None:
        env["AIENG_RUNTIME_ROTATE_THROTTLE_SEC"] = throttle_sec
    return subprocess.run(
        [sys.executable, str(WRAPPER)],
        input="{}",
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )


def test_first_session_end_runs_rotation_and_touches_sentinel(
    project: Path,
) -> None:
    """First call → sentinel created, exit 0."""
    sentinel = project / ".ai-engineering" / "runtime" / ".rotate-lastrun"
    assert not sentinel.exists(), "fixture sanity: sentinel must not pre-exist"

    proc = _run_wrapper_in_project(project)

    assert proc.returncode == 0, f"wrapper should exit 0; stderr={proc.stderr!r}"
    assert sentinel.exists(), "wrapper should have stamped the sentinel after rotating"
    # Sanity: runtime_rotate.py emits a framework event into the project's
    # NDJSON when it runs. Presence of the file is sufficient proof that
    # the wrapper actually subprocessed the rotation script.
    events_path = project / ".ai-engineering" / "state" / "framework-events.ndjson"
    if events_path.exists():
        text = events_path.read_text(encoding="utf-8")
        # Either runtime_rotate or the hook heartbeat may have appended.
        # We don't pin the exact event — just that NDJSON was touched.
        assert text.strip(), "events file exists but is empty after rotation"


def test_second_session_end_within_throttle_skips_rotation(
    project: Path,
) -> None:
    """Second call inside the throttle window → sentinel mtime unchanged."""
    sentinel = project / ".ai-engineering" / "runtime" / ".rotate-lastrun"

    # First invocation: 1-hour default throttle, rotation runs.
    first = _run_wrapper_in_project(project)
    assert first.returncode == 0
    assert sentinel.exists()
    first_mtime = sentinel.stat().st_mtime

    # Force a tiny gap so any false mtime bump would be visible.
    time.sleep(0.05)

    # Second invocation: still within the default 1-hour window, MUST skip.
    second = _run_wrapper_in_project(project)
    assert second.returncode == 0
    second_mtime = sentinel.stat().st_mtime

    # Sentinel mtime must not have moved — the throttle short-circuited
    # before the touch() / utime() call.
    assert second_mtime == first_mtime, (
        f"sentinel mtime moved from {first_mtime} → {second_mtime}; "
        "the wrapper re-ran rotation despite the throttle window"
    )


def test_throttle_seconds_env_override_lets_second_call_run(
    project: Path,
) -> None:
    """``AIENG_RUNTIME_ROTATE_THROTTLE_SEC=0.5`` → second call after 1s re-rotates."""
    sentinel = project / ".ai-engineering" / "runtime" / ".rotate-lastrun"

    # First call: tiny 1-second throttle. Note the env var is parsed as
    # ``int`` — fractional seconds collapse to 0, which the wrapper
    # rejects in favour of the default. Use "1" so we can sleep past it.
    first = _run_wrapper_in_project(project, throttle_sec="1")
    assert first.returncode == 0
    assert sentinel.exists()
    first_mtime = sentinel.stat().st_mtime

    # Wait past the 1-second window so the throttle releases.
    time.sleep(1.2)

    second = _run_wrapper_in_project(project, throttle_sec="1")
    assert second.returncode == 0
    second_mtime = sentinel.stat().st_mtime

    assert second_mtime > first_mtime, (
        f"sentinel mtime did not advance (first={first_mtime}, second={second_mtime}); "
        "throttle override should have allowed the second rotation to run"
    )


def test_wrapper_skips_when_event_is_not_session_end(project: Path, wrapper_mod) -> None:
    """Defensive: non-SessionEnd event → wrapper returns early, no sentinel."""
    sentinel = project / ".ai-engineering" / "runtime" / ".rotate-lastrun"
    assert not sentinel.exists()

    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env["CLAUDE_HOOK_EVENT_NAME"] = "PreToolUse"  # NOT SessionEnd / Stop
    env["AIENG_HOOK_ENGINE"] = "claude_code"
    env["AIENG_HOOK_INTEGRITY_MODE"] = "off"

    proc = subprocess.run(
        [sys.executable, str(WRAPPER)],
        input="{}",
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0
    assert not sentinel.exists(), "wrapper must not touch the sentinel for non-SessionEnd events"


def test_throttle_seconds_default_when_env_missing(wrapper_mod) -> None:
    """Direct test on the resolver: unset env → 3600s default."""
    assert wrapper_mod._throttle_seconds.__name__ == "_throttle_seconds"
    # Snapshot + restore to keep parallel test invocations safe.
    saved = os.environ.pop("AIENG_RUNTIME_ROTATE_THROTTLE_SEC", None)
    try:
        assert wrapper_mod._throttle_seconds() == 3600
    finally:
        if saved is not None:
            os.environ["AIENG_RUNTIME_ROTATE_THROTTLE_SEC"] = saved


def test_throttle_seconds_invalid_env_falls_back_to_default(wrapper_mod) -> None:
    """Garbage env value (non-int, zero, negative) → 3600s default."""
    for raw in ("", "  ", "abc", "0", "-5"):
        saved = os.environ.pop("AIENG_RUNTIME_ROTATE_THROTTLE_SEC", None)
        os.environ["AIENG_RUNTIME_ROTATE_THROTTLE_SEC"] = raw
        try:
            assert wrapper_mod._throttle_seconds() == 3600, (
                f"value {raw!r} should fall back to 3600s default"
            )
        finally:
            if saved is None:
                del os.environ["AIENG_RUNTIME_ROTATE_THROTTLE_SEC"]
            else:
                os.environ["AIENG_RUNTIME_ROTATE_THROTTLE_SEC"] = saved


def test_throttle_seconds_positive_env_is_honoured(wrapper_mod) -> None:
    """Positive int env value → returned verbatim."""
    saved = os.environ.pop("AIENG_RUNTIME_ROTATE_THROTTLE_SEC", None)
    os.environ["AIENG_RUNTIME_ROTATE_THROTTLE_SEC"] = "42"
    try:
        assert wrapper_mod._throttle_seconds() == 42
    finally:
        if saved is None:
            del os.environ["AIENG_RUNTIME_ROTATE_THROTTLE_SEC"]
        else:
            os.environ["AIENG_RUNTIME_ROTATE_THROTTLE_SEC"] = saved


def _read_events(project_root: Path) -> list[dict]:
    path = project_root / ".ai-engineering" / "state" / "framework-events.ndjson"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
