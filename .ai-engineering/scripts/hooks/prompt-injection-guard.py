#!/usr/bin/env python3
"""PreToolUse hook: scan tool inputs for prompt injection patterns.

Blocks CRITICAL matches (exit 2), warns on HIGH matches (exit 0 advisory).
Applies to Bash, Write, Edit, and MultiEdit tools.

spec-105 G-12: ``ai-eng risk accept`` and ``ai-eng risk accept-all`` are
explicitly whitelisted because their inputs (gate-findings.json fixtures)
intentionally embed rule names like ``aws-access-token`` /
``stripe-key`` / etc. that the injection-pattern set classifies as
CRITICAL. Whitelisted invocations bypass the pattern scan but still emit
a telemetry event so the bypass is auditable.
"""

import hashlib
import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from datetime import UTC

from _lib.audit import is_debug_mode, passthrough_stdin
from _lib.hook_context import get_hook_context
from _lib.injection_patterns import PATTERNS
from _lib.observability import emit_control_outcome

_GUARDED_TOOLS = {"Bash", "Write", "Edit", "MultiEdit"}
_MIN_CONTENT_LEN = 10
_MAX_CONTENT_LEN = 4000

# spec-105 G-12: commands that legitimately handle gate-findings JSON
# embedding secret-related rule names. Match by argv[0..2] joined with
# single spaces. Add new entries with care -- every whitelisted command
# bypasses the injection-pattern scan.
WHITELISTED_COMMANDS = frozenset(
    {
        "ai-eng risk accept-all",
        "ai-eng risk accept",
    }
)


def _extract_content(tool_name: str, tool_input: dict) -> str:
    """Extract scannable content from tool input based on tool type."""
    if tool_name in ("Write", "MultiEdit"):
        return tool_input.get("content", "")
    if tool_name == "Edit":
        return tool_input.get("new_string", "")
    if tool_name == "Bash":
        return tool_input.get("command", "")
    return ""


def _parsed_command_prefix(command: str) -> str | None:
    """Return the first three argv tokens joined with single spaces.

    Used to match against ``WHITELISTED_COMMANDS``. Returns ``None`` when
    parsing fails (malformed quoting) or the command has fewer than two
    tokens (top-level only -- never enough to be a whitelisted invocation).
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) < 2:
        return None
    return " ".join(tokens[:3])


def _is_whitelisted(tool_name: str, content: str) -> str | None:
    """Return the matched whitelist key, or ``None`` if not whitelisted.

    Only Bash invocations can be whitelisted; Write/Edit/MultiEdit always
    pass through the pattern scan because the whitelist contract is
    ``ai-eng risk *`` CLI invocations -- not file edits.
    """
    if tool_name != "Bash":
        return None
    prefix = _parsed_command_prefix(content)
    if prefix is None:
        return None
    if prefix in WHITELISTED_COMMANDS:
        return prefix
    return None


def main() -> None:
    ctx = get_hook_context()
    tool_name = ctx.data.get("tool_name", "")

    if tool_name not in _GUARDED_TOOLS:
        passthrough_stdin(ctx.data)
        return

    tool_input = ctx.data.get("tool_input", {})
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}

    content = _extract_content(tool_name, tool_input)

    if len(content) < _MIN_CONTENT_LEN:
        passthrough_stdin(ctx.data)
        return

    # spec-105 G-12: short-circuit pattern scan for whitelisted CLI
    # invocations. The findings.json payload embeds rule names like
    # ``aws-access-token`` / ``stripe-key`` that the CRITICAL pattern set
    # would otherwise flag. Emit telemetry so the bypass remains auditable.
    matched_command = _is_whitelisted(tool_name, content)
    if matched_command is not None:
        argv_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        emit_control_outcome(
            ctx.project_root,
            category="security",
            control="prompt-guard-whitelisted",
            component="hook.prompt-injection-guard",
            outcome="success",
            source="hook",
            metadata={
                "tool": tool_name,
                "command": matched_command,
                "argv_hash": argv_hash,
            },
        )
        passthrough_stdin(ctx.data)
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
        emit_control_outcome(
            ctx.project_root,
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

            debug_log = ctx.project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
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

    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        sys.exit(e.code)
    except Exception:
        sys.exit(0)
