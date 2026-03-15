"""Audit event emission for ai-engineering observability.

Provides structured signal emission to the single event store
(audit-log.ndjson). All agents and gates emit events through this
module to avoid dual-write (Fowler: single source of truth).

Event types:
- gate_result: Git hook gate execution outcomes
- scan_complete: Scanner mode completion with score/findings
- build_complete: Build agent task completion
- deploy_complete: Deployment outcomes
- session_metric: AI session efficiency metrics
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ai_engineering.git.context import get_git_context
from ai_engineering.lib.signals import audit_log_path
from ai_engineering.state.io import append_ndjson
from ai_engineering.state.models import AuditEntry
from ai_engineering.vcs.repo_context import get_repo_context

if TYPE_CHECKING:
    from ai_engineering.policy.gates import GateResult

logger = logging.getLogger(__name__)


def _emit(
    project_root: Path,
    *,
    event: str,
    actor: str,
    detail: dict[str, Any],
) -> None:
    """Emit a structured event to the audit log (fail-open)."""
    # Resolve VCS context (cached, fail-open)
    repo_ctx = get_repo_context(project_root)
    git_ctx = get_git_context(project_root)

    entry = AuditEntry(
        timestamp=datetime.now(tz=UTC),
        event=event,
        actor=actor,
        detail=detail,
        vcs_provider=repo_ctx.provider if repo_ctx else None,
        vcs_organization=repo_ctx.organization if repo_ctx else None,
        vcs_project=repo_ctx.project if repo_ctx else None,
        vcs_repository=repo_ctx.repository if repo_ctx else None,
        branch=git_ctx.branch if git_ctx else None,
        commit_sha=git_ctx.commit_sha if git_ctx else None,
    )
    try:
        append_ndjson(audit_log_path(project_root), entry)
    except OSError:
        logger.debug(
            "Failed to emit %s audit event",
            event,
            exc_info=True,
        )


_FIXABLE_CHECKS: frozenset[str] = frozenset(
    {
        "ruff-format",
        "ruff-lint",
        "dotnet-format",
    }
)


def emit_gate_event(project_root: Path, result: GateResult) -> None:
    """Emit a gate_result event after gate execution."""
    checks_detail: dict[str, str] = {}
    for check in result.checks:
        checks_detail[check.name] = "pass" if check.passed else "fail"

    failed = result.failed_checks
    fixable_failures = [n for n in failed if n in _FIXABLE_CHECKS]

    _emit(
        project_root,
        event="gate_result",
        actor="gate-engine",
        detail={
            "type": "gate_result",
            "gate": result.hook.value,
            "result": "pass" if result.passed else "fail",
            "checks": checks_detail,
            "total_checks": len(result.checks),
            "failed_checks": failed,
            "fixable_failures": fixable_failures,
        },
    )


def emit_scan_event(
    project_root: Path,
    *,
    mode: str,
    score: int,
    findings: dict[str, int],
    stacks_scanned: list[str] | None = None,
    duration_ms: int = 0,
) -> None:
    """Emit a scan_complete event to the audit log."""
    _emit(
        project_root,
        event="scan_complete",
        actor="verify",
        detail={
            "type": "scan_complete",
            "agent": "verify",
            "mode": mode,
            "score": score,
            "findings": findings,
            "stacks_scanned": stacks_scanned or [],
            "duration_ms": duration_ms,
        },
    )


def emit_build_event(
    project_root: Path,
    *,
    mode: str,
    files_changed: int = 0,
    lines_added: int = 0,
    lines_removed: int = 0,
    tests_added: int = 0,
    stack: str = "",
    duration_ms: int = 0,
) -> None:
    """Emit a build_complete event to the audit log."""
    _emit(
        project_root,
        event="build_complete",
        actor="build",
        detail={
            "type": "build_complete",
            "agent": "build",
            "mode": mode,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "tests_added": tests_added,
            "stack": stack,
            "duration_ms": duration_ms,
        },
    )


def emit_deploy_event(
    project_root: Path,
    *,
    environment: str,
    strategy: str,
    version: str,
    result: str,
    rollback: bool = False,
) -> None:
    """Emit a deploy_complete event to the audit log."""
    _emit(
        project_root,
        event="deploy_complete",
        actor="release",
        detail={
            "type": "deploy_complete",
            "environment": environment,
            "strategy": strategy,
            "version": version,
            "result": result,
            "rollback": rollback,
        },
    )


def emit_session_event(
    project_root: Path,
    *,
    tokens_used: int = 0,
    tokens_available: int = 200000,
    skills_loaded: list[str] | None = None,
    decisions_reused: int = 0,
    decisions_reprompted: int = 0,
    checkpoint_saved: bool = False,
) -> None:
    """Emit a session_metric event to the audit log."""
    _emit(
        project_root,
        event="session_metric",
        actor="ai-session",
        detail={
            "type": "session_metric",
            "tokens_used": tokens_used,
            "tokens_available": tokens_available,
            "skills_loaded": skills_loaded or [],
            "decisions_reused": decisions_reused,
            "decisions_reprompted": decisions_reprompted,
            "checkpoint_saved": checkpoint_saved,
        },
    )
