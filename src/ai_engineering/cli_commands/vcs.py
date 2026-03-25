"""VCS CLI commands: status and set-primary.

Provides the ``ai-eng vcs status`` and ``ai-eng vcs set-primary`` commands
for inspecting and configuring VCS provider settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import error, info, kv, success
from ai_engineering.config.loader import load_manifest_config, update_manifest_field
from ai_engineering.paths import resolve_project_root
from ai_engineering.vcs.factory import get_provider

_VALID_PROVIDERS = ("github", "azure_devops", "azdo")


def vcs_status(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Show current VCS provider configuration and availability."""
    root = resolve_project_root(target)
    ai_eng_dir = root / ".ai-engineering"

    if not ai_eng_dir.is_dir():
        if is_json_mode():
            emit_error(
                "ai-eng vcs status",
                "Framework not installed",
                "NO_FRAMEWORK",
                "Run 'ai-eng install' first",
            )
        else:
            error("Framework not installed")
            info("Run 'ai-eng install' first")
        raise typer.Exit(code=1)

    config = load_manifest_config(root)
    provider = get_provider(root)

    if is_json_mode():
        emit_success(
            "ai-eng vcs status",
            {
                "primary_provider": config.providers.vcs,
                "enabled_providers": [config.providers.vcs],
                "active_provider": provider.provider_name(),
                "available": provider.is_available(),
            },
            [
                NextAction(
                    command="ai-eng vcs set-primary <provider>",
                    description="Change primary provider",
                ),
            ],
        )
    else:
        kv("Primary provider", config.providers.vcs)
        kv("Active provider", provider.provider_name())
        kv("Provider available", provider.is_available())


def vcs_set_primary(
    provider_name: Annotated[
        str,
        typer.Argument(help="Provider to set as primary: 'github' or 'azure_devops'."),
    ],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Set the primary VCS provider in the manifest config."""
    if provider_name not in _VALID_PROVIDERS:
        if is_json_mode():
            emit_error(
                "ai-eng vcs set-primary",
                f"Invalid provider: {provider_name}",
                "INVALID_PROVIDER",
                f"Choose from: {', '.join(_VALID_PROVIDERS)}",
            )
        else:
            error(f"Invalid provider: {provider_name}")
            info(f"Choose from: {', '.join(_VALID_PROVIDERS)}")
        raise typer.Exit(code=1)

    root = resolve_project_root(target)
    ai_eng_dir = root / ".ai-engineering"

    if not ai_eng_dir.is_dir():
        if is_json_mode():
            emit_error(
                "ai-eng vcs set-primary",
                "Framework not installed",
                "NO_FRAMEWORK",
                "Run 'ai-eng install' first",
            )
        else:
            error("Framework not installed")
            info("Run 'ai-eng install' first")
        raise typer.Exit(code=1)

    config = load_manifest_config(root)
    previous = config.providers.vcs
    resolved_name = "azure_devops" if provider_name == "azdo" else provider_name
    update_manifest_field(root, "providers.vcs", resolved_name)

    if is_json_mode():
        emit_success(
            "ai-eng vcs set-primary",
            {
                "provider": resolved_name,
                "previous": previous,
            },
        )
    else:
        success(f"Primary VCS provider set to: {resolved_name}")
