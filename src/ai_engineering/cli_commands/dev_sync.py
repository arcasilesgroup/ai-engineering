"""CLI command for syncing command mirrors across IDE surfaces.

Provides the ``ai-eng dev sync`` command (renamed from ``ai-eng sync`` per
spec-132 D-132-05) that regenerates all IDE-adapted mirrors from canonical
``.claude/skills/`` and ``.claude/agents/`` sources, plus provider-owned
install surfaces, into ``.codex/``, ``.agents/``, ``.github/``, and project
templates, or verifies they are in sync (``--check`` mode).

The command is registered under the ``dev`` hidden group; it is intended for
the source-repo only (not consumer projects).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.core.output import NextAction, Renderer
from ai_engineering.installer.capability_catalog import (
    CatalogStatus,
    apply_capability_catalog,
    check_capability_catalog,
)
from ai_engineering.paths import resolve_project_root
from ai_engineering.state.locking import artifact_lock


def dev_sync_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    check: Annotated[
        bool,
        typer.Option("--check", help="Verify mirrors are in sync; exit 1 if drift detected."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show detailed diff and hash information."),
    ] = False,
) -> None:
    """Sync command mirrors across all IDE surfaces.

    Regenerates skill and agent mirrors from canonical .claude/skills/
    and .claude/agents/ sources, plus provider-owned install surfaces,
    into .codex/, .agents/, .github/, and project templates.

    Use --check to verify without writing changes.
    """
    root = resolve_project_root(target)
    script = root / "scripts" / "sync_command_mirrors.py"
    renderer = Renderer.from_app("dev sync")

    if not script.is_file():
        renderer.error(
            f"Sync script not found: {script}",
            code="SCRIPT_NOT_FOUND",
            fix="Ensure scripts/sync_command_mirrors.py exists in the project root.",
        )

    cmd = [sys.executable, str(script)]
    if check:
        cmd.append("--check")
    if verbose:
        cmd.append("--verbose")

    action = "Checking mirror sync..." if check else "Syncing mirrors..."
    renderer.header()
    renderer.action("Verifying" if check else "Updating", action)
    with artifact_lock(root, "mirror-sync"), renderer.progress(total=1, desc=action):
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(root))

    exit_code = result.returncode

    if exit_code == 0:
        # Capability catalog (spec-153 W5): regenerate (or, under --check,
        # verify) the README catalog block alongside the mirrors. Fail-open
        # when the README has no markers yet (Wave 6 adds them).
        catalog = check_capability_catalog(root) if check else apply_capability_catalog(root)
        if catalog.status.name.startswith("SKIPPED"):
            catalog_verb = "Skipping"
        elif check:
            catalog_verb = "Verifying"
        else:
            catalog_verb = "Updating"
        renderer.action(catalog_verb, catalog.message)

        # spec-192 D-192-05: re-pin hooks-manifest after mirror sync.
        # spec-201 H8: under --check this VERIFIES instead. Re-signing the
        # integrity manifest from a verify-only command silently launders a
        # corrupted pin, an edited hook, or an injected hook into a freshly
        # signed clean state — invisible on a clean tree (generatedAt is
        # preserved) and catastrophic on the drifted tree that matters.
        from ai_engineering.cli_commands.core import (
            _check_hooks_manifest,
            _finalize_hooks_manifest,
        )

        if check:
            hooks_pinned = _check_hooks_manifest(root)
        else:
            _finalize_hooks_manifest(root)
            hooks_pinned = True

        if catalog.status is CatalogStatus.DRIFT:
            renderer.error(
                "Capability catalog drift detected",
                code="CATALOG_DRIFT",
                fix="Run 'ai-eng dev sync' without --check to regenerate the catalog.",
                next_actions=[
                    NextAction(label="Regenerate catalog", command="ai-eng dev sync"),
                ],
            )

        if not hooks_pinned:
            renderer.error(
                "Hook integrity manifest drift detected",
                code="HOOKS_MANIFEST_DRIFT",
                fix=(
                    "A hook script no longer matches its pinned sha256. Review the "
                    "change (git diff .ai-engineering/scripts/hooks/) BEFORE re-pinning."
                ),
                next_actions=[
                    NextAction(
                        label="Re-pin after reviewing the hook diff",
                        command="python3 .ai-engineering/scripts/regenerate-hooks-manifest.py",
                    ),
                ],
            )

        status = "in sync" if check else "synced"
        renderer.ok(
            f"Mirrors {status}",
            result={
                "status": "in_sync",
                "check": check,
                "catalog": catalog.status.value,
            },
        )
    elif exit_code == 1:
        if not renderer.is_json and result.stdout:
            typer.echo(result.stdout, err=True)
        renderer.error(
            "Mirror drift detected",
            code="DRIFT",
            fix="Run 'ai-eng dev sync' without --check to apply changes.",
            next_actions=[
                NextAction(label="Apply sync to fix drift", command="ai-eng dev sync"),
            ],
        )
    else:
        if not renderer.is_json:
            if result.stderr:
                typer.echo(result.stderr, err=True)
            if result.stdout:
                typer.echo(result.stdout, err=True)
        renderer.error(
            "Canonical source validation failed",
            code="VALIDATION_ERROR",
            fix="Check .claude/skills/ and .claude/agents/ for errors.",
        )
