"""Governance gate CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import typer

from ai_engineering.paths import repo_root
from ai_engineering.policy.gates import (
    gate_requirements,
    run_docs_contract,
    run_commit_msg,
    run_pre_commit,
    run_pre_push,
)
from ai_engineering.policy.risk_acceptance import (
    check_reuse,
    parse_context_payload,
    record_acceptance,
)


def _normalize_severity(raw: str) -> str:
    value = raw.strip().lower()
    if value not in {"low", "medium", "high", "critical"}:
        raise typer.BadParameter("severity must be one of: low, medium, high, critical")
    return value


def register(gate_app: typer.Typer) -> None:
    """Register gate command group."""

    @gate_app.command("pre-commit")
    def gate_pre_commit() -> None:
        """Run pre-commit gate checks."""
        ok, messages = run_pre_commit()
        for message in messages:
            typer.echo(message)
        if not ok:
            raise typer.Exit(code=1)

    @gate_app.command("commit-msg")
    def gate_commit_msg(commit_msg_file: str) -> None:
        """Run commit-msg gate checks."""
        message_path = Path(commit_msg_file)
        if not message_path.exists():
            typer.echo(f"missing commit message file: {commit_msg_file}")
            raise typer.Exit(code=1)
        ok, messages = run_commit_msg(message_path)
        for message in messages:
            typer.echo(message)
        if not ok:
            raise typer.Exit(code=1)

    @gate_app.command("pre-push")
    def gate_pre_push() -> None:
        """Run pre-push gate checks."""
        ok, messages = run_pre_push()
        for message in messages:
            typer.echo(message)
        if not ok:
            raise typer.Exit(code=1)

    @gate_app.command("docs")
    def gate_docs() -> None:
        """Run backlog/delivery documentation contract checks."""
        ok, messages = run_docs_contract()
        for message in messages:
            typer.echo(message)
        if not ok:
            raise typer.Exit(code=1)

    @gate_app.command("list")
    def gate_list(
        json_output: bool = typer.Option(False, "--json", help="Print JSON output"),
    ) -> None:
        """Show configured mandatory gate requirements."""
        requirements = gate_requirements(repo_root())
        if json_output:
            typer.echo(json.dumps(requirements, indent=2))
            return

        protected_raw = requirements.get("protectedBranches", [])
        protected = protected_raw if isinstance(protected_raw, list) else []
        protected_names = [str(item) for item in protected]
        typer.echo(
            f"protected branches: {', '.join(protected_names) if protected_names else 'none'}"
        )
        stages = requirements.get("stages", {})
        if isinstance(stages, dict):
            for stage, checks in stages.items():
                typer.echo(f"{stage}:")
                if isinstance(checks, list):
                    for check in checks:
                        if isinstance(check, dict):
                            typed_check = cast(dict[str, Any], check)
                            tool_raw = typed_check.get("tool")
                            tool = str(tool_raw) if tool_raw is not None else "unknown"
                            typer.echo(f"  - {tool}")

    @gate_app.command("risk-accept")
    def gate_risk_accept(
        policy_id: str = typer.Option(..., "--policy-id", help="Policy identifier"),
        decision: str = typer.Option(..., "--decision", help="Accepted decision value"),
        rationale: str = typer.Option(..., "--rationale", help="Acceptance rationale"),
        severity: str = typer.Option("medium", "--severity", help="Risk severity"),
        context_json: str = typer.Option("{}", "--context", help="Context JSON object"),
        path_pattern: str | None = typer.Option(
            None, "--path-pattern", help="Optional scope path pattern"
        ),
        actor: str = typer.Option("engineer", "--actor", help="Decision actor"),
    ) -> None:
        """Persist explicit risk acceptance and append an audit event."""
        parsed_context = parse_context_payload(context_json)
        payload = record_acceptance(
            root=repo_root(),
            policy_id=policy_id,
            decision=decision,
            rationale=rationale,
            severity=cast(Any, _normalize_severity(severity)),
            context_payload=parsed_context,
            path_pattern=path_pattern,
            created_by=actor,
        )
        typer.echo(json.dumps(payload, indent=2))

    @gate_app.command("risk-check")
    def gate_risk_check(
        policy_id: str = typer.Option(..., "--policy-id", help="Policy identifier"),
        severity: str = typer.Option("medium", "--severity", help="Risk severity"),
        context_json: str = typer.Option("{}", "--context", help="Context JSON object"),
        path_pattern: str | None = typer.Option(
            None, "--path-pattern", help="Optional scope path pattern"
        ),
        expected_decision: str | None = typer.Option(
            None,
            "--expected-decision",
            help="Optional decision that must match for reuse",
        ),
    ) -> None:
        """Evaluate if stored decision can be reused or needs re-prompt."""
        parsed_context = parse_context_payload(context_json)
        payload = check_reuse(
            root=repo_root(),
            policy_id=policy_id,
            severity=cast(Any, _normalize_severity(severity)),
            context_payload=parsed_context,
            path_pattern=path_pattern,
            expected_decision=expected_decision,
        )
        typer.echo(json.dumps(payload, indent=2))
