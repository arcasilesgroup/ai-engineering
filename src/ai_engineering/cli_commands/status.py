"""Status CLI command per spec-132 D-132-04.

ai-eng status prints a read-only summary of the installed framework
(active stacks / IDEs / providers / VCS).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.core.output import Renderer
from ai_engineering.installer.operations import InstallerError, list_status
from ai_engineering.paths import resolve_project_root


def status_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Show summary of the installed framework configuration."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("status")
    try:
        manifest = list_status(root)
    except InstallerError as exc:
        renderer.error(
            str(exc),
            code="STATUS_FAILED",
            fix="Run 'ai-eng install'",
        )
    renderer.header()
    stacks = list(manifest.providers.stacks)
    ides = list(manifest.providers.ides)
    providers = list(manifest.ai_providers.enabled)
    vcs = manifest.providers.vcs

    if stacks:
        for s in stacks:
            renderer.record("restored", f"stack: {s}")
    else:
        renderer.step("No stacks configured")
    if ides:
        for i in ides:
            renderer.record("restored", f"ide: {i}")
    else:
        renderer.step("No IDEs configured")
    if providers:
        for p in providers:
            renderer.record("restored", f"provider: {p}")
    else:
        renderer.step("No providers configured")
    renderer.record("restored", f"vcs: {vcs}")
    renderer.ok(
        "framework status",
        result={
            "stacks": stacks,
            "ides": ides,
            "providers": providers,
            "vcs": vcs,
        },
    )
