"""Spec lifecycle reset after PR merge (Working Buffer model).

Reads the current spec from ``specs/spec.md``, appends a history entry
to ``specs/_history.md``, and writes placeholder content to clear the
working buffer for the next ``/ai-brainstorm`` invocation.

Functions:
- ``check_active_spec`` -- read ``specs/spec.md`` and determine if content exists.
- ``clear_spec_buffer`` -- write placeholder content to spec.md and plan.md.
- ``append_history`` -- add a line to ``_history.md``.
- ``run_spec_reset`` -- orchestrate the full reset flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ai_engineering.lib.parsing import parse_frontmatter as _parse_frontmatter

_SPEC_PLACEHOLDER = "# No active spec\n\nRun /ai-brainstorm to start a new spec.\n"
_PLAN_PLACEHOLDER = "# No active plan\n\nRun /ai-plan after brainstorm approval.\n"


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
    spec_path = ai_eng_dir / "specs" / "spec.md"
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
    """Append a line to ``_history.md`` recording the completed spec.

    Creates the file with a table header if it does not exist.

    Args:
        specs_dir: Path to ``specs/`` directory.
        spec_id: Spec ID (e.g. ``"055"``).
        title: Spec title.
        branch: Git branch name (optional).

    Returns:
        True if the entry was appended.
    """
    history_path = specs_dir / "_history.md"
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    if not history_path.exists():
        header = (
            "# Spec History\n\n| ID | Title | Date | Branch |\n|-----|-------|------|--------|\n"
        )
        history_path.write_text(header, encoding="utf-8")

    entry = f"| {spec_id or '?'} | {title or 'untitled'} | {today} | {branch} |\n"
    with history_path.open("a", encoding="utf-8") as f:
        f.write(entry)

    return True


def clear_spec_buffer(specs_dir: Path) -> None:
    """Write placeholder content to ``spec.md`` and ``plan.md``.

    Args:
        specs_dir: Path to ``specs/`` directory.
    """
    (specs_dir / "spec.md").write_text(_SPEC_PLACEHOLDER, encoding="utf-8")
    (specs_dir / "plan.md").write_text(_PLAN_PLACEHOLDER, encoding="utf-8")


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
    ai_eng_dir = project_root / ".ai-engineering"
    specs_dir = ai_eng_dir / "specs"

    if not specs_dir.is_dir():
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

    # Append to history
    try:
        result.history_updated = append_history(specs_dir, spec_id, title)
    except OSError as e:
        result.errors.append(f"Failed to update history: {e}")

    # Clear the buffer
    try:
        clear_spec_buffer(specs_dir)
        result.files_cleared = True
    except OSError as e:
        result.errors.append(f"Failed to clear spec buffer: {e}")

    return result
