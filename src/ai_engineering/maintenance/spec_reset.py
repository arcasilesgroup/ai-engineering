"""Spec lifecycle reset after PR merge.

Detects completed specs, archives them, and resets ``_active.md``
so the repository is ready for the next ``/create-spec`` invocation.

Functions:
- ``check_active_spec`` — read ``_active.md`` and determine completion status.
- ``find_completed_specs`` — scan specs directory for completed specs.
- ``archive_spec`` — move a completed spec to ``specs/archive/``.
- ``reset_active_md`` — write a clean ``_active.md`` with no active spec.
- ``run_spec_reset`` — orchestrate the full reset flow.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SpecResetResult:
    """Outcome of a spec reset operation."""

    active_spec_cleared: bool = False
    archived_specs: list[str] = field(default_factory=list)
    orphan_specs: list[str] = field(default_factory=list)
    active_spec_was: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if reset completed without errors."""
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, object]:
        """Serialize the spec reset result as a plain dictionary for JSON output."""
        return {
            "success": self.success,
            "active_spec_cleared": self.active_spec_cleared,
            "active_spec_was": self.active_spec_was,
            "archived_specs": self.archived_specs,
            "orphan_specs": self.orphan_specs,
            "errors": self.errors,
        }

    def to_markdown(self) -> str:
        """Render the reset result as Markdown.

        Returns:
            Markdown-formatted spec reset summary.
        """
        lines: list[str] = []
        lines.append("## Spec Reset Summary")
        lines.append("")

        if self.active_spec_was:
            lines.append(f"- **Previous active spec**: `{self.active_spec_was}`")
        else:
            lines.append("- **Previous active spec**: none")

        lines.append(f"- **Active spec cleared**: {'yes' if self.active_spec_cleared else 'no'}")
        lines.append(f"- **Specs archived**: {len(self.archived_specs)}")
        lines.append(f"- **Orphan specs found**: {len(self.orphan_specs)}")
        lines.append("")

        if self.archived_specs:
            lines.append("### Archived")
            lines.append("")
            for slug in sorted(self.archived_specs):
                lines.append(f"- `{slug}`")
            lines.append("")

        if self.orphan_specs:
            lines.append("### Orphans (completed but not yet archived)")
            lines.append("")
            for slug in sorted(self.orphan_specs):
                lines.append(f"- `{slug}`")
            lines.append("")

        if self.errors:
            lines.append("### Errors")
            lines.append("")
            for e in self.errors:
                lines.append(f"- {e}")
            lines.append("")

        return "\n".join(lines)


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract YAML-like frontmatter key-value pairs from text.

    Supports simple ``key: "value"`` or ``key: value`` lines
    between ``---`` fences.

    Args:
        text: File content with optional frontmatter.

    Returns:
        Dictionary of frontmatter keys to string values.
    """
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip('"').strip("'")
        result[key.strip()] = value

    return result


def check_active_spec(ai_eng_dir: Path) -> tuple[str | None, bool]:
    """Read ``_active.md`` and determine if the active spec is completed.

    A spec is considered completed when:
    1. Its directory contains ``done.md``, OR
    2. Its ``tasks.md`` has ``completed == total`` in frontmatter.

    Args:
        ai_eng_dir: Path to the ``.ai-engineering`` directory.

    Returns:
        Tuple of (slug_or_None, is_completed).
    """
    active_path = ai_eng_dir / "context" / "specs" / "_active.md"
    if not active_path.exists():
        return None, False

    text = active_path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    slug = fm.get("active", "").strip()

    if not slug or slug == "null" or slug == "none":
        return None, False

    spec_dir = ai_eng_dir / "context" / "specs" / slug
    if not spec_dir.is_dir():
        return slug, False

    # Check for done.md
    if (spec_dir / "done.md").exists():
        return slug, True

    # Check tasks.md frontmatter
    tasks_path = spec_dir / "tasks.md"
    if tasks_path.exists():
        tasks_fm = _parse_frontmatter(tasks_path.read_text(encoding="utf-8"))
        total = tasks_fm.get("total", "")
        completed = tasks_fm.get("completed", "")
        if total and completed and total == completed:
            try:
                if int(total) > 0 and int(completed) > 0:
                    return slug, True
            except ValueError:
                pass

    return slug, False


def find_completed_specs(specs_dir: Path) -> list[str]:
    """Find completed specs outside the ``archive/`` directory.

    Detection heuristics:
    1. Has ``done.md`` in spec directory.
    2. Has ``tasks.md`` with ``completed == total`` (both > 0).

    Args:
        specs_dir: Path to ``context/specs/`` directory.

    Returns:
        List of slug names for completed specs outside archive.
    """
    completed: list[str] = []

    for item in sorted(specs_dir.iterdir()):
        if not item.is_dir():
            continue
        if item.name == "archive" or item.name.startswith("_"):
            continue

        # Check done.md
        if (item / "done.md").exists():
            completed.append(item.name)
            continue

        # Check tasks.md frontmatter
        tasks_path = item / "tasks.md"
        if tasks_path.exists():
            try:
                fm = _parse_frontmatter(tasks_path.read_text(encoding="utf-8"))
                total = fm.get("total", "")
                comp = fm.get("completed", "")
                if total and comp and total == comp and int(total) > 0 and int(comp) > 0:
                    completed.append(item.name)
            except (ValueError, OSError):
                continue

    return completed


def archive_spec(specs_dir: Path, slug: str) -> bool:
    """Move a spec directory to ``specs/archive/``.

    Args:
        specs_dir: Path to ``context/specs/`` directory.
        slug: Spec directory name (e.g. ``022-test-pyramid-rewrite``).

    Returns:
        True if the spec was successfully archived.
    """
    source = specs_dir / slug
    if not source.is_dir():
        return False

    archive_dir = specs_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    dest = archive_dir / slug
    if dest.exists():
        return False  # Already archived

    shutil.move(str(source), str(dest))
    return True


def reset_active_md(active_path: Path) -> None:
    """Write a clean ``_active.md`` with no active spec.

    Args:
        active_path: Path to ``_active.md`` file.
    """
    from datetime import UTC, datetime

    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    content = f"""---
active: null
updated: "{today}"
---

# Active Spec

No active spec. Ready for `/create-spec`.

## Quick Resume

No spec in progress.
"""
    active_path.write_text(content, encoding="utf-8")


def run_spec_reset(
    project_root: Path,
    *,
    dry_run: bool = False,
) -> SpecResetResult:
    """Orchestrate the full spec reset flow.

    Steps:
    1. Check if ``_active.md`` points to a completed spec.
    2. Find any completed specs outside ``archive/``.
    3. Archive completed specs (unless dry_run).
    4. Reset ``_active.md`` (unless dry_run).

    Args:
        project_root: Root directory of the project.
        dry_run: If True, report findings without modifying files.

    Returns:
        SpecResetResult with operation details.
    """
    result = SpecResetResult()
    ai_eng_dir = project_root / ".ai-engineering"
    specs_dir = ai_eng_dir / "context" / "specs"

    if not specs_dir.is_dir():
        result.errors.append("Specs directory not found")
        return result

    # Check active spec
    active_slug, active_completed = check_active_spec(ai_eng_dir)
    result.active_spec_was = active_slug

    # Find all completed specs outside archive
    completed = find_completed_specs(specs_dir)
    result.orphan_specs = completed

    if dry_run:
        return result

    # Archive completed specs
    for slug in completed:
        try:
            if archive_spec(specs_dir, slug):
                result.archived_specs.append(slug)
        except OSError as e:
            result.errors.append(f"Failed to archive {slug}: {e}")

    # Reset _active.md if active spec is completed or was archived
    active_path = specs_dir / "_active.md"
    if active_completed or (active_slug and active_slug in completed):
        reset_active_md(active_path)
        result.active_spec_cleared = True

    # Update orphans list — remove successfully archived ones
    result.orphan_specs = [s for s in completed if s not in result.archived_specs]

    return result
