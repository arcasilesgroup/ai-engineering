"""Decision store CLI commands.

Provides `ai-eng decision list`, `ai-eng decision expire-check`,
and `ai-eng decision record` for managing the decision store
without AI tokens.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_ui import error, header, info, kv, status_line, success
from ai_engineering.paths import find_project_root
from ai_engineering.state.observability import emit_control_outcome
from ai_engineering.state.service import StateService


def _load_store(root: Path):
    path = root / ".ai-engineering" / "state" / "decision-store.json"
    if not path.exists():
        return None
    try:
        return StateService(root).load_decisions()
    except (OSError, ValueError):
        return None


def decision_list() -> None:
    """List all decisions in the decision store."""
    root = find_project_root()
    store = _load_store(root)

    if store is None or not store.decisions:
        info("Decision store is empty.")
        return

    header(f"Decisions ({len(store.decisions)} total)")

    for d in store.decisions:
        exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "no expiry"
        severity = d.severity.value if d.severity else "?"
        d_status = d.status.value if d.status else "?"
        line_status = "ok" if d_status == "active" else "warn"
        status_line(line_status, d.id, f"{d_status} · {severity} · expires: {exp}")
        kv("  Context", d.context[:80])
        kv("  Decision", d.decision[:80])
        typer.echo("")


def decision_expire_check() -> None:
    """Check for decisions expiring within 7 days or already expired."""
    root = find_project_root()
    store = _load_store(root)

    if store is None or not store.decisions:
        info("No decisions to check.")
        return

    now = datetime.now(tz=UTC)
    expired = []
    expiring = []

    for d in store.decisions:
        if d.status.value != "active":
            continue
        if d.expires_at is None:
            continue
        if d.expires_at <= now:
            expired.append(d)
        elif (d.expires_at - now).days <= 7:
            expiring.append(d)

    if not expired and not expiring:
        status_line("ok", "Decisions", "all within validity period")
        return

    if expired:
        header(f"Expired ({len(expired)})")
        for d in expired:
            status_line("fail", d.id, f"expired {d.expires_at}")
        typer.echo("")

    if expiring:
        header(f"Expiring soon ({len(expiring)})")
        for d in expiring:
            days_left = (d.expires_at - now).days if d.expires_at else 0
            status_line("warn", d.id, f"expires in {days_left} days")


def decision_record(
    decision_id: Annotated[
        str,
        typer.Argument(help="Unique decision ID (e.g. 'd-034-shared-parser')."),
    ],
    context: Annotated[
        str,
        typer.Option("--context", "-c", help="Context/scope of the decision."),
    ],
    decision_text: Annotated[
        str,
        typer.Option("--decision", "-d", help="The decision made."),
    ],
    spec_id: Annotated[
        str,
        typer.Option("--spec", "-s", help="Spec that owns this decision."),
    ] = "",
    severity: Annotated[
        str | None,
        typer.Option("--severity", help="Risk severity: low, medium, high, critical."),
    ] = None,
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            help="Category: risk-acceptance, flow-decision, architecture-decision.",
        ),
    ] = None,
    expires: Annotated[
        str | None,
        typer.Option("--expires", help="Expiry date in ISO format (YYYY-MM-DD)."),
    ] = None,
) -> None:
    """Record a new decision in the decision store."""
    from ai_engineering.state.models import (
        Decision,
        DecisionStatus,
        DecisionStore,
        RiskCategory,
        RiskSeverity,
    )

    root = find_project_root()
    svc = StateService(root)
    store_path = root / ".ai-engineering" / "state" / "decision-store.json"

    # Load or create store
    if store_path.exists():
        try:
            store = svc.load_decisions()
        except (OSError, ValueError):
            store = DecisionStore()
    else:
        store = DecisionStore()

    # Check for duplicate ID
    if store.find_by_id(decision_id):
        error(f"Decision '{decision_id}' already exists. Use a unique ID.")
        raise typer.Exit(code=1)

    # Parse optional fields
    parsed_severity = RiskSeverity(severity) if severity else None
    parsed_category = RiskCategory(category) if category else None
    parsed_expires = datetime.fromisoformat(expires).replace(tzinfo=UTC) if expires else None

    now = datetime.now(tz=UTC)
    entry = Decision(
        id=decision_id,
        context=context,
        decision=decision_text,
        decidedAt=now,
        spec=spec_id,
        severity=parsed_severity,
        risk_category=parsed_category,
        expires_at=parsed_expires,
        status=DecisionStatus.ACTIVE,
    )

    store.decisions.append(entry)
    svc.save_decisions(store)

    emit_control_outcome(
        root,
        category="governance",
        control="decision-record",
        component="decision-store",
        outcome="success",
        source="cli",
        metadata={
            "decision_id": decision_id,
            "context": context,
            "spec_id": spec_id or None,
            "severity": severity,
            "category": category,
            "expires": expires,
        },
    )

    success(f"Recorded decision '{decision_id}' → decision-store.json + framework-events.")
