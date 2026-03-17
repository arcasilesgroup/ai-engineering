"""CLI command for ai-eng verify.

Runs verification checks in a specified mode and produces a scored report
with findings, severity levels, and a pass/warn/fail verdict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_progress import spinner
from ai_engineering.cli_ui import kv, result_header, status_line, suggest_next
from ai_engineering.paths import resolve_project_root
from ai_engineering.verify.service import MODES


def verify_cmd(
    mode: Annotated[
        str,
        typer.Argument(
            help="Verification mode: quality | security | governance | platform",
        ),
    ],
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Project root to verify. Defaults to cwd."),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output report as JSON (deprecated: use global --json)."),
    ] = False,
) -> None:
    """Run verification in the specified mode and produce a scored report."""
    if mode not in MODES:
        valid = ", ".join(sorted(MODES))
        typer.echo(f"Unknown mode: {mode}. Available: {valid}", err=True)
        raise typer.Exit(code=2)

    root = resolve_project_root(target)
    func = MODES[mode]

    with spinner(f"Running {mode} verification..."):
        result = func(root)

    if is_json_mode() or output_json:
        report = {
            "mode": mode,
            "score": result.score,
            "verdict": result.verdict.value,
            "findings_summary": result.summary(),
            "findings": [
                {
                    "severity": f.severity.value,
                    "category": f.category,
                    "message": f.message,
                    "file": f.file,
                    "line": f.line,
                }
                for f in result.findings
            ],
        }
        if is_json_mode():
            next_actions = []
            if result.verdict.value == "FAIL":
                next_actions = [
                    NextAction(
                        command="ai-eng doctor",
                        description="Run health diagnostics",
                    ),
                ]
            emit_success(f"ai-eng verify {mode}", report, next_actions)
        else:
            typer.echo(json.dumps(report, indent=2))
    else:
        result_header("Verify", result.verdict.value, f"{mode} @ {root}")
        kv("Score", f"{result.score}/100")
        kv("Verdict", result.verdict.value)

        if result.findings:
            typer.echo(err=True)
            summary = result.summary()
            summary_str = ", ".join(f"{k}: {v}" for k, v in sorted(summary.items()))
            kv("Findings", f"{len(result.findings)} ({summary_str})")

            for f in result.findings:
                loc = f" ({f.file}:{f.line})" if f.file else ""
                status_line(
                    "fail" if f.severity.value in ("blocker", "critical") else "warn",
                    f"[{f.severity.value}] {f.category}",
                    f"{f.message}{loc}",
                )
        else:
            typer.echo(err=True)
            status_line("ok", "No findings", "All checks passed")

        if result.verdict.value == "FAIL":
            suggest_next(
                [
                    ("ai-eng verify quality", "Re-run quality checks only"),
                    ("ai-eng verify security", "Re-run security checks only"),
                    ("ai-eng doctor", "Run health diagnostics"),
                ]
            )

    if result.verdict.value == "FAIL":
        raise typer.Exit(code=1)
