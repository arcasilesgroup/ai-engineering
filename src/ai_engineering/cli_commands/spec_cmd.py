"""Spec lifecycle CLI commands (Working Buffer model).

Provides deterministic, zero-token commands for spec management:

- ``ai-eng spec activate`` -- point runtime consumers at a work-plane root.
- ``ai-eng spec verify``  -- count checkboxes in plan.md, auto-correct frontmatter.
- ``ai-eng spec list``    -- display current spec title and progress.
"""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_ui import error, info, kv, status_line, success, warning
from ai_engineering.lib.parsing import count_checkboxes, parse_frontmatter
from ai_engineering.maintenance.spec_activate import run_spec_activate
from ai_engineering.paths import find_project_root
from ai_engineering.state.models import TaskLifecycleState
from ai_engineering.state.observability import emit_framework_operation
from ai_engineering.state.work_plane import read_task_ledger, resolve_active_work_plane

_SPEC_FILENAME = "spec.md"
_PLAN_FILENAME = "plan.md"


def _specs_dir(root: Path) -> Path:
    return resolve_active_work_plane(root).specs_dir


def _emit_signal(root: Path, event: str, detail: dict) -> None:
    """Emit a framework operation event if observability is available."""
    with suppress(OSError):
        emit_framework_operation(
            root,
            operation=event,
            component="cli.spec",
            source="cli",
            metadata=detail,
        )


def _auto_correct_frontmatter(root: Path, real_total: int, real_completed: int) -> bool:
    """Rewrite total/completed in plan.md frontmatter if they drift.

    Returns True if corrections were made.
    """
    plan_path = _specs_dir(root) / _PLAN_FILENAME
    text = plan_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    fm_total = fm.get("total", "")
    fm_completed = fm.get("completed", "")

    if fm_total == str(real_total) and fm_completed == str(real_completed):
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

        new_lines.append(
            _rewrite_frontmatter_line(
                line,
                in_frontmatter=in_frontmatter,
                real_total=real_total,
                real_completed=real_completed,
            )
        )

    plan_path.write_text("\n".join(new_lines), encoding="utf-8")
    return True


def _rewrite_frontmatter_line(
    line: str,
    *,
    in_frontmatter: bool,
    real_total: int,
    real_completed: int,
) -> str:
    """Rewrite one line of plan frontmatter when counters drift."""
    if not in_frontmatter:
        return line

    stripped = line.strip()
    if stripped.startswith("total:"):
        return f"total: {real_total}"
    if stripped.startswith("completed:"):
        return f"completed: {real_completed}"
    return line


def spec_activate(
    specs_dir: Annotated[
        Path,
        typer.Option("--specs-dir", help="Project-relative specs dir to mark active."),
    ],
) -> None:
    """Activate a work plane and ensure compatibility buffer files exist."""
    root = find_project_root()
    result = run_spec_activate(root, specs_dir)

    if not result.success:
        for item in result.errors:
            error(item)
        raise typer.Exit(code=1)

    relative_specs_dir = result.specs_dir.resolve().relative_to(root.resolve()).as_posix()
    kv("Specs dir", relative_specs_dir)
    kv("Pointer", "enabled" if result.pointer_enabled else "legacy singleton")
    kv("spec.md", "created" if result.spec_created else "preserved")
    kv("plan.md", "created" if result.plan_created else "preserved")
    success("Active work plane updated.")
    _emit_signal(
        root,
        "spec_activated",
        {
            "specs_dir": relative_specs_dir,
            "pointer_enabled": result.pointer_enabled,
        },
    )


def spec_verify(
    fix: Annotated[bool, typer.Option("--fix", help="Auto-correct drifted counters.")] = True,
) -> None:
    """Verify spec task counters and status consistency.

    Reads specs/plan.md, counts checkboxes, verifies frontmatter, and
    optionally auto-corrects drift.
    """
    root = find_project_root()
    plan_path = _specs_dir(root) / _PLAN_FILENAME

    if not plan_path.exists():
        error("No specs/plan.md found.")
        raise typer.Exit(code=1)

    plan_text = plan_path.read_text(encoding="utf-8")

    # Check for placeholder content
    if plan_text.strip().startswith("# No active plan"):
        info("No active plan.")
        return

    # Count real checkboxes
    real_total, real_completed = count_checkboxes(plan_text)
    fm = parse_frontmatter(plan_text)
    fm_total = fm.get("total", "?")
    fm_completed = fm.get("completed", "?")

    drift_detected = fm_total != str(real_total) or fm_completed != str(real_completed)

    kv("Checkboxes", f"{real_completed}/{real_total}")
    kv("Frontmatter", f"completed={fm_completed} total={fm_total}")

    if drift_detected:
        warning("Drift detected")
        if fix:
            corrected = _auto_correct_frontmatter(root, real_total, real_completed)
            if corrected:
                success(f"Auto-fixed: total={real_total}, completed={real_completed}")
    else:
        status_line("ok", "Counters", "match")

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
    specs_dir = _specs_dir(root)
    spec_path = specs_dir / _SPEC_FILENAME
    plan_path = specs_dir / _PLAN_FILENAME

    if not spec_path.exists():
        info("No specs/spec.md found.")
        return

    spec_text = spec_path.read_text(encoding="utf-8")
    placeholder_spec = spec_text.strip().startswith("# No active spec")
    if placeholder_spec:
        ledger = read_task_ledger(root)
        if ledger is None or all(task.status == TaskLifecycleState.DONE for task in ledger.tasks):
            info("No active spec.")
            return

    title = specs_dir.name if placeholder_spec else "unknown"
    if not placeholder_spec:
        for line in spec_text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

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

    kv("Title", title)
    kv("Progress", progress)
