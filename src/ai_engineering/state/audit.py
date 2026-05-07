"""Canonical framework event emission for legacy callers.

This module retains the public emitter names used across the codebase while
redirecting all new observability writes to ``framework-events.ndjson``.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, cast

from ai_engineering.state.observability import (
    emit_control_outcome,
    emit_framework_operation,
    emit_git_hook_outcome,
)
from ai_engineering.state.work_plane import (
    active_work_plane_placeholder_fallback_id,
    resolve_active_work_plane,
)

if TYPE_CHECKING:
    from ai_engineering.policy.gates import GateResult

logger = logging.getLogger(__name__)


_UNSET = object()

_cached_stack: str | None | object = _UNSET


def _read_active_spec(root: Path) -> str | None:
    """Read active spec ID from ``spec.md`` frontmatter (fail-open, cached)."""
    try:
        work_plane = resolve_active_work_plane(root)
        spec_path = work_plane.spec_path
        if not spec_path.exists():
            return None
        content = spec_path.read_text(encoding="utf-8")
        if content.strip().startswith("# No active spec"):
            return active_work_plane_placeholder_fallback_id(root)
        for line in content.splitlines():
            line_s = line.strip()
            if line_s.startswith("id:"):
                value = line_s.split(":", 1)[1].strip().strip("\"'")
                if value:
                    return value
        for line in content.splitlines():
            line_s = line.strip()
            if line_s and not line_s.startswith("#") and not line_s.startswith("<!--"):
                match = re.search(r"(\d{3})-", line_s)
                if match:
                    return match.group(1)
        return None
    except Exception:
        return None


def _read_active_stack(root: Path) -> str | None:
    """Read primary stack from ``manifest.yml`` (fail-open, cached)."""
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
    """Reset enrichment caches for tests."""
    global _cached_stack
    _cached_stack = _UNSET


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
    """Emit a canonical git hook outcome event after gate execution."""
    checks_detail: dict[str, str] = {}
    failure_reasons: dict[str, str] = {}
    for check in result.checks:
        checks_detail[check.name] = "pass" if check.passed else "fail"
        if not check.passed and check.output:
            failure_reasons[check.name] = check.output

    failed = result.failed_checks
    fixable_failures = [name for name in failed if name in _FIXABLE_CHECKS]

    try:
        emit_git_hook_outcome(
            project_root,
            hook_kind=result.hook.value,
            checks=checks_detail,
            failed_checks=failed,
            failure_reasons=failure_reasons,
            component="gate-engine",
            source=source or "gate-engine",
            metadata={
                "total_checks": len(result.checks),
                "fixable_failures": fixable_failures,
                "duration_ms": duration_ms,
            },
        )
    except OSError:
        logger.debug("Failed to emit canonical git hook event", exc_info=True)


def emit_scan_event(
    project_root: Path,
    *,
    mode: str,
    score: int,
    findings: dict[str, int],
    stacks_scanned: list[str] | None = None,
    duration_ms: int = 0,
    source: str | None = None,
    outcome: str = "success",
) -> None:
    """Emit a canonical verification or scan control outcome."""
    emit_control_outcome(
        project_root,
        category="quality",
        control=mode,
        component="verify",
        outcome=outcome,
        source=source or "cli",
        metadata={
            "score": score,
            "findings": findings,
            "stacks_scanned": stacks_scanned or [],
            "duration_ms": duration_ms,
            "spec_id": _read_active_spec(project_root),
            "stack": _read_active_stack(project_root),
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
    source: str | None = None,
) -> None:
    """Emit a canonical framework build operation event."""
    emit_framework_operation(
        project_root,
        operation="build",
        component="build",
        source=source or "gate-engine",
        metadata={
            "mode": mode,
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "tests_added": tests_added,
            "stack": stack,
            "duration_ms": duration_ms,
            "spec_id": _read_active_spec(project_root),
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
    source: str | None = None,
) -> None:
    """Emit a canonical deployment operation event."""
    emit_framework_operation(
        project_root,
        operation="deploy",
        component="release",
        outcome="success" if result.lower() == "success" else "failure",
        source=source or "cli",
        metadata={
            "environment": environment,
            "strategy": strategy,
            "version": version,
            "result": result,
            "rollback": rollback,
            "spec_id": _read_active_spec(project_root),
        },
    )


def emit_guard_advisory(
    project_root: Path,
    *,
    files_checked: int = 0,
    warnings: int = 0,
    concerns: int = 0,
    source: str | None = None,
) -> None:
    """Emit a canonical governance advisory outcome."""
    outcome = "warning" if warnings or concerns else "success"
    emit_control_outcome(
        project_root,
        category="governance",
        control="guard-advisory",
        component="guard",
        outcome=outcome,
        source=source or "cli",
        metadata={
            "mode": "advise",
            "files_checked": files_checked,
            "warnings": warnings,
            "concerns": concerns,
            "spec_id": _read_active_spec(project_root),
        },
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
    """Emit a canonical governance gate outcome."""
    normalized = verdict.lower()
    outcome = "success" if normalized in {"pass", "success"} else "failure"
    emit_control_outcome(
        project_root,
        category="governance",
        control=task or "guard-gate",
        component="guard",
        outcome=outcome,
        source=source or "cli",
        metadata={
            "mode": "gate",
            "verdict": verdict,
            "task": task,
            "agent": agent,
            "findings": findings,
            "spec_id": _read_active_spec(project_root),
        },
    )


def emit_guard_drift(
    project_root: Path,
    *,
    decisions_checked: int = 0,
    drifted: int = 0,
    critical: int = 0,
    source: str | None = None,
) -> None:
    """Emit a canonical governance drift control outcome."""
    outcome = "failure" if critical or drifted else "success"
    emit_control_outcome(
        project_root,
        category="governance",
        control="guard-drift",
        component="guard",
        outcome=outcome,
        source=source or "cli",
        metadata={
            "mode": "drift",
            "decisions_checked": decisions_checked,
            "drifted": drifted,
            "critical": critical,
            "spec_id": _read_active_spec(project_root),
        },
    )
