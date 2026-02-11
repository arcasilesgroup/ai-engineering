"""CLI command for content-integrity validation.

Provides the ``ai-eng validate`` command that runs programmatic checks
across all 6 content-integrity categories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.paths import resolve_project_root
from ai_engineering.validator.service import (
    IntegrityCategory,
    validate_content_integrity,
)

# Map CLI-friendly names to enum values
_CATEGORY_NAMES: dict[str, IntegrityCategory] = {
    cat.value: cat for cat in IntegrityCategory
}


def validate_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help=(
                "Run a specific category only. "
                "Values: file-existence, mirror-sync, counter-accuracy, "
                "cross-reference, instruction-consistency, manifest-coherence."
            ),
        ),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output report as JSON."),
    ] = False,
) -> None:
    """Validate content integrity across all governance categories."""
    root = resolve_project_root(target)

    categories: list[IntegrityCategory] | None = None
    if category:
        if category not in _CATEGORY_NAMES:
            valid = ", ".join(sorted(_CATEGORY_NAMES))
            typer.echo(f"Unknown category: {category}")
            typer.echo(f"Valid categories: {valid}")
            raise typer.Exit(code=2)
        categories = [_CATEGORY_NAMES[category]]

    report = validate_content_integrity(root, categories=categories)

    if output_json:
        typer.echo(json.dumps(report.to_dict(), indent=2))
    else:
        status = "PASS" if report.passed else "FAIL"
        by_cat = report.by_category()
        passed_count = sum(1 for cat in IntegrityCategory if report.category_passed(cat))
        typer.echo(f"Content Integrity [{status}] ({passed_count}/{len(IntegrityCategory)} categories passed)")
        typer.echo()

        for cat in IntegrityCategory:
            cat_checks = by_cat.get(cat, [])
            cat_pass = all(c.status.value != "fail" for c in cat_checks)
            icon = "✓" if cat_pass else "✗"
            typer.echo(f"  {icon} {cat.value}")
            for check in cat_checks:
                check_icon = {"ok": "✓", "warn": "⚠", "fail": "✗"}.get(
                    check.status.value, "?"
                )
                suffix = f" [{check.file_path}]" if check.file_path else ""
                typer.echo(f"    {check_icon} {check.name}: {check.message}{suffix}")

    if not report.passed:
        raise typer.Exit(code=1)
