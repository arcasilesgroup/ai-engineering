"""Gate CLI commands: pre-commit, commit-msg, pre-push, risk-check, all.

Invoked by git hooks to run quality gate checks.
Performance-critical: no logo, no stage banner, minimal colour.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_envelope import NextAction, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import (
    header,
    info,
    print_stdout,
    result_header,
    status_line,
    success,
    suggest_next,
    warning,
)
from ai_engineering.paths import resolve_project_root
from ai_engineering.policy.gates import GateResult, run_gate
from ai_engineering.state.decision_logic import list_expired_decisions, list_expiring_soon
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import DecisionStore, GateHook


def _print_gate_result(result: GateResult) -> None:
    """Print gate results and exit with appropriate code."""
    status = "PASS" if result.passed else "FAIL"

    if is_json_mode():
        next_actions = []
        if not result.passed:
            next_actions = [
                NextAction(command="ruff check --fix .", description="Auto-fix lint issues"),
            ]
        emit_success(
            f"ai-eng gate {result.hook.value}",
            {
                "hook": result.hook.value,
                "passed": result.passed,
                "checks": [
                    {"name": c.name, "passed": c.passed, "output": c.output} for c in result.checks
                ],
            },
            next_actions,
        )
    else:
        # Primary result on stdout (preserves test assertions)
        print_stdout(f"Gate [{result.hook.value}] {status}")
        for check in result.checks:
            st = "ok" if check.passed else "fail"
            status_line(st, check.name, "passed" if check.passed else "failed")
            if not check.passed and check.output:
                for line in check.output.splitlines()[:5]:
                    info(f"  {line}")

    if not result.passed:
        raise typer.Exit(code=1)


def gate_pre_commit(
    target: Annotated[
        Path | None,
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
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Run commit-msg gate checks (message format validation)."""
    root = resolve_project_root(target)
    result = run_gate(GateHook.COMMIT_MSG, root, commit_msg_file=msg_file)
    _print_gate_result(result)


def gate_pre_push(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Run pre-push gate checks (semgrep, pip-audit, tests, ty)."""
    root = resolve_project_root(target)
    result = run_gate(GateHook.PRE_PUSH, root)
    _print_gate_result(result)


def _check_risk_inline(root: Path, strict: bool) -> bool:
    """Check risk acceptance status inline. Returns True if any failure detected."""
    ds_path = root / ".ai-engineering" / "state" / "decision-store.json"

    if not ds_path.exists():
        info("No decision store found — no risk acceptances to evaluate")
        return False

    store = read_json_model(ds_path, DecisionStore)
    expired = list_expired_decisions(store)
    expiring = list_expiring_soon(store)

    if not expired and not expiring:
        success("All risk acceptances are current")
        return False

    if expiring:
        warning(f"{len(expiring)} risk acceptance(s) expiring soon:")
        for d in expiring:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
            info(f"  - {d.id}: expires {exp}")

    if expired:
        warning(f"{len(expired)} expired risk acceptance(s):")
        for d in expired:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "unknown"
            info(f"  - {d.id}: expired {exp}")

    return bool(expired or (strict and expiring))


def gate_risk_check(
    target: Annotated[
        Path | None,
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
    if _check_risk_inline(root, strict):
        raise typer.Exit(code=1)


def gate_all(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Fail on expiring risk acceptances too."),
    ] = False,
) -> None:
    """Run all gate checks (pre-commit + pre-push + risk-check).

    For manual use before committing. Not for git hooks.
    Excludes commit-msg (requires a message file).
    """
    root = resolve_project_root(target)
    any_failed = False
    all_results: list[GateResult] = []

    for hook in (GateHook.PRE_COMMIT, GateHook.PRE_PUSH):
        result = run_gate(hook, root)
        all_results.append(result)
        if not result.passed:
            any_failed = True

    risk_failed = _check_risk_inline(root, strict)
    if risk_failed:
        any_failed = True

    if is_json_mode():
        checks = []
        for r in all_results:
            checks.extend(
                {"gate": r.hook.value, "name": c.name, "passed": c.passed, "output": c.output}
                for c in r.checks
            )
        emit_success(
            "ai-eng gate all",
            {"passed": not any_failed, "checks": checks},
            []
            if not any_failed
            else [NextAction(command="ai-eng doctor", description="Diagnose issues")],
        )
    else:
        overall = "PASS" if not any_failed else "FAIL"
        result_header("Gate All", overall)
        for r in all_results:
            header(f"gate {r.hook.value}")
            for check in r.checks:
                st = "ok" if check.passed else "fail"
                status_line(st, check.name, "passed" if check.passed else "failed")
        if any_failed:
            suggest_next(
                [
                    ("ai-eng doctor --fix-tools", "Install missing tools"),
                    ("ai-eng gate pre-commit", "Re-run specific gate"),
                ]
            )

    if any_failed:
        raise typer.Exit(code=1)
