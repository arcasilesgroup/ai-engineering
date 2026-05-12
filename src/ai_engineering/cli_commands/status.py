"""Status CLI command per spec-132 D-132-04.

``ai-eng status`` prints a read-only summary of the installed framework
(active stacks / IDEs / providers / VCS). It is a display-only command —
nothing is mutated, nothing is "restored". Output mirrors the visual
contract used by ``install`` and ``doctor`` (header → action → kv block
→ next-steps).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.core.output import NextAction, Renderer
from ai_engineering.installer.operations import InstallerError, list_status
from ai_engineering.paths import resolve_project_root


def _format_list(values: list[str], *, empty: str = "(none)") -> str:
    """Render a sorted, comma-separated list with an explicit empty fallback."""
    return ", ".join(values) if values else empty


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
            fix="Run 'ai-eng install' first.",
            next_actions=[
                NextAction(
                    label="Install the framework here",
                    command="ai-eng install",
                ),
            ],
        )

    stacks = list(manifest.providers.stacks)
    ides = list(manifest.providers.ides)
    providers = list(manifest.ai_providers.enabled)
    vcs = manifest.providers.vcs

    renderer.header()
    renderer.action("Verifying", "framework status", detail=str(root))

    renderer.section("Configuration")
    renderer.kv("VCS", vcs)
    renderer.kv("Providers", _format_list(providers))
    renderer.kv("Stacks", _format_list(stacks))
    renderer.kv("IDEs", _format_list(ides))

    renderer.next(
        [
            NextAction(label="Run health diagnostics", command="ai-eng doctor"),
            NextAction(label="Run content-integrity check", command="ai-eng check"),
        ]
    )

    renderer.ok(
        "framework status",
        result={
            "stacks": stacks,
            "ides": ides,
            "providers": providers,
            "vcs": vcs,
        },
    )
