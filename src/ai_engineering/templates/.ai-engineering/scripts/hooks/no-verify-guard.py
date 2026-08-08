#!/usr/bin/env python3
"""PreToolUse hook: token-aware ``--no-verify`` matcher (spec-131 sub-004 T-4.E).

Replaces the substring-glob ``Bash(*--no-verify*)`` deny rule that
previously sat at ``.claude/settings.json:19`` and produced false
positives on legitimate operations:

* ``AIENG_VERIFY_NO_VERIFY=1 git status`` — env-var prefix that happens
  to contain the substring.
* ``python3 -c "print('--no-verify')"`` — literal lives inside a
  quoted Python string, never reaches git.
* ``git log --grep='--no-verify'`` — legit search of the git log.

The matcher shlex-parses the Bash argv and denies ONLY when
``--no-verify`` appears as a discrete token under a git verb that
supports the flag (``commit``, ``push``, ``merge``, ``rebase``,
``cherry-pick``).

Exit codes:
- 0 — passthrough (no deny condition).
- 2 — deny (mirrors prompt-injection-guard semantics so the IDE knows
  the tool call was blocked by a policy hook).

Stdlib-only (no ``ai_engineering.*`` imports) — same sealed contract as
the rest of ``.ai-engineering/scripts/hooks/``.
"""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import passthrough_stdin
from _lib.hook_common import run_hook_safe
from _lib.hook_context import get_hook_context

_NO_VERIFY_VERBS: frozenset[str] = frozenset({"commit", "push", "merge", "rebase", "cherry-pick"})


def _strip_env_prefix(tokens: list[str]) -> list[str]:
    """Drop leading ``KEY=VALUE`` env-var prefix tokens.

    Bash accepts ``FOO=bar BAZ=qux git status`` as a valid invocation
    where the env-var assignments precede the command itself. shlex.split
    preserves those tokens; the matcher peels them off so the git verb
    detection operates on the actual argv.
    """
    out = list(tokens)
    while out and "=" in out[0] and not out[0].startswith("="):
        # Heuristic: first token contains `=` and starts with an identifier
        # character (alpha/underscore). Stops as soon as we hit the actual
        # command (e.g. ``git``).
        key = out[0].split("=", 1)[0]
        if not key or not (key[0].isalpha() or key[0] == "_"):
            break
        if not all(c.isalnum() or c == "_" for c in key):
            break
        out.pop(0)
    return out


def _is_no_verify_attempt(argv: str) -> bool:
    """Return True when ``argv`` is a git verb invocation carrying ``--no-verify``.

    Contract:
    1. shlex-parse ``argv``; malformed quoting -> True (fail CLOSED).
    2. Strip leading ``KEY=VALUE`` env-var prefix tokens.
    3. First non-env token MUST be ``git``.
    4. ``--no-verify`` MUST appear as a discrete argv token (not as a
       substring inside a quoted literal or a flag value).
    5. The first non-flag token after ``git`` MUST be in
       :data:`_NO_VERIFY_VERBS`.

    spec-147 G1 T-1.11/1.12: this hook is a security boundary on untrusted
    input. Previously a command with malformed quoting fell through to
    ``False`` (allow) — a ``git commit --no-verify`` hidden behind an
    unterminated quote slipped past the deny rule. We now fail CLOSED: a
    command we cannot parse is refused, because we cannot prove it is NOT a
    ``--no-verify`` bypass.
    """
    if not argv:
        return False
    try:
        tokens = shlex.split(argv)
    except ValueError:
        # Unparseable (e.g. unterminated quoting). We cannot prove the
        # command is safe, so refuse it (fail closed). A legitimate caller
        # ships well-formed Bash; a malformed command is itself a defect the
        # author must fix before re-running.
        return True
    tokens = _strip_env_prefix(tokens)
    if not tokens or tokens[0] != "git":
        return False
    if "--no-verify" not in tokens:
        return False
    verb = ""
    for token in tokens[1:]:
        if not token.startswith("-"):
            verb = token
            break
    return verb in _NO_VERIFY_VERBS


def main() -> None:
    ctx = get_hook_context()
    if ctx.data.get("tool_name") != "Bash":
        passthrough_stdin(ctx.data)
        return
    tool_input = ctx.data.get("tool_input") or {}
    if isinstance(tool_input, str):
        try:
            tool_input = json.loads(tool_input)
        except (json.JSONDecodeError, TypeError):
            tool_input = {}
    command = ""
    if isinstance(tool_input, dict):
        command = tool_input.get("command") or ""
    if not isinstance(command, str):
        command = ""
    if _is_no_verify_attempt(command):
        sys.stderr.write(
            "[no-verify-guard] refusing Bash: --no-verify is a deterministic "
            "deny rule.\n"
            "[no-verify-guard] remove the flag or escalate via the standard "
            "policy review.\n"
        )
        sys.stderr.flush()
        sys.stdout.write(
            json.dumps(
                {
                    "decision": "block",
                    "reason": "git --no-verify is denied (spec-131 sub-004 T-4.E).",
                }
            )
        )
        sys.stdout.flush()
        sys.exit(2)
    passthrough_stdin(ctx.data)


if __name__ == "__main__":
    run_hook_safe(
        main,
        component="hook.no-verify-guard",
        hook_kind="pre-tool-use",
        script_path=Path(__file__),
    )
