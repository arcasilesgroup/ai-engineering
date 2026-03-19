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
            # Use 'is not None' — empty strings (e.g. `key: ""`) are valid values.
            value = (
                m.group(2)
                if m.group(2) is not None
                else m.group(3)
                if m.group(3) is not None
                else m.group(4) or ""
            )
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
    """Determine next spec number from ``_history.md``.

    Parses the history table for rows matching ``| NNN | ...`` and
    returns ``max + 1``.  Falls back to scanning ``spec.md`` frontmatter
    for the current ID.  Returns 1 when no history exists.

    Args:
        specs_dir: Path to the specs directory (e.g. ``specs/``).

    Returns:
        Next sequential spec number.
    """
    max_num = 0

    # Parse _history.md table rows
    history_path = specs_dir / "_history.md"
    if history_path.exists():
        text = history_path.read_text(encoding="utf-8")
        for line in text.splitlines():
            match = re.match(r"^\|\s*(\d{3})\s*\|", line)
            if match:
                max_num = max(max_num, int(match.group(1)))

    # Also check current spec.md frontmatter ID
    spec_path = specs_dir / "spec.md"
    if spec_path.exists():
        from ai_engineering.lib.parsing import parse_frontmatter

        fm = parse_frontmatter(spec_path.read_text(encoding="utf-8"))
        spec_id = fm.get("id", "")
        id_match = re.match(r"^(\d{3})$", spec_id.strip())
        if id_match:
            max_num = max(max_num, int(id_match.group(1)))

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
