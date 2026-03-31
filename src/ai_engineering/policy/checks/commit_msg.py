"""Commit message validation and gate trailer injection."""

from __future__ import annotations

import re
from pathlib import Path

_GATE_TRAILER = "Ai-Eng-Gate: passed"

_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|perf|refactor|style|docs|test|build|ci|chore|revert)"
    r"(\([^)]+\))?!?:\s+.+"
)


def validate_commit_message(msg: str) -> list[str]:
    """Validate a commit message against conventional commit format.

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

    if not _CONVENTIONAL_RE.match(first_line):
        errors.append(
            "Commit message should follow conventional commit format: type(scope): description"
        )

    return errors


def inject_gate_trailer(commit_msg_file: Path) -> None:
    """Append gate verification trailer if not already present."""
    try:
        content = commit_msg_file.read_text(encoding="utf-8")
    except OSError:
        return

    if _GATE_TRAILER in content:
        return

    updated = content.rstrip() + f"\n\n{_GATE_TRAILER}\n"
    try:
        commit_msg_file.write_text(updated, encoding="utf-8")
    except OSError:
        return
