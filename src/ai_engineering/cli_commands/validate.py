"""CLI command for content-integrity validation.

Provides the ``ai-eng validate`` command that runs programmatic checks
across all 7 content-integrity categories.
"""

from __future__ import annotations

import contextlib
import json
import time as _time
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_progress import spinner
from ai_engineering.cli_ui import kv, result_header, status_line, suggest_next
from ai_engineering.paths import resolve_project_root
from ai_engineering.state.locking import artifact_lock
from ai_engineering.validator.service import (
    IntegrityCategory,
    validate_content_integrity,
)

# Map CLI-friendly names to enum values
_CATEGORY_NAMES: dict[str, IntegrityCategory] = {cat.value: cat for cat in IntegrityCategory}


def _validation_lock(project_root: Path, categories: list[IntegrityCategory] | None):
    """Serialize mirror-affecting validation with mirror sync adapters."""
    if categories is None or IntegrityCategory.MIRROR_SYNC in categories:
        return artifact_lock(project_root, "mirror-sync")
    return contextlib.nullcontext()


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
                "cross-reference, instruction-consistency, manifest-coherence, "
                "skill-frontmatter, required-tools."
            ),
        ),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output report as JSON (deprecated: use global --json)."),
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

    t0 = _time.monotonic()
    with _validation_lock(root, categories), spinner("Validating content integrity..."):
        report = validate_content_integrity(root, categories=categories)
    elapsed_ms = int((_time.monotonic() - t0) * 1000)

    # Emit events (fail-open)
    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_scan_event

        passed_count = sum(1 for cat in IntegrityCategory if report.category_passed(cat))
        total_cats = len(IntegrityCategory)
        score = int(passed_count / total_cats * 100) if total_cats > 0 else 0
        emit_scan_event(
            root,
            mode="integrity",
            score=score,
            findings={"pass": passed_count, "fail": total_cats - passed_count},
            duration_ms=elapsed_ms,
            outcome="success" if report.passed else "failure",
        )

    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_guard_drift

        passed_count = sum(1 for cat in IntegrityCategory if report.category_passed(cat))
        total_cats = len(IntegrityCategory)
        failed_cats = total_cats - passed_count
        emit_guard_drift(
            root,
            decisions_checked=total_cats,
            drifted=failed_cats,
            critical=0,
        )

    if is_json_mode() or output_json:
        report_dict = report.to_dict()
        if is_json_mode():
            emit_success(
                "ai-eng validate",
                report_dict,
                [NextAction(command="ai-eng doctor", description="Run health diagnostics")]
                if not report.passed
                else [],
            )
        else:
            typer.echo(json.dumps(report_dict, indent=2))
    else:
        status = "PASS" if report.passed else "FAIL"
        by_cat = report.by_category()
        passed_count = sum(1 for cat in IntegrityCategory if report.category_passed(cat))
        total_cats = len(IntegrityCategory)

        result_header("Validate", status, str(root))
        kv("Categories", f"{passed_count}/{total_cats} passed")

        for cat in IntegrityCategory:
            cat_checks = by_cat.get(cat, [])
            cat_pass = report.category_passed(cat)
            cat_status = "ok" if cat_pass else "fail"
            status_line(cat_status, cat.value, "passed" if cat_pass else "FAILED")
            for check in cat_checks:
                suffix = f" [{check.file_path}]" if check.file_path else ""
                status_line(check.status.value, f"  {check.name}", f"{check.message}{suffix}")

        if not report.passed:
            suggest_next(
                [
                    ("ai-eng validate -c <category>", "Re-run a specific category"),
                    ("ai-eng doctor", "Run health diagnostics"),
                ]
            )

    if not report.passed:
        raise typer.Exit(code=1)
