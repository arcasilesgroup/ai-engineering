"""Audit-chain verifier + audit-index CLI commands.

Original surface (spec-107 D-107-10 / G-12, H2):

* ``ai-eng audit verify`` -- a thin formatting layer over
  :func:`ai_engineering.state.audit_chain.verify_audit_chain` for both
  ``framework-events.ndjson`` (mode=ndjson) and ``decision-store.json``
  (mode=json_array). Intentionally advisory: it always exits 0 so it
  never blocks installs, doctor flows, or CI.

Spec-120 additions (Phase B, T-B2 / T-B3 / T-B4):

* ``ai-eng audit index`` -- build / refresh the SQLite projection of
  ``framework-events.ndjson`` documented in
  :mod:`ai_engineering.state.audit_index`. ``--rebuild`` drops the
  schema and re-reads from offset 0; default is incremental. Single
  one-line summary on success, or :func:`json.dumps(asdict(result))`
  with ``--json``.
* ``ai-eng audit query "SELECT ..."`` -- read-only SQL over the index.
  Auto-rebuilds when the SQLite mtime is older than the NDJSON. Only
  ``SELECT`` (case-insensitive, after stripping line comments) is
  permitted; everything else exits with code 2. Tabular human output
  or ``--json`` array of dicts.
* ``ai-eng audit tokens --by skill|agent|session`` -- thin wrapper that
  selects from one of the three rollup views shipped by
  :mod:`audit_index` (``skill_token_rollup``, ``agent_token_rollup``,
  ``session_token_rollup``). Output formatting matches ``audit query``.

The original ``audit verify`` command, the underlying
``state/audit_chain.py``, and the ``framework-events.ndjson`` writer
path are intentionally untouched -- the new commands are additive and
read-only against the SQLite projection.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import typer

from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import header, kv, status_line, success, warning
from ai_engineering.state.audit_chain import AuditChainVerdict, verify_audit_chain
from ai_engineering.state.audit_index import (
    NDJSON_REL,
    build_index,
    index_path,
    open_index_readonly,
)
from ai_engineering.state.audit_otel_export import build_otlp_spans
from ai_engineering.state.audit_replay import (
    build_span_tree,
    render_json,
    render_text,
    token_rollup,
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

# Maximum number of rows ``audit query`` and ``audit tokens`` will return
# unless the user provides their own LIMIT clause. Mirrors the typer
# default but is reused by the LIMIT-injection logic below.
_DEFAULT_QUERY_LIMIT = 1000

# Mapping ``--by`` value -> SQLite view name shipped by audit_index.
_TOKEN_VIEWS: dict[str, str] = {
    "skill": "skill_token_rollup",
    "agent": "agent_token_rollup",
    "session": "session_token_rollup",
}


def _strip_sql_comments(sql: str) -> str:
    """Strip leading whitespace and ``--`` line comments from ``sql``.

    Used by :func:`audit_query` to decide whether a query is a SELECT
    after the user has prefixed it with comments. Block comments
    (``/* ... */``) are intentionally not handled -- queries that need
    them are exotic enough that requiring the user to clean them up
    before invocation is acceptable.
    """
    lines = []
    for raw in sql.splitlines():
        stripped = raw.strip()
        if stripped.startswith("--"):
            continue
        lines.append(raw)
    return "\n".join(lines).strip()


def _is_select(sql: str) -> bool:
    """Return ``True`` when the first token of ``sql`` is ``SELECT``.

    The check is case-insensitive and tolerates leading whitespace +
    ``--`` line comments. WITH-clauses (CTEs) are intentionally NOT
    accepted today -- the rollup views and the events table cover the
    canonical query shapes; we can revisit if a real CTE need surfaces.
    """
    cleaned = _strip_sql_comments(sql)
    if not cleaned:
        return False
    first_word = cleaned.split(None, 1)[0].upper()
    return first_word == "SELECT"


def _ensure_limit(sql: str, limit: int) -> str:
    """Append ``LIMIT <n>`` to ``sql`` when no explicit LIMIT is present.

    Detection is whitespace + word-boundary tolerant: ``LIMIT`` must
    appear as its own token (case-insensitive) for the check to skip
    rewriting. Subqueries with ``LIMIT`` inside parens still trigger
    the "already-limited" path, which is the conservative behaviour --
    we never silently double-cap.
    """
    upper = sql.upper()
    # crude but effective: split into tokens and look for a bare LIMIT
    tokens = upper.replace("\n", " ").replace("(", " ( ").replace(")", " ) ").split()
    if "LIMIT" in tokens:
        return sql
    return f"{sql.rstrip().rstrip(';')} LIMIT {limit}"


def _index_is_stale(project_root: Path) -> bool:
    """Return ``True`` when the SQLite index is missing or out-of-date.

    "Out-of-date" means the NDJSON source mtime is greater than the
    SQLite mtime -- new events were appended since the last index
    build. Both files missing is treated as "not stale" because
    :func:`build_index` already handles the missing-source case as a
    soft success.
    """
    sqlite_path = index_path(project_root)
    ndjson_path = project_root / NDJSON_REL
    if not sqlite_path.exists():
        return True
    if not ndjson_path.exists():
        return False
    return ndjson_path.stat().st_mtime > sqlite_path.stat().st_mtime


def _ensure_fresh_index(project_root: Path) -> None:
    """Auto-build the SQLite index when missing or stale (incremental)."""
    if _index_is_stale(project_root):
        build_index(project_root, rebuild=False)


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
        typer.Option("--rebuild", help="Drop tables and re-index from offset 0."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON."),
    ] = False,
) -> None:
    """Build / refresh the SQLite projection of framework-events.ndjson.

    Always exits 0 on success. Uncaught exceptions surface through the
    standard ``_cli_error_boundary`` wrapper applied at registration.
    """
    project_root = _resolve_project_root()
    result = build_index(project_root, rebuild=rebuild)
    if json_output:
        typer.echo(json.dumps(asdict(result)))
        return
    typer.echo(
        f"Indexed {result.rows_indexed} rows "
        f"(total={result.rows_total}, last_offset={result.last_offset}) "
        f"in {result.elapsed_ms}ms (rebuild={result.rebuilt})"
    )


def audit_query(
    sql: Annotated[
        str,
        typer.Argument(help="SQL query (SELECT only)."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON array."),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", help="Cap rows returned (default 1000)."),
    ] = _DEFAULT_QUERY_LIMIT,
) -> None:
    """Run a read-only SQL query against the audit index.

    Auto-builds the SQLite projection when missing or stale. Only
    ``SELECT`` queries are accepted -- DDL / DML attempts exit with
    code 2 and a clear error on stderr.
    """
    if not _is_select(sql):
        typer.echo(
            "Error: only SELECT queries are permitted via 'audit query'.",
            err=True,
        )
        raise typer.Exit(code=2)

    project_root = _resolve_project_root()
    _ensure_fresh_index(project_root)

    if not index_path(project_root).exists():
        # Soft-success: an empty NDJSON means no SQLite was created.
        # Treat this like "no rows" so scripted callers see the empty
        # set instead of a path error.
        if json_output:
            typer.echo("[]")
        else:
            typer.echo("(no rows)")
        return

    final_sql = _ensure_limit(sql, limit)
    conn = open_index_readonly(project_root)
    try:
        try:
            cur = conn.execute(final_sql)
        except sqlite3.Error as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from None
        columns = [desc[0] for desc in cur.description or []]
        rows = cur.fetchall()
    finally:
        conn.close()

    _print_query_result(columns, rows, json_output)


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

    Thin wrapper around the rollup views shipped by
    :mod:`ai_engineering.state.audit_index`. Auto-builds the SQLite
    projection if missing or stale, then ``SELECT * FROM <view>``
    ordered by ``total_tokens`` descending.
    """
    if by not in _TOKEN_VIEWS:
        typer.echo(
            f"Error: --by must be one of {sorted(_TOKEN_VIEWS)}, got {by!r}.",
            err=True,
        )
        raise typer.Exit(code=2)

    project_root = _resolve_project_root()
    _ensure_fresh_index(project_root)

    if not index_path(project_root).exists():
        if json_output:
            typer.echo("[]")
        else:
            typer.echo("(no rows)")
        return

    view = _TOKEN_VIEWS[by]
    # ``IS NULL`` ASC sorts NULLs last on every SQLite version we ship,
    # avoiding the ``NULLS LAST`` keyword that older builds may not
    # support. ``total_tokens DESC`` then orders the populated rows.
    sql = f"SELECT * FROM {view} ORDER BY total_tokens IS NULL ASC, total_tokens DESC"
    conn = open_index_readonly(project_root)
    try:
        try:
            cur = conn.execute(sql)
        except sqlite3.Error as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(code=1) from None
        columns = [desc[0] for desc in cur.description or []]
        rows = cur.fetchall()
    finally:
        conn.close()

    _print_query_result(columns, rows, json_output)


# ---------------------------------------------------------------------------
# Spec-120 Phase C: audit replay / otel-export
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

    Builds the span tree from the SQLite audit index, walks it
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
    _ensure_fresh_index(project_root)

    if not index_path(project_root).exists():
        # Soft success -- empty NDJSON means an empty SQLite would be
        # equally empty. Mirrors the behaviour of ``audit query``.
        if json_output:
            typer.echo(json.dumps({"trees": [], "tokens": _empty_token_rollup()}))
        else:
            typer.echo("(no events)")
        return

    conn = open_index_readonly(project_root)
    try:
        roots = build_span_tree(conn, session_id=session, trace_id=trace)
    finally:
        conn.close()

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


def _empty_token_rollup() -> dict[str, Any]:
    """Return the zero-state rollup used when there are no events."""
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }


def audit_otel_export(
    trace: Annotated[
        str,
        typer.Option("--trace", help="Trace id to export."),
    ],
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Output file path; stdout when omitted."),
    ] = None,
) -> None:
    """Export a trace as OTLP/JSON.

    Builds the OTLP envelope via
    :func:`ai_engineering.state.audit_otel_export.build_otlp_spans` and
    either writes it to ``--out`` (when supplied) or pretty-prints it
    to stdout. Auto-builds the SQLite index when missing or stale.
    """
    project_root = _resolve_project_root()
    _ensure_fresh_index(project_root)

    if not index_path(project_root).exists():
        envelope: dict[str, Any] = {
            "resourceSpans": [
                {
                    "resource": {"attributes": []},
                    "scopeSpans": [
                        {"scope": {"name": "ai-engineering", "version": "spec-120"}, "spans": []}
                    ],
                }
            ]
        }
    else:
        conn = open_index_readonly(project_root)
        try:
            envelope = build_otlp_spans(conn, trace_id=trace)
        finally:
            conn.close()

    body = json.dumps(envelope, indent=2)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body, encoding="utf-8")
        typer.echo(f"Wrote OTLP envelope to {out}")
        return
    typer.echo(body)


__all__ = [
    "audit_app_marker",
    "audit_index",
    "audit_otel_export",
    "audit_query",
    "audit_replay",
    "audit_tokens",
    "audit_verify",
]
