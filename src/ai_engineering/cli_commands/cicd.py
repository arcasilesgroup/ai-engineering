"""CI/CD command group."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.installer.cicd import generate_pipelines
from ai_engineering.paths import resolve_project_root
from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.models import InstallManifest


def cicd_regenerate(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Regenerate provider-aware stack-aware CI/CD files."""
    root = resolve_project_root(target)
    manifest_path = root / ".ai-engineering" / "state" / "install-manifest.json"
    if not manifest_path.exists():
        typer.echo("No install manifest found. Run 'ai-eng install' first.")
        raise typer.Exit(code=1)

    manifest = read_json_model(manifest_path, InstallManifest)
    result = generate_pipelines(
        root,
        provider=manifest.providers.primary,
        stacks=manifest.installed_stacks,
    )
    manifest.cicd.generated = bool(result.created or result.skipped)
    manifest.cicd.provider = manifest.providers.primary
    manifest.cicd.files = [str(p.relative_to(root)) for p in (result.created + result.skipped)]
    write_json_model(manifest_path, manifest)

    typer.echo(f"CI/CD regenerate for provider: {manifest.providers.primary}")
    typer.echo(f"  Created: {len(result.created)}")
    typer.echo(f"  Skipped: {len(result.skipped)}")
