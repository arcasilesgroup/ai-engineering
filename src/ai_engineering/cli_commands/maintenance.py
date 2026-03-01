"""Maintenance CLI commands: report, pr, branch-cleanup, risk-status, pipeline-compliance, all.

Framework maintenance operations including health reports, PR creation,
branch cleanup, risk governance status, pipeline compliance scanning,
and combined dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from ai_engineering.cli_envelope import NextAction, emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_progress import spinner, step_progress
from ai_engineering.cli_ui import (
    error,
    header,
    info,
    kv,
    result_header,
    success,
    suggest_next,
    warning,
)
from ai_engineering.maintenance.branch_cleanup import run_branch_cleanup
from ai_engineering.maintenance.repo_status import run_repo_status
from ai_engineering.maintenance.report import (
    create_maintenance_pr,
    generate_report,
)
from ai_engineering.maintenance.spec_reset import run_spec_reset
from ai_engineering.paths import resolve_project_root
from ai_engineering.pipeline.compliance import scan_all_pipelines
from ai_engineering.pipeline.injector import suggest_injection
from ai_engineering.state.decision_logic import (
    list_expired_decisions,
    list_expiring_soon,
)
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import DecisionStore


def maintenance_report(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    staleness_days: Annotated[
        int,
        typer.Option("--staleness-days", help="Days before a file is stale."),
    ] = 90,
) -> None:
    """Generate a framework maintenance report."""
    root = resolve_project_root(target)
    report = generate_report(root, staleness_days=staleness_days)

    if is_json_mode():
        emit_success(
            "ai-eng maintenance report",
            report.to_dict(),
            [
                NextAction(
                    command="ai-eng maintenance all",
                    description="Full maintenance dashboard",
                ),
            ],
        )
    else:
        typer.echo(report.to_markdown())


def maintenance_pr(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    branch: Annotated[
        str,
        typer.Option("--branch", "-b", help="Branch name for the PR."),
    ] = "maintenance/framework-update",
) -> None:
    """Generate a maintenance report and create a PR."""
    root = resolve_project_root(target)
    report = generate_report(root)
    result = create_maintenance_pr(root, report, branch_name=branch)

    if is_json_mode():
        if result:
            emit_success(
                "ai-eng maintenance pr",
                {"created": True, "branch": branch},
            )
        else:
            emit_error(
                "ai-eng maintenance pr",
                "Failed to create maintenance PR",
                "PR_CREATE_FAILED",
                "Check git and VCS provider configuration",
            )
            raise typer.Exit(code=1)
    else:
        if result:
            success("Maintenance PR created successfully.")
        else:
            error("Failed to create maintenance PR")
            raise typer.Exit(code=1)


def maintenance_branch_cleanup(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    base: Annotated[
        str,
        typer.Option("--base", "-b", help="Base branch for merge check."),
    ] = "main",
    force: Annotated[
        bool,
        typer.Option("--force", help="Force-delete unmerged branches."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="List branches without deleting."),
    ] = False,
) -> None:
    """Clean up stale local branches (fetch, prune, delete merged)."""
    root = resolve_project_root(target)
    with spinner("Cleaning up branches..."):
        result = run_branch_cleanup(
            root,
            base_branch=base,
            force=force,
            dry_run=dry_run,
        )

    if is_json_mode():
        emit_success(
            "ai-eng maintenance branch-cleanup",
            result.to_dict(),
            [
                NextAction(
                    command="ai-eng maintenance repo-status",
                    description="View branch status",
                ),
            ],
        )
    else:
        typer.echo(result.to_markdown())

    if not result.success:
        raise typer.Exit(code=1)


def _collect_risk_status(root: Path) -> dict[str, Any]:
    """Collect risk acceptance status as a dict. Returns empty dict if no store."""
    ds_path = root / ".ai-engineering" / "state" / "decision-store.json"

    if not ds_path.exists():
        return {"total": 0, "active": 0, "expiring": 0, "expired": 0, "details": []}

    store = read_json_model(ds_path, DecisionStore)
    risk = store.risk_decisions()
    expired = list_expired_decisions(store)
    expiring = list_expiring_soon(store)
    active = [d for d in risk if d not in expired and d not in expiring]

    details: list[dict[str, str]] = []
    for d in expiring:
        exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "?"
        details.append({"id": d.id, "status": "expiring", "expires_at": exp})
    for d in expired:
        exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "?"
        details.append({"id": d.id, "status": "expired", "expires_at": exp})

    return {
        "total": len(risk),
        "active": len(active),
        "expiring": len(expiring),
        "expired": len(expired),
        "details": details,
    }


def _display_risk_status(root: Path) -> None:
    """Display risk acceptance status. Shared by risk-status and all commands."""
    ds_path = root / ".ai-engineering" / "state" / "decision-store.json"

    if not ds_path.exists():
        info("No decision store found \u2014 no risk decisions to report")
        return

    store = read_json_model(ds_path, DecisionStore)
    risk = store.risk_decisions()
    expired = list_expired_decisions(store)
    expiring = list_expiring_soon(store)
    active = [d for d in risk if d not in expired and d not in expiring]

    kv("Total risk acceptances", len(risk))
    kv("Active (current)", len(active))
    kv("Expiring soon (<=7d)", len(expiring))
    kv("Expired", len(expired))

    if expiring:
        header("Expiring Soon")
        for d in expiring:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "?"
            warning(f"{d.id}: expires {exp} \u2014 {d.context[:80]}")

    if expired:
        header("Expired (action required)")
        for d in expired:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "?"
            warning(f"{d.id}: expired {exp} \u2014 {d.context[:80]}")


def maintenance_risk_status(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
) -> None:
    """Show risk acceptance status (active, expiring, expired)."""
    root = resolve_project_root(target)

    if is_json_mode():
        emit_success(
            "ai-eng maintenance risk-status",
            _collect_risk_status(root),
            [
                NextAction(
                    command="ai-eng maintenance all",
                    description="Full maintenance dashboard",
                ),
            ],
        )
    else:
        header("Risk Acceptance Status")
        _display_risk_status(root)


def maintenance_pipeline_compliance(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    suggest: Annotated[
        bool,
        typer.Option("--suggest", help="Show injection snippets for non-compliant pipelines."),
    ] = False,
) -> None:
    """Scan CI/CD pipelines for risk governance compliance."""
    root = resolve_project_root(target)
    report = scan_all_pipelines(root)

    if is_json_mode():
        emit_success(
            "ai-eng maintenance pipeline-compliance",
            report.to_dict(),
            [
                NextAction(
                    command="ai-eng maintenance pipeline-compliance --suggest",
                    description="Show injection snippets",
                ),
            ],
        )
    else:
        typer.echo(report.to_markdown())

        if suggest:
            for r in report.results:
                if not r.compliant:
                    typer.echo(suggest_injection(r.pipeline))


def maintenance_repo_status(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    base: Annotated[
        str,
        typer.Option("--base", "-b", help="Base branch for comparisons."),
    ] = "main",
    include_prs: Annotated[
        bool,
        typer.Option("--include-prs/--no-prs", help="Include open PR listing."),
    ] = True,
) -> None:
    """Show repository branch and PR status dashboard."""
    root = resolve_project_root(target)
    with spinner("Analyzing repository..."):
        result = run_repo_status(root, base_branch=base, include_prs=include_prs)

    if is_json_mode():
        emit_success(
            "ai-eng maintenance repo-status",
            result.to_dict(),
            [
                NextAction(
                    command="ai-eng maintenance branch-cleanup",
                    description="Clean up stale branches",
                ),
            ],
        )
    else:
        typer.echo(result.to_markdown())


def maintenance_spec_reset(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Report findings without modifying files."),
    ] = False,
) -> None:
    """Reset spec state: archive completed specs, clear _active.md."""
    root = resolve_project_root(target)
    result = run_spec_reset(root, dry_run=dry_run)

    if is_json_mode():
        emit_success(
            "ai-eng maintenance spec-reset",
            result.to_dict(),
        )
    else:
        typer.echo(result.to_markdown())

    if not result.success:
        raise typer.Exit(code=1)


def maintenance_all(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    base: Annotated[
        str,
        typer.Option("--base", "-b", help="Base branch for comparisons."),
    ] = "main",
    staleness_days: Annotated[
        int,
        typer.Option("--staleness-days", help="Days before a file is stale."),
    ] = 90,
) -> None:
    """Run all maintenance checks and produce a combined report.

    Executes: report, risk-status, pipeline-compliance, repo-status,
    and spec-reset (dry-run). Intended for dashboard overview.
    """
    root = resolve_project_root(target)

    with step_progress(5, "Running maintenance checks") as tracker:
        tracker.step("Generating framework report...")
        report = generate_report(root, staleness_days=staleness_days)
        tracker.step("Checking risk status...")
        risk_data = _collect_risk_status(root)
        tracker.step("Scanning pipeline compliance...")
        compliance = scan_all_pipelines(root)
        tracker.step("Analyzing repository status...")
        repo = run_repo_status(root, base_branch=base)
        tracker.step("Checking spec reset...")
        spec = run_spec_reset(root, dry_run=True)

    any_issue = not spec.success

    if is_json_mode():
        emit_success(
            "ai-eng maintenance all",
            {
                "passed": not any_issue,
                "report": report.to_dict(),
                "risk_status": risk_data,
                "pipeline_compliance": compliance.to_dict(),
                "repo_status": repo.to_dict(),
                "spec_reset": spec.to_dict(),
            },
            [
                NextAction(
                    command="ai-eng maintenance spec-reset",
                    description="Apply spec reset",
                ),
                NextAction(command="ai-eng doctor", description="Run health diagnostics"),
            ],
        )
    else:
        header("Framework Report")
        typer.echo(report.to_markdown())

        header("Risk Status")
        _display_risk_status(root)

        header("Pipeline Compliance")
        typer.echo(compliance.to_markdown())

        header("Repository Status")
        typer.echo(repo.to_markdown())

        header("Spec Reset (dry-run)")
        typer.echo(spec.to_markdown())

        header("Summary")
        status = "PASS" if not any_issue else "NEEDS ATTENTION"
        result_header("Maintenance", status)
        suggest_next(
            [
                ("ai-eng maintenance report", "Detailed framework health report"),
                ("ai-eng maintenance spec-reset", "Apply spec reset"),
                ("ai-eng doctor", "Run health diagnostics"),
            ]
        )

    if any_issue:
        raise typer.Exit(code=1)
