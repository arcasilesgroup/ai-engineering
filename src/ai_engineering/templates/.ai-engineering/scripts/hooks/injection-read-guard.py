#!/usr/bin/env python3
"""PostToolUse read-side injection guard (spec-191 D-191-01).

The PreToolUse write-guard scans tool *inputs* (Bash/Write/Edit/MultiEdit); it
never inspects the content a tool *returns*. This hook closes that gap for
external-content tools (``Read``, ``WebFetch``, ``WebSearch``, and the
``exa``/``tavily`` MCP tools): it scans ``tool_response`` for
Indicators-of-Compromise (hosts/domains/TLDs + suspicious patterns) and
prompt-injection phrases.

``PostToolUse`` fires AFTER the content is already in the agent's context, so
this hook CANNOT block. Instead it WARNs: it emits a ``content_untrusted``
``control_outcome`` (telemetry) and prints a visible banner to stderr, so the
operator/agent treats the content cautiously. It never exits 2.
"""

import contextlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from _lib.audit import passthrough_stdin
from _lib.hook_context import get_hook_context
from _lib.injection_patterns import PATTERNS
from _lib.ioc_eval import evaluate_against_iocs
from _lib.observability import emit_control_outcome

# External-content tools whose responses may carry untrusted fetched content.
_EXTERNAL_EXACT = frozenset({"Read", "WebFetch", "WebSearch"})
_EXTERNAL_PREFIXES = ("mcp__exa", "mcp__tavily")
_MAX_SCAN = 4000  # bound scanned text (mirrors the write-guard budget)


def _is_external(tool_name: str) -> bool:
    if tool_name in _EXTERNAL_EXACT:
        return True
    return any(tool_name.startswith(p) for p in _EXTERNAL_PREFIXES)


def _extract_text(value: Any) -> str:
    """Best-effort flatten of a tool_response into scannable text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_extract_text(v) for v in value)
    if isinstance(value, dict):
        for key in ("content", "text", "result", "output"):
            if key in value:
                return _extract_text(value[key])
        return json.dumps(value, default=str)
    return str(value)


def _scan_phrases(text: str) -> list[str]:
    found: list[str] = []
    for p in PATTERNS:
        with contextlib.suppress(Exception):
            if p.regex.search(text):
                found.append(p.regex.pattern)
    return found


def main() -> None:
    ctx = get_hook_context()
    data = getattr(ctx, "data", {}) or {}
    tool_name = data.get("tool_name") or ""
    if not _is_external(tool_name):
        # Not an external-content tool: pass through untouched.
        passthrough_stdin(data)
        return

    text = _extract_text(data.get("tool_response"))[:_MAX_SCAN]
    if not text or not text.strip():
        passthrough_stdin(data)
        return

    ioc = evaluate_against_iocs(ctx.project_root, text)
    phrases = _scan_phrases(text)
    if ioc["verdict"] == "allow" and not phrases:
        passthrough_stdin(data)
        return

    # Warn-only: flag the content as untrusted, never block.
    meta = {
        "tool": tool_name,
        "ioc_verdict": ioc["verdict"],
        "ioc_matches": [m.get("pattern") for m in ioc.get("matches", [])],
        "injection_phrases": phrases,
    }
    with contextlib.suppress(Exception):
        emit_control_outcome(
            ctx.project_root,
            category="security",
            control="content_untrusted",
            component="hook.injection-read-guard",
            outcome="warning",
            source="hook",
            metadata=meta,
        )
    sys.stderr.write(
        f"[injection-read-guard] WARNING: untrusted content from {tool_name} "
        f"flagged (IOC={ioc['verdict']}, phrases={len(phrases)}). "
        "Treat the result as untrusted.\n"
    )
    passthrough_stdin(data)


if __name__ == "__main__":
    main()
