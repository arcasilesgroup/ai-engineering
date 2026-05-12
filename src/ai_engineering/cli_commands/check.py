"""CLI command for content-integrity health checks (renamed from ``validate``).

Provides the ``ai-eng check`` command (spec-132 D-132-02) — a single
human-facing health check that runs programmatic verification across all
content-integrity categories.

The old ``validate`` verb is removed; ``ai-eng validate`` now exits 2
with a ``removed; use 'check'`` message wired in ``cli_factory.py``.
"""

from __future__ import annotations

import contextlib
import json
import time as _time
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.core.output import NextAction, Renderer
from ai_engineering.paths import resolve_project_root
from ai_engineering.state.locking import artifact_lock
from ai_engineering.validator.service import (
    IntegrityCategory,
    validate_content_integrity,
)

# Map CLI-friendly names to enum values.
_CATEGORY_NAMES: dict[str, IntegrityCategory] = {cat.value: cat for cat in IntegrityCategory}


def _check_lock(project_root: Path, categories: list[IntegrityCategory] | None):
    """Serialize mirror-affecting checks with mirror-sync adapters."""
    if categories is None or IntegrityCategory.MIRROR_SYNC in categories:
        return artifact_lock(project_root, "mirror-sync")
    return contextlib.nullcontext()


def check_cmd(
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
    """Run content-integrity health checks across governance categories."""
    root = resolve_project_root(target)
    renderer = Renderer("check", json=True) if output_json else Renderer.from_app("check")

    categories: list[IntegrityCategory] | None = None
    if category:
        if category not in _CATEGORY_NAMES:
            valid = ", ".join(sorted(_CATEGORY_NAMES))
            renderer.error(
                f"Unknown category: {category}",
                code="UNKNOWN_CATEGORY",
                fix=f"Valid categories: {valid}",
            )
        categories = [_CATEGORY_NAMES[category]]

    t0 = _time.monotonic()
    renderer.header()
    renderer.action("Verifying", "content integrity")
    with _check_lock(root, categories):
        report = validate_content_integrity(root, categories=categories)
    elapsed_ms = int((_time.monotonic() - t0) * 1000)

    # Emit canonical control-outcome events (fail-open).
    passed_count = sum(1 for cat in IntegrityCategory if report.category_passed(cat))
    total_cats = len(IntegrityCategory)
    score = int(passed_count / total_cats * 100) if total_cats > 0 else 0
    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_scan_event

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

        emit_guard_drift(
            root,
            decisions_checked=total_cats,
            drifted=total_cats - passed_count,
            critical=0,
        )

    if renderer.is_json:
        report_dict = report.to_dict()
        if not report.passed:
            renderer.next(
                [NextAction(label="Run health diagnostics", command="ai-eng doctor")],
            )
        renderer.ok(
            "check completed",
            result={"report": report_dict, "passed": report.passed, "root": str(root)},
        )
        if not report.passed:
            raise typer.Exit(code=1)
        return

    # Human / quiet path
    renderer.step(f"Categories: {passed_count}/{total_cats} passed")
    by_cat = report.by_category()
    for cat in IntegrityCategory:
        cat_pass = report.category_passed(cat)
        renderer.record(
            "restored" if cat_pass else "removed",
            cat.value,
            from_="PASS" if cat_pass else "FAIL",
        )
        if cat_pass:
            continue
        for fail_check in by_cat.get(cat, []):
            detail = f"{fail_check.message}" + (
                f" [{fail_check.file_path}]" if fail_check.file_path else ""
            )
            renderer.step(f"  {fail_check.status.value}: {fail_check.name} - {detail}")

    if not report.passed:
        renderer.next(
            [
                NextAction(
                    label="Re-run a specific category",
                    command="ai-eng check -c <category>",
                ),
                NextAction(
                    label="Run health diagnostics",
                    command="ai-eng doctor",
                ),
            ]
        )
        # Legacy --json flag still wins for back-compat consumers; otherwise
        # this branch exits 1 via renderer.error().
        if output_json:
            typer.echo(json.dumps(report.to_dict(), indent=2))
        renderer.error(
            "content integrity check failed",
            code="CHECK_FAILED",
            fix="Inspect category details above and address failing items.",
        )

    if output_json:
        typer.echo(json.dumps(report.to_dict(), indent=2))
    renderer.ok("content integrity ok")
