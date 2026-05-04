"""CLI surface for the spec-119 evaluation gate.

Wraps :mod:`ai_engineering.eval.gate` so CI can call ``ai-eng eval check
--json`` / ``ai-eng eval enforce`` without spinning up a Claude Code
agent. Three modes mirror the underlying gate runtime:

* ``check`` — emit JSON describing the gate outcome (advisory, exit 0).
* ``report`` — emit a markdown summary (advisory, exit 0).
* ``enforce`` — run the gate and exit with the gate-decided code
  (NO_GO under blocking enforcement → exit 1).

The trial runner defaults to the filesystem-graded one shipped with
:mod:`ai_engineering.eval.gate`, which inspects scenario metadata for
``expected_path`` / ``expected_content_substring`` / ``forbidden_path``.
This is the right runner for the seed scenario packs under
``.ai-engineering/evals/scenarios/``; bespoke runners are wired by
calling the underlying engine directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.eval.gate import (
    filesystem_trial_runner,
    mode_check,
    mode_enforce,
    mode_report,
    to_json,
)
from ai_engineering.paths import resolve_project_root


def eval_check(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of human text."),
    ] = False,
) -> None:
    """Advisory mode: run the gate, emit the outcome, exit 0.

    Used by PR-time CI lanes that should surface eval drift without
    blocking the merge. The same engine is invoked by ``ai-eng eval
    enforce`` for push-to-main; this command never raises a non-zero
    exit even when the gate verdict is NO_GO.
    """
    root = resolve_project_root(target)
    outcome = mode_check(root, trial_runner=filesystem_trial_runner(root))
    if json_output:
        import json

        typer.echo(json.dumps(outcome, indent=2, sort_keys=True, default=str))
    else:
        typer.echo(f"verdict: {outcome.get('verdict')}")
        typer.echo(f"enforcement: {outcome.get('enforcement')}")
        scorecards = outcome.get("scorecards") or []
        if scorecards:
            for sc in scorecards:
                typer.echo(
                    f"  pack: pass@{sc.get('k')}={sc.get('pass_at_k')!r} "
                    f"halluc={sc.get('hallucination_rate')!r} "
                    f"failed={sc.get('failed_scenarios')!r}"
                )
        skipped = outcome.get("skipped_reasons") or []
        for reason in skipped:
            typer.echo(f"  skipped: {reason}")


def eval_report(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Emit a markdown summary of the gate outcome."""
    root = resolve_project_root(target)
    md = mode_report(root, trial_runner=filesystem_trial_runner(root))
    typer.echo(md)


def eval_enforce(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope (machine-readable)."),
    ] = False,
    skip: Annotated[
        bool,
        typer.Option("--skip", help="Bypass the gate (audit-tagged SKIPPED verdict)."),
    ] = False,
    skip_reason: Annotated[
        str | None,
        typer.Option("--skip-reason", help="Required when --skip is set."),
    ] = None,
) -> None:
    """Enforcing mode: gate verdict drives the process exit code.

    Used by push-to-main CI lanes. ``skip=True`` short-circuits with a
    SKIPPED verdict so the audit log captures the bypass; the caller
    is responsible for emitting the audit event with the reason.
    """
    if skip and not skip_reason:
        typer.echo("Error: --skip requires --skip-reason for audit traceability.", err=True)
        raise typer.Exit(code=2)

    root = resolve_project_root(target)
    code, outcome = mode_enforce(
        root,
        trial_runner=filesystem_trial_runner(root),
        skip=skip,
        skip_reason=skip_reason,
    )
    if json_output:
        typer.echo(to_json(outcome))
    else:
        typer.echo(f"verdict: {outcome.verdict.value}")
        typer.echo(f"enforcement: {outcome.enforcement}")
        typer.echo(f"exit_code: {outcome.exit_code}")
        for reason in outcome.skipped_reasons:
            typer.echo(f"  skipped: {reason}")
    if code != 0:
        raise typer.Exit(code=code)


__all__ = ["eval_check", "eval_enforce", "eval_report"]
