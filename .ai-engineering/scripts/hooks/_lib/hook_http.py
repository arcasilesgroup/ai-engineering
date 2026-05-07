"""HTTP sink helper for hook scripts (spec-121).

Some enterprise installations want hook telemetry mirrored to a
centralized audit backend (Splunk, Elastic, Langfuse self-hosted,
etc.). The framework's primary audit chain is the local NDJSON; this
helper is a *secondary*, fail-open sink invoked opportunistically by
hooks that opt in.

Activation: set ``AIENG_HOOK_HTTP_SINK_URL`` in the environment.
Optional: ``AIENG_HOOK_HTTP_SINK_TOKEN`` adds a bearer header.

Hard rules
----------
- stdlib only (``urllib.request``).
- 5 second timeout, never blocking.
- Any error is swallowed; never raises into the hook caller.
- Payload is JSON-serialized. Non-serializable values are dropped
  silently (best-effort).

This is the ``http`` hook type from
``.ai-engineering/schemas/hooks.schema.json`` reduced to its useful
core: a Python helper command hooks can call. A standalone executor
for ``type: http`` hooks is deferred (see spec-121 §Out-of-scope).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

_DEFAULT_TIMEOUT = 5.0
_ENV_URL = "AIENG_HOOK_HTTP_SINK_URL"
_ENV_TOKEN = "AIENG_HOOK_HTTP_SINK_TOKEN"


def _sink_url() -> str | None:
    raw = (os.environ.get(_ENV_URL) or "").strip()
    return raw or None


def dispatch_http_hook(
    payload: dict[str, Any],
    *,
    url: str | None = None,
    timeout: float = _DEFAULT_TIMEOUT,
) -> bool:
    """POST ``payload`` as JSON to the sink URL. Returns ``True`` on 2xx.

    Fail-open: returns ``False`` (and never raises) on any error.
    """
    target = url or _sink_url()
    if not target:
        return False

    try:
        body = json.dumps(payload, default=str).encode("utf-8")
    except (TypeError, ValueError):
        return False

    req = urllib.request.Request(
        target,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    token = (os.environ.get(_ENV_TOKEN) or "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return False
    except Exception:
        # Last-ditch swallow: never propagate into the hook caller.
        return False


__all__ = ["dispatch_http_hook"]
