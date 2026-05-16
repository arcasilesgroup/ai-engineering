"""Git hook gate checks for ai-engineering.

Implements the quality gates invoked by git hooks:
- **pre-commit**: stack-aware format/lint checks + gitleaks + risk expiry warnings.
- **commit-msg**: commit message format validation.
- **pre-push**: stack-aware tests/type-checks/vuln-scans + semgrep + expired risk blocking.

Gate dispatch is stack-aware: reads ``providers.stacks`` from
``manifest.yml`` via :func:`load_manifest_config` and runs only checks
relevant to active stacks.  Falls back to Python-only checks if no
manifest exists.

Also enforces protected branch blocking: direct commits to main/master
are rejected.
"""

from __future__ import annotations

import time as _time
import warnings
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.state.audit import emit_gate_event
from ai_engineering.state.models import GateHook


@dataclass
class GateCheckResult:
    """Result of a single gate check."""

    name: str
    passed: bool
    output: str = ""


@dataclass
class GateResult:
    """Aggregated result from a gate execution."""

    hook: GateHook
    checks: list[GateCheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if all gate checks passed."""
        return all(c.passed for c in self.checks)

    @property
    def failed_checks(self) -> list[str]:
        """Names of failed checks."""
        return [c.name for c in self.checks if not c.passed]


def _emit_gate_audit(project_root: Path, result: GateResult, *, started_at: float) -> None:
    """Emit the standard gate audit event with elapsed time."""
    elapsed_ms = int((_time.monotonic() - started_at) * 1000)
    emit_gate_event(project_root, result, duration_ms=elapsed_ms)


def _emit_build_complete_if_needed(project_root: Path, result: GateResult) -> None:
    """Emit the build-complete event for successful pre-push runs."""
    if not result.passed or result.hook != GateHook.PRE_PUSH:
        return

    import contextlib

    with contextlib.suppress(Exception):
        from ai_engineering.state.audit import emit_build_event

        stats = _git_diff_stats(project_root)
        emit_build_event(
            project_root,
            mode="pre-push",
            files_changed=stats["files"],
            lines_added=stats["insertions"],
            lines_removed=stats["deletions"],
            stack=",".join(_get_active_stacks(project_root)),
        )


def _run_common_gate_guards(
    project_root: Path,
    result: GateResult,
    *,
    started_at: float,
) -> bool:
    """Run the common branch/version/hook guards for hook-style gates."""
    from ai_engineering.policy.checks.branch_protection import (
        check_branch_protection,
        check_hook_integrity,
        check_version_deprecation,
    )

    check_branch_protection(project_root, result)
    if not result.passed:
        _emit_gate_audit(project_root, result, started_at=started_at)
        return False

    check_version_deprecation(result)
    if not result.passed:
        _emit_gate_audit(project_root, result, started_at=started_at)
        return False

    check_hook_integrity(project_root, result)
    if not result.passed:
        _emit_gate_audit(project_root, result, started_at=started_at)
        return False

    return True


def run_commit_msg_gate(
    project_root: Path,
    *,
    commit_msg_file: Path | None = None,
) -> GateResult:
    """Execute the commit-msg hook through a thin dedicated adapter path."""
    started_at = _time.monotonic()
    result = GateResult(hook=GateHook.COMMIT_MSG)

    if not _run_common_gate_guards(project_root, result, started_at=started_at):
        return result

    _run_commit_msg_checks(commit_msg_file, result, project_root=project_root)
    _emit_gate_audit(project_root, result, started_at=started_at)
    return result


def run_gate(
    hook: GateHook,
    project_root: Path,
    *,
    commit_msg_file: Path | None = None,
) -> GateResult:
    """Execute all checks for a specific gate hook.

    Args:
        hook: The gate hook type to execute.
        project_root: Root directory of the project.
        commit_msg_file: Path to the commit message file (commit-msg only).

    Returns:
        GateResult with all check outcomes.
    """
    warnings.warn(
        "policy.gates.run_gate is the legacy gate engine and is deprecated; route CLI and hook flows through policy.orchestrator.run_gate instead.",  # noqa: E501
        DeprecationWarning,
        stacklevel=2,
    )

    t0 = _time.monotonic()
    result = GateResult(hook=hook)

    if hook == GateHook.COMMIT_MSG:
        return run_commit_msg_gate(project_root, commit_msg_file=commit_msg_file)

    if not _run_common_gate_guards(project_root, result, started_at=t0):
        return result

    if hook == GateHook.PRE_COMMIT:
        _run_pre_commit_checks(project_root, result)
    elif hook == GateHook.PRE_PUSH:
        _run_pre_push_checks(project_root, result)

    _emit_gate_audit(project_root, result, started_at=t0)
    _emit_build_complete_if_needed(project_root, result)

    return result


# --- Helper functions ---


def _get_active_stacks(project_root: Path) -> list[str]:
    """Read installed stacks from manifest.yml."""
    try:
        stacks = load_manifest_config(project_root).providers.stacks
        return stacks if stacks else ["python"]
    except (OSError, ValueError):
        return ["python"]


def _git_diff_stats(project_root: Path) -> dict[str, int]:
    """Get diff stats for changes being pushed (fail-open)."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "--numstat"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=10,
        )
        files = insertions = deletions = 0
        for line in proc.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                files += 1
                try:
                    insertions += int(parts[0]) if parts[0] != "-" else 0
                    deletions += int(parts[1]) if parts[1] != "-" else 0
                except ValueError:
                    pass
        return {"files": files, "insertions": insertions, "deletions": deletions}
    except Exception:
        return {"files": 0, "insertions": 0, "deletions": 0}


def _run_commit_msg_checks(
    commit_msg_file: Path | None,
    result: GateResult,
    *,
    project_root: Path | None = None,
) -> None:
    """Validate commit message format.

    Spec-122 Phase C T-3.11: when ``project_root`` is provided the format
    check is delegated to OPA via
    ``commit_msg.validate_commit_message_opa``; the legacy regex is
    retained as a fallback for the OPA-unavailable path. Without
    ``project_root`` we default to the regex-only check to preserve the
    original signature for legacy test fixtures.
    """
    from ai_engineering.policy.checks.commit_msg import (
        inject_gate_trailer,
        validate_commit_message,
        validate_commit_message_opa,
    )

    if commit_msg_file is None or not commit_msg_file.is_file():
        result.checks.append(
            GateCheckResult(
                name="commit-msg-format",
                passed=True,
                output="No commit message file provided — skipped",
            )
        )
        return

    try:
        msg = commit_msg_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        result.checks.append(
            GateCheckResult(
                name="commit-msg-format",
                passed=False,
                output=f"Failed to read commit message: {exc}",
            )
        )
        return

    if project_root is not None:
        errors = validate_commit_message_opa(msg, project_root=project_root)
    else:
        errors = validate_commit_message(msg)
    if errors:
        result.checks.append(
            GateCheckResult(
                name="commit-msg-format",
                passed=False,
                output="; ".join(errors),
            )
        )
    else:
        inject_gate_trailer(commit_msg_file)
        result.checks.append(
            GateCheckResult(
                name="commit-msg-format",
                passed=True,
                output="Commit message format valid",
            )
        )


def _check_expired_risk_acceptances(project_root: Path, result: GateResult) -> None:
    """Delegate to risk module — kept here for test patching compatibility."""
    from ai_engineering.policy.checks.risk import check_expired_risk_acceptances

    check_expired_risk_acceptances(project_root, result)


def _run_pre_commit_checks(project_root: Path, result: GateResult) -> None:
    """Run pre-commit gate checks: common + per-stack checks + risk warnings.

    spec-101 R-15 / D-101-01: dispatch goes through the data-driven
    :func:`get_checks_for_stage` so the canonical stack names from
    ``manifest.yml.required_tools`` (``csharp``, ``typescript``,
    ``javascript``, ...) drive the per-stage check list. The legacy
    registry (keyed on obsolete ``dotnet``/``nextjs``) is no longer
    consulted -- adding a stack absent from ``required_tools.<stack>``
    raises :class:`UnknownStackError` from the loader, closing the
    silent-no-op gap.

    When ``manifest.yml`` is absent (fresh checkout / smoke fixtures) the
    data-driven loader returns an empty list. In that case we fall back
    to the legacy ``PRE_COMMIT_CHECKS`` registry so the baseline gates
    (gitleaks, ruff format/lint) keep firing -- otherwise the gate would
    trivially pass on a project without ai-engineering installed.
    """
    from ai_engineering.policy.checks.risk import check_expiring_risk_acceptances
    from ai_engineering.policy.checks.stack_runner import (
        PRE_COMMIT_CHECKS,
        get_checks_for_stage,
        run_checks_for_specs,
        run_checks_for_stacks,
    )

    stacks = _get_active_stacks(project_root)
    specs = get_checks_for_stage(GateHook.PRE_COMMIT, stacks, project_root=project_root)
    if specs:
        run_checks_for_specs(project_root, result, specs)
    else:
        run_checks_for_stacks(project_root, result, PRE_COMMIT_CHECKS, stacks)
    check_expiring_risk_acceptances(project_root, result)


def _run_pre_push_checks(project_root: Path, result: GateResult) -> None:
    """Run pre-push gate checks: common + per-stack checks + expired risks.

    spec-101 R-15 / D-101-01: dispatch goes through the data-driven
    :func:`get_checks_for_stage` -- see :func:`_run_pre_commit_checks`
    for the rationale. The pre-push surface adds the SonarCloud gate and
    the expired-risk-acceptance enforcement.

    Mirrors the pre-commit fallback: an empty data-driven spec list (no
    manifest) routes through the legacy registry so semgrep, pip-audit,
    and ty/pytest gates keep running on legacy fixtures.
    """
    from ai_engineering.policy.checks.sonar import check_sonar_gate
    from ai_engineering.policy.checks.stack_runner import (
        PRE_PUSH_CHECKS,
        get_checks_for_stage,
        run_checks_for_specs,
        run_checks_for_stacks,
    )

    stacks = _get_active_stacks(project_root)
    specs = get_checks_for_stage(GateHook.PRE_PUSH, stacks, project_root=project_root)
    if specs:
        run_checks_for_specs(project_root, result, specs)
    else:
        run_checks_for_stacks(project_root, result, PRE_PUSH_CHECKS, stacks)
    check_sonar_gate(project_root, result)
    _check_expired_risk_acceptances(project_root, result)
