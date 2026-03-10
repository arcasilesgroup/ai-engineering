"""Shared frontmatter, checkbox, and spec-numbering utilities.

Provides deterministic parsing for YAML frontmatter in Markdown files,
checkbox counting for task tracking, spec numbering, and slug generation.
Single source of truth — consumed by ``spec_reset``,
``sync_command_mirrors``, ``spec_cmd``, and ``agents/plan.md``.
"""

from __future__ import annotations

import re
from pathlib import Path


def parse_frontmatter(text: str) -> dict[str, str]:
    """Extract YAML-like frontmatter key-value pairs from text.

    Supports simple ``key: "value"``, ``key: 'value'``, or ``key: value``
    lines between ``---`` fences.

    Args:
        text: File content with optional ``---`` fenced frontmatter.

    Returns:
        Dictionary of frontmatter keys to string values.
    """
    match = re.match(r"^---[ \t]*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        m = re.match(r"^(\w[\w-]*):[ \t]*(?:\"([^\"]*)\"|'([^']*)'|(.+))$", line.strip())
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


def next_spec_number(specs_dir: Path) -> int:
    """Determine next spec number from existing directories.

    Scans ``specs_dir`` (and its ``archive/`` subdirectory) for directories
    matching the ``NNN-<slug>`` pattern and returns ``max + 1``.  Returns 1
    when the directory is empty or does not exist.

    Args:
        specs_dir: Path to the specs directory (e.g. ``context/specs/``).

    Returns:
        Next sequential spec number.
    """
    max_num = 0
    if specs_dir.is_dir():
        for child in specs_dir.iterdir():
            if child.is_dir():
                match = re.match(r"^(\d{3})-", child.name)
                if match:
                    max_num = max(max_num, int(match.group(1)))
    # Also check archive
    archive = specs_dir / "archive"
    if archive.is_dir():
        for child in archive.iterdir():
            if child.is_dir():
                match = re.match(r"^(\d{3})-", child.name)
                if match:
                    max_num = max(max_num, int(match.group(1)))
    return max_num + 1


def slugify(text: str) -> str:
    """Convert text to a kebab-case slug.

    Lowercases, strips non-alphanumeric characters, collapses whitespace
    and underscores to hyphens, and truncates to 40 characters.

    Args:
        text: Human-readable text to slugify.

    Returns:
        Kebab-case slug suitable for directory or branch names.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s_-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:40]
