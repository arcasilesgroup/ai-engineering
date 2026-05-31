"""Version-check cache repository (spec version-update-notice).

Stores the latest-known PyPI release under
``~/.ai-engineering/state/version-check.json`` so the hot-path update
notice can read it without any network call. The PyPI fetch happens out
of band (``version.refresh``); this module is the repository port.

All functions are fail-open (D-010-3): any IO/JSON error is swallowed and
treated as "no usable cache" so a corrupt file never crashes the CLI.

Schema::

    {
      "latest": "0.9.0",            # latest known release string
      "checked_at": "<iso8601>",    # when the cache was last written
      "last_shown_at": "<iso8601>", # when the notice was last shown (throttle)
      "source": "pypi"              # source adapter that produced ``latest``
    }
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path


def cache_path() -> Path:
    """Return the on-disk cache path under the user's home directory."""
    return Path.home() / ".ai-engineering" / "state" / "version-check.json"


def read() -> dict:
    """Read the cache, returning an empty dict on any error (fail-open)."""
    path = cache_path()
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _atomic_write(path: Path, payload: dict) -> None:
    """Write ``payload`` to ``path`` atomically (temp file + replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        os.replace(tmp_name, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def write(latest: str, source: str = "pypi") -> None:
    """Persist the latest known release, stamping ``checked_at`` to now.

    Preserves any existing ``last_shown_at`` throttle stamp. Fail-open on
    IO errors so a read-only home directory never crashes the CLI.
    """
    existing = read()
    payload = {
        "latest": latest,
        "checked_at": datetime.now(UTC).isoformat(),
        "last_shown_at": existing.get("last_shown_at"),
        "source": source,
    }
    with contextlib.suppress(OSError):
        _atomic_write(cache_path(), payload)


def touch_checked_at() -> None:
    """Advance ``checked_at`` to now WITHOUT changing ``latest`` (fail-open).

    spec-156 D-156-13: a failed PyPI fetch must still bump ``checked_at`` so the
    cache is not perpetually stale — otherwise every CLI invocation respawns a
    detached refresh while offline. Preserves ``latest`` and ``last_shown_at``.
    """
    data = read()
    data["checked_at"] = datetime.now(UTC).isoformat()
    with contextlib.suppress(OSError):
        _atomic_write(cache_path(), data)


def is_stale(ttl_hours: int) -> bool:
    """Return True if the cache is missing, malformed, or older than TTL."""
    data = read()
    checked_at = data.get("checked_at")
    if not isinstance(checked_at, str) or not checked_at:
        return True
    try:
        stamp = datetime.fromisoformat(checked_at)
    except ValueError:
        return True
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    age = datetime.now(UTC) - stamp
    return age.total_seconds() > ttl_hours * 3600


def mark_shown() -> None:
    """Stamp ``last_shown_at`` to now for notice throttling (fail-open)."""
    data = read()
    data["last_shown_at"] = datetime.now(UTC).isoformat()
    with contextlib.suppress(OSError):
        _atomic_write(cache_path(), data)
