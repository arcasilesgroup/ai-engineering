"""Decision store CLI commands.

Provides `ai-eng decision list` and `ai-eng decision expire-check`
for managing the decision store without AI tokens.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer

from ai_engineering.state.service import StateService


def _project_root() -> Path:
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".ai-engineering").is_dir():
            return parent
    return cwd


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
    root = _project_root()
    store = _load_store(root)

    if store is None or not store.decisions:
        typer.echo("Decision store is empty.")
        return

    typer.echo(f"# Decisions ({len(store.decisions)} total)")
    typer.echo("")

    for d in store.decisions:
        exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "no expiry"
        severity = d.severity.value if d.severity else "?"
        status = d.status.value if d.status else "?"
        typer.echo(f"  {d.id} | {status} | {severity} | expires: {exp}")
        typer.echo(f"    Context: {d.context[:80]}")
        typer.echo(f"    Decision: {d.decision[:80]}")
        typer.echo("")


def decision_expire_check() -> None:
    """Check for decisions expiring within 7 days or already expired."""
    root = _project_root()
    store = _load_store(root)

    if store is None or not store.decisions:
        typer.echo("No decisions to check.")
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
        typer.echo("All active decisions are within validity period.")
        return

    if expired:
        typer.echo(f"## EXPIRED ({len(expired)})")
        for d in expired:
            typer.echo(f"  - {d.id}: expired {d.expires_at}")
        typer.echo("")

    if expiring:
        typer.echo(f"## EXPIRING SOON ({len(expiring)})")
        for d in expiring:
            days_left = (d.expires_at - now).days if d.expires_at else 0
            typer.echo(f"  - {d.id}: expires in {days_left} days ({d.expires_at})")
