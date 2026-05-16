"""Risk acceptance lifecycle CLI commands (spec-105 D-105-05).

This module exposes the ``ai-eng risk *`` namespace — seven subcommands
that wrap ``decision_logic`` lifecycle helpers (``create_risk_acceptance``,
``renew_decision``, ``mark_remediated``, ``revoke_decision``) and provide
a thin formatting/validation layer over ``DecisionStore``. Cero
duplicación funcional: el módulo solo añade input validation, output
formatting y telemetry emission.

Surface (positional + flags):

* ``risk accept --finding-id ID --severity ...`` -- create one DEC entry
  for a single finding.
* ``risk accept-all <findings.json> --justification ... --spec ...`` --
  create N DEC entries sharing one ``batch_id`` (D-105-06).
* ``risk renew <DEC-ID> --justification ... --spec ...`` -- extend a
  prior decision (max 2 renewals per ``_MAX_RENEWALS``).
* ``risk resolve <DEC-ID> --note ...`` -- mark REMEDIATED.
* ``risk revoke <DEC-ID> --reason ...`` -- mark REVOKED.
* ``risk list [--status ...] [--severity ...] [--expires-within N]
  [--format table|json|markdown]`` -- query the active risk surface.
* ``risk show <DEC-ID> [--format human|json]`` -- single decision detail.

OQ-1: ``accept-all`` skips findings whose ``rule_id`` is NULL/empty/
whitespace-only, emits ``category=risk-acceptance,
control=invalid-rule-id-skipped`` per skip, and returns exit 0 provided
the rest of the document parses. The malformed entry is *not* counted
toward the bulk batch.
"""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from ai_engineering.cli_ui import error, header, info, kv, status_line, success, warning
from ai_engineering.state.decision_logic import (
    create_risk_acceptance,
    mark_remediated,
    renew_decision,
    revoke_decision,
)
from ai_engineering.state.observability import emit_control_outcome
from ai_engineering.state.service import StateService

# --- Constants --------------------------------------------------------------

# Permissive actor-format regex. Accepts emails (RFC-5322 subset),
# usernames (alphanumerics + ``-_.``), and ``user@host``-style strings.
# Rejects whitespace, parentheses, sentence-style descriptions.
_VALID_ACTOR_RE = re.compile(r"^[A-Za-z0-9_.+\-]+(@[A-Za-z0-9.\-]+)?$")

# Max severity ordering used by ``--max-severity`` filtering in accept-all.
_SEVERITY_ORDER: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}


# --- Helpers ----------------------------------------------------------------


def _resolve_project_root() -> Path:
    """Return the project root anchored at the current working directory.

    Mirrors :func:`policy.orchestrator._resolve_root` rather than the
    walk-up :func:`paths.find_project_root` to match the spec-104
    convention: state writes land under ``cwd/.ai-engineering/state/``.
    Tests that ``monkeypatch.chdir(tmp_path)`` therefore see writes land
    in their tmp_path, independent of stale ancestor ``.ai-engineering``
    directories on macOS ``/private/var/folders/...``.
    """
    return Path.cwd()


def _git_user_email() -> str:
    """Return ``git config user.email`` or ``"unknown@local"`` on failure.

    Uses a fixed argv via PATH lookup (``git`` resolved by the OS); no
    shell interpretation — therefore safe from injection.
    """
    try:
        result = subprocess.run(
            ["git", "config", "user.email"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        email = result.stdout.strip()
        return email or "unknown@local"
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown@local"


def _validate_justification(justification: str) -> None:
    """Reject empty / whitespace-only justifications (exit 2 per D-105-01)."""
    stripped = (justification or "").strip()
    if not stripped:
        error("--justification must be non-empty.")
        raise typer.Exit(code=2)


def _validate_actor(actor: str | None) -> None:
    """Reject actors that contain whitespace or human-prose patterns."""
    if actor is None:
        return
    if not _VALID_ACTOR_RE.match(actor):
        error(
            "--accepted-by must be an email address or username "
            "(alphanumerics plus ``._+-`` and an optional ``@host`` segment); "
            f"got {actor!r}."
        )
        raise typer.Exit(code=2)


def _parse_expires_at(expires_at: str | None) -> datetime | None:
    """Parse an ISO-8601 ``--expires-at`` value or exit 2 on malformed input."""
    if expires_at is None:
        return None
    try:
        parsed = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        error(f"--expires-at must be an ISO-8601 datetime (got {expires_at!r}).")
        raise typer.Exit(code=2) from None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _validate_severity(value: str) -> str:
    """Confirm ``--severity`` is one of the canonical values (exit 2 otherwise)."""
    from ai_engineering.state.models import RiskSeverity

    try:
        return RiskSeverity(value).value
    except ValueError:
        valid = ", ".join(s.value for s in RiskSeverity)
        error(f"--severity must be one of: {valid} (got {value!r}).")
        raise typer.Exit(code=2) from None


def _generate_dec_id(now: datetime, store_existing_ids: set[str]) -> str:
    """Generate ``DEC-YYYY-MM-DD-<short_uuid>`` collision-safe inside ``store``."""
    date_part = now.strftime("%Y-%m-%d")
    while True:
        short = uuid.uuid4().hex[:8].upper()
        candidate = f"DEC-{date_part}-{short}"
        if candidate not in store_existing_ids:
            return candidate


def _load_or_create_store(svc: StateService):
    """Load the decision store, creating an empty one if no file exists."""
    from ai_engineering.state.models import DecisionStore

    store_path = svc.state_dir / "decision-store.json"
    if not store_path.exists():
        return DecisionStore()
    try:
        return svc.load_decisions()
    except (OSError, ValueError):
        return DecisionStore()


def _decision_to_dict(decision: Any) -> dict[str, Any]:
    """Render a ``Decision`` as a JSON-friendly dict using aliases."""
    return decision.model_dump(by_alias=True, exclude_none=True, mode="json")


def _gate_risk_acceptance_via_opa(
    *,
    project_root: Path,
    now: datetime,
    expires_at: datetime | None,
    severity: str,
    justification: str,
) -> None:
    """Run ``risk_acceptance_ttl.deny`` and exit 2 on a deny verdict.

    Spec-122 Phase C T-3.13: the policy denies when the requested
    ``ttl_expires_at`` is at or before ``now``. We only invoke OPA when
    the binary is on PATH (fail-open during the rollout window) and
    only when the caller actually supplied an explicit ``--expires-at``;
    severity-default TTLs land in the future by construction.
    """
    if expires_at is None:
        return

    from ai_engineering.governance import opa_runner

    if not opa_runner.available():
        return

    from ai_engineering.policy.checks.opa_gate import evaluate_deny

    decision = evaluate_deny(
        project_root=project_root,
        policy="risk_acceptance_ttl",
        input_data={
            "ttl_expires_at": expires_at.isoformat(),
            "now": now.isoformat(),
            "severity": severity,
            "justification": justification,
        },
        component="risk-cmd",
        source="risk-accept",
    )
    if not decision.passed:
        error("; ".join(decision.deny_messages) or "risk acceptance denied by policy")
        raise typer.Exit(code=2)


# --- Commands ---------------------------------------------------------------


def risk_accept(
    finding_id: Annotated[
        str,
        typer.Option(
            "--finding-id",
            help="Stable rule_id from the finding (e.g. ``E501``, ``aws-secret``).",
        ),
    ],
    severity: Annotated[
        str,
        typer.Option(
            "--severity",
            help="Severity: critical, high, medium, low.",
        ),
    ],
    justification: Annotated[
        str,
        typer.Option(
            "--justification",
            help="Why this finding is being accepted (>=10 chars).",
        ),
    ],
    spec: Annotated[
        str,
        typer.Option("--spec", help="Spec that owns this acceptance (e.g. ``spec-105``)."),
    ],
    follow_up: Annotated[
        str,
        typer.Option("--follow-up", help="Plan to remediate before expiry."),
    ],
    expires_at: Annotated[
        str | None,
        typer.Option(
            "--expires-at",
            help="ISO-8601 expiry override; defaults to severity-default TTL.",
        ),
    ] = None,
    accepted_by: Annotated[
        str | None,
        typer.Option(
            "--accepted-by",
            help="Actor accepting the risk; defaults to ``git config user.email``.",
        ),
    ] = None,
) -> None:
    """Accept a single gate finding as a tracked risk acceptance."""
    from ai_engineering.state.models import RiskSeverity

    _validate_justification(justification)
    if not (spec or "").strip():
        error("--spec must be non-empty.")
        raise typer.Exit(code=2)
    if not (follow_up or "").strip():
        error("--follow-up must be non-empty.")
        raise typer.Exit(code=2)
    severity_value = _validate_severity(severity)
    parsed_expires = _parse_expires_at(expires_at)
    _validate_actor(accepted_by)

    if not (finding_id or "").strip():
        error("--finding-id must be non-empty.")
        raise typer.Exit(code=2)

    actor = (accepted_by or _git_user_email()).strip()
    root = _resolve_project_root()
    svc = StateService(root)
    store = _load_or_create_store(svc)
    now = datetime.now(tz=UTC)
    existing_ids = {d.id for d in store.decisions}
    dec_id = _generate_dec_id(now, existing_ids)

    # Spec-122 Phase C T-3.13: gate the acceptance on the OPA TTL policy
    # before persisting. The policy denies when the requested expiry is
    # already in the past relative to ``now``; the rule lives in
    # ``risk_acceptance_ttl.rego`` and is the canonical source of truth.
    _gate_risk_acceptance_via_opa(
        project_root=root,
        now=now,
        expires_at=parsed_expires,
        severity=severity_value,
        justification=justification,
    )

    decision = create_risk_acceptance(
        store,
        decision_id=dec_id,
        context=f"finding:{finding_id}",
        decision_text=justification.strip(),
        severity=RiskSeverity(severity_value),
        follow_up=follow_up.strip(),
        spec=spec.strip(),
        accepted_by=actor,
        expires_at=parsed_expires,
    )
    decision.finding_id = finding_id

    svc.save_decisions(store)

    emit_control_outcome(
        root,
        category="risk-acceptance",
        control="finding-accepted",
        component="cli",
        outcome="success",
        source="risk-accept",
        metadata={
            "dec_id": decision.id,
            "finding_id": finding_id,
            "severity": severity_value,
            "spec": spec,
            "expires_at": (decision.expires_at.isoformat() if decision.expires_at else None),
        },
    )

    success(f"Accepted finding {finding_id} -> {decision.id}")
    if decision.expires_at:
        kv("Expires", decision.expires_at.isoformat())


def risk_accept_all(
    findings_path: Annotated[
        Path,
        typer.Argument(
            help="Path to a ``gate-findings.json`` document (v1 or v1.1).",
            exists=False,  # validated explicitly to surface a clean exit-2 message.
        ),
    ],
    justification: Annotated[
        str,
        typer.Option("--justification", help="Why this batch is accepted (>=10 chars)."),
    ],
    spec: Annotated[
        str,
        typer.Option("--spec", help="Spec that owns this acceptance batch."),
    ],
    follow_up: Annotated[
        str,
        typer.Option("--follow-up", help="Plan to remediate before expiry."),
    ],
    max_severity: Annotated[
        str | None,
        typer.Option(
            "--max-severity",
            help="Skip findings stricter than this (default: accept all).",
        ),
    ] = None,
    expires_at: Annotated[
        str | None,
        typer.Option("--expires-at", help="ISO-8601 expiry override per-finding."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print the planned batch without persisting."),
    ] = False,
    accepted_by: Annotated[
        str | None,
        typer.Option("--accepted-by", help="Actor; defaults to ``git config user.email``."),
    ] = None,
) -> None:
    """Bulk-accept all findings in a ``gate-findings.json`` document."""
    from ai_engineering.state.models import GateFindingsDocument, RiskSeverity

    _validate_justification(justification)
    if not (spec or "").strip():
        error("--spec must be non-empty.")
        raise typer.Exit(code=2)
    if not (follow_up or "").strip():
        error("--follow-up must be non-empty.")
        raise typer.Exit(code=2)
    parsed_expires = _parse_expires_at(expires_at)
    _validate_actor(accepted_by)

    if not findings_path.exists():
        error(f"findings file not found: {findings_path}")
        raise typer.Exit(code=2)

    try:
        raw = findings_path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        error(f"findings file is not valid JSON: {exc.msg} (line {exc.lineno})")
        raise typer.Exit(code=2) from None
    except OSError as exc:
        error(f"could not read findings file: {exc}")
        raise typer.Exit(code=2) from None

    try:
        document = GateFindingsDocument.model_validate(payload)
    except ValidationError as exc:
        error(
            f"findings file does not match the gate-findings schema: {exc.error_count()} error(s)"
        )
        raise typer.Exit(code=2) from None

    actor = (accepted_by or _git_user_email()).strip()
    root = _resolve_project_root()

    # OQ-1: skip findings whose ``rule_id`` is NULL/empty/whitespace-only.
    valid_findings: list[Any] = []
    skipped_count = 0
    for finding in document.findings:
        rule_id = (finding.rule_id or "").strip()
        if not rule_id:
            skipped_count += 1
            warning(
                "Skipping finding with empty rule_id: "
                f"{finding.check} {finding.file}:{finding.line}"
            )
            emit_control_outcome(
                root,
                category="risk-acceptance",
                control="invalid-rule-id-skipped",
                component=finding.check or "unknown",
                outcome="skipped",
                source="risk-accept-all",
                metadata={
                    "file": finding.file,
                    "line": finding.line,
                    "severity": finding.severity.value if finding.severity else None,
                },
            )
            continue
        valid_findings.append(finding)

    # Optional severity filter (D-105-05 ``--max-severity``).
    if max_severity is not None:
        max_severity_value = _validate_severity(max_severity)
        max_rank = _SEVERITY_ORDER.get(max_severity_value, 0)
        before = len(valid_findings)
        valid_findings = [
            f for f in valid_findings if _SEVERITY_ORDER.get(f.severity.value, 0) <= max_rank
        ]
        filtered_out = before - len(valid_findings)
        if filtered_out:
            info(
                f"Filtered out {filtered_out} finding(s) above --max-severity={max_severity_value}."
            )

    if not valid_findings:
        if skipped_count == 0:
            info("No findings to accept.")
        else:
            info(f"Skipped {skipped_count} malformed finding(s); nothing to accept.")
        return

    if dry_run:
        header(f"Dry run — would accept {len(valid_findings)} finding(s)")
        for finding in valid_findings:
            kv(finding.rule_id, f"{finding.check} {finding.file}:{finding.line}")
        return

    # Persist N DEC entries with shared batch_id.
    svc = StateService(root)
    store = _load_or_create_store(svc)
    now = datetime.now(tz=UTC)
    batch_id = uuid.uuid4().hex
    existing_ids = {d.id for d in store.decisions}

    accepted_decisions: list[Any] = []
    for finding in valid_findings:
        dec_id = _generate_dec_id(now, existing_ids)
        existing_ids.add(dec_id)
        decision = create_risk_acceptance(
            store,
            decision_id=dec_id,
            context=f"finding:{finding.rule_id}",
            decision_text=justification.strip(),
            severity=RiskSeverity(finding.severity.value),
            follow_up=follow_up.strip(),
            spec=spec.strip(),
            accepted_by=actor,
            expires_at=parsed_expires,
        )
        decision.finding_id = finding.rule_id
        decision.batch_id = batch_id
        accepted_decisions.append((finding, decision))

    svc.save_decisions(store)

    # Per-finding telemetry (one event per accepted finding).
    for finding, decision in accepted_decisions:
        emit_control_outcome(
            root,
            category="risk-acceptance",
            control="finding-accepted",
            component=finding.check,
            outcome="success",
            source="risk-accept-all",
            metadata={
                "dec_id": decision.id,
                "finding_id": finding.rule_id,
                "batch_id": batch_id,
                "severity": finding.severity.value,
                "spec": spec.strip(),
                "expires_at": (decision.expires_at.isoformat() if decision.expires_at else None),
            },
        )

    header(f"Accepted {len(accepted_decisions)} finding(s) — batch {batch_id[:8]}")
    for finding, decision in accepted_decisions:
        kv(
            finding.rule_id,
            f"{finding.check} {finding.file}:{finding.line} -> {decision.id}",
        )


def risk_renew(
    dec_id: Annotated[str, typer.Argument(help="DEC-XXXX-YYYY ID to renew.")],
    justification: Annotated[
        str,
        typer.Option("--justification", help="Why remediation hasn't happened yet."),
    ],
    spec: Annotated[
        str,
        typer.Option("--spec", help="Spec owning this renewal."),
    ],
    actor: Annotated[
        str | None,
        typer.Option("--actor", help="Renewer identity; defaults to ``git config user.email``."),
    ] = None,
) -> None:
    """Renew a risk acceptance (max 2 renewals via ``_MAX_RENEWALS``)."""
    _validate_justification(justification)
    if not (spec or "").strip():
        error("--spec must be non-empty.")
        raise typer.Exit(code=2)
    _validate_actor(actor)

    actor_value = (actor or _git_user_email()).strip()
    root = _resolve_project_root()
    svc = StateService(root)
    store = _load_or_create_store(svc)

    try:
        renewed = renew_decision(
            store,
            decision_id=dec_id,
            justification=justification.strip(),
            spec=spec.strip(),
            actor=actor_value,
        )
    except ValueError as exc:
        error(str(exc))
        raise typer.Exit(code=1) from None

    svc.save_decisions(store)

    emit_control_outcome(
        root,
        category="risk-acceptance",
        control="finding-renewed",
        component="cli",
        outcome="success",
        source="risk-renew",
        metadata={
            "dec_id": renewed.id,
            "renewed_from": dec_id,
            "renewal_count": renewed.renewal_count,
            "spec": spec,
        },
    )

    success(f"Renewed {dec_id} -> {renewed.id} (renewal #{renewed.renewal_count})")
    if renewed.expires_at:
        kv("Expires", renewed.expires_at.isoformat())


def risk_resolve(
    dec_id: Annotated[str, typer.Argument(help="DEC-XXXX-YYYY ID to mark remediated.")],
    note: Annotated[str, typer.Option("--note", help="Remediation note (commit, PR, fix link).")],
    actor: Annotated[
        str | None,
        typer.Option("--actor", help="Resolver identity; defaults to ``git config user.email``."),
    ] = None,
) -> None:
    """Mark a risk acceptance as remediated (fix landed)."""
    if not (note or "").strip():
        error("--note must be non-empty.")
        raise typer.Exit(code=2)
    _validate_actor(actor)

    actor_value = (actor or _git_user_email()).strip()
    root = _resolve_project_root()
    svc = StateService(root)
    store = _load_or_create_store(svc)

    try:
        resolved = mark_remediated(store, decision_id=dec_id)
    except ValueError as exc:
        error(str(exc))
        raise typer.Exit(code=1) from None

    svc.save_decisions(store)

    emit_control_outcome(
        root,
        category="risk-acceptance",
        control="finding-remediated",
        component="cli",
        outcome="success",
        source="risk-resolve",
        metadata={"dec_id": resolved.id, "actor": actor_value, "note": note.strip()},
    )

    success(f"Resolved {resolved.id} -> remediated")


def risk_revoke(
    dec_id: Annotated[str, typer.Argument(help="DEC-XXXX-YYYY ID to revoke.")],
    reason: Annotated[str, typer.Option("--reason", help="Why this acceptance is revoked.")],
    actor: Annotated[
        str | None,
        typer.Option("--actor", help="Revoker identity; defaults to ``git config user.email``."),
    ] = None,
) -> None:
    """Revoke a risk acceptance (mistaken / no longer valid)."""
    if not (reason or "").strip():
        error("--reason must be non-empty.")
        raise typer.Exit(code=2)
    _validate_actor(actor)

    actor_value = (actor or _git_user_email()).strip()
    root = _resolve_project_root()
    svc = StateService(root)
    store = _load_or_create_store(svc)

    try:
        revoked = revoke_decision(store, decision_id=dec_id)
    except ValueError as exc:
        error(str(exc))
        raise typer.Exit(code=1) from None

    svc.save_decisions(store)

    emit_control_outcome(
        root,
        category="risk-acceptance",
        control="finding-revoked",
        component="cli",
        outcome="success",
        source="risk-revoke",
        metadata={"dec_id": revoked.id, "actor": actor_value, "reason": reason.strip()},
    )

    success(f"Revoked {revoked.id}")


def risk_list(
    status: Annotated[
        str,
        typer.Option(
            "--status",
            help="Filter by status: active, expired, superseded, revoked, remediated, all.",
        ),
    ] = "active",
    severity: Annotated[
        str | None,
        typer.Option("--severity", help="Filter by severity (critical, high, medium, low)."),
    ] = None,
    expires_within: Annotated[
        int | None,
        typer.Option(
            "--expires-within",
            help="Only show decisions expiring within N days (active only).",
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: table, json, markdown."),
    ] = "table",
) -> None:
    """List risk-acceptance decisions filtered by status/severity/expiry."""
    from ai_engineering.state.models import DecisionStatus

    if output_format not in {"table", "json", "markdown"}:
        error("--format must be one of: table, json, markdown.")
        raise typer.Exit(code=2)

    root = _resolve_project_root()
    svc = StateService(root)
    store = _load_or_create_store(svc)

    decisions = list(store.risk_decisions())

    if status != "all":
        try:
            status_enum = DecisionStatus(status)
        except ValueError:
            valid = ", ".join(s.value for s in DecisionStatus)
            error(f"--status must be one of: {valid}, all (got {status!r}).")
            raise typer.Exit(code=2) from None
        decisions = [d for d in decisions if d.status == status_enum]

    if severity is not None:
        severity_value = _validate_severity(severity)
        decisions = [d for d in decisions if d.severity and d.severity.value == severity_value]

    if expires_within is not None:
        now = datetime.now(tz=UTC)
        from datetime import timedelta

        threshold = now + timedelta(days=expires_within)
        decisions = [
            d for d in decisions if d.expires_at is not None and now <= d.expires_at <= threshold
        ]

    if output_format == "json":
        typer.echo(json.dumps([_decision_to_dict(d) for d in decisions], indent=2, sort_keys=True))
        return

    if output_format == "markdown":
        typer.echo("| DEC ID | Status | Severity | Finding | Expires |")
        typer.echo("| --- | --- | --- | --- | --- |")
        for d in decisions:
            exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "-"
            sev = d.severity.value if d.severity else "?"
            typer.echo(
                f"| {d.id} | {d.status.value} | {sev} | {d.finding_id or d.context[:30]} | {exp} |"
            )
        return

    if not decisions:
        info("No risk acceptances match the filter.")
        return

    header(f"Risk acceptances ({len(decisions)})")
    for d in decisions:
        exp = d.expires_at.strftime("%Y-%m-%d") if d.expires_at else "-"
        sev = d.severity.value if d.severity else "?"
        line_status = "ok" if d.status == DecisionStatus.ACTIVE else "warn"
        status_line(line_status, d.id, f"{d.status.value} · {sev} · expires {exp}")
        kv("  Finding", d.finding_id or d.context[:80])


def risk_show(
    dec_id: Annotated[str, typer.Argument(help="DEC-XXXX-YYYY ID to inspect.")],
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: human, json."),
    ] = "human",
) -> None:
    """Show full detail for a single risk acceptance decision."""
    if output_format not in {"human", "json"}:
        error("--format must be one of: human, json.")
        raise typer.Exit(code=2)

    root = _resolve_project_root()
    svc = StateService(root)
    store = _load_or_create_store(svc)
    decision = store.find_by_id(dec_id)
    if decision is None:
        error(f"Decision {dec_id!r} not found.")
        raise typer.Exit(code=1)

    if output_format == "json":
        typer.echo(json.dumps(_decision_to_dict(decision), indent=2, sort_keys=True))
        return

    header(decision.id)
    kv("Status", decision.status.value)
    kv("Severity", decision.severity.value if decision.severity else "?")
    kv("Risk category", decision.risk_category.value if decision.risk_category else "?")
    kv("Finding", decision.finding_id or "-")
    kv("Batch", decision.batch_id or "-")
    kv("Spec", decision.spec)
    kv("Context", decision.context)
    kv("Decision", decision.decision)
    kv("Accepted by", decision.accepted_by or "-")
    kv("Follow-up", decision.follow_up_action or "-")
    kv("Decided at", decision.decided_at.isoformat())
    if decision.expires_at:
        kv("Expires at", decision.expires_at.isoformat())
    kv("Renewal count", str(decision.renewal_count))
    if decision.renewed_from:
        kv("Renewed from", decision.renewed_from)


__all__ = [
    "risk_accept",
    "risk_accept_all",
    "risk_list",
    "risk_renew",
    "risk_resolve",
    "risk_revoke",
    "risk_show",
]
