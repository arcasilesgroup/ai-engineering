"""Spec lifecycle CLI commands (Working Buffer model).

Provides deterministic, zero-token commands for spec management:

- ``ai-eng spec verify``  -- count checkboxes in plan.md, auto-correct frontmatter.
- ``ai-eng spec list``    -- display current spec title and progress.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.lib.parsing import count_checkboxes, parse_frontmatter
from ai_engineering.paths import find_project_root


def _specs_dir(root: Path) -> Path:
    return root / ".ai-engineering" / "specs"


def _emit_signal(root: Path, event: str, detail: dict) -> None:
    """Emit a signal to audit-log.ndjson if the state module is available."""
    try:
        from ai_engineering.state.models import AuditEntry
        from ai_engineering.state.service import StateService

        entry = AuditEntry(
            timestamp=datetime.now(tz=UTC),
            event=event,
            actor="cli",
            detail=detail,
        )
        StateService(root).append_audit(entry)
    except (ImportError, OSError):
        pass


def _auto_correct_frontmatter(root: Path, real_total: int, real_completed: int) -> bool:
    """Rewrite total/completed in plan.md frontmatter if they drift.

    Returns True if corrections were made.
    """
    plan_path = _specs_dir(root) / "plan.md"
    text = plan_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    fm_total = fm.get("total", "")
    fm_completed = fm.get("completed", "")

    needs_fix = False
    if fm_total != str(real_total):
        needs_fix = True
    if fm_completed != str(real_completed):
        needs_fix = True

    if not needs_fix:
        return False

    lines = text.split("\n")
    new_lines: list[str] = []
    in_frontmatter = False
    fence_count = 0

    for line in lines:
        if line.strip() == "---":
            fence_count += 1
            if fence_count == 1:
                in_frontmatter = True
            elif fence_count == 2:
                in_frontmatter = False
            new_lines.append(line)
            continue

        if in_frontmatter:
            if line.strip().startswith("total:"):
                new_lines.append(f"total: {real_total}")
            elif line.strip().startswith("completed:"):
                new_lines.append(f"completed: {real_completed}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    plan_path.write_text("\n".join(new_lines), encoding="utf-8")
    return True


def spec_verify(
    fix: Annotated[bool, typer.Option("--fix", help="Auto-correct drifted counters.")] = True,
) -> None:
    """Verify spec task counters and status consistency.

    Reads specs/plan.md, counts checkboxes, verifies frontmatter, and
    optionally auto-corrects drift.
    """
    root = find_project_root()
    plan_path = _specs_dir(root) / "plan.md"

    if not plan_path.exists():
        typer.echo("No specs/plan.md found.", err=True)
        raise typer.Exit(code=1)

    plan_text = plan_path.read_text(encoding="utf-8")

    # Check for placeholder content
    if plan_text.strip().startswith("# No active plan"):
        typer.echo("No active plan.")
        return

    # Count real checkboxes
    real_total, real_completed = count_checkboxes(plan_text)
    fm = parse_frontmatter(plan_text)
    fm_total = fm.get("total", "?")
    fm_completed = fm.get("completed", "?")

    drift_detected = fm_total != str(real_total) or fm_completed != str(real_completed)

    typer.echo(f"  Checkboxes: {real_completed}/{real_total}")
    typer.echo(f"  Frontmatter: completed={fm_completed} total={fm_total}")

    if drift_detected:
        typer.echo("  DRIFT DETECTED")
        if fix:
            corrected = _auto_correct_frontmatter(root, real_total, real_completed)
            if corrected:
                typer.echo(f"  AUTO-FIXED: total={real_total}, completed={real_completed}")
    else:
        typer.echo("  OK -- counters match")

    # Emit signal
    _emit_signal(
        root,
        "spec_verified",
        {
            "total": real_total,
            "completed": real_completed,
            "drift_detected": drift_detected,
        },
    )


def spec_list() -> None:
    """Display current spec title and progress."""
    root = find_project_root()
    spec_path = _specs_dir(root) / "spec.md"
    plan_path = _specs_dir(root) / "plan.md"

    if not spec_path.exists():
        typer.echo("No specs/spec.md found.")
        return

    spec_text = spec_path.read_text(encoding="utf-8")

    # Check for placeholder content
    if spec_text.strip().startswith("# No active spec"):
        typer.echo("No active spec.")
        return

    # Extract title from first H1 heading
    title = "unknown"
    for line in spec_text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break

    # Get progress from plan.md
    progress = "?"
    if plan_path.exists():
        plan_text = plan_path.read_text(encoding="utf-8")
        if not plan_text.strip().startswith("# No active plan"):
            total, completed = count_checkboxes(plan_text)
            if total > 0:
                pct = int(completed / total * 100)
                progress = f"{completed}/{total} ({pct}%)"
            else:
                progress = "0/0"

    typer.echo(f"  Title: {title}")
    typer.echo(f"  Progress: {progress}")
