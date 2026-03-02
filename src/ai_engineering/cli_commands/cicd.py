"""CI/CD command group."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_progress import spinner
from ai_engineering.cli_ui import error, info, kv, success
from ai_engineering.installer.cicd import generate_pipelines
from ai_engineering.installer.service import _resolve_sonar_cicd_config
from ai_engineering.paths import resolve_project_root
from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.models import InstallManifest, SonarCicdConfig


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
        if is_json_mode():
            emit_error(
                "ai-eng cicd regenerate",
                "No install manifest found",
                "NO_MANIFEST",
                "Run 'ai-eng install' first",
            )
        else:
            error("No install manifest found")
            info("Run 'ai-eng install' first")
        raise typer.Exit(code=1)

    manifest = read_json_model(manifest_path, InstallManifest)
    sonar_config = _resolve_sonar_cicd_config(root)
    with spinner("Regenerating pipelines..."):
        result = generate_pipelines(
            root,
            provider=manifest.providers.primary,
            stacks=manifest.installed_stacks,
            sonar_config=sonar_config,
        )
    manifest.cicd.generated = bool(result.created or result.skipped)
    manifest.cicd.provider = manifest.providers.primary
    manifest.cicd.files = [str(p.relative_to(root)) for p in (result.created + result.skipped)]
    manifest.cicd.sonar = sonar_config or SonarCicdConfig()
    write_json_model(manifest_path, manifest)

    if is_json_mode():
        emit_success(
            "ai-eng cicd regenerate",
            {
                "provider": manifest.providers.primary,
                "created": [str(p.relative_to(root)) for p in result.created],
                "skipped": [str(p.relative_to(root)) for p in result.skipped],
                "created_count": len(result.created),
                "skipped_count": len(result.skipped),
            },
            [
                NextAction(
                    command="ai-eng maintenance pipeline-compliance",
                    description="Verify pipeline compliance",
                ),
            ],
        )
    else:
        success(f"CI/CD regenerate for provider: {manifest.providers.primary}")
        kv("Created", len(result.created))
        kv("Skipped", len(result.skipped))
