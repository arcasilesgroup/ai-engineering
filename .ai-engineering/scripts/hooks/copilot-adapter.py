#!/usr/bin/env python3
"""Translate Copilot hook payloads to the Claude-style canonical shape."""

from __future__ import annotations

import json
import re
import sys
from typing import Any

_FIRST_CAP_RE = re.compile("(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile("([a-z0-9])([A-Z])")


def _snake_case(key: str) -> str:
    step1 = _FIRST_CAP_RE.sub(r"\1_\2", key)
    return _ALL_CAP_RE.sub(r"\1_\2", step1).lower()


# Canonical key remap. Earlier versions only special-cased toolName/toolArgs and
# let toolResult fall through `_snake_case` to `tool_result`, but runtime-guard
# reads `tool_response` — so under the bash-Copilot wrapper the runtime guard
# saw an empty payload and never offloaded. The PowerShell wrapper had the
# correct mapping inline; this consolidation is the single source of truth.
_KEY_REMAP: dict[str, str] = {
    "toolArgs": "tool_input",
    "toolName": "tool_name",
    "toolResult": "tool_response",
    "toolResponse": "tool_response",
}


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            name = _KEY_REMAP.get(key, _snake_case(key))
            normalized[name] = _normalize(item)
        return normalized
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return _normalize(parsed)
    return value


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    json.dump(_normalize(payload), sys.stdout, separators=(",", ":"))


if __name__ == "__main__":
    main()
