"""CLI command for ai-eng verify.

Runs verification checks in a specified mode and produces a scored report
with findings, severity levels, and a pass/warn/fail verdict.
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
from ai_engineering.verify.service import MODES


def _verify_execution_lock(project_root: Path, mode: str):
    """Serialize governance verification with mirror-affecting adapter flows."""
    if mode == "governance":
        return artifact_lock(project_root, "mirror-sync")
    return contextlib.nullcontext()


def verify_cmd(
    mode: Annotated[
        str,
        typer.Argument(
            help=(
                "Verification mode: governance | security | architecture | quality | "
                "feature | platform"
            ),
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
    full: Annotated[
        bool,
        typer.Option("--full", help="Use the expensive one-specialist-per-agent profile."),
    ] = False,
) -> None:
    """Run verification in the specified mode and produce a scored report."""
    if mode not in MODES:
        valid = ", ".join(sorted(MODES))
        typer.echo(f"Unknown mode: {mode}. Available: {valid}", err=True)
        raise typer.Exit(code=2)

    root = resolve_project_root(target)
    func = MODES[mode]
    profile = "full" if full else "normal"

    t0 = _time.monotonic()
    with _verify_execution_lock(root, mode), spinner(f"Running {mode} verification..."):
        result = func(root, profile=profile)
    elapsed_ms = int((_time.monotonic() - t0) * 1000)

    # Emit scan and advisory events (fail-open)
    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_scan_event

        emit_scan_event(
            root,
            mode=mode,
            score=result.score,
            findings=result.summary(),
            duration_ms=elapsed_ms,
            outcome="failure" if result.verdict.value == "FAIL" else "success",
        )

    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_guard_advisory

        summary = result.summary()
        emit_guard_advisory(
            root,
            files_checked=len({f.file for f in result.findings if f.file}),
            warnings=summary.get("blocker", 0)
            + summary.get("critical", 0)
            + summary.get("major", 0),
            concerns=summary.get("minor", 0) + summary.get("info", 0),
        )

    if is_json_mode() or output_json:
        report = {
            "mode": mode,
            "profile": result.profile,
            "score": result.score,
            "verdict": result.verdict.value,
            "findings_summary": result.summary(),
            "specialists": [
                {
                    "name": specialist.name,
                    "label": specialist.label,
                    "runner": specialist.runner,
                    "applicable": specialist.applicable,
                    "rationale": specialist.rationale,
                    "score": specialist.score,
                    "verdict": specialist.verdict.value,
                    "findings_summary": specialist.summary(),
                }
                for specialist in result.specialists
            ],
            "findings": [
                {
                    "severity": f.severity.value,
                    "category": f.category,
                    "message": f.message,
                    "file": f.file,
                    "line": f.line,
                    "specialist": f.specialist,
                    "runner": f.runner,
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
        kv("Profile", result.profile)
        kv("Score", f"{result.score}/100")
        kv("Verdict", result.verdict.value)

        if result.specialists:
            typer.echo(err=True)
            kv("Specialists", len(result.specialists))

            for specialist in result.specialists:
                if not specialist.applicable:
                    status_line(
                        "info",
                        f"[{specialist.runner}] {specialist.label}",
                        specialist.rationale or "not applicable",
                    )
                    continue

                specialist_status = (
                    "fail"
                    if specialist.verdict.value == "FAIL"
                    else "warn"
                    if specialist.verdict.value == "WARN"
                    else "ok"
                )
                specialist_summary = specialist.summary()
                summary_str = ", ".join(
                    f"{severity}: {count}" for severity, count in sorted(specialist_summary.items())
                )
                detail = f"{specialist.verdict.value} {specialist.score}/100"
                if summary_str:
                    detail += f" ({summary_str})"
                status_line(
                    specialist_status,
                    f"[{specialist.runner}] {specialist.label}",
                    detail,
                )
                for finding in result.findings_for_specialist(specialist.name):
                    loc = f" ({finding.file}:{finding.line})" if finding.file else ""
                    status_line(
                        "fail" if finding.severity.value in ("blocker", "critical") else "warn",
                        f"  [{finding.severity.value}] {finding.category}",
                        f"{finding.message}{loc}",
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
