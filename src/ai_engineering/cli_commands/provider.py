"""AI Provider CLI commands: add, remove, list.

Manages AI coding assistant providers for an installed project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import error, info, kv, success
from ai_engineering.installer.operations import (
    InstallerError,
    add_provider,
    list_status,
    remove_provider,
)
from ai_engineering.paths import resolve_project_root


def provider_add(
    provider: Annotated[
        str,
        typer.Argument(help="Provider to add (claude_code, github_copilot, gemini, codex)."),
    ],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Add an AI provider."""
    root = resolve_project_root(target)
    try:
        manifest = add_provider(root, provider)
        if is_json_mode():
            emit_success(
                "ai-eng provider add",
                {
                    "action": "add",
                    "provider": provider,
                    "active_providers": manifest.providers.ides,
                    "primary": manifest.providers.ides[0] if manifest.providers.ides else "none",
                },
            )
        else:
            success(f"Added provider '{provider}'")
            kv("Active providers", ", ".join(manifest.providers.ides))
            kv("Primary", manifest.providers.ides[0] if manifest.providers.ides else "none")
    except InstallerError as exc:
        if is_json_mode():
            emit_error(
                "ai-eng provider add",
                str(exc),
                "PROVIDER_ADD_FAILED",
                "Check provider name",
            )
        else:
            error(str(exc))
        raise typer.Exit(code=1) from exc


def provider_remove(
    provider: Annotated[
        str,
        typer.Argument(help="Provider to remove."),
    ],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Remove an AI provider."""
    root = resolve_project_root(target)
    try:
        manifest = remove_provider(root, provider)
        if is_json_mode():
            emit_success(
                "ai-eng provider remove",
                {
                    "action": "remove",
                    "provider": provider,
                    "active_providers": manifest.providers.ides,
                    "primary": manifest.providers.ides[0] if manifest.providers.ides else "none",
                },
            )
        else:
            success(f"Removed provider '{provider}'")
            kv("Active providers", ", ".join(manifest.providers.ides))
            kv("Primary", manifest.providers.ides[0] if manifest.providers.ides else "none")
    except InstallerError as exc:
        if is_json_mode():
            emit_error(
                "ai-eng provider remove",
                str(exc),
                "PROVIDER_REMOVE_FAILED",
                "Check provider name",
            )
        else:
            error(str(exc))
        raise typer.Exit(code=1) from exc


def provider_list(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List active AI providers."""
    root = resolve_project_root(target)
    try:
        manifest = list_status(root)
        if is_json_mode():
            emit_success(
                "ai-eng provider list",
                {
                    "providers": manifest.providers.ides,
                    "primary": manifest.providers.ides[0] if manifest.providers.ides else "none",
                },
            )
        else:
            if manifest.providers.ides:
                primary = manifest.providers.ides[0]
                for p in manifest.providers.ides:
                    marker = " (primary)" if p == primary else ""
                    info(f"  - {p}{marker}")
            else:
                info("No providers configured")
    except InstallerError as exc:
        if is_json_mode():
            emit_error(
                "ai-eng provider list",
                str(exc),
                "PROVIDER_LIST_FAILED",
                "Run 'ai-eng install'",
            )
        else:
            error(str(exc))
        raise typer.Exit(code=1) from exc
