"""Release CLI command: validate, bump, PR, tag, monitor."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import error, info, status_line, success
from ai_engineering.paths import resolve_project_root
from ai_engineering.release.orchestrator import ReleaseConfig, execute_release
from ai_engineering.vcs.factory import get_provider


def _normalize_version(raw: str) -> str:
    return raw[1:] if raw.startswith("v") else raw


def release_cmd(
    version: Annotated[
        str,
        typer.Argument(help="Semver version (e.g. 0.2.0, 1.0.0-rc.1)"),
    ],
    target: Annotated[Path | None, typer.Option("--target", "-t")] = None,
    wait: Annotated[bool, typer.Option("--wait", help="Wait for pipeline")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate only")] = False,
    skip_bump: Annotated[bool, typer.Option("--skip-bump", help="Skip version bump")] = False,
    wait_timeout: Annotated[int, typer.Option("--wait-timeout")] = 600,
) -> None:
    """Create a governed release: validate, bump, PR, tag, monitor."""
    root = resolve_project_root(target)
    normalized = _normalize_version(version)
    provider = get_provider(root)
    config = ReleaseConfig(
        version=normalized,
        project_root=root,
        wait=wait,
        dry_run=dry_run,
        skip_bump=skip_bump,
        wait_timeout=wait_timeout,
    )

    result = execute_release(config, provider)

    if is_json_mode():
        payload = {
            "success": result.success,
            "version": result.version,
            "tag": result.tag_name,
            "pr_url": result.pr_url,
            "release_url": result.release_url,
            "pipeline_status": result.pipeline_status,
            "phases": [
                {
                    "phase": phase.phase,
                    "success": phase.success,
                    "skipped": phase.skipped,
                    "output": phase.output,
                }
                for phase in result.phases
            ],
            "errors": result.errors,
            "bump_files": result.bump_files,
        }
        if result.success:
            emit_success(
                "ai-eng release",
                payload,
                [
                    NextAction(
                        command=f"gh release view {result.tag_name}",
                        description="Inspect published release",
                    )
                ],
            )
            return

        emit_error(
            "ai-eng release",
            result.errors[0] if result.errors else "Release failed",
            "RELEASE_FAILED",
            "Fix the failed phase and rerun ai-eng release <version> to resume.",
        )
        raise typer.Exit(code=1)

    info(f"Release v{result.version}")
    for phase in result.phases:
        status = "ok" if phase.success else "fail"
        label = phase.phase if not phase.skipped else f"{phase.phase} (skipped)"
        status_line(status, label, phase.output or ("passed" if phase.success else "failed"))

    if result.success:
        if result.pr_url:
            success(f"PR: {result.pr_url}")
        if result.release_url:
            success(f"Release: {result.release_url}")
        success(f"Release v{result.version} completed")
        return

    error(result.errors[0] if result.errors else "Release failed")
    info("Next action: fix the failed phase and rerun the same command to resume.")
    raise typer.Exit(code=1)
