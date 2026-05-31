"""PyPI version source adapter (spec version-update-notice).

Fetches the latest published ``ai-engineering`` release from the PyPI JSON
API. Modelled on ``platforms/sonar.py``: lazy ``httpx`` import with an
``http.client`` stdlib fallback, a tight timeout, and strict fail-open
semantics — every error path returns ``None`` and nothing ever raises.

This adapter runs out of band (``version.refresh``), never on the CLI hot
path, so a single bounded network call is acceptable here.
"""

from __future__ import annotations

import contextlib
import json
from typing import Any

_PYPI_JSON_URL = "https://pypi.org/pypi/ai-engineering/json"
_DEFAULT_TIMEOUT = 2.0


def _parse_version(payload: Any) -> str | None:
    """Extract ``info.version`` from a PyPI JSON payload, or None."""
    if not isinstance(payload, dict):
        return None
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    version = info.get("version")
    return version if isinstance(version, str) and version else None


def _fetch_latest_stdlib(timeout: float) -> str | None:
    """Fallback fetch using the stdlib ``http.client`` (no httpx)."""
    import http.client
    from urllib.parse import urlparse

    parsed = urlparse(_PYPI_JSON_URL)
    conn: http.client.HTTPSConnection | None = None
    try:
        conn = http.client.HTTPSConnection(parsed.netloc, timeout=timeout)
        conn.request("GET", parsed.path)
        resp = conn.getresponse()
        if resp.status != 200:
            return None
        payload = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError, http.client.HTTPException):
        return None
    finally:
        if conn is not None:
            with contextlib.suppress(OSError):
                conn.close()
    return _parse_version(payload)


def fetch_latest(timeout: float = _DEFAULT_TIMEOUT) -> str | None:
    """Return the latest published release string, or ``None`` (fail-open).

    Tries ``httpx`` first (lazy import) and falls back to ``http.client``
    when ``httpx`` is unavailable. Any error — timeout, offline, non-200,
    malformed JSON — yields ``None``; this function never raises.
    """
    try:
        import importlib

        _httpx = importlib.import_module("httpx")
    except ImportError:
        return _fetch_latest_stdlib(timeout)

    try:
        response = _httpx.get(_PYPI_JSON_URL, timeout=timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
    except Exception:
        return None
    return _parse_version(payload)
