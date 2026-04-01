"""Stack and IDE CLI commands: add, remove, list.

Manages technology stacks and IDE integrations for an installed project.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import error, info, kv, status_line, success
from ai_engineering.installer.operations import (
    InstallerError,
    add_ide,
    add_stack,
    list_status,
    remove_ide,
    remove_stack,
)
from ai_engineering.paths import resolve_project_root


def stack_add(
    stack: Annotated[str, typer.Argument(help="Stack name to add (e.g. python).")],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Add a technology stack."""
    root = resolve_project_root(target)
    try:
        manifest = add_stack(root, stack)
        if is_json_mode():
            emit_success(
                "ai-eng stack add",
                {"action": "add", "stack": stack, "active_stacks": manifest.providers.stacks},
            )
        else:
            success(f"Added stack '{stack}'")
            kv("Active stacks", ", ".join(manifest.providers.stacks))
    except InstallerError as exc:
        if is_json_mode():
            emit_error("ai-eng stack add", str(exc), "STACK_ADD_FAILED", "Check stack name")
        else:
            error(str(exc))
        raise typer.Exit(code=1) from exc


def stack_remove(
    stack: Annotated[str, typer.Argument(help="Stack name to remove.")],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Remove a technology stack."""
    root = resolve_project_root(target)
    try:
        manifest = remove_stack(root, stack)
        if is_json_mode():
            emit_success(
                "ai-eng stack remove",
                {"action": "remove", "stack": stack, "active_stacks": manifest.providers.stacks},
            )
        else:
            success(f"Removed stack '{stack}'")
            kv("Active stacks", ", ".join(manifest.providers.stacks))
    except InstallerError as exc:
        if is_json_mode():
            emit_error("ai-eng stack remove", str(exc), "STACK_REMOVE_FAILED", "Check stack name")
        else:
            error(str(exc))
        raise typer.Exit(code=1) from exc


def stack_list(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List active technology stacks."""
    root = resolve_project_root(target)
    try:
        manifest = list_status(root)
        if is_json_mode():
            emit_success(
                "ai-eng stack list",
                {"stacks": manifest.providers.stacks},
            )
        else:
            if manifest.providers.stacks:
                for s in manifest.providers.stacks:
                    status_line("ok", s, "")
            else:
                info("No stacks configured")
    except InstallerError as exc:
        if is_json_mode():
            emit_error("ai-eng stack list", str(exc), "STACK_LIST_FAILED", "Run 'ai-eng install'")
        else:
            error(str(exc))
        raise typer.Exit(code=1) from exc


def ide_add(
    ide: Annotated[str, typer.Argument(help="IDE name to add (e.g. vscode).")],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Add an IDE integration."""
    root = resolve_project_root(target)
    try:
        manifest = add_ide(root, ide)
        if is_json_mode():
            emit_success(
                "ai-eng ide add",
                {"action": "add", "ide": ide, "active_ides": manifest.providers.ides},
            )
        else:
            success(f"Added IDE '{ide}'")
            kv("Active IDEs", ", ".join(manifest.providers.ides))
    except InstallerError as exc:
        if is_json_mode():
            emit_error("ai-eng ide add", str(exc), "IDE_ADD_FAILED", "Check IDE name")
        else:
            error(str(exc))
        raise typer.Exit(code=1) from exc


def ide_remove(
    ide: Annotated[str, typer.Argument(help="IDE name to remove.")],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Remove an IDE integration."""
    root = resolve_project_root(target)
    try:
        manifest = remove_ide(root, ide)
        if is_json_mode():
            emit_success(
                "ai-eng ide remove",
                {"action": "remove", "ide": ide, "active_ides": manifest.providers.ides},
            )
        else:
            success(f"Removed IDE '{ide}'")
            kv("Active IDEs", ", ".join(manifest.providers.ides))
    except InstallerError as exc:
        if is_json_mode():
            emit_error("ai-eng ide remove", str(exc), "IDE_REMOVE_FAILED", "Check IDE name")
        else:
            error(str(exc))
        raise typer.Exit(code=1) from exc


def ide_list(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """List active IDE integrations."""
    root = resolve_project_root(target)
    try:
        manifest = list_status(root)
        if is_json_mode():
            emit_success(
                "ai-eng ide list",
                {"ides": manifest.providers.ides},
            )
        else:
            if manifest.providers.ides:
                for i in manifest.providers.ides:
                    status_line("ok", i, "")
            else:
                info("No IDEs configured")
    except InstallerError as exc:
        if is_json_mode():
            emit_error("ai-eng ide list", str(exc), "IDE_LIST_FAILED", "Run 'ai-eng install'")
        else:
            error(str(exc))
        raise typer.Exit(code=1) from exc
