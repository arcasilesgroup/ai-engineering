"""Spec lifecycle CLI commands (Working Buffer model).

Provides deterministic, zero-token commands for spec management:

- ``ai-eng spec start`` -- point runtime consumers at a work-plane root.
- ``ai-eng spec verify``  -- count checkboxes in plan.md, auto-correct frontmatter.
- ``ai-eng spec verify --sections <path>`` -- deterministic section header
  pre-flight per ``.ai-engineering/reference/spec-schema.md`` (spec-139 M7.T1).
- ``ai-eng spec list``    -- display current spec title and progress.
"""

from __future__ import annotations

import json as _json
from contextlib import suppress
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_ui import error, info, kv, status_line, success, warning
from ai_engineering.lib.parsing import count_checkboxes, parse_frontmatter
from ai_engineering.maintenance.spec_activate import run_spec_activate
from ai_engineering.paths import find_project_root
from ai_engineering.state.observability import emit_framework_operation
from ai_engineering.state.work_plane import read_task_ledger, resolve_active_work_plane
from skill_domain.state_models import TaskLifecycleState

_SPEC_FILENAME = "spec.md"
_PLAN_FILENAME = "plan.md"

# spec-139 M7.T1 -- required section headers per spec-schema.md rule 2.
# Optional sections (References, Open Questions) are recognised but not
# required for ``valid=true``.
_REQUIRED_SECTIONS: tuple[str, ...] = (
    "## Summary",
    "## Goals",
    "## Non-Goals",
    "## Decisions",
    "## Risks",
)
_OPTIONAL_SECTIONS: tuple[str, ...] = (
    "## References",
    "## Open Questions",
)


def _specs_dir(root: Path) -> Path:
    return resolve_active_work_plane(root).specs_dir


def _emit_signal(root: Path, event: str, detail: dict, outcome: str = "success") -> None:
    """Emit a framework operation event if observability is available."""
    with suppress(OSError):
        emit_framework_operation(
            root,
            operation=event,
            component="cli.spec",
            source="cli",
            outcome=outcome,
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


def spec_start(
    path: Annotated[
        Path | None,
        typer.Argument(help="Project-relative specs dir to mark active."),
    ] = None,
    specs_dir: Annotated[
        Path | None,
        typer.Option(
            "--specs-dir",
            help="Deprecated alias for the positional <path> argument.",
        ),
    ] = None,
) -> None:
    """Activate a work plane and ensure spec/plan buffer files exist.

    Canonical entry point (spec-133): accepts the specs directory as a
    positional argument. The ``--specs-dir`` option is preserved as a
    deprecated alias for one release.
    """
    import click

    target = path or specs_dir
    if target is None:
        # spec-133 #5: no-args invocation prints help and exits 0, matching
        # the universal help-on-no-args contract used by every other verb.
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        raise typer.Exit(code=0)
    root = find_project_root()
    result = run_spec_activate(root, target)

    if not result.success:
        for item in result.errors:
            error(item)
        raise typer.Exit(code=1)

    relative_specs_dir = result.specs_dir.resolve().relative_to(root.resolve()).as_posix()
    kv("Specs dir", relative_specs_dir)
    kv("Pointer", "enabled" if result.pointer_enabled else "legacy singleton")
    kv("spec.md", "created" if result.spec_created else "preserved")
    kv("plan.md", "created" if result.plan_created else "preserved")
    success("Active spec buffer updated.")
    _emit_signal(
        root,
        "spec_activated",
        {
            "specs_dir": relative_specs_dir,
            "pointer_enabled": result.pointer_enabled,
        },
    )


def _classify_sections(text: str) -> tuple[list[str], list[str]]:
    """Return ``(present, missing)`` required-section lists for a spec body.

    spec-139 M7.T1: pure string-contains scan. A section header matches
    when its canonical ``## Title`` literal appears at the start of any
    line in the document (after frontmatter stripping is unnecessary —
    headers live in the body and ``## Title`` never appears inside a
    fenced frontmatter block by contract).
    """
    lines = text.splitlines()
    line_set = {line.rstrip() for line in lines}
    present: list[str] = []
    missing: list[str] = []
    for header in _REQUIRED_SECTIONS:
        if header in line_set:
            present.append(header)
        else:
            missing.append(header)
    return present, missing


def spec_verify(
    fix: Annotated[
        bool,
        typer.Option(
            "--fix",
            help="Auto-correct drifted counters in plan.md frontmatter (opt-in).",
        ),
    ] = False,
    sections: Annotated[
        Path | None,
        typer.Option(
            "--sections",
            help=(
                "Deterministic section-header pre-flight (spec-139 M7.T1). "
                "Reads <path> (defaults to the active spec.md), checks for "
                "required headers per spec-schema.md, emits JSON, exits 1 "
                "when required sections are missing."
            ),
        ),
    ] = None,
) -> None:
    """Verify spec task counters and status consistency.

    Reads specs/plan.md, counts checkboxes, verifies frontmatter, and
    optionally auto-corrects drift.

    When ``--sections`` is supplied, runs the spec-139 M7.T1 deterministic
    section-header pre-flight instead: scans the target spec.md for the
    required headers declared in ``.ai-engineering/reference/spec-schema.md``
    and emits a JSON report. Exits 0 when every required header is
    present, 1 when one or more are missing. The structural counter
    workflow is skipped when ``--sections`` is provided.
    """
    if sections is not None:
        _run_sections_preflight(sections)
        return
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

    kv("BEFORE", f"{fm_completed}/{fm_total} (frontmatter)")
    kv("Counted", f"{real_completed}/{real_total} (plan body)")

    corrected = False
    if drift_detected:
        if fix:
            corrected = _auto_correct_frontmatter(root, real_total, real_completed)
        if corrected:
            kv("AFTER", f"{real_completed}/{real_total} (frontmatter)")
            success("counter drift auto-fixed")
        else:
            kv("AFTER", f"{fm_completed}/{fm_total} (unchanged)")
            warning("drift detected -- re-run with --fix to auto-correct")
    else:
        kv("AFTER", f"{real_completed}/{real_total} (no drift)")
        status_line("ok", "Counters", "match")

    # Emit signal -- spec-137 D-137-01 relevance discipline.
    # `spec_verified` was the #1 polling-style emitter (848 rows/day,
    # 63.5% of the audit tail). Convert to change-driven: only emit when
    # drift was actually detected. Read-time consumers that want to know
    # "did spec verify run" should derive it from git hook traces, not a
    # heartbeat row.
    if drift_detected:
        _emit_signal(
            root,
            "spec_verified",
            {
                "total": real_total,
                "completed": real_completed,
                "drift_detected": drift_detected,
            },
            outcome="success" if corrected else "failure",
        )


def _run_sections_preflight(target: Path) -> None:
    """Run the spec-139 M7.T1 section-header pre-flight on ``target``.

    Emits a JSON report to stdout and raises ``typer.Exit`` with the
    appropriate exit code (0 valid, 1 missing required sections).
    Missing-file errors emit a JSON error envelope to stderr and exit 1.
    """
    # Resolve relative paths against the caller's CWD so the flag behaves
    # like a normal positional path: ``ai-eng spec verify --sections foo.md``.
    spec_path = target if target.is_absolute() else Path.cwd() / target
    if not spec_path.exists() or not spec_path.is_file():
        message = f"spec file not found: {spec_path}"
        typer.echo(
            _json.dumps(
                {
                    "path": str(spec_path),
                    "missing_sections": [],
                    "present_sections": [],
                    "valid": False,
                    "error": message,
                }
            ),
            err=True,
        )
        raise typer.Exit(code=1)
    text = spec_path.read_text(encoding="utf-8")
    present, missing = _classify_sections(text)
    payload = {
        "path": str(spec_path),
        "missing_sections": missing,
        "present_sections": present,
        "valid": not missing,
    }
    typer.echo(_json.dumps(payload))
    raise typer.Exit(code=0 if not missing else 1)


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


def spec_show() -> None:
    """Print the active spec handoff surface (paths + progress)."""
    root = find_project_root()
    specs_dir = _specs_dir(root)
    spec_path = specs_dir / _SPEC_FILENAME
    plan_path = specs_dir / _PLAN_FILENAME

    if not spec_path.exists():
        info("No specs/spec.md found.")
        return

    spec_text = spec_path.read_text(encoding="utf-8")
    placeholder_spec = spec_text.strip().startswith("# No active spec")
    state = "placeholder" if placeholder_spec else "active"

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
            progress = f"{completed}/{total}" if total else "0/0"

    kv("State", state)
    kv("Title", title)
    kv("Progress", progress)
    kv("spec.md", str(spec_path) if spec_path.exists() else "(missing)")
    kv("plan.md", str(plan_path) if plan_path.exists() else "(missing)")
