"""Keep-a-Changelog helpers for release promotion and validation."""

from __future__ import annotations

import os
import re
from pathlib import Path


def _section_bounds(text: str, heading: str) -> tuple[int, int] | None:
    pattern = re.compile(rf"^##\s+\[{re.escape(heading)}\].*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return None
    start = match.start()
    next_match = re.compile(r"^##\s+\[", re.MULTILINE).search(text, match.end())
    end = len(text) if next_match is None else next_match.start()
    return start, end


def extract_release_notes(changelog_path: Path, version: str) -> str | None:
    """Extract release notes for a specific version section."""
    text = changelog_path.read_text(encoding="utf-8")
    bounds = _section_bounds(text, version)
    if bounds is None:
        return None
    start, end = bounds
    section = text[start:end].strip()
    lines = section.splitlines()
    if not lines:
        return None
    body = "\n".join(lines[1:]).strip()
    return body or None


def validate_changelog(changelog_path: Path, version: str) -> list[str]:
    """Return blocking changelog validation errors."""
    text = changelog_path.read_text(encoding="utf-8")
    errors: list[str] = []

    unreleased = _section_bounds(text, "Unreleased")
    if unreleased is None:
        errors.append("Missing [Unreleased] section in CHANGELOG.md")

    if _section_bounds(text, version) is not None:
        errors.append(f"CHANGELOG already contains [{version}] section")

    return errors


def promote_unreleased(changelog_path: Path, version: str, date_str: str) -> bool:
    """Move [Unreleased] content to [version] - date and clear unreleased."""
    text = changelog_path.read_text(encoding="utf-8")
    bounds = _section_bounds(text, "Unreleased")
    if bounds is None:
        return False

    start, end = bounds
    section = text[start:end]
    lines = section.splitlines()
    if not lines:
        return False

    body_lines = lines[1:]
    body = "\n".join(body_lines).strip("\n")
    promoted = f"## [{version}] - {date_str}\n"
    if body.strip():
        promoted += f"\n{body.strip()}\n"
    else:
        promoted += "\n"

    unreleased_replacement = "## [Unreleased]\n\n"
    new_block = unreleased_replacement + promoted
    updated = text[:start] + new_block + text[end:]

    canonical = os.path.realpath(changelog_path)
    if Path(canonical).name != "CHANGELOG.md":
        return False
    Path(canonical).write_text(updated, encoding="utf-8")
    return True
