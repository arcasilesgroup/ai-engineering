"""Detached background refresh of the version-check cache.

Two entrypoints:

* ``refresh_now()`` — the synchronous child entrypoint. Fetches the latest
  release from the PyPI adapter and writes it to the cache. Fail-open.
* ``spawn_background()`` — fire-and-forget. Launches ``refresh_now`` in a
  fully detached child process (``start_new_session=True``, stdio to
  ``DEVNULL``) and returns immediately so the CLI hot path never blocks.
  Spawn failures are swallowed (fail-open).

This is the first detached-spawn in ``src``. The child is reachable both as
``python -m ai_engineering.version.refresh`` (see the ``__main__`` guard) and
via the hidden ``ai-eng internal version-refresh`` command.
"""

from __future__ import annotations

import contextlib
import subprocess
import sys

from ai_engineering.version import cache, pypi


def refresh_now() -> None:
    """Fetch the latest release and persist it to the cache (fail-open)."""
    try:
        latest = pypi.fetch_latest()
    except Exception:
        return
    if latest:
        cache.write(latest, source="pypi")


def spawn_background() -> None:
    """Launch ``refresh_now`` in a detached child; return immediately.

    Never blocks and never raises — any spawn error is swallowed so the
    hot path stays unaffected when the cache is stale.
    """
    with contextlib.suppress(Exception):
        subprocess.Popen(
            [sys.executable, "-m", "ai_engineering.version.refresh"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    refresh_now()
