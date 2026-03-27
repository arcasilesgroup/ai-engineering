#!/usr/bin/env python3
"""PreToolUse hook: scan tool inputs for prompt injection patterns.

Blocks CRITICAL matches (exit 2), warns on HIGH matches (exit 0 advisory).
Applies to Bash, Write, Edit, and MultiEdit tools.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from datetime import UTC

from _lib.audit import (
    get_project_root,
    is_debug_mode,
    passthrough_stdin,
    read_stdin,
)
from _lib.injection_patterns import PATTERNS

from ai_engineering.state.observability import emit_control_outcome

_GUARDED_TOOLS = {"Bash", "Write", "Edit", "MultiEdit"}
_MIN_CONTENT_LEN = 10
_MAX_CONTENT_LEN = 4000


def _extract_content(tool_name: str, tool_input: dict) -> str:
    """Extract scannable content from tool input based on tool type."""
    if tool_name in ("Write", "MultiEdit"):
        return tool_input.get("content", "")
    if tool_name == "Edit":
        return tool_input.get("new_string", "")
    if tool_name == "Bash":
        return tool_input.get("command", "")
    return ""


def main() -> None:
    data = read_stdin()
    tool_name = data.get("tool_name", "")

    if tool_name not in _GUARDED_TOOLS:
        passthrough_stdin(data)
        return

    tool_input = data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}

    content = _extract_content(tool_name, tool_input)

    if len(content) < _MIN_CONTENT_LEN:
        passthrough_stdin(data)
        return

    scan_content = content[:_MAX_CONTENT_LEN]

    critical_matches = []
    high_matches = []

    for pattern in PATTERNS:
        if pattern.regex.search(scan_content):
            match_info = {"pattern": pattern.name, "severity": pattern.severity}
            if pattern.severity == "CRITICAL":
                critical_matches.append(match_info)
            else:
                high_matches.append(match_info)

    all_matches = critical_matches + high_matches

    if all_matches:
        project_root = get_project_root()
        emit_control_outcome(
            project_root,
            category="security",
            control="prompt-injection-guard",
            component="hook.prompt-injection-guard",
            outcome="failure" if critical_matches else "warning",
            source="hook",
            metadata={
                "tool": tool_name,
                "matches": all_matches,
                "action": "blocked" if critical_matches else "warned",
            },
        )

        if is_debug_mode():
            from datetime import datetime

            debug_log = project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
            try:
                timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                names = ", ".join(m["pattern"] for m in all_matches)
                with open(debug_log, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] injection scan: tool={tool_name} matches=[{names}]\n")
            except Exception:
                pass

    if critical_matches:
        pattern_names = ", ".join(m["pattern"] for m in critical_matches)
        feedback = {
            "decision": "block",
            "reason": (
                f"Prompt injection detected: {pattern_names}. "
                "This tool call has been blocked for security. "
                "Please rephrase your request without injection patterns."
            ),
        }
        sys.stdout.write(json.dumps(feedback))
        sys.stdout.flush()
        sys.exit(2)

    if high_matches:
        pattern_names = ", ".join(m["pattern"] for m in high_matches)
        sys.stderr.write(
            f"[prompt-injection-guard] WARNING: Suspicious pattern detected: {pattern_names}. "
            "Allowing tool call but logging for review.\n"
        )
        sys.stderr.flush()

    passthrough_stdin(data)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
    except Exception:
        sys.exit(0)
