"""Audit event emission for ai-engineering observability.

Provides structured signal emission to the single event store
(audit-log.ndjson). All agents and gates emit events through this
module to avoid dual-write (Fowler: single source of truth).

Event types:
- gate_result: Git hook gate execution outcomes
- scan_complete: Scanner mode completion with score/findings
- build_complete: Build agent task completion
- deploy_complete: Deployment outcomes
- guard_advisory: Guard advise mode findings
- guard_gate: Guard gate mode verdicts
- guard_drift: Guard drift detection results
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ai_engineering.git.context import get_git_context
from ai_engineering.lib.signals import audit_log_path
from ai_engineering.state.io import append_ndjson
from ai_engineering.state.models import AuditEntry
from ai_engineering.vcs.repo_context import get_repo_context

if TYPE_CHECKING:
    from ai_engineering.policy.gates import GateResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auto-enrichment helpers (fail-open, cached per-process)
# ---------------------------------------------------------------------------

_UNSET = object()  # stable sentinel for "not yet cached"

_cached_spec_id: str | None | object = _UNSET
_cached_stack: str | None | object = _UNSET


def _read_active_spec(root: Path) -> str | None:
    """Read active spec ID from specs/spec.md frontmatter (fail-open, cached)."""
    global _cached_spec_id
    if _cached_spec_id is not _UNSET:
        return cast("str | None", _cached_spec_id)
    try:
        spec_path = root / ".ai-engineering" / "specs" / "spec.md"
        if not spec_path.exists():
            _cached_spec_id = None
            return None
        content = spec_path.read_text(encoding="utf-8")
        # Placeholder means no active spec
        if content.strip().startswith("# No active spec"):
            _cached_spec_id = None
            return None
        # Try frontmatter id field first
        for line in content.splitlines():
            line_s = line.strip()
            if line_s.startswith("id:"):
                value = line_s.split(":", 1)[1].strip().strip("\"'")
                if value:
                    _cached_spec_id = value
                    return _cached_spec_id
        # Fallback: scan for NNN- pattern
        for line in content.splitlines():
            line_s = line.strip()
            if line_s and not line_s.startswith("#") and not line_s.startswith("<!--"):
                match = re.search(r"(\d{3})-", line_s)
                if match:
                    _cached_spec_id = match.group(1)
                    return _cached_spec_id
        _cached_spec_id = None
        return None
    except Exception:
        _cached_spec_id = None
        return None


def _read_active_stack(root: Path) -> str | None:
    """Read primary stack from manifest.yml config (fail-open)."""
    global _cached_stack
    if _cached_stack is not _UNSET:
        return cast("str | None", _cached_stack)
    try:
        from ai_engineering.config.loader import load_manifest_config

        config = load_manifest_config(root)
        stacks = config.providers.stacks
        _cached_stack = stacks[0] if stacks else None
        return _cached_stack
    except Exception:
        _cached_stack = None
        return None


def _reset_enrichment_cache() -> None:
    """Reset enrichment caches (for testing)."""
    global _cached_spec_id, _cached_stack
    _cached_spec_id = _UNSET
    _cached_stack = _UNSET


# ---------------------------------------------------------------------------
# Core emit
# ---------------------------------------------------------------------------


def _emit(
    project_root: Path,
    *,
    event: str,
    actor: str,
    detail: dict[str, Any],
    source: str | None = None,
    duration_ms: int | None = None,
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
        source=source,
        spec_id=_read_active_spec(project_root),
        stack=_read_active_stack(project_root),
        duration_ms=duration_ms,
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


def emit_gate_event(
    project_root: Path,
    result: GateResult,
    *,
    source: str | None = None,
    duration_ms: int | None = None,
) -> None:
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
            "gate": result.hook.value,
            "result": "pass" if result.passed else "fail",
            "checks": checks_detail,
            "total_checks": len(result.checks),
            "failed_checks": failed,
            "fixable_failures": fixable_failures,
        },
        source=source or "gate-engine",
        duration_ms=duration_ms,
    )


def emit_scan_event(
    project_root: Path,
    *,
    mode: str,
    score: int,
    findings: dict[str, int],
    stacks_scanned: list[str] | None = None,
    duration_ms: int = 0,
    source: str | None = None,
) -> None:
    """Emit a scan_complete event to the audit log."""
    _emit(
        project_root,
        event="scan_complete",
        actor="verify",
        detail={
            "agent": "verify",
            "mode": mode,
            "score": score,
            "findings": findings,
            "stacks_scanned": stacks_scanned or [],
        },
        source=source or "cli",
        duration_ms=duration_ms,
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
    source: str | None = None,
) -> None:
    """Emit a build_complete event to the audit log."""
    _emit(
        project_root,
        event="build_complete",
        actor="build",
        detail={
            "agent": "build",
            "mode": mode,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "tests_added": tests_added,
            "stack": stack,
        },
        source=source or "gate-engine",
        duration_ms=duration_ms,
    )


def emit_deploy_event(
    project_root: Path,
    *,
    environment: str,
    strategy: str,
    version: str,
    result: str,
    rollback: bool = False,
    source: str | None = None,
) -> None:
    """Emit a deploy_complete event to the audit log."""
    _emit(
        project_root,
        event="deploy_complete",
        actor="release",
        detail={
            "environment": environment,
            "strategy": strategy,
            "version": version,
            "result": result,
            "rollback": rollback,
        },
        source=source or "cli",
    )


def emit_guard_advisory(
    project_root: Path,
    *,
    files_checked: int = 0,
    warnings: int = 0,
    concerns: int = 0,
    source: str | None = None,
) -> None:
    """Emit a guard_advisory event after advise mode analysis."""
    _emit(
        project_root,
        event="guard_advisory",
        actor="guard",
        detail={
            "mode": "advise",
            "files_checked": files_checked,
            "warnings": warnings,
            "concerns": concerns,
        },
        source=source or "cli",
    )


def emit_guard_gate(
    project_root: Path,
    *,
    verdict: str,
    task: str = "",
    agent: str = "",
    findings: int = 0,
    source: str | None = None,
) -> None:
    """Emit a guard_gate event after gate mode validation."""
    _emit(
        project_root,
        event="guard_gate",
        actor="guard",
        detail={
            "mode": "gate",
            "verdict": verdict,
            "task": task,
            "agent": agent,
            "findings": findings,
        },
        source=source or "cli",
    )


def emit_guard_drift(
    project_root: Path,
    *,
    decisions_checked: int = 0,
    drifted: int = 0,
    critical: int = 0,
    source: str | None = None,
) -> None:
    """Emit a guard_drift event after drift detection."""
    _emit(
        project_root,
        event="guard_drift",
        actor="guard",
        detail={
            "mode": "drift",
            "decisions_checked": decisions_checked,
            "drifted": drifted,
            "critical": critical,
        },
        source=source or "cli",
    )
