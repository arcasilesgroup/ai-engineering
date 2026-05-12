"""Config CLI commands (spec-132 D-132-04): inspection + interactive setup.

Consolidates the mutator surface from the deleted ``stack``, ``ide``,
``provider``, and ``vcs`` top-level groups behind a single
``ai-eng config`` interactive flow (which wraps ``install --reconfigure``)
plus inspection commands::

    ai-eng config                      # interactive wizard
    ai-eng config stack list           # list active stacks
    ai-eng config ide list             # list active IDE integrations
    ai-eng config provider list        # list AI providers
    ai-eng config vcs status           # show primary VCS provider

Mutator verbs (``add`` / ``remove``) collapsed away: any change goes
through the interactive flow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.core.output import Renderer
from ai_engineering.installer.operations import InstallerError, list_status
from ai_engineering.paths import resolve_project_root


def config_cmd(
    ctx: typer.Context,
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Interactive configuration wizard.

    Re-runs the installer in reconfigure mode so the operator can adjust
    stacks, IDE integrations, AI providers, and the primary VCS provider
    in one place.

    When a subcommand (``stack``, ``ide``, ``provider``, ``vcs``) is
    invoked this callback short-circuits without running the wizard so
    the inspection sub-command can execute normally (spec-132 sub-004
    closure: avoids invoking the interactive flow on every read).
    """
    if ctx.invoked_subcommand is not None:
        return

    from ai_engineering.cli_commands import core as core_cmd

    root = resolve_project_root(target)
    renderer = Renderer.from_app("config")
    renderer.header()
    renderer.action("Updating", "configuration", detail="interactive")
    # Delegate to install --reconfigure (the existing wizard entry-point).
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


def ide_list(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List active IDE integrations."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("config ide list")
    try:
        manifest = list_status(root)
    except InstallerError as exc:
        renderer.error(
            str(exc),
            code="IDE_LIST_FAILED",
            fix="Run 'ai-eng install'",
        )
    renderer.header()
    if manifest.providers.ides:
        for i in manifest.providers.ides:
            renderer.record("restored", i)
    else:
        renderer.step("No IDEs configured")
    renderer.ok(
        "ides listed",
        result={"ides": list(manifest.providers.ides)},
    )


def provider_list(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List active AI providers."""
    root = resolve_project_root(target)
    renderer = Renderer.from_app("config provider list")
    try:
        manifest = list_status(root)
    except InstallerError as exc:
        renderer.error(
            str(exc),
            code="PROVIDER_LIST_FAILED",
            fix="Run 'ai-eng install'",
        )
    enabled = list(manifest.ai_providers.enabled)
    primary = manifest.ai_providers.primary or (enabled[0] if enabled else "none")
    renderer.header()
    if enabled:
        for p in enabled:
            renderer.record("restored", p, from_="primary" if p == primary else None)
    else:
        renderer.step("No providers configured")
    renderer.ok(
        "providers listed",
        result={"providers": enabled, "primary": primary},
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
