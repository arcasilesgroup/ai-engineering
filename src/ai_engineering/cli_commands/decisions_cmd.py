"""Decision store CLI commands.

Provides ``ai-eng decision list``, ``ai-eng decision expire-check``,
``ai-eng decision record``, and ``ai-eng decision backfill`` for
managing the canonical ``decisions`` table in ``state.db``.

Per CLAUDE.md §0 bootstrap, ``state.db decisions`` is the source of
truth (D-132-08 wave; legacy ``decision-store.json`` is deprecated).
These commands read and write the SQL table directly via
``state_db.list_decisions`` and ``state_db.upsert_decision_rows_raw``;
no Pydantic shape is reconstructed for the CLI surface.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_ui import error, header, info, status_line, success
from ai_engineering.paths import find_project_root
from ai_engineering.state.observability import emit_control_outcome
from ai_engineering.state.state_db import (
    list_decisions,
    state_db_path,
    upsert_decision_rows_raw,
)

# Canonical regex for governance decision IDs: ``D-<spec>-<NN>[a-z]?``.
# Examples: D-127-11, D-131-09b, D-131-09. Matches three-digit specs (100+).
_DECISION_ID_RE = re.compile(r"\bD-(?P<spec>\d{3})-(?P<num>\d{2}[a-z]?)\b")


def decision_list() -> None:
    """List all decisions in the canonical state.db ``decisions`` table."""
    root = find_project_root()
    rows = list_decisions(root)

    if not rows:
        info("Decision store is empty.")
        info("Run `ai-eng decision backfill` to seed from specs/CHANGELOG.")
        return

    header(f"Decisions ({len(rows)} total)")

    for row in rows:
        decision_id = row.get("decision_id") or "?"
        spec_id = row.get("spec_id") or "-"
        d_status = row.get("status") or "?"
        title = (row.get("title") or "").strip()
        title_short = title[:80] + ("…" if len(title) > 80 else "")
        expires_at = row.get("expires_at")
        expiry_chunk = f" · expires {expires_at[:10]}" if expires_at else ""
        line_status = "ok" if d_status == "active" else "warn"
        status_line(
            line_status,
            decision_id,
            f"{spec_id} · {d_status}{expiry_chunk} · {title_short}",
        )


def _parse_expires_at(value: str | None) -> datetime | None:
    """Parse an ISO-8601 string (date or full timestamp) into UTC datetime."""
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def decision_expire_check() -> None:
    """Flag decisions whose ``expires_at`` is past or within 7 days."""
    root = find_project_root()
    rows = list_decisions(root, status="active")

    if not rows:
        info("No active decisions to check.")
        return

    now = datetime.now(tz=UTC)
    expired: list[dict[str, str | None]] = []
    expiring: list[tuple[dict[str, str | None], int]] = []

    for row in rows:
        raw = row.get("expires_at")
        if not raw:
            continue
        try:
            exp_dt = datetime.fromisoformat(str(raw))
        except ValueError:
            continue
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=UTC)
        if exp_dt <= now:
            expired.append(row)
        elif (exp_dt - now).days <= 7:
            expiring.append((row, (exp_dt - now).days))

    if not expired and not expiring:
        status_line("ok", "Decisions", "all within validity period")
        return

    if expired:
        header(f"Expired ({len(expired)})")
        for row in expired:
            decision_id = row.get("decision_id") or "?"
            expires_at = row.get("expires_at") or ""
            status_line("fail", decision_id, f"expired {expires_at[:10]}")
        typer.echo("")

    if expiring:
        header(f"Expiring soon ({len(expiring)})")
        for row, days_left in expiring:
            decision_id = row.get("decision_id") or "?"
            status_line("warn", decision_id, f"expires in {days_left} days")


def decision_record(
    decision_id: Annotated[
        str,
        typer.Argument(help="Unique decision ID (e.g. 'D-132-08')."),
    ],
    context: Annotated[
        str,
        typer.Option("--context", "-c", help="Context/scope of the decision."),
    ],
    decision_text: Annotated[
        str,
        typer.Option("--decision", "-d", help="The decision made (becomes title)."),
    ],
    spec_id: Annotated[
        str,
        typer.Option("--spec", "-s", help="Spec that owns this decision."),
    ] = "",
    rationale: Annotated[
        str | None,
        typer.Option("--rationale", help="Optional rationale text."),
    ] = None,
    status: Annotated[
        str,
        typer.Option(
            "--status",
            help="Status: active|expired|revoked|superseded|remediated.",
        ),
    ] = "active",
    expires: Annotated[
        str | None,
        typer.Option(
            "--expires",
            help="Expiry date (ISO-8601 date or datetime, e.g. 2026-06-01).",
        ),
    ] = None,
) -> None:
    """Record a new decision into the canonical state.db ``decisions`` table."""
    root = find_project_root()

    existing = list_decisions(root)
    if any(r.get("decision_id") == decision_id for r in existing):
        error(f"Decision '{decision_id}' already exists. Use a unique ID.")
        raise typer.Exit(code=1)

    try:
        parsed_expires = _parse_expires_at(expires)
    except ValueError:
        error(f"Invalid --expires value: {expires!r}. Use ISO-8601 (YYYY-MM-DD).")
        raise typer.Exit(code=1) from None

    expires_iso = parsed_expires.isoformat() if parsed_expires else None

    row = {
        "decision_id": decision_id,
        "spec_id": spec_id,
        "status": status,
        "title": decision_text,
        "rationale": rationale,
        "context": context,
        "expires_at": expires_iso,
    }

    attempted = upsert_decision_rows_raw(root, [row])
    if attempted != 1:
        error(f"Failed to record decision '{decision_id}'.")
        raise typer.Exit(code=1)

    emit_control_outcome(
        root,
        category="governance",
        control="decision-record",
        component="decision-store",
        outcome="success",
        source="cli",
        metadata={
            "decision_id": decision_id,
            "spec_id": spec_id or None,
            "status": status,
            "expires_at": expires_iso,
        },
    )

    success(f"Recorded decision '{decision_id}' → state.db + framework-events.")


# ---------------------------------------------------------------------------
# Backfill subcommand
# ---------------------------------------------------------------------------


# Source priority: specs are authoritative; CHANGELOG / CONSTITUTION /
# CLAUDE.md are fallbacks. The first hit in this order wins (most
# descriptive `title` from spec context).
_DEFAULT_BACKFILL_GLOBS: tuple[str, ...] = (
    ".ai-engineering/specs/*.md",
    "CHANGELOG.md",
    "CONSTITUTION.md",
    "CLAUDE.md",
)

_SOURCE_LABELS = {
    ".ai-engineering/specs": "specs",
    "CHANGELOG.md": "changelog",
    "CONSTITUTION.md": "constitution",
    "CLAUDE.md": "claude.md",
}


def _label_for_path(rel_path: str) -> str:
    """Map a relative path to a short source label for the report."""
    for prefix, label in _SOURCE_LABELS.items():
        if rel_path == prefix or rel_path.startswith(prefix + "/"):
            return label
    return "other"


def _iter_source_files(root: Path, globs: tuple[str, ...]) -> list[Path]:
    """Expand ``globs`` relative to ``root`` preserving priority order."""
    seen: set[Path] = set()
    ordered: list[Path] = []
    for pattern in globs:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and path not in seen:
                seen.add(path)
                ordered.append(path)
    return ordered


def _scan_decisions(root: Path, files: list[Path]) -> list[dict[str, str | None]]:
    """Extract unique ``D-XXX-NN`` references from ``files``.

    First hit per ``decision_id`` wins (so specs aporta the title before
    CHANGELOG / CONSTITUTION / CLAUDE.md fallbacks override it).
    """
    found: dict[str, dict[str, str | None]] = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        source_label = _label_for_path(rel)
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for lineno, raw_line in enumerate(lines, start=1):
            for match in _DECISION_ID_RE.finditer(raw_line):
                decision_id = f"D-{match.group('spec')}-{match.group('num')}"
                if decision_id in found:
                    continue
                line_stripped = raw_line.strip()
                title = line_stripped[:200]
                found[decision_id] = {
                    "decision_id": decision_id,
                    "spec_id": f"spec-{match.group('spec')}",
                    "status": "active",
                    "title": title,
                    "rationale": None,
                    "context": f"{rel}:{lineno}",
                    "consequences": None,
                    "superseded_by": None,
                    "_source": source_label,
                }
    return list(found.values())


def decision_backfill(
    sources: Annotated[
        list[str] | None,
        typer.Option(
            "--source",
            help=(
                "Glob (relative to repo root) to scan. Repeatable. "
                "Default: specs + CHANGELOG.md + CONSTITUTION.md + CLAUDE.md."
            ),
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="List entries without writing."),
    ] = False,
) -> None:
    """Backfill the decisions table from markdown sources.

    Scans the default four sources (specs + CHANGELOG.md + CONSTITUTION.md
    + CLAUDE.md) -- or the operator-supplied ``--source`` globs -- for
    ``D-<spec>-<NN>`` references, extracting the surrounding line as the
    decision title. UPSERT is idempotent: re-running is a no-op once
    rows already match.
    """
    root = find_project_root()
    db_path = state_db_path(root)

    globs = tuple(sources) if sources else _DEFAULT_BACKFILL_GLOBS
    files = _iter_source_files(root, globs)
    if not files:
        info("No source files matched the requested globs.")
        return

    rows = _scan_decisions(root, files)
    if not rows:
        info("No decision IDs (D-XXX-NN) found in the scanned sources.")
        return

    by_source: dict[str, int] = {}
    for row in rows:
        label = str(row.get("_source") or "other")
        by_source[label] = by_source.get(label, 0) + 1

    header(f"Backfill candidates ({len(rows)} total)")
    for row in sorted(rows, key=lambda r: r.get("decision_id") or ""):
        decision_id = row.get("decision_id") or "?"
        spec_id = row.get("spec_id") or "-"
        source_label = row.get("_source") or "?"
        title = (row.get("title") or "").strip()
        title_short = title[:60] + ("…" if len(title) > 60 else "")
        status_line(
            "ok",
            decision_id,
            f"{spec_id} · {source_label} · {title_short}",
        )

    by_source_pretty = ", ".join(f"{k}={v}" for k, v in sorted(by_source.items()))
    info(f"Sources: {by_source_pretty}")

    if dry_run:
        info("Dry run: no rows written.")
        return

    write_rows = [{k: v for k, v in row.items() if k != "_source"} for row in rows]
    attempted = upsert_decision_rows_raw(root, write_rows)

    emit_control_outcome(
        root,
        category="governance",
        control="decision-backfill",
        component="decision-store",
        outcome="success",
        source="cli",
        metadata={
            "count": attempted,
            "by_source": by_source,
            "db_path": str(db_path),
            "globs": list(globs),
        },
    )

    success(f"Backfilled {attempted} decision rows → state.db.")
