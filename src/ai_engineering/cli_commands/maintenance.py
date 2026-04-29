"""Maintenance CLI commands: report, pr, branch-cleanup, risk-status, all.

Framework maintenance operations including health reports, PR creation,
branch cleanup, risk governance status, and combined dashboard.
"""

from __future__ import annotations

import gzip
import json
import shutil
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
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
from ai_engineering.state.decision_logic import (
    list_expired_decisions,
    list_expiring_soon,
)
from ai_engineering.state.service import StateService

# spec-114 G-5 / G-6 -- NDJSON reset constants.
_FRAMEWORK_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"
_LEGACY_READ_MARKER = "legacy hash location detected"
_LEGACY_READ_WINDOW = timedelta(hours=24)
_RESET_ELIGIBLE_OFFSET = timedelta(days=14)
# D-114-05: archive name uses ISO 8601 with `T` and `-` only -- no `:`
# (cross-OS filesystem safety; Windows rejects ':' in filenames).
_ARCHIVE_TIMESTAMP_FORMAT = "%Y-%m-%dT%H-%M-%S"


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

    store = StateService(root).load_decisions()
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

    store = StateService(root).load_decisions()
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
    """Reset spec state: append to history, clear spec buffer."""
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


# ---------------------------------------------------------------------------
# spec-114 G-5 / G-6 -- ai-eng maintenance reset-events
# ---------------------------------------------------------------------------


def _spec_110_in_main(project_root: Path) -> bool:
    """Return True iff origin/main carries a commit referencing spec-110.

    Tests monkeypatch this helper -- no stub git binary required on
    PATH. Production calls ``git log origin/main --grep=spec-110
    --max-count=1`` and treats any non-empty stdout as a signal that
    spec-110 has merged. Errors (no remote, git not installed) are
    treated as "not yet merged" so the gate is fail-safe.
    """
    try:
        result = subprocess.run(
            ["git", "log", "origin/main", "--grep=spec-110", "--max-count=1"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return bool(result.stdout.strip())


def _has_recent_legacy_reads(events_path: Path, *, now: datetime | None = None) -> bool:
    """Scan the last 24 h of NDJSON for the spec-110 dual-read marker.

    The dual-read warning fires from ``state/audit_chain.iter_validate_chain``
    when an event still carries ``prev_event_hash`` only under
    ``detail.prev_event_hash`` (legacy location). If the warning shows up
    inside the rolling window, a live reader is still on the legacy path
    and a reset would silently break their understanding of the chain.
    """
    if not events_path.exists():
        return False
    cutoff = (now or datetime.now(tz=UTC)) - _LEGACY_READ_WINDOW
    try:
        text = events_path.read_text(encoding="utf-8")
    except OSError:
        return False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or _LEGACY_READ_MARKER not in stripped:
            continue
        try:
            event = json.loads(stripped)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(event, dict):
            continue
        ts = event.get("timestamp")
        if not isinstance(ts, str):
            continue
        try:
            event_dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
        except ValueError:
            continue
        if event_dt >= cutoff:
            return True
    return False


def _archive_events(events_path: Path) -> Path:
    """Gzip-compress ``events_path`` to a timestamped legacy archive.

    Returns the archive path. Uses :func:`Path.replace` semantics for the
    atomic swap: gzip the file in place then unlink the source so that
    callers see either the archive (success) or the original NDJSON
    (failure). The archive name follows D-114-05.
    """
    timestamp = datetime.now(tz=UTC).strftime(_ARCHIVE_TIMESTAMP_FORMAT)
    archive_path = events_path.with_name(f"{events_path.name}.legacy-{timestamp}.gz")
    with events_path.open("rb") as src, gzip.open(archive_path, "wb") as dst:
        shutil.copyfileobj(src, dst)
    events_path.unlink()
    return archive_path


def _write_seed_event(events_path: Path, *, archive_name: str) -> dict:
    """Write the D-114-06 seed event into a fresh ``framework-events.ndjson``.

    The seed is the first event in the new chain so ``prev_event_hash``
    is ``None`` (anchor). We set the field explicitly so audit-chain
    walkers do not treat the event as legacy / pre-spec-110.
    """
    project_name = events_path.parents[2].name
    seed = {
        "kind": "framework_operation",
        "engine": "ai_engineering",
        "timestamp": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "component": "maintenance.reset-events",
        "outcome": "success",
        "correlationId": uuid.uuid4().hex,
        "schemaVersion": "1.0",
        "project": project_name,
        "detail": {
            "reset_reason": "spec-114 G-5",
            "previous_archive": archive_name,
        },
        "prev_event_hash": None,
    }
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(seed, sort_keys=True, default=str) + "\n")
    return seed


def maintenance_reset_events(
    target: Annotated[
        Path | None,
        typer.Option("--target", "-t", help="Target project root."),
    ] = None,
    print_eligible_date: Annotated[
        bool,
        typer.Option(
            "--print-eligible-date",
            help="Print earliest date /ai-skill-sharpen x49 may run (today + 14 days) and exit.",
        ),
    ] = False,
) -> None:
    """Archive ``framework-events.ndjson`` and seed a fresh chain (spec-114 G-5).

    Gates (spec-114 G-6):
      1. ``git log origin/main --grep=spec-110`` must return at least one
         commit; otherwise the spec-110 hash-chain root migration has not
         landed in main and a reset would lose mid-migration data (R-1).
      2. No ``legacy hash location detected`` warnings may appear in the
         NDJSON within the last 24 h; a live reader still on the legacy
         pointer would lose chain continuity (R-8).

    Both gates are *fail-closed*: an error refuses the reset, exits
    non-zero, and surfaces the actionable hint to the operator.
    """
    root = resolve_project_root(target)

    if print_eligible_date:
        eligible = (datetime.now(tz=UTC).date() + _RESET_ELIGIBLE_OFFSET).isoformat()
        if is_json_mode():
            emit_success(
                "ai-eng maintenance reset-events",
                {"eligible_date": eligible, "applied": False},
            )
        else:
            typer.echo(f"Earliest /ai-skill-sharpen x49 eligible date: {eligible}")
        return

    events_path = root / _FRAMEWORK_EVENTS_REL

    if not _spec_110_in_main(root):
        msg = (
            "Refusing to reset framework-events.ndjson: spec-110 commits "
            "are not yet present in origin/main. Wait for the spec-110 PR "
            "to merge before running reset-events (R-1 mitigation)."
        )
        if is_json_mode():
            emit_error(
                "ai-eng maintenance reset-events",
                msg,
                "RESET_GATE_SPEC_110",
                "Run after spec-110 PR merges into main.",
            )
        else:
            error(msg)
        raise typer.Exit(code=1)

    if _has_recent_legacy_reads(events_path):
        msg = (
            "Refusing to reset framework-events.ndjson: 'legacy hash "
            "location detected' warnings have fired within the last 24h. "
            "A live reader is still on the pre-spec-110 chain pointer. "
            "Wait for legacy reads to clear before running reset-events "
            "(R-8 mitigation)."
        )
        if is_json_mode():
            emit_error(
                "ai-eng maintenance reset-events",
                msg,
                "RESET_GATE_LEGACY_READS",
                "Wait 24h after the last legacy hash warning, then retry.",
            )
        else:
            error(msg)
        raise typer.Exit(code=1)

    if not events_path.exists():
        msg = (
            "Nothing to reset: framework-events.ndjson does not exist. "
            "Run a hook or `ai-eng doctor` once to bootstrap the file."
        )
        if is_json_mode():
            emit_error(
                "ai-eng maintenance reset-events",
                msg,
                "RESET_NO_EVENTS_FILE",
                "Bootstrap the events file first.",
            )
        else:
            error(msg)
        raise typer.Exit(code=1)

    archive_path = _archive_events(events_path)
    seed = _write_seed_event(events_path, archive_name=archive_path.name)

    if is_json_mode():
        emit_success(
            "ai-eng maintenance reset-events",
            {
                "applied": True,
                "archive": archive_path.name,
                "seed_event": seed,
            },
            [
                NextAction(
                    command="ai-eng audit verify",
                    description="Verify the fresh hash chain.",
                ),
            ],
        )
    else:
        success(f"Archived NDJSON to {archive_path.name}")
        success("Wrote fresh framework-events.ndjson with seed event.")
        suggest_next(
            [
                ("ai-eng audit verify", "Verify the fresh hash chain"),
            ]
        )


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

    Executes: report, risk-status, repo-status, and spec-reset (dry-run).
    Intended for dashboard overview.
    """
    root = resolve_project_root(target)

    with step_progress(4, "Running maintenance checks") as tracker:
        tracker.step("Generating framework report...")
        report = generate_report(root, staleness_days=staleness_days)
        tracker.step("Checking risk status...")
        risk_data = _collect_risk_status(root)
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
