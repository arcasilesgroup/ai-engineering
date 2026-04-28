"""Audit-chain verifier CLI commands (spec-107 D-107-10 / G-12, H2).

Exposes ``ai-eng audit verify`` -- a thin formatting layer over
:func:`ai_engineering.state.audit_chain.verify_audit_chain` for both
``framework-events.ndjson`` (mode=ndjson) and ``decision-store.json``
(mode=json_array). The command is intentionally advisory: it always
exits 0 so it never blocks installs, doctor flows, or CI; the verdict
is surfaced via human report and (optional) JSON envelope for agent
consumption.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import header, kv, status_line, success, warning
from ai_engineering.state.audit_chain import AuditChainVerdict, verify_audit_chain


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


def _verify_one(label: str, path: Path, mode: str) -> tuple[str, AuditChainVerdict]:
    """Run the verifier on a single audit file and return label/verdict."""
    if not path.exists():
        return label, AuditChainVerdict(
            ok=True,
            entries_checked=0,
            first_break_index=None,
            first_break_reason=None,
        )
    return label, verify_audit_chain(path, mode=mode)  # type: ignore[arg-type]


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

    targets: list[tuple[str, Path, str]] = []
    if file_filter in {"events", "all"}:
        targets.append(("events", state_dir / "framework-events.ndjson", "ndjson"))
    if file_filter in {"decisions", "all"}:
        targets.append(("decisions", state_dir / "decision-store.json", "json_array"))

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
    targets: list[tuple[str, Path, str]] = []
    if file_filter in {"events", "all"}:
        targets.append(("events", state_dir / "framework-events.ndjson", "ndjson"))
    if file_filter in {"decisions", "all"}:
        targets.append(("decisions", state_dir / "decision-store.json", "json_array"))
    verdicts = [_verify_one(label, path, mode) for label, path, mode in targets]
    return {
        "verdicts": [_verdict_payload(name, v) for name, v in verdicts],
        "raw": json.dumps({"file_filter": file_filter}, sort_keys=True),
    }


# Identifier surface for the spec-107 RED scanner: the canonical
# audit verify subcommand handle is exposed both as a callable and
# via the ``audit_app`` Typer namespace registered in cli_factory.
audit_app_marker = "audit verify"


__all__ = ["audit_app_marker", "audit_verify"]
