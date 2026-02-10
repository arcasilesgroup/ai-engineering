"""Gate CLI commands: pre-commit, commit-msg, pre-push, risk-check.

Invoked by git hooks to run quality gate checks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from ai_engineering.paths import resolve_project_root
from ai_engineering.policy.gates import GateResult, run_gate
from ai_engineering.state.decision_logic import list_expired_decisions, list_expiring_soon
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import DecisionStore, GateHook


def _print_gate_result(result: GateResult) -> None:
    """Print gate results and exit with appropriate code.

    Args:
        result: The gate execution result.
    """
    status = "PASS" if result.passed else "FAIL"
    typer.echo(f"Gate [{result.hook.value}] {status}")

    for check in result.checks:
        icon = "✓" if check.passed else "✗"
        typer.echo(f"  {icon} {check.name}")
        if not check.passed and check.output:
            for line in check.output.splitlines()[:5]:
                typer.echo(f"    {line}")

    if not result.passed:
        raise typer.Exit(code=1)


def gate_pre_commit(
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Run pre-commit gate checks (format, lint, gitleaks)."""
    root = resolve_project_root(target)
    result = run_gate(GateHook.PRE_COMMIT, root)
    _print_gate_result(result)


def gate_commit_msg(
    msg_file: Annotated[
        Path,
        typer.Argument(help="Path to the commit message file."),
    ],
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Run commit-msg gate checks (message format validation)."""
    root = resolve_project_root(target)
    result = run_gate(GateHook.COMMIT_MSG, root, commit_msg_file=msg_file)
    _print_gate_result(result)


def gate_pre_push(
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Run pre-push gate checks (semgrep, pip-audit, tests, ty)."""
    root = resolve_project_root(target)
    result = run_gate(GateHook.PRE_PUSH, root)
    _print_gate_result(result)


def gate_risk_check(
    target: Annotated[
        Optional[Path],
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Fail on any expired risk acceptance."),
    ] = False,
) -> None:
    """Check risk acceptance status (expired and expiring-soon).

    Without --strict: reports status, exits 0 unless expired.
    With --strict: exits 1 if any expired risk acceptances exist.
    """
    root = resolve_project_root(target)
    ds_path = root / ".ai-engineering" / "state" / "decision-store.json"

    if not ds_path.exists():
        typer.echo("No decision store found — no risk acceptances to check.")
        return

    store = read_json_model(ds_path, DecisionStore)
    expired = list_expired_decisions(store)
    expiring = list_expiring_soon(store)

    if not expired and not expiring:
        typer.echo("All risk acceptances are current.")
        return

    if expiring:
        typer.echo(f"\nWarning: {len(expiring)} risk acceptance(s) expiring soon:")
        for d in expiring:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
            typer.echo(f"  - {d.id}: expires {exp}")

    if expired:
        typer.echo(f"\nBlocking: {len(expired)} expired risk acceptance(s):")
        for d in expired:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
            typer.echo(f"  - {d.id}: expired {exp}")

    if expired or (strict and expiring):
        raise typer.Exit(code=1)
