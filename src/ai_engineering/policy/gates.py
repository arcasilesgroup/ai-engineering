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
import time as _time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ai_engineering.policy.test_scope import TestScope, compute_test_scope, resolve_scope_mode
from ai_engineering.state.audit import emit_gate_event
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import GateHook, InstallManifest

if TYPE_CHECKING:
    from ai_engineering.policy.checks.stack_runner import CheckConfig


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

    t0 = _time.monotonic()
    result = GateResult(hook=hook)

    # Branch protection check (all hooks)
    check_branch_protection(project_root, result)
    if not result.passed:
        elapsed_ms = int((_time.monotonic() - t0) * 1000)
        emit_gate_event(project_root, result, duration_ms=elapsed_ms)
        return result

    # Version deprecation check (defense-in-depth, all hooks)
    check_version_deprecation(result)
    if not result.passed:
        elapsed_ms = int((_time.monotonic() - t0) * 1000)
        emit_gate_event(project_root, result, duration_ms=elapsed_ms)
        return result

    check_hook_integrity(project_root, result)
    if not result.passed:
        elapsed_ms = int((_time.monotonic() - t0) * 1000)
        emit_gate_event(project_root, result, duration_ms=elapsed_ms)
        return result

    if hook == GateHook.PRE_COMMIT:
        _run_pre_commit_checks(project_root, result)
    elif hook == GateHook.COMMIT_MSG:
        _run_commit_msg_checks(commit_msg_file, result)
    elif hook == GateHook.PRE_PUSH:
        _run_pre_push_checks(project_root, result)

    # Emit audit event for observability with timing
    elapsed_ms = int((_time.monotonic() - t0) * 1000)
    emit_gate_event(project_root, result, duration_ms=elapsed_ms)

    # Emit build_complete on successful pre-push
    if result.passed and hook == GateHook.PRE_PUSH:
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
    registry: dict[str, list[CheckConfig]],
    config_cls: type[CheckConfig],
) -> dict[str, list[CheckConfig]]:
    """Clone check registry without mutating global constants."""
    clone: dict[str, list[CheckConfig]] = {}
    for stack, checks in registry.items():
        clone[stack] = [
            config_cls(
                name=check.name,
                cmd=list(check.cmd),
                required=check.required,
                timeout=check.timeout,
            )
            for check in checks
        ]
    return clone


def _override_test_cmd(
    registry: dict[str, list[CheckConfig]],
    scope: TestScope,
    config_cls: type[CheckConfig],
) -> dict[str, list[CheckConfig]]:
    """Return cloned registry with python stack-tests command selectively overridden."""
    clone = _clone_registry(registry, config_cls)
    python_checks = clone.get("python", [])
    updated: list[CheckConfig] = []

    for check in python_checks:
        if check.name != "stack-tests":
            updated.append(check)
            continue

        if scope.mode == "selective" and not scope.selected_tests:
            continue

        if scope.mode == "selective":
            updated.append(
                config_cls(
                    name=check.name,
                    cmd=[*check.cmd, *scope.selected_tests],
                    required=check.required,
                    timeout=check.timeout,
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
