"""--no-verify, and everything else that skips .git/hooks.

The flag does not disable a hook, it skips the hook directory entirely, so no git hook
can catch its own bypass. This pre-denial is the only layer that can: it reads the
command before it runs. The old guard fired 3,798 times, and some of those were a
wrapper injecting the flag into a command the operator never typed.
"""

from __future__ import annotations

import re
from pathlib import Path

from _emit import repo_root
from _wrap import guard

SKIPS = (
    (r"\bgit\b[^|;&]*\b(commit|push|merge|rebase|am)\b[^|;&]*--no-verify", "--no-verify"),
    (r"\bgit\b[^|;&]*\bcommit\b[^|;&]*(?<![\w-])-[a-zA-Z]*n", "git commit -n"),
    (r"\bHUSKY=0\b|\bPRE_COMMIT_ALLOW_NO_VERIFY\b|\bSKIP_HOOKS\b", "an environment flag"),
    (r"\brm\b[^|;&]*\.git/hooks", "deleting .git/hooks"),
)

# The directory this install's git hooks live in, as a sibling of the guards. The same
# relationship in a checkout and under site-packages, and the only one available here:
# a guard never imports the package.
OURS = Path(__file__).resolve().parent.parent / "git-hooks"

INLINE = re.compile(r"-c\s+core\.hooksPath=(\S*)", re.I)


def targets(command: str) -> list[str]:
    """Every value this command would leave core.hooksPath at, as written. The empty
    string means unset, which stops every git hook in the repository and says nothing.
    A command that only reads the value returns nothing to judge."""
    words = command.split()
    found = [match.group(1).strip("\"'") for match in INLINE.finditer(command)]
    if "config" in words and any(word.lower() == "core.hookspath" for word in words):
        if any(word.startswith("--unset") for word in words):
            found.append("")
        elif not any(word in ("--get", "--get-all", "--list") for word in words):
            index = next(i for i, word in enumerate(words) if word.lower() == "core.hookspath")
            after = [word for word in words[index + 1 :] if not word.startswith("-")]
            found += [after[0].strip("\"'")] if after else []
    return found


def elsewhere(value: str) -> bool:
    """Decided on the value and never on the verb. Resolved against the repository root
    first, because this repository's own bootstrap writes the relative form and a string
    comparison would deny the command that installs the hooks."""
    if not value:
        return True
    root = repo_root() or Path.cwd()
    try:
        return (root / Path(value).expanduser()).resolve() != OURS.resolve()
    except OSError:
        return True


@guard("no_verify_guard")
def run(payload: dict) -> str | None:
    command = (payload.get("tool_input") or {}).get("command", "")
    if not isinstance(command, str) or not command:
        return None
    for value in targets(command):
        if elsewhere(value):
            return (
                f"this points core.hooksPath at {value or 'nothing'} instead of the "
                f"directory this install wires, so the git hooks stop running and nothing "
                f"says so. Whatever the hooks would have said is what needs fixing."
            )
    for pattern, label in SKIPS:
        if re.search(pattern, command):
            return (
                f"{label} skips the git hooks, which are the floor every agent and every "
                f"person in this repository commits through. Whatever the hooks would "
                f"have said is what needs fixing. Run the command without it."
            )
    return None
