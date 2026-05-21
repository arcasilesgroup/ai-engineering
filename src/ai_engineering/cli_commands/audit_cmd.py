"""Audit-chain verifier + audit-index CLI commands.

Original surface (spec-107 D-107-10 / G-12, H2):

* ``ai-eng audit verify`` -- a thin formatting layer over
  :func:`ai_engineering.state.audit_chain.verify_audit_chain` for both
  ``framework-events.ndjson`` (mode=ndjson) and ``decision-store.json``
  (mode=json_array). Intentionally advisory: it always exits 0 so it
  never blocks installs, doctor flows, or CI.

spec-148 (files-only): the SQLite projection is retired. The audit
surface reads ``framework-events.ndjson`` directly:

* ``ai-eng audit tokens --by skill|agent|session`` -- token rollups
  computed over the NDJSON (see :mod:`ai_engineering.state.audit_rollup`).
* ``ai-eng audit replay`` -- span tree built directly from the NDJSON
  (see :mod:`ai_engineering.state.audit_replay`).
* ``ai-eng audit verify`` -- hash-chain verifier for
  ``framework-events.ndjson`` + ``decision-store.json`` (unchanged).
* ``ai-eng audit index`` / ``ai-eng audit query`` -- removed (fail-loud
  stubs): there is no SQLite projection to build or run ``SELECT`` over.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import typer

from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import header, kv, status_line, success, warning
from ai_engineering.state.audit_chain import AuditChainVerdict, verify_audit_chain
from ai_engineering.state.audit_index import (
    NDJSON_REL,
)
from ai_engineering.state.audit_replay import (
    build_span_tree,
    render_json,
    render_text,
    token_rollup,
)
from ai_engineering.state.audit_rollup import (
    agent_token_rollup,
    session_token_rollup,
    skill_token_rollup,
)

_AuditMode = Literal["ndjson", "json_array"]


def _resolve_project_root() -> Path:
    """Anchor the audit verifier at the current working directory.

    Mirrors :func:`risk_cmd._resolve_project_root` so tests that
    ``monkeypatch.chdir(tmp_path)`` see writes/reads land under
    ``tmp_path/.ai-engineering/state``, matching spec-104 conventions.
    """
    return Path.cwd()


def _verdict_payload(name: str, verdict: AuditChainVerdict) -> dict:
    """Render a verdict as a JSON-friendly dict for the JSON envelope."""
    return {
        "file": name,
        "ok": verdict.ok,
        "entries_checked": verdict.entries_checked,
        "first_break_index": verdict.first_break_index,
        "first_break_reason": verdict.first_break_reason,
    }


def _verify_one(label: str, path: Path, mode: _AuditMode) -> tuple[str, AuditChainVerdict]:
    """Run the verifier on a single audit file and return label/verdict."""
    if not path.exists():
        return label, AuditChainVerdict(
            ok=True,
            entries_checked=0,
            first_break_index=None,
            first_break_reason=None,
        )
    return label, verify_audit_chain(path, mode=mode)


def audit_verify(
    file_filter: Annotated[
        str,
        typer.Option(
            "--file",
            help="Which audit file to verify: events, decisions, or all.",
        ),
    ] = "all",
) -> None:
    """Verify the hash-chained audit trail (events and/or decisions).

    Always exits 0 -- this is a pure advisory surface per D-107-10.
    Operators inspect the output to investigate any reported chain
    breaks; CI / doctor / install flows never get blocked.
    """
    if file_filter not in {"events", "decisions", "all"}:
        # Even input validation stays advisory: surface the typo, default
        # to ``all`` so the user still sees a verdict.
        warning(f"Unknown --file value {file_filter!r}; defaulting to 'all'.")
        file_filter = "all"

    root = _resolve_project_root()
    state_dir = root / ".ai-engineering" / "state"

    targets: list[tuple[str, Path, _AuditMode]] = []
    if file_filter in {"events", "all"}:
        targets.append(
            ("events", state_dir / "framework-events.ndjson", cast(_AuditMode, "ndjson"))
        )
    if file_filter in {"decisions", "all"}:
        targets.append(
            ("decisions", state_dir / "decision-store.json", cast(_AuditMode, "json_array"))
        )

    verdicts = [_verify_one(label, path, mode) for label, path, mode in targets]

    if is_json_mode():
        from ai_engineering.cli_envelope import emit_success

        emit_success(
            "audit-verify",
            {"verdicts": [_verdict_payload(name, v) for name, v in verdicts]},
        )
        return

    header("Audit chain verification")
    for name, verdict in verdicts:
        if verdict.ok:
            status_line(
                "ok",
                name,
                f"chain intact ({verdict.entries_checked} entries verified)",
            )
        else:
            status_line(
                "warn",
                name,
                f"chain break at index {verdict.first_break_index}",
            )
            kv("Reason", verdict.first_break_reason or "-")

    if all(v.ok for _, v in verdicts):
        success("All requested audit chains are intact.")
    else:
        warning("One or more audit chains reported a break -- advisory only, exit 0.")


def _audit_verify_machine_readable(file_filter: str = "all") -> dict:
    """Return the verdict payload as a dict (used by tests / agent surface).

    Helper kept module-level so tests can import without invoking Typer.
    Identifier ``audit verify`` and the docstring marker are scanned by
    spec-107 RED tests to confirm the CLI registration -- searching for
    ``"audit verify"`` and ``audit_app`` strings inside the cli tree.
    """
    root = _resolve_project_root()
    state_dir = root / ".ai-engineering" / "state"
    targets: list[tuple[str, Path, _AuditMode]] = []
    if file_filter in {"events", "all"}:
        targets.append(
            ("events", state_dir / "framework-events.ndjson", cast(_AuditMode, "ndjson"))
        )
    if file_filter in {"decisions", "all"}:
        targets.append(
            ("decisions", state_dir / "decision-store.json", cast(_AuditMode, "json_array"))
        )
    verdicts = [_verify_one(label, path, mode) for label, path, mode in targets]
    return {
        "verdicts": [_verdict_payload(name, v) for name, v in verdicts],
        "raw": json.dumps({"file_filter": file_filter}, sort_keys=True),
    }


# Identifier surface for the spec-107 RED scanner: the canonical
# audit verify subcommand handle is exposed both as a callable and
# via the ``audit_app`` Typer namespace registered in cli_factory.
audit_app_marker = "audit verify"


# ---------------------------------------------------------------------------
# Spec-120 Phase B: audit index / query / tokens
# ---------------------------------------------------------------------------


def _format_table(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    """Render rows as a fixed-width text table with a dashed header.

    Empty result-sets are rendered as ``(no rows)`` by the caller --
    this helper assumes at least one row.
    """
    str_rows = [[("" if cell is None else str(cell)) for cell in row] for row in rows]
    widths = [len(c) for c in columns]
    for row in str_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))
    header_line = "  ".join(col.ljust(widths[idx]) for idx, col in enumerate(columns))
    sep_line = "  ".join("-" * widths[idx] for idx in range(len(columns)))
    body_lines = [
        "  ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row)) for row in str_rows
    ]
    return "\n".join([header_line, sep_line, *body_lines])


def _rows_as_dicts(columns: list[str], rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    """Convert ``cursor.fetchall()`` rows into JSON-friendly dicts."""
    return [dict(zip(columns, row, strict=True)) for row in rows]


def _print_query_result(columns: list[str], rows: list[tuple[Any, ...]], json_output: bool) -> None:
    """Render a query result in either JSON or tabular form."""
    if json_output:
        typer.echo(json.dumps(_rows_as_dicts(columns, rows), default=str))
        return
    if not rows:
        typer.echo("(no rows)")
        return
    typer.echo(_format_table(columns, rows))


def audit_index(
    rebuild: Annotated[
        bool,
        typer.Option("--rebuild", help="(removed in spec-148)"),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="(removed in spec-148)"),
    ] = False,
) -> None:
    """Removed in spec-148 (files-only persistence).

    There is no SQLite projection to build — ``framework-events.ndjson``
    is the single source of truth, read directly by ``audit tokens`` /
    ``audit replay``. The verb stays as a fail-loud stub so scripted
    callers get a clear message instead of silent success.
    """
    typer.echo(
        "Error: 'audit index' was removed in spec-148 — there is no SQLite "
        "projection to build; framework-events.ndjson is read directly by "
        "'audit tokens' / 'audit replay'.",
        err=True,
    )
    raise typer.Exit(code=2)


def audit_query(
    sql: Annotated[
        str,
        typer.Argument(help="(removed in spec-148) formerly arbitrary SELECT."),
    ] = "",
) -> None:
    """Removed in spec-148 (files-only persistence).

    The SQLite projection of ``framework-events.ndjson`` no longer
    exists, so arbitrary ``SELECT`` over the audit log is gone. Use
    ``audit tokens`` (skill/agent/session rollups) or ``audit replay``
    (span tree) — both computed directly over the NDJSON — or parse
    ``framework-events.ndjson`` yourself.
    """
    typer.echo(
        "Error: 'audit query' was removed in spec-148 — the SQLite projection "
        "no longer exists. Use 'audit tokens' / 'audit replay' (computed over "
        "framework-events.ndjson), or parse the NDJSON directly.",
        err=True,
    )
    raise typer.Exit(code=2)


def audit_tokens(
    by: Annotated[
        str,
        typer.Option("--by", help="skill | agent | session"),
    ] = "skill",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON array."),
    ] = False,
) -> None:
    """Aggregate token usage by skill / agent / session.

    spec-148: computes the rollups directly from
    ``framework-events.ndjson`` via
    :mod:`ai_engineering.state.audit_rollup` (no SQLite), ordered by
    ``total_tokens`` descending.
    """
    by_map = {
        "skill": skill_token_rollup,
        "agent": agent_token_rollup,
        "session": session_token_rollup,
    }
    if by not in by_map:
        typer.echo(
            f"Error: --by must be one of {sorted(by_map)}, got {by!r}.",
            err=True,
        )
        raise typer.Exit(code=2)

    project_root = _resolve_project_root()
    ndjson_path = project_root / NDJSON_REL
    rows_dicts = by_map[by](ndjson_path)
    # Order by total_tokens descending; NULL/0 sink to the bottom.
    rows_dicts.sort(key=lambda r: r.get("total_tokens") or 0, reverse=True)

    if not rows_dicts:
        typer.echo("[]" if json_output else "(no rows)")
        return

    columns = list(rows_dicts[0].keys())
    rows = [tuple(row.get(col) for col in columns) for row in rows_dicts]
    _print_query_result(columns, rows, json_output)


# ---------------------------------------------------------------------------
# Spec-120 Phase C: audit replay (spec-148: otel-export removed)
# ---------------------------------------------------------------------------


def _validate_session_xor_trace(session: str | None, trace: str | None) -> None:
    """Reject the empty / both case for ``--session`` / ``--trace`` flags.

    Mirrors the validation in :func:`audit_replay.build_span_tree` but
    raises a Typer-friendly ``Exit`` so the user gets a clean error
    message instead of an uncaught ``ValueError`` traceback.
    """
    if (session is None) == (trace is None):
        typer.echo(
            "Error: exactly one of --session / --trace is required.",
            err=True,
        )
        raise typer.Exit(code=2)


def audit_replay(
    session: Annotated[
        str | None,
        typer.Option("--session", help="Session id to walk."),
    ] = None,
    trace: Annotated[
        str | None,
        typer.Option("--trace", help="Trace id to walk."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit a JSON tree dump instead of text."),
    ] = False,
) -> None:
    """Walk a session or trace as a span tree.

    Builds the span tree directly from framework-events.ndjson, walks it
    depth-first, and prints either an indented text rendering (default)
    or a JSON dump under ``--json``. Exactly one of ``--session`` /
    ``--trace`` must be supplied.

    The text rendering ends with a one-line token rollup footer summing
    every span in the forest. The JSON shape mirrors that footer with
    the trees alongside it::

        {"trees": [...], "tokens": {...}}
    """
    _validate_session_xor_trace(session, trace)

    project_root = _resolve_project_root()
    ndjson_path = project_root / NDJSON_REL
    roots = build_span_tree(ndjson_path, session_id=session, trace_id=trace)

    rollup = token_rollup(roots)

    if json_output:
        envelope = render_json(roots)
        envelope["tokens"] = rollup
        typer.echo(json.dumps(envelope, default=str))
        return

    if not roots:
        typer.echo("(no events)")
        return

    # ``color=False`` keeps rendering hermetic and test-friendly. A future
    # enhancement can flip this on when stdout is a TTY without changing
    # the public surface of ``render_text``.
    typer.echo(render_text(roots, color=False))
    typer.echo(
        f"--- Tokens: input={rollup['input_tokens']}, "
        f"output={rollup['output_tokens']}, "
        f"total={rollup['total_tokens']}, "
        f"cost=${rollup['cost_usd']:.4f} ---"
    )


# ---------------------------------------------------------------------------
# spec-123 T-3.9: 6 audit ops verbs
#   retention apply / rotate / compress / verify-chain / health / vacuum
# ---------------------------------------------------------------------------


def audit_retention_apply(
    days: Annotated[
        int,
        typer.Option("--days", help="HOT cutoff window in days (default 90)."),
    ] = 90,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope."),
    ] = False,
) -> None:
    """Apply the HOT retention cutoff to the events projection (D-123-26).

    Deletes ``events`` rows older than ``now - days`` from ``state.db``.
    NDJSON archives retain the original lines so the prune is loss-free.
    Emits a ``retention_applied`` framework event when rows are deleted.
    """
    from ai_engineering.state import retention, state_db

    project_root = _resolve_project_root()
    conn = state_db.connect(project_root)
    try:
        verdict = retention.apply_hot_cutoff(conn, days=days)
    finally:
        conn.close()

    if json_output:
        typer.echo(json.dumps(verdict))
        return
    typer.echo(
        f"Retention cutoff applied: deleted={verdict['deleted']} "
        f"cutoff_days={verdict['cutoff_days']} "
        f"status={verdict['status']}"
    )


def audit_health(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope."),
    ] = False,
) -> None:
    """Report state.db health: ledger, table counts, NDJSON freshness.

    Returns exit code 0 when state.db carries the migration ledger and
    every required table is present. Used by ``ai-eng doctor`` and CI
    smoke tests.
    """
    from ai_engineering.state import state_db

    project_root = _resolve_project_root()
    payload: dict[str, Any] = {
        "state_db": str(state_db.STATE_DB_REL),
        "tables": {},
        "migrations": [],
        "ok": True,
    }
    # ``hooks_integrity`` was dropped in migration 0008 per spec-138 D-138-01;
    # the manifest at ``state/hooks-manifest.json`` (sha256 truth) plus the
    # NDJSON ``integrity_violation`` event stream cover the surface.
    required_tables = {
        "events",
        "decisions",
        "risk_acceptances",
        "gate_findings",
        "ownership_map",
        "install_steps",
        "_migrations",
    }
    try:
        conn = state_db.connect(project_root)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            payload["migrations"] = [
                row[0] for row in conn.execute("SELECT id FROM _migrations ORDER BY id").fetchall()
            ]
            for table in required_tables:
                if table in tables:
                    count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                    payload["tables"][table] = int(count)
                else:
                    payload["tables"][table] = None
                    payload["ok"] = False
        finally:
            conn.close()
    except Exception as exc:  # pragma: no cover -- defensive
        payload["ok"] = False
        payload["error"] = str(exc)

    if json_output:
        typer.echo(json.dumps(payload))
    else:
        typer.echo(f"audit health: ok={payload['ok']}")
        typer.echo(f"  migrations: {payload['migrations']}")
        for table, count in sorted(payload["tables"].items()):
            typer.echo(f"  {table}: {count}")

    if not payload["ok"]:
        raise typer.Exit(code=1)


def audit_vacuum(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON envelope."),
    ] = False,
) -> None:
    """Reclaim free pages in ``state.db`` via ``PRAGMA incremental_vacuum``.

    Runs ``PRAGMA incremental_vacuum`` (which honours the
    ``auto_vacuum=INCREMENTAL`` setting applied at DB creation per
    D-122-16) and reports pages reclaimed. Safe to run on a hot DB; the
    operation is short and concurrent reads are unaffected.
    """
    from ai_engineering.state import state_db

    project_root = _resolve_project_root()
    conn = state_db.connect(project_root)
    try:
        before = int(conn.execute("PRAGMA freelist_count").fetchone()[0] or 0)
        conn.execute("PRAGMA incremental_vacuum")
        conn.commit()
        after = int(conn.execute("PRAGMA freelist_count").fetchone()[0] or 0)
    finally:
        conn.close()

    payload = {
        "freelist_pages_before": before,
        "freelist_pages_after": after,
        "pages_reclaimed": max(0, before - after),
    }
    if json_output:
        typer.echo(json.dumps(payload))
        return
    typer.echo(
        f"audit vacuum: reclaimed {payload['pages_reclaimed']} page(s) "
        f"(freelist {before} -> {after})"
    )


__all__ = [
    "audit_app_marker",
    "audit_health",
    "audit_index",
    "audit_query",
    "audit_replay",
    "audit_retention_apply",
    "audit_tokens",
    "audit_vacuum",
    "audit_verify",
]
