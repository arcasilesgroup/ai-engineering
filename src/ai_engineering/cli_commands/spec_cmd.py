"""Spec lifecycle CLI commands.

Provides deterministic, zero-token commands for spec management:

- ``ai-eng spec verify``  — count checkboxes, auto-correct frontmatter.
- ``ai-eng spec catalog`` — generate ``_catalog.md`` from all specs.
- ``ai-eng spec list``    — display active specs with progress.
- ``ai-eng spec compact`` — archive old specs keeping only ``done.md``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.lib.parsing import count_checkboxes, parse_frontmatter


def _project_root() -> Path:
    """Walk up from cwd to find the project root."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".ai-engineering").is_dir():
            return parent
    return cwd


def _specs_dir(root: Path) -> Path:
    return root / ".ai-engineering" / "context" / "specs"


def _archive_dir(root: Path) -> Path:
    return _specs_dir(root) / "archive"


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


def _find_all_spec_files(root: Path) -> list[Path]:
    """Find all spec.md files in the archive directory."""
    archive = _archive_dir(root)
    if not archive.is_dir():
        return []
    specs = []
    for spec_dir in sorted(archive.iterdir()):
        if not spec_dir.is_dir():
            continue
        spec_file = spec_dir / "spec.md"
        if spec_file.exists():
            specs.append(spec_file)
    return specs


def _find_tasks_file(spec_path: Path) -> Path | None:
    """Find the tasks.md file for a spec (same dir or single-file sections)."""
    tasks_path = spec_path.parent / "tasks.md"
    if tasks_path.exists():
        return tasks_path
    return None


def _auto_correct_frontmatter(tasks_path: Path, real_total: int, real_completed: int) -> bool:
    """Rewrite total/completed in tasks.md frontmatter if they drift.

    Returns True if corrections were made.
    """
    text = tasks_path.read_text(encoding="utf-8")
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

    tasks_path.write_text("\n".join(new_lines), encoding="utf-8")
    return True


def spec_verify(
    spec_id: Annotated[
        str | None,
        typer.Argument(help="Spec dir name (e.g. 034-slug). Default: active."),
    ] = None,
    fix: Annotated[bool, typer.Option("--fix", help="Auto-correct drifted counters.")] = True,
) -> None:
    """Verify spec task counters and status consistency."""
    root = _project_root()

    # Resolve spec
    if spec_id is None:
        active_path = _specs_dir(root) / "_active.md"
        if not active_path.exists():
            typer.echo("No _active.md found.", err=True)
            raise typer.Exit(code=1)
        fm = parse_frontmatter(active_path.read_text(encoding="utf-8"))
        spec_id = fm.get("active", "")
        if not spec_id or spec_id in ("null", "none"):
            typer.echo("No active spec.", err=True)
            raise typer.Exit(code=1)

    # Find spec directory (check archive and top-level specs)
    spec_dir = _archive_dir(root) / spec_id
    if not spec_dir.is_dir():
        spec_dir = _specs_dir(root) / spec_id
    if not spec_dir.is_dir():
        typer.echo(f"Spec directory not found: {spec_id}", err=True)
        raise typer.Exit(code=1)

    # Find tasks source
    tasks_path = _find_tasks_file(spec_dir / "spec.md")
    tasks_text: str | None = None

    if tasks_path:
        tasks_text = tasks_path.read_text(encoding="utf-8")
    else:
        # Size S: tasks are in spec.md itself
        spec_file = spec_dir / "spec.md"
        if spec_file.exists():
            tasks_text = spec_file.read_text(encoding="utf-8")
            tasks_path = spec_file

    if not tasks_text:
        typer.echo(f"No tasks source found for {spec_id}", err=True)
        raise typer.Exit(code=1)

    # Count real checkboxes
    real_total, real_completed = count_checkboxes(tasks_text)
    fm = parse_frontmatter(tasks_text)
    fm_total = fm.get("total", "?")
    fm_completed = fm.get("completed", "?")

    drift_detected = fm_total != str(real_total) or fm_completed != str(real_completed)

    typer.echo(f"Spec: {spec_id}")
    typer.echo(f"  Checkboxes: {real_completed}/{real_total}")
    typer.echo(f"  Frontmatter: completed={fm_completed} total={fm_total}")

    if drift_detected:
        typer.echo("  DRIFT DETECTED")
        if fix and tasks_path:
            corrected = _auto_correct_frontmatter(tasks_path, real_total, real_completed)
            if corrected:
                typer.echo(f"  AUTO-FIXED: total={real_total}, completed={real_completed}")
    else:
        typer.echo("  OK — counters match")

    # Check done.md vs completion
    has_done = (spec_dir / "done.md").exists()
    if real_total > 0 and real_completed == real_total and not has_done:
        typer.echo("  WARNING: All tasks complete but done.md not found")

    # Emit signal
    _emit_signal(
        root,
        "spec_verified",
        {
            "spec_id": spec_id,
            "total": real_total,
            "completed": real_completed,
            "drift_detected": drift_detected,
        },
    )


def spec_catalog() -> None:
    """Generate _catalog.md from all spec frontmatter."""
    root = _project_root()
    spec_files = _find_all_spec_files(root)

    if not spec_files:
        typer.echo("No specs found in archive.")
        raise typer.Exit(code=1)

    entries: list[dict[str, str]] = []
    tag_index: dict[str, list[str]] = {}

    for spec_file in spec_files:
        text = spec_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        spec_id = fm.get("id", "?")
        slug = fm.get("slug", spec_file.parent.name)
        status = fm.get("status", "unknown")
        created = fm.get("created", "?")
        tags_raw = fm.get("tags", "")

        # Parse tags: could be [a, b] or a, b
        tags: list[str] = []
        if tags_raw and tags_raw not in ("?", ""):
            cleaned = tags_raw.strip("[]")
            tags = [t.strip() for t in cleaned.split(",") if t.strip()]

        # Check if compacted (only done.md)
        has_spec = spec_file.exists()
        has_done = (spec_file.parent / "done.md").exists()
        if not has_spec and has_done:
            status = "compacted"

        # Count tasks if tasks.md exists
        tasks_path = spec_file.parent / "tasks.md"
        task_count = ""
        if tasks_path.exists():
            total, completed = count_checkboxes(tasks_path.read_text(encoding="utf-8"))
            task_count = f"{completed}/{total}"

        entry = {
            "id": spec_id,
            "slug": slug,
            "status": status,
            "created": created,
            "tags": ", ".join(tags),
            "tasks": task_count,
            "dir": spec_file.parent.name,
        }
        entries.append(entry)

        for tag in tags:
            tag_index.setdefault(tag, []).append(f"{spec_id}-{slug}")

    # Generate catalog
    lines: list[str] = []
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    lines.append("---")
    lines.append(f'generated: "{today}"')
    lines.append(f"total_specs: {len(entries)}")
    lines.append("---")
    lines.append("")
    lines.append("# Spec Catalog")
    lines.append("")
    lines.append(f"Generated by `ai-eng spec catalog` on {today}.")
    lines.append("")
    lines.append("## Specs")
    lines.append("")
    lines.append("| ID | Slug | Status | Created | Tags | Tasks |")
    lines.append("|-----|------|--------|---------|------|-------|")

    for e in entries:
        lines.append(
            f"| {e['id']} | {e['slug']} | {e['status']} | {e['created']} "
            f"| {e['tags']} | {e['tasks']} |"
        )

    if tag_index:
        lines.append("")
        lines.append("## Tag Index")
        lines.append("")
        for tag in sorted(tag_index):
            specs_list = ", ".join(sorted(tag_index[tag]))
            lines.append(f"- **{tag}**: {specs_list}")

    lines.append("")
    catalog_path = _specs_dir(root) / "_catalog.md"
    catalog_path.write_text("\n".join(lines), encoding="utf-8")
    typer.echo(f"Catalog generated: {catalog_path.relative_to(root)} ({len(entries)} specs)")

    _emit_signal(
        root,
        "spec_catalog_generated",
        {
            "total_specs": len(entries),
            "tags": list(tag_index.keys()),
        },
    )


def spec_list() -> None:
    """Display active specs with progress."""
    root = _project_root()
    active_path = _specs_dir(root) / "_active.md"

    if not active_path.exists():
        typer.echo("No _active.md found.")
        return

    text = active_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    active = fm.get("active", "")

    if not active or active in ("null", "none"):
        typer.echo("No active spec.")
        return

    # Single active spec (current format)
    spec_dir = _archive_dir(root) / active
    if not spec_dir.is_dir():
        spec_dir = _specs_dir(root) / active
    if not spec_dir.is_dir():
        typer.echo(f"Active spec directory not found: {active}")
        return

    # Get progress
    tasks_path = spec_dir / "tasks.md"
    progress = "?"
    if tasks_path.exists():
        total, completed = count_checkboxes(tasks_path.read_text(encoding="utf-8"))
        if total > 0:
            pct = int(completed / total * 100)
            progress = f"{completed}/{total} ({pct}%)"
        else:
            progress = "0/0"

    # Get spec title
    spec_file = spec_dir / "spec.md"
    title = active
    if spec_file.exists():
        for line in spec_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

    typer.echo(f"Active: {active}")
    typer.echo(f"  Title: {title}")
    typer.echo(f"  Progress: {progress}")
    has_done = (spec_dir / "done.md").exists()
    typer.echo(f"  Done: {'yes' if has_done else 'no'}")


def spec_compact(
    older_than: Annotated[
        str, typer.Option("--older-than", help="Age threshold (e.g. 6m, 1y).")
    ] = "6m",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="List candidates without modifying.")
    ] = False,
) -> None:
    """Archive old specs by removing spec/plan/tasks.md, keeping done.md."""
    root = _project_root()
    archive = _archive_dir(root)

    if not archive.is_dir():
        typer.echo("No archive directory found.")
        return

    # Parse threshold
    threshold_days = _parse_age_threshold(older_than)
    now = datetime.now(tz=UTC)
    candidates: list[tuple[str, str]] = []  # (dir_name, created_date)

    for spec_dir in sorted(archive.iterdir()):
        if not spec_dir.is_dir():
            continue
        spec_file = spec_dir / "spec.md"
        done_file = spec_dir / "done.md"

        # Must have done.md and spec.md to be compactable
        if not done_file.exists() or not spec_file.exists():
            continue

        text = spec_file.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        created = fm.get("created", "")

        if not created:
            continue

        try:
            created_date = datetime.strptime(created, "%Y-%m-%d").replace(tzinfo=UTC)
            age_days = (now - created_date).days
            if age_days >= threshold_days:
                candidates.append((spec_dir.name, created))
        except ValueError:
            continue

    if not candidates:
        typer.echo(f"No specs older than {older_than} with done.md found.")
        return

    typer.echo(f"Compact candidates (older than {older_than}):")
    for name, created in candidates:
        typer.echo(f"  {name} (created: {created})")

    if dry_run:
        typer.echo(f"\n{len(candidates)} specs would be compacted (dry-run).")
        return

    compacted: list[str] = []
    for name, _ in candidates:
        spec_dir = archive / name
        removed = []
        for fname in ("spec.md", "plan.md", "tasks.md"):
            fpath = spec_dir / fname
            if fpath.exists():
                fpath.unlink()
                removed.append(fname)
        if removed:
            compacted.append(name)
            typer.echo(f"  Compacted {name}: removed {', '.join(removed)}")

    typer.echo(f"\n{len(compacted)} specs compacted.")

    _emit_signal(
        root,
        "spec_compacted",
        {
            "compacted_specs": compacted,
            "threshold": older_than,
        },
    )


def _parse_age_threshold(value: str) -> int:
    """Parse age string like '6m' or '1y' into days."""
    value = value.strip().lower()
    if value.endswith("m"):
        try:
            return int(value[:-1]) * 30
        except ValueError:
            pass
    elif value.endswith("y"):
        try:
            return int(value[:-1]) * 365
        except ValueError:
            pass
    elif value.endswith("d"):
        try:
            return int(value[:-1])
        except ValueError:
            pass

    typer.echo(f"Invalid age format: {value}. Use Nd, Nm, or Ny.", err=True)
    raise typer.Exit(code=1)
