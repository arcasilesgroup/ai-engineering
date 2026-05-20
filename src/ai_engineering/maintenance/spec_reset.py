"""Spec lifecycle reset after PR merge (Working Buffer model).

Reads the current spec from ``specs/spec.md``, upserts a canonical
7-column history entry to ``specs/_history.md``, and writes placeholder
content to clear the
working buffer for the next ``/ai-brainstorm`` invocation.

Functions:
- ``check_active_spec`` -- read ``specs/spec.md`` and determine if content exists.
- ``clear_spec_buffer`` -- write placeholder content to spec.md and plan.md.
- ``append_history`` -- upsert a canonical row in ``_history.md``.
- ``run_spec_reset`` -- orchestrate the full reset flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering.lib.parsing import parse_frontmatter as _parse_frontmatter
from ai_engineering.state.work_plane import (
    clear_active_work_plane_pointer,
    ensure_work_plane_artifacts,
    resolve_active_work_plane,
)

_SPEC_PLACEHOLDER = "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n"
_PLAN_PLACEHOLDER = "# No active plan\n\nRun /ai-plan after brainstorm approval.\n"
_HISTORY_PREAMBLE = "# Spec History\n\nCompleted specs. Details in git history.\n\n"
_HISTORY_HEADER = (
    "| ID | Title | Status | Created | Shipped | PR | Branch |\n"
    "|----|-------|--------|---------|---------|----|--------|\n"
)


@dataclass
class SpecResetResult:
    """Outcome of a spec reset operation."""

    spec_title: str | None = None
    history_updated: bool = False
    files_cleared: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if reset completed without errors."""
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, object]:
        """Serialize the spec reset result as a plain dictionary for JSON output."""
        return {
            "success": self.success,
            "spec_title": self.spec_title,
            "history_updated": self.history_updated,
            "files_cleared": self.files_cleared,
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

        if self.spec_title:
            lines.append(f"- **Spec cleared**: `{self.spec_title}`")
        else:
            lines.append("- **Spec cleared**: none (no active spec)")

        lines.append(f"- **History updated**: {'yes' if self.history_updated else 'no'}")
        lines.append(f"- **Files cleared**: {'yes' if self.files_cleared else 'no'}")
        lines.append("")

        if self.errors:
            lines.append("### Errors")
            lines.append("")
            for e in self.errors:
                lines.append(f"- {e}")
            lines.append("")

        return "\n".join(lines)


def check_active_spec(ai_eng_dir: Path) -> tuple[str | None, str | None]:
    """Read ``specs/spec.md`` and extract title and ID.

    A spec is considered active when ``spec.md`` has real content
    (not the placeholder).

    Args:
        ai_eng_dir: Path to the ``.ai-engineering`` directory.

    Returns:
        Tuple of (title_or_None, spec_id_or_None).
    """
    spec_path = resolve_active_work_plane(ai_eng_dir.parent).spec_path
    if not spec_path.exists():
        return None, None

    text = spec_path.read_text(encoding="utf-8")

    # Check for placeholder
    if text.strip().startswith("# No active spec"):
        return None, None

    # Extract title from first H1
    title = None
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Extract ID from frontmatter
    fm = _parse_frontmatter(text)
    spec_id = fm.get("id", None)

    return title, spec_id


def append_history(
    specs_dir: Path,
    spec_id: str | None,
    title: str | None,
    branch: str = "",
) -> bool:
    """Upsert a canonical ``_history.md`` row for the completed spec.

    Creates the file with the 7-column canonical table when missing and
    migrates legacy 4/5/6-column rows on write. Existing rows with the
    same spec id are replaced rather than duplicated.

    Args:
        specs_dir: Path to ``specs/`` directory.
        spec_id: Spec ID (e.g. ``"055"``).
        title: Spec title.
        branch: Git branch name (optional).

    Returns:
        True if the entry was appended.
    """
    specs_dir.mkdir(parents=True, exist_ok=True)
    history_path = specs_dir / "_history.md"
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    target_id = spec_id or "?"
    entry = [
        target_id,
        title or "untitled",
        "done",
        today,
        today,
        "—",
        branch or "—",
    ]

    rows: list[list[str]] = []
    tail = ""
    if history_path.exists():
        rows, tail = _read_history_rows(history_path.read_text(encoding="utf-8"))

    replaced = False
    rendered_rows: list[list[str]] = []
    for row in rows:
        if row and row[0] == target_id:
            if not replaced:
                rendered_rows.append(entry)
                replaced = True
            continue
        rendered_rows.append(row)
    if not replaced:
        rendered_rows.append(entry)

    body = _HISTORY_PREAMBLE + _HISTORY_HEADER
    body += "\n".join("| " + " | ".join(row) + " |" for row in rendered_rows)
    body += "\n"
    if tail.strip():
        body += "\n" + tail.rstrip() + "\n"
    history_path.write_text(body, encoding="utf-8")

    return True


def _read_history_rows(text: str) -> tuple[list[list[str]], str]:
    """Read canonical row cells plus preserved free-form tail from history text."""
    table_rows, tail = _split_history(text)
    if len(table_rows) < 2:
        return [], tail
    migrated: list[list[str]] = []
    for row in table_rows[2:]:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) == 4:
            spec_id, row_title, date, row_branch = cells
            migrated.append([spec_id, row_title, "done", date, date, "—", row_branch or "—"])
        elif len(cells) == 5:
            spec_id, row_title, status, created, row_branch = cells
            migrated.append([spec_id, row_title, status, created, "—", "—", row_branch or "—"])
        elif len(cells) == 6:
            spec_id, row_title, status, created, shipped, row_branch = cells
            migrated.append([spec_id, row_title, status, created, shipped, "—", row_branch or "—"])
        elif len(cells) == 7:
            migrated.append(cells)
    return migrated, tail


def _split_history(text: str) -> tuple[list[str], str]:
    """Split markdown history into table rows and preserved free-form tail."""
    lines = text.splitlines()
    rows: list[str] = []
    tail_start = len(lines)
    in_table = False
    for i, line in enumerate(lines):
        if line.startswith("|"):
            in_table = True
            rows.append(line)
            continue
        if in_table:
            tail_start = i
            break
    return rows, "\n".join(lines[tail_start:]).lstrip("\n")


def clear_spec_buffer(specs_dir: Path) -> None:
    """Write placeholder content to ``spec.md`` and ``plan.md``.

    Args:
        specs_dir: Path to ``specs/`` directory.
    """
    ensure_spec_buffer_files(specs_dir, overwrite=True)


def ensure_spec_buffer_files(specs_dir: Path, *, overwrite: bool = False) -> tuple[bool, bool]:
    """Ensure compatibility buffer files exist, optionally overwriting them.

    Returns:
        Tuple of ``(spec_written, plan_written)``.
    """
    specs_dir.mkdir(parents=True, exist_ok=True)

    spec_path = specs_dir / "spec.md"
    plan_path = specs_dir / "plan.md"
    spec_written = overwrite or not spec_path.exists()
    plan_written = overwrite or not plan_path.exists()

    if spec_written:
        spec_path.write_text(_SPEC_PLACEHOLDER, encoding="utf-8")
    if plan_written:
        plan_path.write_text(_PLAN_PLACEHOLDER, encoding="utf-8")

    return spec_written, plan_written


def run_spec_reset(
    project_root: Path,
    *,
    dry_run: bool = False,
) -> SpecResetResult:
    """Orchestrate the full spec reset flow.

    Steps:
    1. Read ``specs/spec.md`` -- extract title and ID.
    2. Append entry to ``specs/_history.md``.
    3. Write placeholder content to ``spec.md`` and ``plan.md``.

    Args:
        project_root: Root directory of the project.
        dry_run: If True, report findings without modifying files.

    Returns:
        SpecResetResult with operation details.
    """
    result = SpecResetResult()
    work_plane = resolve_active_work_plane(project_root)
    ai_eng_dir = work_plane.ai_eng_dir
    legacy_specs_dir = ai_eng_dir / "specs"

    if not work_plane.specs_dir.is_dir():
        result.errors.append("Specs directory not found")
        return result

    # Check current spec
    title, spec_id = check_active_spec(ai_eng_dir)
    result.spec_title = title

    if title is None:
        # No active spec -- nothing to reset
        return result

    if dry_run:
        return result

    # History and compatibility placeholders stay on the legacy singleton
    # surface even when the active work plane is spec-scoped.
    try:
        result.history_updated = append_history(legacy_specs_dir, spec_id, title)
    except OSError as e:
        result.errors.append(f"Failed to update history: {e}")

    # Clear the compatibility buffer and then drop the pointer so consumers
    # fall back to the legacy singleton layout for the next activation.
    try:
        clear_spec_buffer(legacy_specs_dir)
        ensure_work_plane_artifacts(legacy_specs_dir)
        clear_active_work_plane_pointer(project_root)
        result.files_cleared = True
    except OSError as e:
        result.errors.append(f"Failed to clear spec buffer: {e}")

    return result
