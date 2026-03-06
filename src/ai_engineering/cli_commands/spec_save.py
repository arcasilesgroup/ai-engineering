"""Spec save CLI command.

Reads a structured spec from stdin or file, validates it, and persists
to disk as spec/plan/tasks files. Deterministic — no AI tokens consumed.

Usage::

    cat <<'EOF' | ai-eng spec save --title "OAuth Auth"
    ## Problem
    No social auth...
    ## Solution
    Implement OAuth 2.0...
    ## Tasks
    - [ ] 1.1 Configure provider
    - [ ] 1.2 Create callback endpoint
    EOF

Or from file::

    ai-eng spec save --file /tmp/spec-draft.md --title "OAuth Auth"
"""

from __future__ import annotations

import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.lib.parsing import count_checkboxes


def _project_root() -> Path:
    """Walk up from cwd to find the project root."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".ai-engineering").is_dir():
            return parent
    return cwd


def _specs_dir(root: Path) -> Path:
    return root / ".ai-engineering" / "context" / "specs"


def _next_spec_number(specs_dir: Path) -> int:
    """Determine next spec number from existing directories."""
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


def _extract_section(text: str, heading: str) -> str:
    """Extract content under a ## heading until next ## or end."""
    pattern = rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _extract_title(text: str) -> str:
    """Extract title from first # heading."""
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _slugify(text: str) -> str:
    """Convert text to kebab-case slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:40]


def _validate_spec_content(text: str) -> list[str]:
    """Validate that required sections exist. Returns list of errors."""
    errors: list[str] = []
    required = ["Problem", "Solution"]
    for section in required:
        if not _extract_section(text, section):
            errors.append(f"Missing required section: ## {section}")
    return errors


def _build_spec_md(
    spec_num: int,
    slug: str,
    title: str,
    content: str,
    pipeline: str,
    size: str,
    tags: list[str],
    branch: str,
) -> str:
    """Build spec.md from parsed content."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    tags_str = "[" + ", ".join(f'"{t}"' for t in tags) + "]" if tags else "[]"

    problem = _extract_section(content, "Problem")
    solution = _extract_section(content, "Solution")
    scope = _extract_section(content, "Scope")
    acceptance = _extract_section(content, "Acceptance Criteria")
    decisions = _extract_section(content, "Decisions")

    lines = [
        "---",
        f'id: "{spec_num:03d}"',
        f'slug: "{slug}"',
        'status: "in-progress"',
        f'created: "{today}"',
        f'size: "{size}"',
        f"tags: {tags_str}",
        f'branch: "{branch}"',
        f'pipeline: "{pipeline}"',
        "decisions: []",
        "---",
        "",
        f"# Spec {spec_num:03d} — {title}",
        "",
        "## Problem",
        "",
        problem or "TODO",
        "",
        "## Solution",
        "",
        solution or "TODO",
        "",
        "## Scope",
        "",
        scope or "### In Scope\n\nTODO\n\n### Out of Scope\n\nTODO",
        "",
        "## Acceptance Criteria",
        "",
        acceptance or "1. TODO",
        "",
        "## Decisions",
        "",
        decisions or "| ID | Decision | Rationale |\n|----|----------|-----------|\n| — | — | — |",
        "",
    ]
    return "\n".join(lines)


def _build_plan_md(spec_num: int, title: str, content: str) -> str:
    """Build plan.md from parsed content."""
    architecture = _extract_section(content, "Architecture")
    session_map = _extract_section(content, "Session Map")
    patterns = _extract_section(content, "Patterns")

    lines = [
        "---",
        f'spec: "{spec_num:03d}"',
        'approach: "serial-phases"',
        "---",
        "",
        f"# Plan — {title}",
        "",
        "## Architecture",
        "",
        architecture or "TODO",
        "",
        "## Session Map",
        "",
        session_map or "TODO",
        "",
        "## Patterns",
        "",
        patterns or "TODO",
        "",
    ]
    return "\n".join(lines)


def _build_tasks_md(spec_num: int, title: str, content: str) -> str:
    """Build tasks.md from parsed content."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    # Extract tasks from ## Tasks section or from checkboxes in content
    tasks_section = _extract_section(content, "Tasks")
    if not tasks_section:
        # Try to find checkboxes anywhere in content
        checkboxes = re.findall(r"^- \[[ xX]\] .+$", content, re.MULTILINE)
        tasks_section = "\n".join(checkboxes) if checkboxes else "- [ ] 1.1 TODO"

    total, completed = count_checkboxes(tasks_section)
    if total == 0:
        total = 1  # At least the TODO task

    lines = [
        "---",
        f'spec: "{spec_num:03d}"',
        f"total: {total}",
        f"completed: {completed}",
        f'last_session: "{today}"',
        'next_session: "Phase 1"',
        "---",
        "",
        f"# Tasks — {title}",
        "",
        tasks_section,
        "",
    ]
    return "\n".join(lines)


def _update_active_md(specs_dir: Path, spec_num: int, slug: str, title: str, branch: str) -> None:
    """Update _active.md to point to the new spec."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    dir_name = f"{spec_num:03d}-{slug}"

    content = f"""---
active: "{dir_name}"
updated: "{today}"
---

# Active Spec

**Spec {spec_num:03d} — {title}**

## Quick Resume

- Spec: [spec.md](specs/{dir_name}/spec.md)
- Plan: [plan.md](specs/{dir_name}/plan.md)
- Tasks: [tasks.md](specs/{dir_name}/tasks.md)
- Branch: `{branch}`
- Next: Phase 1
"""
    active_path = specs_dir / "_active.md"
    active_path.write_text(content, encoding="utf-8")


def spec_save(
    title: Annotated[
        str | None,
        typer.Option("--title", "-t", help="Spec title. Auto-detected from # heading if omitted."),
    ] = None,
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Read spec from file instead of stdin."),
    ] = None,
    pipeline: Annotated[
        str,
        typer.Option("--pipeline", "-p", help="Pipeline type: full|standard|hotfix|trivial."),
    ] = "standard",
    size: Annotated[
        str,
        typer.Option("--size", "-s", help="Spec size: S|M|L|XL."),
    ] = "M",
    tags: Annotated[
        str | None,
        typer.Option("--tags", help="Comma-separated tags."),
    ] = None,
    branch: Annotated[
        str | None,
        typer.Option("--branch", "-b", help="Branch name. Auto-generated if omitted."),
    ] = None,
    no_commit: Annotated[
        bool,
        typer.Option("--no-commit", help="Skip git commit (just write files)."),
    ] = False,
    no_branch: Annotated[
        bool,
        typer.Option("--no-branch", help="Skip branch creation (use current branch)."),
    ] = False,
) -> None:
    """Save a spec from stdin or file to the spec lifecycle directory.

    Reads structured markdown, validates required sections, scaffolds
    spec.md/plan.md/tasks.md, updates _active.md, and optionally commits.
    """
    # Read input
    if file:
        if not file.exists():
            typer.echo(f"Error: File not found: {file}", err=True)
            raise typer.Exit(code=1)
        content = file.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        typer.echo("Error: No input. Pipe spec via stdin or use --file.", err=True)
        raise typer.Exit(code=1)

    if not content.strip():
        typer.echo("Error: Empty input.", err=True)
        raise typer.Exit(code=1)

    # Validate
    errors = _validate_spec_content(content)
    if errors:
        typer.echo("Validation errors:", err=True)
        for err in errors:
            typer.echo(f"  - {err}", err=True)
        raise typer.Exit(code=1)

    # Resolve title
    if not title:
        title = _extract_title(content)
    if not title:
        typer.echo("Error: No title. Use --title or include a # heading.", err=True)
        raise typer.Exit(code=1)

    # Determine spec number and slug
    root = _project_root()
    specs_dir = _specs_dir(root)
    spec_num = _next_spec_number(specs_dir)
    slug = _slugify(title)
    dir_name = f"{spec_num:03d}-{slug}"
    spec_dir = specs_dir / dir_name

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    # Resolve branch name
    if not branch:
        branch = f"feat/{dir_name}"

    # Create branch if needed
    if not no_branch:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=root,
        )
        current_branch = result.stdout.strip()

        # Only create branch if on main/master
        if current_branch in ("main", "master"):
            create = subprocess.run(
                ["git", "checkout", "-b", branch],
                capture_output=True,
                text=True,
                cwd=root,
            )
            if create.returncode != 0:
                typer.echo(f"Error creating branch: {create.stderr}", err=True)
                raise typer.Exit(code=1)
            typer.echo(f"Branch: {branch}")
        else:
            branch = current_branch
            typer.echo(f"Branch: {branch} (existing)")

    # Scaffold files
    spec_dir.mkdir(parents=True, exist_ok=True)

    spec_md = _build_spec_md(spec_num, slug, title, content, pipeline, size, tag_list, branch)
    plan_md = _build_plan_md(spec_num, title, content)
    tasks_md = _build_tasks_md(spec_num, title, content)

    (spec_dir / "spec.md").write_text(spec_md, encoding="utf-8")
    (spec_dir / "plan.md").write_text(plan_md, encoding="utf-8")
    (spec_dir / "tasks.md").write_text(tasks_md, encoding="utf-8")

    # Update _active.md
    _update_active_md(specs_dir, spec_num, slug, title, branch)

    typer.echo(f"Spec: {dir_name}")
    typer.echo("Files: spec.md, plan.md, tasks.md")
    typer.echo("Active: _active.md updated")

    # Commit
    if not no_commit:
        import subprocess

        files_to_add = [
            str(spec_dir / "spec.md"),
            str(spec_dir / "plan.md"),
            str(spec_dir / "tasks.md"),
            str(specs_dir / "_active.md"),
        ]
        subprocess.run(["git", "add", *files_to_add], cwd=root, check=True)

        msg = f"spec-{spec_num:03d}: Phase 0 — scaffold spec files and activate"
        result = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True,
            text=True,
            cwd=root,
        )
        if result.returncode != 0:
            typer.echo(f"Commit output: {result.stdout}{result.stderr}", err=True)
            typer.echo("Files written but commit failed. Commit manually.", err=True)
        else:
            typer.echo(f"Commit: {msg}")

    # Emit signal
    try:
        from ai_engineering.state.models import AuditEntry
        from ai_engineering.state.service import StateService

        entry = AuditEntry(
            timestamp=datetime.now(tz=UTC),
            event="spec_saved",
            actor="cli",
            detail={
                "spec_id": f"{spec_num:03d}",
                "slug": slug,
                "title": title,
                "pipeline": pipeline,
                "size": size,
            },
        )
        StateService(root).append_audit(entry)
    except (ImportError, OSError):
        pass

    typer.echo(f"\nSpec {spec_num:03d} saved. Review and run /ai:execute to begin.")
