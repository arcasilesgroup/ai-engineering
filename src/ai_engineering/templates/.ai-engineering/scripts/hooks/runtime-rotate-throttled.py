#!/usr/bin/env python3
"""SessionEnd throttle wrapper around ``runtime_rotate.py`` (spec-139 M6.T1).

Why a wrapper?
--------------
The retention sweep at ``.ai-engineering/scripts/runtime_rotate.py`` is
idempotent and cheap on steady-state repos, but every SessionEnd that
fires it back-to-back (Claude opens / closes a context several times per
hour in long workflows) still pays the directory-walk cost. This wrapper
limits the actual rotation to **at most once per
``AIENG_RUNTIME_ROTATE_THROTTLE_SEC``** (default 1 hour) by stamping a
sentinel file ``.ai-engineering/runtime/.rotate-lastrun`` and skipping
when its mtime is fresher than the throttle window.

Hot-path contract (spec-139 M6 + D-139-12)
------------------------------------------
* Stdlib-only. No third-party imports, no ``ai_engineering.*`` imports.
* Budget: under 30 s wall-clock per ``SessionEnd`` invocation.
* Fail-open on EVERY error — never block ``SessionEnd``.
* Uses :func:`run_hook_safe` so timing + integrity behaviour matches the
  rest of the canonical hook surface.

Coordination with spec-138
--------------------------
``runtime-session-end.py`` already owns the NDJSON tail-truncation
(scoped to spec-138 M4 when it lands). This script narrows to the
**retention sweep** only — `_rotate_tool_outputs`, `_rotate_autopilot`,
`_truncate_tool_history` from ``runtime_rotate.py``. Per D-139-12, do
not duplicate the NDJSON rotation invocation.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.hook_common import run_hook_safe
from _lib.hook_context import RUNTIME_DIR, get_hook_context

_COMPONENT = "hook.runtime-rotate-throttled"

# Default throttle window: 1 hour. Operators tune via
# ``AIENG_RUNTIME_ROTATE_THROTTLE_SEC`` (positive integer seconds; any
# malformed or non-positive value falls back to the default so a typo
# never silently disables the sweep).
_DEFAULT_THROTTLE_SEC = 3600
_SENTINEL_NAME = ".rotate-lastrun"
# Subprocess wall-clock ceiling. The hook itself has a 30 s timeout in
# the IDE settings.json; we use 25 s here to leave room for cleanup +
# heartbeat write before the IDE forces a SIGTERM.
_SUBPROCESS_TIMEOUT_SEC = 25


def _throttle_seconds() -> int:
    """Resolve ``AIENG_RUNTIME_ROTATE_THROTTLE_SEC`` with a safe fallback."""
    raw = (os.environ.get("AIENG_RUNTIME_ROTATE_THROTTLE_SEC") or "").strip()
    if not raw:
        return _DEFAULT_THROTTLE_SEC
    try:
        value = int(raw)
    except ValueError:
        return _DEFAULT_THROTTLE_SEC
    if value <= 0:
        return _DEFAULT_THROTTLE_SEC
    return value


def _sentinel_path(project_root: Path) -> Path:
    return RUNTIME_DIR(project_root) / _SENTINEL_NAME


def _is_throttled(sentinel: Path, throttle_sec: int, *, now: float | None = None) -> bool:
    """Return True when the sentinel's mtime is within ``throttle_sec`` of ``now``."""
    if not sentinel.exists():
        return False
    try:
        last_mtime = sentinel.stat().st_mtime
    except OSError:
        return False
    current = now if now is not None else time.time()
    return (current - last_mtime) < throttle_sec


def _touch_sentinel(sentinel: Path) -> None:
    """Create / refresh the sentinel mtime. Idempotent + fail-open."""
    try:
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.touch(exist_ok=True)
        # Touch only sets mtime when the file exists already on some
        # filesystems; explicitly stamp it to ``time.time()`` so the
        # throttle window starts at a known reference even when the file
        # was created moments ago.
        now = time.time()
        os.utime(sentinel, (now, now))
    except OSError:
        return


def _runtime_rotate_script(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "scripts" / "runtime_rotate.py"


def _run_rotation(script: Path) -> bool:
    """Invoke ``runtime_rotate.py`` as a subprocess. Return True on success.

    The script is stdlib-only so ``sys.executable`` is enough — no venv
    activation needed. Any non-zero exit, timeout, or OSError is
    swallowed: the SessionEnd path must never block the IDE shutdown.
    """
    try:
        # argv is a hardcoded repo path — sys.executable + a Path under
        # the project root that we already validated with ``script.is_file``.
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SEC,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def main() -> None:
    ctx = get_hook_context()
    # We honour SessionEnd (Claude / Codex) AND AfterAgent (Antigravity's
    # end-of-session event normalised to "Stop" by hook_context). Any
    # other event short-circuits — the IDE wiring should never fire us
    # outside those, but defence-in-depth keeps the hot path tight.
    if ctx.event_name not in {"SessionEnd", "Stop"}:
        return

    throttle_sec = _throttle_seconds()
    sentinel = _sentinel_path(ctx.project_root)

    if _is_throttled(sentinel, throttle_sec):
        # Within window — exit fast. The heartbeat from ``run_hook_safe``
        # still records the skip via ``duration_ms`` so operators see the
        # throttle is working.
        return

    script = _runtime_rotate_script(ctx.project_root)
    if not script.is_file():
        # Missing rotation script is not fatal — early checkouts or repos
        # that have not yet pulled the script must not block SessionEnd.
        return

    with contextlib.suppress(Exception):
        if _run_rotation(script):
            _touch_sentinel(sentinel)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component=_COMPONENT,
        hook_kind="session-end",
        script_path=__file__,
    )
