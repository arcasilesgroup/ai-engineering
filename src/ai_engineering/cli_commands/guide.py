"""Guide CLI command: re-display branch policy setup instructions."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import header, info, print_stdout, warning
from ai_engineering.paths import resolve_project_root
from ai_engineering.state.service import StateService


def guide_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Display branch policy setup instructions."""
    root = resolve_project_root(target)
    manifest_path = root / ".ai-engineering" / "state" / "install-manifest.json"

    if not manifest_path.exists():
        warning("Framework not installed. Run 'ai-eng install' first.")
        raise typer.Exit(code=1)

    manifest = StateService(root).load_manifest()
    guide_text = manifest.branch_policy.manual_guide

    if is_json_mode():
        emit_success(
            "ai-eng guide",
            {
                "has_guide": guide_text is not None,
                "branch_policy_guide": guide_text,
            },
        )
        return

    if not guide_text:
        info("No branch policy guide available (policy was applied automatically).")
        return

    header("Branch Policy Setup Guide")
    print_stdout(guide_text)

    # Hint to remove stale guides directory if it still exists
    stale_dir = root / ".ai-engineering" / "guides"
    if stale_dir.is_dir():
        info(
            f"Stale guides directory found: {stale_dir.relative_to(root)}\n"
            "  This directory is no longer needed and can be safely removed."
        )
