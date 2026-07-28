"""Skills CLI commands: status, resolve.

Provides local skill eligibility diagnostics and read-only skill resolution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_progress import spinner
from ai_engineering.cli_ui import error, header, info, kv, status_line, success
from ai_engineering.paths import resolve_project_root
from ai_engineering.skills.service import (
    list_local_skill_status,
    resolve_skill,
    skill_surfaces,
)


def skill_status(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    all_skills: Annotated[
        bool,
        typer.Option("--all", help="Show all skills, including eligible ones."),
    ] = False,
) -> None:
    """Check which local skills meet their runtime requirements.

    Scans local skill directories and evaluates each skill's 'requires' block
    (bins, env vars, config paths, OS). Use --all to include eligible skills.
    """
    root = resolve_project_root(target)
    with spinner("Checking skill eligibility..."):
        statuses = list_local_skill_status(root)

    if is_json_mode():
        ineligible = [s for s in statuses if not s.eligible]
        emit_success(
            "ai-eng skill status",
            {
                "total": len(statuses),
                "eligible": len(statuses) - len(ineligible),
                "ineligible": len(ineligible),
                "skills": [
                    {
                        "name": s.name,
                        "eligible": s.eligible,
                        "file_path": s.file_path,
                        "missing_bins": s.missing_bins,
                        "missing_any_bins": s.missing_any_bins,
                        "missing_env": s.missing_env,
                        "missing_config": s.missing_config,
                        "missing_os": s.missing_os,
                        "errors": s.errors,
                    }
                    for s in statuses
                ],
            },
        )
        return

    if not statuses:
        info("No local skills found")
        return

    ineligible = [s for s in statuses if not s.eligible]
    displayed = statuses if all_skills else ineligible

    if not displayed:
        success(f"All {len(statuses)} skills are eligible.")
        return

    for s in displayed:
        st = "ok" if s.eligible else "fail"
        status_line(st, s.name, "eligible" if s.eligible else "ineligible")
        kv("  file", s.file_path)
        if s.errors:
            for entry in s.errors:
                status_line("fail", "  error", entry)
        if s.missing_bins:
            kv("  missing bins", ", ".join(s.missing_bins))
        if s.missing_any_bins:
            kv("  missing anyBins", ", ".join(s.missing_any_bins))
        if s.missing_env:
            kv("  missing env", ", ".join(s.missing_env))
        if s.missing_config:
            kv("  missing config", ", ".join(s.missing_config))
        if s.missing_os:
            kv("  unsupported OS", ", ".join(s.missing_os))

    header("Summary")
    kv("Eligible", len(statuses) - len(ineligible))
    kv("Ineligible", len(ineligible))
    kv("Total", len(statuses))


def skill_resolve(
    name: Annotated[
        str,
        typer.Argument(help="Skill name, with or without the `ai-` prefix."),
    ],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Resolve a skill name to its SKILL.md path, handlers, and references.

    Read-only metadata (spec-201 D-201-11): reports where a skill lives so a
    caller can hand the resolved body to the agent surface that owns it. It
    never executes a skill.
    """
    root = resolve_project_root(target)
    resolution = resolve_skill(root, name)
    surfaces = ", ".join(skill_surfaces())

    if resolution is None:
        message = f"No skill named {name!r} under: {surfaces}"
        if is_json_mode():
            emit_error(
                "ai-eng skill resolve",
                message,
                "SKILL_NOT_FOUND",
                "Run `ai-eng skill status` to list the skills this project can see.",
            )
        else:
            error(message)
        raise typer.Exit(code=1)

    if is_json_mode():
        emit_success(
            "ai-eng skill resolve",
            {
                "name": resolution.name,
                "file_path": resolution.file_path,
                "surface": resolution.surface,
                "handlers": resolution.handlers,
                "references": resolution.references,
            },
        )
        return

    status_line("ok", resolution.name, resolution.surface)
    kv("  file", resolution.file_path)
    for handler in resolution.handlers:
        kv("  handler", handler)
    for reference in resolution.references:
        kv("  reference", reference)
