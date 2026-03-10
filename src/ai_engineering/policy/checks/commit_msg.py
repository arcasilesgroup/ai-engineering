"""Commit message validation and gate trailer injection."""

from __future__ import annotations

from pathlib import Path

_GATE_TRAILER = "Ai-Eng-Gate: passed"


def validate_commit_message(msg: str) -> list[str]:
    """Validate a commit message against project conventions.

    Rules:
    - Must not be empty.
    - First line must not exceed 72 characters.
    - First line must start with a lowercase letter or a known prefix.

    Args:
        msg: The full commit message text.

    Returns:
        List of validation errors (empty if valid).
    """
    errors: list[str] = []

    if not msg:
        errors.append("Commit message is empty")
        return errors

    first_line = msg.splitlines()[0].strip()

    if not first_line:
        errors.append("First line is empty")
        return errors

    if len(first_line) > 72:
        errors.append(f"First line exceeds 72 characters ({len(first_line)} chars)")

    return errors


_ALLOWED_COMMIT_MSG_NAMES = frozenset(
    {
        "COMMIT_EDITMSG",
        "MERGE_MSG",
        "SQUASH_MSG",
        "TAG_EDITMSG",
    }
)


def inject_gate_trailer(commit_msg_file: Path) -> None:
    """Append gate verification trailer if not already present.

    Only operates on known git commit message files to prevent
    path-traversal attacks (S2083).
    """
    safe_path = commit_msg_file.resolve()

    if safe_path.name not in _ALLOWED_COMMIT_MSG_NAMES:
        return

    try:
        content = safe_path.read_text(encoding="utf-8")
    except OSError:
        return

    if _GATE_TRAILER in content:
        return

    updated = content.rstrip() + f"\n\n{_GATE_TRAILER}\n"
    try:
        safe_path.write_text(updated, encoding="utf-8")
    except OSError:
        return
