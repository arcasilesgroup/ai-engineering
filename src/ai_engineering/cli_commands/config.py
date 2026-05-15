"""Config CLI commands.

spec-133 D-133-16 hard-cut + spec-128 slim refactor: a single Surface
sub-group replaces the legacy ``ide`` and ``provider`` groups. The
default callback renders the canonical posture (``render_config``).
Mutations route through the interactive wizard via ``install --reconfigure``.

    ai-eng config                      # show posture (calls render_config)
    ai-eng config stack list           # list active stacks
    ai-eng config surface list         # list available surfaces x enabled
    ai-eng config vcs status           # show primary VCS provider
    ai-eng config reconfigure          # re-run the interactive wizard
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_commands._render_config import render_config, render_config_payload
from ai_engineering.core.output import Renderer
from ai_engineering.domain.surface import SURFACE_REGISTRY
from ai_engineering.installer.operations import InstallerError, list_status
from ai_engineering.paths import resolve_project_root


def config_cmd(
    ctx: typer.Context,
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Display the current configuration posture.

    With no sub-command, prints the canonical ``render_config`` view
    (surfaces x stacks x policy). Sub-commands (``stack``, ``surface``,
    ``vcs``, ``reconfigure``) are routed by Typer.
    """
    if ctx.invoked_subcommand is not None:
        return

    root = resolve_project_root(target)
    renderer = Renderer.from_app("config")
    try:
        cfg = list_status(root)
    except InstallerError as exc:
        renderer.error(
            str(exc),
            code="CONFIG_NO_FRAMEWORK",
            fix="Run 'ai-eng install' first.",
        )
        return

    renderer.header()
    render_config(cfg, renderer)
    renderer.ok("config posture", result=render_config_payload(cfg))


def reconfigure_cmd(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Re-run the interactive configuration wizard.

    Routes through ``install --reconfigure`` so the same single-question
    flow handles both fresh installs and reconfiguration.
    """
    from ai_engineering.cli_commands import core as core_cmd

    root = resolve_project_root(target)
    renderer = Renderer.from_app("config reconfigure")
    renderer.header()
    renderer.action("Updating", "configuration", detail="interactive")
    core_cmd.install_cmd(target=root, reconfigure=True)
    renderer.ok("configuration updated")


# ---------------------------------------------------------------------------
# Inspection sub-commands.
# ---------------------------------------------------------------------------


def stack_list(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List active technology stacks."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("config stack list")
    try:
        manifest = list_status(root)
    except InstallerError as exc:
        renderer.error(
            str(exc),
            code="STACK_LIST_FAILED",
            fix="Run 'ai-eng install'",
        )
        return
    renderer.header()
    if manifest.providers.stacks:
        for s in manifest.providers.stacks:
            renderer.record("restored", s)
    else:
        renderer.step("No stacks configured")
    renderer.ok(
        "stacks listed",
        result={"stacks": list(manifest.providers.stacks)},
    )


def surface_list(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List available Surfaces with check marks against the user's enabled set."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("config surface list")
    try:
        manifest = list_status(root)
    except InstallerError as exc:
        renderer.error(
            str(exc),
            code="SURFACE_LIST_FAILED",
            fix="Run 'ai-eng install'",
        )
        return
    enabled = set(manifest.surfaces.enabled or [])
    renderer.header()
    for surface_id, surface in SURFACE_REGISTRY.items():
        marker = "[✓]" if surface_id in enabled else "[ ]"
        renderer.step(
            f"  {marker} {surface_id:<18} {surface.display_name:<18} {surface.hook_engine} hooks"
        )
    renderer.ok(
        "surfaces listed",
        result={
            "available": list(SURFACE_REGISTRY.keys()),
            "enabled": list(manifest.surfaces.enabled or []),
        },
    )


def vcs_status(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Show current VCS provider configuration and availability."""
    from ai_engineering.config.loader import load_manifest_config
    from ai_engineering.vcs.factory import get_provider

    root = resolve_project_root(target)
    renderer = Renderer.from_app("config vcs status")
    ai_eng_dir = root / ".ai-engineering"

    if not ai_eng_dir.is_dir():
        renderer.error(
            "Framework not installed",
            code="NO_FRAMEWORK",
            fix="Run 'ai-eng install' first",
        )
        return

    config = load_manifest_config(root)
    provider = get_provider(root)

    renderer.header()
    renderer.record("restored", f"primary={config.providers.vcs}")
    renderer.record("restored", f"active={provider.provider_name()}")
    renderer.record(
        "restored",
        f"available={provider.is_available()}",
    )
    renderer.ok(
        "vcs status",
        result={
            "primary_provider": config.providers.vcs,
            "enabled_providers": [config.providers.vcs],
            "active_provider": provider.provider_name(),
            "available": provider.is_available(),
        },
    )
