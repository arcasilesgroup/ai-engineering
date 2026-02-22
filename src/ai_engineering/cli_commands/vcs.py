"""VCS CLI commands: status and set-primary.

Provides the ``ai-eng vcs status`` and ``ai-eng vcs set-primary`` commands
for inspecting and configuring VCS provider settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.paths import resolve_project_root
from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.models import InstallManifest
from ai_engineering.vcs.factory import get_provider

_VALID_PROVIDERS = ("github", "azure_devops")


def vcs_status(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Show current VCS provider configuration and availability."""
    root = resolve_project_root(target)
    manifest_path = root / ".ai-engineering" / "state" / "install-manifest.json"

    if not manifest_path.exists():
        typer.echo("No install manifest found. Run 'ai-eng install' first.")
        raise typer.Exit(code=1)

    manifest = read_json_model(manifest_path, InstallManifest)
    provider = get_provider(root)

    typer.echo(f"Primary provider: {manifest.providers.primary}")
    typer.echo(f"Enabled providers: {', '.join(manifest.providers.enabled)}")
    typer.echo(f"Active provider: {provider.provider_name()}")
    typer.echo(f"Provider available: {provider.is_available()}")


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
    """Set the primary VCS provider in the install manifest."""
    if provider_name not in _VALID_PROVIDERS:
        typer.echo(f"Invalid provider: {provider_name}. Choose from: {', '.join(_VALID_PROVIDERS)}")
        raise typer.Exit(code=1)

    root = resolve_project_root(target)
    manifest_path = root / ".ai-engineering" / "state" / "install-manifest.json"

    if not manifest_path.exists():
        typer.echo("No install manifest found. Run 'ai-eng install' first.")
        raise typer.Exit(code=1)

    manifest = read_json_model(manifest_path, InstallManifest)
    manifest.providers.primary = provider_name
    if provider_name not in manifest.providers.enabled:
        manifest.providers.enabled.append(provider_name)

    write_json_model(manifest_path, manifest)
    typer.echo(f"Primary VCS provider set to: {provider_name}")
