"""Audit-chain verifier + audit-index CLI commands.

Original surface (spec-107 D-107-10 / G-12, H2):

* ``ai-eng audit verify`` -- a thin formatting layer over
  :func:`ai_engineering.state.audit_chain.verify_audit_chain` for both
  ``framework-events.ndjson`` (mode=ndjson) and ``decision-store.json``
  (mode=json_array). Intentionally advisory: it always exits 0 so it
  never blocks installs, doctor flows, or CI. It stays advisory while a
  missing ``prev_event_hash`` re-anchors the chain -- see
  :func:`audit_verify`.

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
import shutil
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import typer

from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import header, kv, status_line, success, warning
from ai_engineering.state.audit_chain import (
    AuditChainVerdict,
    RelinkResult,
    relink_audit_chain,
    verify_audit_chain,
)
from ai_engineering.state.audit_replay import (
    build_span_tree,
    render_json,
    render_text,
    token_rollup,
)
from ai_engineering.state.audit_rollup import (
    NDJSON_REL,
    agent_token_rollup,
    session_token_rollup,
    skill_token_rollup,
)
from ai_engineering.state.observability import emit_framework_operation

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


def _audit_targets(file_filter: str, root: Path) -> list[tuple[str, Path, _AuditMode]]:
    """Resolve ``--file`` to the (label, path, mode) ledgers it selects.

    One table for every audit verb so ``verify`` and ``relink`` can never
    disagree about which files the audit surface owns.
    """
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
    return targets


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

    spec-201 sub-001 added a ``--strict`` flag that made this fail closed;
    it was removed rather than shipped. The verifier treats a *missing*
    ``prev_event_hash`` as a legitimate re-anchor, so deleting that key
    from the entry after a tampered one verifies the whole ledger clean --
    a gate an editor can defeat by removing a field asserts integrity it
    cannot check. It can return once every entry is pointer-stamped and a
    missing pointer is itself a break (follow-up spec).
    """
    if file_filter not in {"events", "decisions", "all"}:
        # Even input validation stays advisory: surface the typo, default
        # to ``all`` so the user still sees a verdict.
        warning(f"Unknown --file value {file_filter!r}; defaulting to 'all'.")
        file_filter = "all"

    root = _resolve_project_root()
    targets = _audit_targets(file_filter, root)

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
        warning(
            "One or more audit chains reported a break -- advisory only, exit 0. "
            "Review with `ai-eng audit relink --file <events|decisions>`, "
            "then apply with --write."
        )


def _audit_verify_machine_readable(file_filter: str = "all") -> dict:
    """Return the verdict payload as a dict (used by tests / agent surface).

    Helper kept module-level so tests can import without invoking Typer.
    Identifier ``audit verify`` and the docstring marker are scanned by
    spec-107 RED tests to confirm the CLI registration -- searching for
    ``"audit verify"`` and ``audit_app`` strings inside the cli tree.
    """
    root = _resolve_project_root()
    targets = _audit_targets(file_filter, root)
    verdicts = [_verify_one(label, path, mode) for label, path, mode in targets]
    return {
        "verdicts": [_verdict_payload(name, v) for name, v in verdicts],
        "raw": json.dumps({"file_filter": file_filter}, sort_keys=True),
    }


# Identifier surface for the spec-107 RED scanner: the canonical
# audit verify subcommand handle is exposed both as a callable and
# via the ``audit_app`` Typer namespace registered in cli_factory.
audit_app_marker = "audit verify"


def _relink_payload(name: str, result: RelinkResult) -> dict:
    """Render a relink result as a JSON-friendly dict for the envelope."""
    return {
        "file": name,
        "ok": result.ok,
        "entries_total": result.entries_total,
        "relinked": result.relinked,
        "written": result.written,
        "reason": result.reason,
    }


def _backup_ledger(path: Path) -> Path:
    """Copy ``path`` to ``<name>.bak`` before a repair rewrites it.

    ``framework-events.ndjson`` is gitignored, so a relink of it is otherwise
    unrecoverable — there is no second copy anywhere (spec-201 H9). Raises
    ``OSError`` on failure; the caller refuses the repair rather than mutating
    tamper-evidence with no way back.
    """
    backup = path.with_name(path.name + ".bak")
    shutil.copy2(path, backup)
    return backup


def _emit_relink_event(
    root: Path,
    *,
    file_filter: str,
    before: list[tuple[str, AuditChainVerdict]],
    results: list[tuple[str, RelinkResult]],
    backups: dict[str, str],
) -> None:
    """Record the repair in the audit chain itself.

    The only write verb on the integrity plane used to leave no trace at all:
    doctor FAILed, the operator ran the printed remedy, the chain verified
    clean, and nothing anywhere said a repair had happened (spec-201 H9).
    Emitted AFTER the rewrite so the event chains onto the repaired ledger.
    """
    verdicts = dict(before)
    emit_framework_operation(
        root,
        operation="audit_relink",
        component="cli.audit-relink",
        source="cli",
        metadata={
            "file_filter": file_filter,
            "files": [
                {
                    "file": name,
                    "entries_checked_before": (
                        verdicts[name].entries_checked if name in verdicts else None
                    ),
                    "chain_ok_before": verdicts[name].ok if name in verdicts else None,
                    "first_break_index_before": (
                        verdicts[name].first_break_index if name in verdicts else None
                    ),
                    "entries_after": result.entries_total,
                    "relinked": result.relinked,
                    "written": result.written,
                    "backup": backups.get(name),
                }
                for name, result in results
            ],
        },
    )


def audit_relink(
    file_filter: Annotated[
        str,
        typer.Option(
            "--file",
            help="Which audit file to repair: events, decisions, or all.",
        ),
    ] = "all",
    write: Annotated[
        bool,
        typer.Option(
            "--write",
            help="Apply the repair. Without it the verb only reports (the default).",
        ),
    ] = False,
) -> None:
    """Repair a broken hash chain by re-stamping ``prev_event_hash`` pointers.

    The repair counterpart to ``audit verify`` (spec-201 D-201-09). Only
    chain-pointer fields move: entry payloads are never touched, an
    unparseable ledger is refused rather than rewritten, and the rewrite
    is atomic under the same lock every event writer takes.

    This is the only write verb on the integrity plane, so it is
    report-only until ``--write`` says otherwise (spec-201 H9), it copies
    each ledger to ``<name>.bak`` before touching it — ``framework-events.ndjson``
    is gitignored, so a repair is otherwise unrecoverable — and it records the
    repair as an ``audit_relink`` ``framework_operation`` carrying the
    before/after entry counts. An unknown ``--file`` value is a hard error
    rather than the advisory default ``audit verify`` uses.
    """
    if file_filter not in {"events", "decisions", "all"}:
        typer.echo(
            f"Error: --file must be one of ['all', 'decisions', 'events'], got {file_filter!r}.",
            err=True,
        )
        raise typer.Exit(code=2)

    dry_run = not write
    root = _resolve_project_root()
    targets = _audit_targets(file_filter, root)

    # Record the pre-repair state before anything moves: once the chain is
    # re-stamped the break it repaired is unreconstructable.
    before = [_verify_one(label, path, mode) for label, path, mode in targets]

    backups: dict[str, str] = {}
    if not dry_run:
        for label, path, _mode in targets:
            if not path.exists():
                continue
            try:
                backups[label] = _backup_ledger(path).name
            except OSError as exc:
                typer.echo(
                    f"Error: cannot back up {path} before repairing it ({exc}). "
                    "Refusing to rewrite tamper-evidence with no way back.",
                    err=True,
                )
                raise typer.Exit(code=1) from exc

    results = [
        (
            label,
            relink_audit_chain(path, mode=mode, project_root=root, dry_run=dry_run),
        )
        for label, path, mode in targets
    ]

    event_recorded = True
    if not dry_run and any(r.written for _, r in results):
        try:
            _emit_relink_event(
                root,
                file_filter=file_filter,
                before=before,
                results=results,
                backups=backups,
            )
        except Exception:
            # The rewrite already happened; an unrecorded repair on
            # tamper-evidence must stay visible, so surface it below rather
            # than crash with a traceback the operator can ignore.
            event_recorded = False

    if is_json_mode():
        from ai_engineering.cli_envelope import emit_success

        emit_success(
            "audit-relink",
            {
                "dry_run": dry_run,
                "backups": backups,
                "event_recorded": event_recorded,
                "relinks": [_relink_payload(name, r) for name, r in results],
            },
        )
    else:
        header("Audit chain relink" + (" (report only)" if dry_run else ""))
        for name, result in results:
            if not result.ok:
                status_line("fail", name, "refused: ledger is unreadable")
                kv("Reason", result.reason or "-")
            elif result.relinked == 0:
                status_line(
                    "ok",
                    name,
                    f"chain already intact ({result.entries_total} entries)",
                )
            else:
                status_line(
                    "warn" if dry_run else "ok",
                    name,
                    f"{result.relinked} of {result.entries_total} entries "
                    f"{'need relinking' if dry_run else 'relinked'}",
                )
        for name, backup in sorted(backups.items()):
            kv(f"Backup ({name})", backup)

        if all(r.ok for _, r in results):
            if dry_run:
                warning("Report only: nothing was written. Re-run with --write to repair.")
            else:
                success("Audit chains relinked.")

    if not event_recorded:
        warning(
            "The repair was applied but could NOT be recorded as an audit_relink event. "
            "Note it manually: an unrecorded repair on tamper-evidence is invisible."
        )

    if not all(r.ok for _, r in results) or not event_recorded:
        raise typer.Exit(code=1)


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


__all__ = [
    "audit_app_marker",
    "audit_relink",
    "audit_replay",
    "audit_tokens",
    "audit_verify",
]
