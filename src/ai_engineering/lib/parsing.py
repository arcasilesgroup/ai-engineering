"""Shared frontmatter and checkbox parsing utilities.

Provides deterministic parsing for YAML frontmatter in Markdown files
and checkbox counting for task tracking.  Single source of truth —
consumed by ``spec_reset``, ``sync_command_mirrors``, and ``spec_cmd``.
"""

from __future__ import annotations

import re


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract YAML-like frontmatter key-value pairs from text.

    Supports simple ``key: "value"``, ``key: 'value'``, or ``key: value``
    lines between ``---`` fences.

    Args:
        text: File content with optional ``---`` fenced frontmatter.

    Returns:
        Dictionary of frontmatter keys to string values.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        m = re.match(r"^(\w[\w-]*):\s*(?:\"(.*?)\"|'(.*?)'|(.+))$", line.strip())
        if m:
            key = m.group(1)
            value = m.group(2) or m.group(3) or m.group(4)
            result[key] = value.strip()
    return result


def count_checkboxes(text: str) -> tuple[int, int]:
    """Count Markdown task checkboxes in text.

    Recognises ``- [ ] …`` (unchecked) and ``- [x] …`` / ``- [X] …``
    (checked).

    Args:
        text: Markdown content with checkbox task lists.

    Returns:
        Tuple of (total_checkboxes, checked_checkboxes).
    """
    checked = len(re.findall(r"^- \[[xX]\] ", text, re.MULTILINE))
    unchecked = len(re.findall(r"^- \[ \] ", text, re.MULTILINE))
    return checked + unchecked, checked
