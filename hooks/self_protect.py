"""Writes against anything that governs the agent.

The first thing an agent obeying injected text does is unhook its guards. The list is
not maintained here: it is read from policy/surfaces.toml, which is the same file the
installer wires from, so it cannot fall behind the wiring. A copied list can: a skills
root the installer writes into that appears in no entry, or an unprotected policy
directory, lets one edit to the IOC catalogue disarm the injection guard. The settings
and skills columns are derived here, never copied.

A shell command is judged one command at a time. Deciding over the whole string joined a
protected path named in one command to a `>` belonging to another and reported a write
that never happened: `cat <a protected file> 2>/dev/null; ls <the same directory>` was
denied twice in a real session, and the second time the two halves were on different
lines. Inside one command, a redirect is judged by where it points, never by what else the
command mentions.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from _wrap import guard

POLICY = Path(__file__).resolve().parent.parent / "policy" / "surfaces.toml"

# A command whose first word is one of these writes wherever its arguments point, so a
# protected path anywhere in it is a write to that path. `sed` joins them only with -i,
# which is the difference between rewriting a file and printing part of it. The list is
# allowed to fall behind towards denying too much: that is a person told to use the edit
# tool, rather than a write nobody saw.
WRITERS = (
    "rm",
    "mv",
    "cp",
    "install",
    "truncate",
    "dd",
    "tee",
    "chmod",
    "chown",
    "ln",
    "python",
    "python3",
    "perl",
    "ruby",
    "node",
    "sh",
    "bash",
    "zsh",
)

# Where a redirect points, which is the only thing about a redirect that matters. `2>&1`
# points at a file descriptor and `2>/dev/null` at the bit bucket; neither is a write to
# whatever else the command happens to name.
REDIRECT = re.compile(r"\d*>>?\s*(\"[^\"]*\"|'[^']*'|[^\s;|&]+)")
SEPARATORS = re.compile(r"[\n;|&]+")


def protected() -> list[str]:
    """Every path this session may not write to, derived from the wiring table and from
    where this file itself is. Empty values are dropped: the test below is a substring
    test, and an empty string is a substring of every command on the machine."""
    table = tomllib.loads(POLICY.read_text(encoding="utf-8"))
    entries = list(table["protect"]["paths"])
    for surface in table["surface"]:
        settings = surface.get("settings", "")
        if settings:
            # Where the file carries our name, the directory holding it is one we created
            # and the whole of it is protected. Where it is the surface's own settings
            # file, only that file is — protecting ~/.claude would deny every write
            # anywhere under it, including a person's own notes.
            name = Path(settings).name
            entries.append(str(Path(settings).parent) if "ai-eng" in name else settings)
        if surface.get("skills"):
            entries.append(surface["skills"])
    out = []
    for entry in entries:
        if entry:
            out.append(str(Path(entry).expanduser()) if entry.startswith("~") else entry)
    guards = Path(__file__).resolve().parent
    out.append(str(guards))  # the guards themselves
    if not (guards.parent / "pyproject.toml").exists():
        # The wheel's own data, as siblings of the guards. Skipped in a working copy of
        # this project, which is exactly what an editable install is, and where protecting
        # it would deny every edit anybody makes in here.
        out += [str(guards.parent / name) for name in ("policy", "git-hooks", "surfaces")]
    return sorted(set(out))


def offends(text: str) -> str | None:
    for path in protected():
        if path in text:
            return path
    return None


def writes(command: str) -> str | None:
    """The protected path this one shell command writes to, or None. Two ways it can: a
    verb that writes wherever its arguments point, or a redirect aimed at the path."""
    words = command.split()
    if not words:
        return None
    verb = Path(words[0]).name
    if verb in WRITERS or (verb == "sed" and "-i" in words):
        return offends(command)
    for match in REDIRECT.finditer(command):
        found = offends(match.group(1).strip("\"'"))
        if found:
            return found
    return None


@guard("self_protect")
def run(payload: dict) -> str | None:
    args = payload.get("tool_input") or {}
    target = args.get("file_path") or args.get("path") or ""
    if target:
        resolved = str(Path(str(target)).expanduser().resolve())
        found = offends(resolved) or offends(str(target))
        if found:
            return (
                f"{target} is part of what governs this session — it is how the rules "
                f"reach you and how what happens here is recorded. Changing it from "
                f"inside the session it governs is not a change a session gets to make. "
                f"A person edits it, in a diff, in a pull request."
            )
    command = args.get("command", "")
    if isinstance(command, str) and command:
        # The protected list holds expanded paths only, so a command written with a tilde
        # matched nothing and every one of these denials could be skipped by typing ~.
        expanded = command.replace("~/", f"{Path.home()}/")
        pieces = SEPARATORS.split(expanded)
        for index, one in enumerate(pieces):
            # A heredoc is one command that spans lines, and what it writes is in the body
            # underneath rather than on the line that opened it.
            found = writes(" ".join(pieces[index:]) if "<<" in one else one)
            if found:
                return (
                    f"this command writes to {found}, which is part of what governs this "
                    f"session. A person changes that, in a reviewed diff — not the session "
                    f"it governs."
                )
    return None
