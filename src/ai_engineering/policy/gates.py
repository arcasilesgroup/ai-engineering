"""Git hook gate checks for ai-engineering.

Implements the quality gates invoked by git hooks:
- **pre-commit**: stack-aware format/lint checks + gitleaks + risk expiry warnings.
- **commit-msg**: commit message format validation.
- **pre-push**: stack-aware tests/type-checks/vuln-scans + semgrep + expired risk blocking.

Gate dispatch is stack-aware: reads ``installedStacks`` from
``install-manifest.json`` and runs only checks relevant to active stacks.
Falls back to Python-only checks if no manifest exists.

Also enforces protected branch blocking: direct commits to main/master
are rejected.
"""

from __future__ import annotations

import os
import shutil  # noqa: F401 — re-exported for test patching
import subprocess  # noqa: F401 — re-exported for test patching
from dataclasses import dataclass, field
from pathlib import Path

from ai_engineering.policy.test_scope import TestScope, compute_test_scope, resolve_scope_mode
from ai_engineering.state.audit import emit_gate_event
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import GateHook, InstallManifest


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
    from ai_engineering.policy.checks.branch_protection import (
        check_branch_protection,
        check_hook_integrity,
        check_version_deprecation,
    )

    result = GateResult(hook=hook)

    # Branch protection check (all hooks)
    check_branch_protection(project_root, result)
    if not result.passed:
        return result

    # Version deprecation check (defense-in-depth, all hooks)
    check_version_deprecation(result)
    if not result.passed:
        return result

    check_hook_integrity(project_root, result)
    if not result.passed:
        return result

    if hook == GateHook.PRE_COMMIT:
        _run_pre_commit_checks(project_root, result)
    elif hook == GateHook.COMMIT_MSG:
        _run_commit_msg_checks(commit_msg_file, result)
    elif hook == GateHook.PRE_PUSH:
        _run_pre_push_checks(project_root, result)

    # Emit audit event for observability (Phase 0 instrumentation)
    emit_gate_event(project_root, result)

    return result


# --- Helper functions ---


def _get_active_stacks(project_root: Path) -> list[str]:
    """Read installed stacks from install-manifest.json."""
    manifest_path = project_root / ".ai-engineering" / "state" / "install-manifest.json"
    if not manifest_path.exists():
        return ["python"]
    try:
        manifest = read_json_model(manifest_path, InstallManifest)
        stacks = manifest.installed_stacks
        return stacks if stacks else ["python"]
    except (OSError, ValueError):
        return ["python"]


def _run_commit_msg_checks(
    commit_msg_file: Path | None,
    result: GateResult,
) -> None:
    """Validate commit message format."""
    from ai_engineering.policy.checks.commit_msg import inject_gate_trailer, validate_commit_message

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


def _clone_registry(
    registry: dict[str, list[object]],
    config_cls: type,
) -> dict[str, list[object]]:
    """Clone check registry without mutating global constants."""
    clone: dict[str, list[object]] = {}
    for stack, checks in registry.items():
        clone[stack] = [
            config_cls(
                name=check.name,  # type: ignore[attr-defined]
                cmd=list(check.cmd),  # type: ignore[attr-defined]
                required=check.required,  # type: ignore[attr-defined]
                timeout=check.timeout,  # type: ignore[attr-defined]
            )
            for check in checks
        ]
    return clone


def _override_test_cmd(
    registry: dict[str, list[object]],
    scope: TestScope,
    config_cls: type,
) -> dict[str, list[object]]:
    """Return cloned registry with python stack-tests command selectively overridden."""
    clone = _clone_registry(registry, config_cls)
    python_checks = clone.get("python", [])
    updated: list[object] = []

    for check in python_checks:
        if check.name != "stack-tests":  # type: ignore[attr-defined]
            updated.append(check)
            continue

        if scope.mode == "selective" and not scope.selected_tests:
            continue

        if scope.mode == "selective":
            updated.append(
                config_cls(
                    name=check.name,  # type: ignore[attr-defined]
                    cmd=[*check.cmd, *scope.selected_tests],  # type: ignore[attr-defined]
                    required=check.required,  # type: ignore[attr-defined]
                    timeout=check.timeout,  # type: ignore[attr-defined]
                )
            )
            continue

        updated.append(check)

    clone["python"] = updated
    return clone


def _append_scope_diagnostic(result: GateResult, *, scope: TestScope, mode: str) -> None:
    """Append structured scope diagnostics to gate results."""
    sample = ", ".join(scope.selected_tests[:5]) if scope.selected_tests else "none"
    output = "\n".join(
        [
            f"mode={mode}",
            f"resolved_mode={scope.mode}",
            f"test_count={len(scope.selected_tests)}",
            f"reasons={','.join(scope.reasons) if scope.reasons else 'none'}",
            f"sample_tests={sample}",
        ]
    )
    result.checks.append(
        GateCheckResult(
            name="test-scope",
            passed=True,
            output=output,
        )
    )


def _compute_test_scope(project_root: Path) -> TestScope:
    """Compute unit-tier test scope for pre-push checks."""
    return compute_test_scope(project_root, tier="unit", base_ref="auto")


def _check_expired_risk_acceptances(project_root: Path, result: GateResult) -> None:
    """Delegate to risk module — kept here for test patching compatibility."""
    from ai_engineering.policy.checks.risk import check_expired_risk_acceptances

    check_expired_risk_acceptances(project_root, result)


def _run_pre_commit_checks(project_root: Path, result: GateResult) -> None:
    """Run pre-commit gate checks: common + per-stack checks + risk warnings."""
    from ai_engineering.policy.checks.risk import check_expiring_risk_acceptances
    from ai_engineering.policy.checks.stack_runner import PRE_COMMIT_CHECKS, run_checks_for_stacks

    stacks = _get_active_stacks(project_root)
    run_checks_for_stacks(project_root, result, PRE_COMMIT_CHECKS, stacks)
    check_expiring_risk_acceptances(project_root, result)


def _run_pre_push_checks(project_root: Path, result: GateResult) -> None:
    """Run pre-push gate checks: common + per-stack checks + expired risks."""
    from ai_engineering.policy.checks.sonar import check_sonar_gate
    from ai_engineering.policy.checks.stack_runner import (
        PRE_PUSH_CHECKS,
        CheckConfig,
        run_checks_for_stacks,
    )

    stacks = _get_active_stacks(project_root)
    registry = PRE_PUSH_CHECKS

    if "python" in stacks:
        mode = resolve_scope_mode(os.environ)
        if mode == "off":
            result.checks.append(
                GateCheckResult(
                    name="test-scope",
                    passed=True,
                    output="mode=off\nresolved_mode=full\ntest_count=0\nreasons=scope_disabled",
                )
            )
        else:
            try:
                scope = _compute_test_scope(project_root)
                _append_scope_diagnostic(result, scope=scope, mode=mode)
                if mode == "enforce":
                    registry = _override_test_cmd(PRE_PUSH_CHECKS, scope, CheckConfig)
            except Exception as exc:
                result.checks.append(
                    GateCheckResult(
                        name="test-scope",
                        passed=True,
                        output=(
                            "mode="
                            f"{mode}\nresolved_mode=full\ntest_count=0\n"
                            f"reasons=scope_computation_failed:{exc}"
                        ),
                    )
                )

    run_checks_for_stacks(project_root, result, registry, stacks)
    check_sonar_gate(project_root, result)
    _check_expired_risk_acceptances(project_root, result)


# ---------------------------------------------------------------------------
# Backward-compatible re-exports for tests and consumers.
# These were previously defined directly in this module.
# Deferred imports to avoid circular dependency (check modules import
# GateCheckResult/GateResult from this module).
# ---------------------------------------------------------------------------


def __getattr__(name: str) -> object:
    """Lazy re-export of names moved to policy.checks sub-modules."""
    if name == "CheckConfig":
        from ai_engineering.policy.checks.stack_runner import CheckConfig

        return CheckConfig
    if name == "_PRE_COMMIT_CHECKS":
        from ai_engineering.policy.checks.stack_runner import PRE_COMMIT_CHECKS

        return PRE_COMMIT_CHECKS
    if name == "_PRE_PUSH_CHECKS":
        from ai_engineering.policy.checks.stack_runner import PRE_PUSH_CHECKS

        return PRE_PUSH_CHECKS
    if name == "_run_checks_for_stacks":
        from ai_engineering.policy.checks.stack_runner import run_checks_for_stacks

        return run_checks_for_stacks
    if name == "_run_tool_check":
        from ai_engineering.policy.checks.stack_runner import run_tool_check

        return run_tool_check
    if name == "_validate_commit_message":
        from ai_engineering.policy.checks.commit_msg import validate_commit_message

        return validate_commit_message
    if name == "_check_expiring_risk_acceptances":
        from ai_engineering.policy.checks.risk import check_expiring_risk_acceptances

        return check_expiring_risk_acceptances
    if name == "_check_expired_risk_acceptances":
        from ai_engineering.policy.checks.risk import check_expired_risk_acceptances

        return check_expired_risk_acceptances
    if name == "_check_sonar_gate":
        from ai_engineering.policy.checks.sonar import check_sonar_gate

        return check_sonar_gate
    if name == "_check_branch_protection":
        from ai_engineering.policy.checks.branch_protection import check_branch_protection

        return check_branch_protection
    if name == "_check_version_deprecation":
        from ai_engineering.policy.checks.branch_protection import check_version_deprecation

        return check_version_deprecation
    if name == "_check_hook_integrity":
        from ai_engineering.policy.checks.branch_protection import check_hook_integrity

        return check_hook_integrity
    if name == "_load_decision_store":
        from ai_engineering.policy.checks.risk import load_decision_store

        return load_decision_store
    if name == "_GATE_TRAILER":
        from ai_engineering.policy.checks.commit_msg import _GATE_TRAILER

        return _GATE_TRAILER
    if name == "_inject_gate_trailer":
        from ai_engineering.policy.checks.commit_msg import inject_gate_trailer

        return inject_gate_trailer
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
