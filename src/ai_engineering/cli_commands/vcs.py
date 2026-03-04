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
from ai_engineering.paths import resolve_project_root
from ai_engineering.state.service import StateService
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
        if is_json_mode():
            emit_error(
                "ai-eng vcs status",
                "No install manifest found",
                "NO_MANIFEST",
                "Run 'ai-eng install' first",
            )
        else:
            error("No install manifest found")
            info("Run 'ai-eng install' first")
        raise typer.Exit(code=1)

    state_svc = StateService(root)
    manifest = state_svc.load_manifest()
    provider = get_provider(root)

    if is_json_mode():
        emit_success(
            "ai-eng vcs status",
            {
                "primary_provider": manifest.providers.primary,
                "enabled_providers": manifest.providers.enabled,
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
        kv("Primary provider", manifest.providers.primary)
        kv("Enabled providers", ", ".join(manifest.providers.enabled))
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
    no_cicd: Annotated[
        bool,
        typer.Option("--no-cicd", help="Skip CI/CD pipeline regeneration."),
    ] = False,
) -> None:
    """Set the primary VCS provider in the install manifest."""
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
    manifest_path = root / ".ai-engineering" / "state" / "install-manifest.json"

    if not manifest_path.exists():
        if is_json_mode():
            emit_error(
                "ai-eng vcs set-primary",
                "No install manifest found",
                "NO_MANIFEST",
                "Run 'ai-eng install' first",
            )
        else:
            error("No install manifest found")
            info("Run 'ai-eng install' first")
        raise typer.Exit(code=1)

    state_svc = StateService(root)
    manifest = state_svc.load_manifest()
    previous = manifest.providers.primary
    manifest.providers.primary = provider_name
    if provider_name not in manifest.providers.enabled:
        manifest.providers.enabled.append(provider_name)

    state_svc.save_manifest(manifest)

    # Regenerate CI/CD pipelines for the new provider
    cicd_regenerated = False
    if not no_cicd:
        from ai_engineering.installer.cicd import generate_pipelines

        cicd_result = generate_pipelines(
            root,
            provider=provider_name,
            stacks=manifest.installed_stacks,
        )
        cicd_regenerated = bool(cicd_result.created or cicd_result.skipped)

    if is_json_mode():
        emit_success(
            "ai-eng vcs set-primary",
            {
                "provider": provider_name,
                "previous": previous,
                "cicd_regenerated": cicd_regenerated,
            },
        )
    else:
        success(f"Primary VCS provider set to: {provider_name}")
        if cicd_regenerated:
            info("CI/CD pipelines regenerated for new provider")
