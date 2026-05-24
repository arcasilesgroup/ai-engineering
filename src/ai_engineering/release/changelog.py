"""Keep-a-Changelog helpers for release promotion and validation."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

_CHANGELOG_SUBGROUPS = frozenset(
    {
        "Added",
        "Changed",
        "Deprecated",
        "Removed",
        "Fixed",
        "Security",
        "BREAKING",
    }
)
_SECTION_HEADING_PATTERN = re.compile(r"^##\s+\[(?P<name>[^\]]+)\](?P<suffix>.*)$", re.MULTILINE)
_TARGET_DATE_PATTERN = re.compile(r"^-\s+(?P<date>\d{4}-\d{2}-\d{2})$")


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
    else:
        unreleased_body = _section_body(text, unreleased)
        if not _has_release_note_content(unreleased_body):
            errors.append("CHANGELOG [Unreleased] release notes are empty")
        if not _has_keep_a_changelog_subgroup(unreleased_body):
            errors.append(
                "CHANGELOG [Unreleased] must include at least one Keep-a-Changelog "
                "subgroup (### Added, Changed, Deprecated, Removed, Fixed, Security, "
                "or BREAKING)"
            )
        # Keep-a-Changelog ``### Fixed`` entries are non-breaking bug fixes by
        # definition, so a release-path *fix* must not trip the BREAKING-subgroup
        # requirement that exists for release-path *semantic changes*. Scan every
        # subgroup except Fixed for the requirement trigger.
        semantic_body = _body_excluding_subsection(unreleased_body, "Fixed")
        if _release_path_semantics_changed(semantic_body):
            breaking_body = _subsection_body(unreleased_body, "BREAKING")
            if breaking_body is None or not _release_path_semantics_changed(breaking_body):
                errors.append(
                    "Release-path semantic changes in CHANGELOG [Unreleased] must be "
                    "documented under a ### BREAKING subgroup"
                )

    if _section_bounds(text, version) is not None:
        errors.append(f"CHANGELOG already contains [{version}] section")
        date_error = _validate_target_section_date(text, version)
        if date_error is not None:
            errors.append(date_error)

    return errors


def _section_body(text: str, bounds: tuple[int, int]) -> str:
    start, end = bounds
    lines = text[start:end].splitlines()
    return "\n".join(lines[1:]).strip()


def _has_release_note_content(section_body: str) -> bool:
    return any(
        line.strip() and not line.lstrip().startswith("#") for line in section_body.splitlines()
    )


def _changelog_subgroup_name(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("###"):
        return None
    name = stripped[3:]
    if not name or not name[0].isspace():
        return None
    normalized = name.strip()
    return normalized or None


def _has_keep_a_changelog_subgroup(section_body: str) -> bool:
    return any(
        name in _CHANGELOG_SUBGROUPS
        for line in section_body.splitlines()
        if (name := _changelog_subgroup_name(line)) is not None
    )


def _release_path_semantics_changed(text: str) -> bool:
    normalized = text.lower()
    if "semantic-release" in normalized and "removed" in normalized:
        return True
    return any(
        token in normalized
        for token in (
            "manual ci commit-back",
            "sole authority",
            "release packet",
            "trusted publishing",
            "testpypi",
        )
    )


def _subsection_body(section_body: str, heading: str) -> str | None:
    lines = section_body.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if _changelog_subgroup_name(line) == heading:
            start = index + 1
            break
    if start is None:
        return None

    end = len(lines)
    for index in range(start, len(lines)):
        if _changelog_subgroup_name(lines[index]) is not None:
            end = index
            break
    return "\n".join(lines[start:end]).strip()


def _body_excluding_subsection(section_body: str, heading: str) -> str:
    """Return the section body with the named ``### heading`` subgroup removed."""
    lines = section_body.splitlines()
    kept: list[str] = []
    in_target = False
    for line in lines:
        name = _changelog_subgroup_name(line)
        if name is not None:
            in_target = name == heading
            if in_target:
                continue
        if in_target:
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _validate_target_section_date(text: str, version: str) -> str | None:
    for match in _SECTION_HEADING_PATTERN.finditer(text):
        if match.group("name") != version:
            continue
        suffix = match.group("suffix").strip()
        date_match = _TARGET_DATE_PATTERN.fullmatch(suffix)
        if date_match is None:
            return f"CHANGELOG [{version}] section date must use format YYYY-MM-DD"
        try:
            date.fromisoformat(date_match.group("date"))
        except ValueError:
            return f"CHANGELOG [{version}] section date must use a valid YYYY-MM-DD date"
        return None
    return None


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

    changelog_path.resolve().write_text(updated, encoding="utf-8")
    return True
