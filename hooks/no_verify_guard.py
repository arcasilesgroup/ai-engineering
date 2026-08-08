"""--no-verify, and everything else that skips .git/hooks.

The flag does not disable a hook, it skips the hook directory entirely, so no git hook
can catch its own bypass. This pre-denial is the only layer that can: it reads the
command before it runs. The old guard fired 3,798 times, and some of those were a
wrapper injecting the flag into a command the operator never typed.
"""

from __future__ import annotations

import re

from _wrap import guard

SKIPS = (
    (r"\bgit\b[^|;&]*\b(commit|push|merge|rebase|am)\b[^|;&]*--no-verify", "--no-verify"),
    (r"\bgit\b[^|;&]*\bcommit\b[^|;&]*(?<![\w-])-[a-zA-Z]*n", "git commit -n"),
    (r"\bgit\b[^|;&]*-c\s+core\.hooksPath=", "-c core.hooksPath="),
    (r"\bHUSKY=0\b|\bPRE_COMMIT_ALLOW_NO_VERIFY\b|\bSKIP_HOOKS\b", "an environment flag"),
    (r"\brm\b[^|;&]*\.git/hooks", "deleting .git/hooks"),
)


@guard("no_verify_guard")
def run(payload: dict) -> str | None:
    command = (payload.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str) or not command:
        return None
    for pattern, label in SKIPS:
        if re.search(pattern, command):
            return (
                f"{label} skips the git hooks, which are the floor every agent and every "
                f"person in this repository commits through. Whatever the hooks would "
                f"have said is what needs fixing. Run the command without it."
            )
    return None
