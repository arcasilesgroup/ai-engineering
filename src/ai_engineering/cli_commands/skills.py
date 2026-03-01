"""Skills CLI commands: list, sync, add, remove, status.

Manages remote skill sources, synchronisation, and local eligibility diagnostics.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_progress import spinner
from ai_engineering.cli_ui import error, header, info, kv, status_line, success
from ai_engineering.paths import resolve_project_root
from ai_engineering.skills.service import (
    add_source,
    list_local_skill_status,
    list_sources,
    remove_source,
    sync_sources,
)


def skill_list(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List configured remote skill sources and their trust status."""
    root = resolve_project_root(target)
    sources = list_sources(root)

    if is_json_mode():
        emit_success(
            "ai-eng skill list",
            {
                "sources": [{"url": s.url, "trusted": s.trusted} for s in sources],
                "total": len(sources),
            },
            [NextAction(command="ai-eng skill sync", description="Sync remote sources")],
        )
    else:
        if not sources:
            info("No remote skill sources configured")
            return

        for src in sources:
            trust = "trusted" if src.trusted else "untrusted"
            status_line("ok" if src.trusted else "warn", src.url, trust)


def skill_sync(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    offline: Annotated[
        bool,
        typer.Option("--offline", help="Only use cached content."),
    ] = False,
) -> None:
    """Fetch and cache remote skill definitions from trusted sources.

    Use --offline to serve only from cache.
    """
    root = resolve_project_root(target)
    with spinner("Syncing remote sources..."):
        result = sync_sources(root, offline=offline)

    if is_json_mode():
        emit_success(
            "ai-eng skill sync",
            {
                "fetched": result.fetched,
                "cached": result.cached,
                "failed": result.failed,
                "untrusted": result.untrusted,
            },
            [NextAction(command="ai-eng skill status", description="Check skill eligibility")],
        )
    else:
        kv("Fetched", len(result.fetched))
        kv("Cached", len(result.cached))

        if result.failed:
            kv("Failed", len(result.failed))
            for url in result.failed:
                status_line("fail", url, "fetch failed")

        if result.untrusted:
            kv("Untrusted (skipped)", len(result.untrusted))


def skill_add(
    url: Annotated[str, typer.Argument(help="URL of the remote skill source.")],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    trusted: Annotated[
        bool,
        typer.Option("--trusted/--untrusted", help="Trust status."),
    ] = True,
) -> None:
    """Register a remote URL as a skill source.

    New sources are trusted by default. Use --untrusted to skip during sync.
    """
    root = resolve_project_root(target)
    try:
        add_source(root, url, trusted=trusted)
        if is_json_mode():
            emit_success(
                "ai-eng skill add",
                {"added": url, "trusted": trusted},
                [NextAction(command="ai-eng skill sync", description="Sync remote sources")],
            )
        else:
            success(f"Added source: {url}")
    except ValueError as exc:
        error(str(exc))
        raise typer.Exit(code=1) from exc


def skill_remove(
    url: Annotated[str, typer.Argument(help="URL of the remote skill source.")],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Unregister a remote skill source. Cached content is not deleted."""
    root = resolve_project_root(target)
    try:
        remove_source(root, url)
        if is_json_mode():
            emit_success(
                "ai-eng skill remove",
                {"removed": url},
            )
        else:
            success(f"Removed source: {url}")
    except ValueError as exc:
        error(str(exc))
        raise typer.Exit(code=1) from exc


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

    Scans .ai-engineering/skills/ and evaluates each skill's 'requires' block
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
        info("No local skills found under .ai-engineering/skills")
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
