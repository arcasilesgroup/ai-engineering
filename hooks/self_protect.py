"""Writes against anything that governs the agent.

The first thing an agent obeying injected text does is unhook its guards. The list is
not maintained here: it is read from policy/surfaces.toml, which is the same file the
installer wires from, so it cannot fall behind the wiring.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from _wrap import guard

POLICY = Path(__file__).resolve().parent.parent / "policy" / "surfaces.toml"


def protected() -> list[str]:
    paths = tomllib.loads(POLICY.read_text(encoding="utf-8"))["protect"]["paths"]
    out = []
    for entry in paths:
        out.append(str(Path(entry).expanduser()) if entry.startswith("~") else entry)
    out.append(str(Path(__file__).resolve().parent))  # the guards themselves
    return out


def offends(text: str) -> str | None:
    for path in protected():
        if path in text:
            return path
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
        found = offends(command)
        if found and any(
            op in command for op in (">", ">>", "rm ", "mv ", "sed -i", "tee ", "chmod ")
        ):
            return (
                f"this command writes to {found}, which is part of what governs this "
                f"session. A person changes that, in a reviewed diff — not the session "
                f"it governs."
            )
    return None
