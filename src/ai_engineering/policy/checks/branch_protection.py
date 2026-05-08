"""Branch protection, version deprecation, and hook integrity checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ai_engineering.git.operations import PROTECTED_BRANCHES, current_branch
from ai_engineering.hooks.manager import verify_hooks
from ai_engineering.policy.gates import GateCheckResult, GateResult


def check_branch_protection(project_root: Path, result: GateResult) -> None:
    """Block direct commits to protected branches.

    Spec-122 Phase C T-3.12: when OPA is on PATH the verdict comes from
    ``data.branch_protection.deny`` so the canonical rule lives in the
    .rego file. The Python fallback uses the original
    ``branch in PROTECTED_BRANCHES`` check for hosts without OPA.
    """
    branch = current_branch(project_root)

    from ai_engineering.governance import opa_runner

    bundle_dir = project_root / opa_runner.DEFAULT_BUNDLE_PATH
    if branch and opa_runner.available() and bundle_dir.is_dir():
        from ai_engineering.policy.checks.opa_gate import evaluate_deny

        decision = evaluate_deny(
            project_root=project_root,
            policy="branch_protection",
            input_data={"branch": branch, "action": "push"},
            component="gate-engine",
            source="pre-commit",
        )
        if not decision.passed:
            result.checks.append(
                GateCheckResult(
                    name="branch-protection",
                    passed=False,
                    output=f"Direct commits to '{branch}' are blocked. Use a feature branch.",
                )
            )
            return
        result.checks.append(
            GateCheckResult(
                name="branch-protection",
                passed=True,
                output=f"On branch: {branch}",
            )
        )
        return

    if branch and branch in PROTECTED_BRANCHES:
        result.checks.append(
            GateCheckResult(
                name="branch-protection",
                passed=False,
                output=f"Direct commits to '{branch}' are blocked. Use a feature branch.",
            )
        )
    else:
        result.checks.append(
            GateCheckResult(
                name="branch-protection",
                passed=True,
                output=f"On branch: {branch or 'unknown'}",
            )
        )


def check_version_deprecation(result: GateResult) -> None:
    """Block gate execution if the installed version is deprecated or EOL."""
    from ai_engineering import __version__
    from ai_engineering.version.checker import check_version

    check = check_version(__version__)

    if check.is_deprecated or check.is_eol:
        status_label = "deprecated" if check.is_deprecated else "end-of-life"
        result.checks.append(
            GateCheckResult(
                name="version-deprecation",
                passed=False,
                output=(
                    f"ai-engineering {__version__} is {status_label}. "
                    f"{check.message}. "
                    f"Run 'ai-eng update' to upgrade."
                ),
            )
        )
    else:
        result.checks.append(
            GateCheckResult(
                name="version-deprecation",
                passed=True,
                output=f"Version lifecycle: {check.message}",
            )
        )


def check_hook_integrity(project_root: Path, result: GateResult) -> None:
    """Verify managed hooks are intact (marker + optional hash check)."""
    hooks_dir = project_root / ".git" / "hooks"
    if not hooks_dir.is_dir():
        result.checks.append(
            GateCheckResult(
                name="hook-integrity",
                passed=True,
                output="No .git/hooks directory — skipped",
            )
        )
        return

    status = verify_hooks(project_root)
    failing = [hook for hook, ok in status.items() if not ok and (hooks_dir / hook).exists()]
    if failing:
        result.checks.append(
            GateCheckResult(
                name="hook-integrity",
                passed=False,
                output=(
                    "Hook integrity check failed for: "
                    + ", ".join(sorted(failing))
                    + ". Reinstall hooks with 'ai-eng doctor --fix --phase hooks'."
                ),
            )
        )
        return

    result.checks.append(
        GateCheckResult(
            name="hook-integrity",
            passed=True,
            output="Hook integrity verified",
        )
    )


# spec-105 D-105-03 + OQ-7: pre-push target ref check.
#
# Per spec-105 Q3 / OQ-7, the pre-push hook must inspect the target ref to
# detect direct pushes to a protected branch from a feature branch. The
# canonical POSIX path is to read the four-token line(s) from stdin in the
# documented git-hook format ``"<local_ref> <local_sha> <remote_ref>
# <remote_sha>"``. When stdin is a TTY (manual invocation) or empty (some
# Windows shells), the dispatcher falls back to ``git rev-parse --abbrev-ref
# @{u}`` to read the upstream tracking branch.


def _parse_push_stdin_target(text: str) -> str | None:
    """Return the first ``remote_ref`` from a pre-push stdin payload.

    The git pre-push protocol emits one line per ref being pushed in the
    format ``"<local_ref> <local_sha> <remote_ref> <remote_sha>"``. We pick
    the first valid line; multi-ref pushes that span both protected and
    unprotected refs escalate on the first protected match.
    """
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            remote_ref = parts[2].strip()
            if remote_ref:
                return remote_ref
    return None


def _upstream_branch_or_none(project_root: Path) -> str | None:
    """Return the upstream tracking branch via ``git rev-parse --abbrev-ref``.

    Used as the fallback when stdin is a TTY (manual invocation) or empty.
    Returns ``None`` on any subprocess error -- the caller treats this as
    "no target known" and skips the escalation.
    """
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "@{u}"],
            cwd=project_root,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    return output.strip() or None


def check_push_target(
    project_root: Path,
    result: GateResult,
    *,
    stdin_text: str | None = None,
) -> None:
    """Inspect the pre-push target ref and append a result.

    Resolution order per spec-105 OQ-7:

    1. If ``stdin_text`` is provided (test injection) or ``sys.stdin`` is
       not a TTY and has data, parse the canonical
       ``"<local_ref> <local_sha> <remote_ref> <remote_sha>"`` lines and
       use the first ``remote_ref``.
    2. Otherwise, query ``git rev-parse --abbrev-ref @{u}`` for the
       upstream tracking branch.
    3. If neither yields a target, the check passes (no target = no
       escalation surface).

    The check fails (blocking) when the resolved target matches one of
    :data:`PROTECTED_BRANCHES`. The ``refs/heads/`` prefix is stripped
    before matching so both spellings work uniformly.
    """
    target_text: str | None = stdin_text
    if target_text is None:
        try:
            is_tty = bool(sys.stdin.isatty())
        except (AttributeError, ValueError):
            is_tty = True
        if not is_tty:
            try:
                target_text = sys.stdin.read()
            except (OSError, ValueError):
                target_text = ""

    target_ref: str | None = None
    if target_text:
        target_ref = _parse_push_stdin_target(target_text)
    if not target_ref:
        target_ref = _upstream_branch_or_none(project_root)

    if not target_ref:
        result.checks.append(
            GateCheckResult(
                name="push-target",
                passed=True,
                output="No push target ref detected -- skipped",
            )
        )
        return

    # Strip the canonical prefix so both ``refs/heads/main`` and ``main``
    # match the protected-branch frozenset.
    branch = target_ref.removeprefix("refs/heads/").removeprefix("origin/")

    # Spec-122 Phase C T-3.12: delegate to OPA when available; fall
    # through to the Python check otherwise.
    from ai_engineering.governance import opa_runner

    if opa_runner.available():
        from ai_engineering.policy.checks.opa_gate import evaluate_deny

        decision = evaluate_deny(
            project_root=project_root,
            policy="branch_protection",
            input_data={"branch": branch, "action": "push"},
            component="gate-engine",
            source="pre-push",
        )
        if not decision.passed:
            result.checks.append(
                GateCheckResult(
                    name="push-target",
                    passed=False,
                    output=(
                        f"Direct push to protected branch '{branch}' is blocked. "
                        "Open a pull request from a feature branch instead."
                    ),
                )
            )
            return
        result.checks.append(
            GateCheckResult(
                name="push-target",
                passed=True,
                output=f"Push target: {target_ref}",
            )
        )
        return

    if branch in PROTECTED_BRANCHES:
        result.checks.append(
            GateCheckResult(
                name="push-target",
                passed=False,
                output=(
                    f"Direct push to protected branch '{branch}' is blocked. "
                    "Open a pull request from a feature branch instead."
                ),
            )
        )
        return

    result.checks.append(
        GateCheckResult(
            name="push-target",
            passed=True,
            output=f"Push target: {target_ref}",
        )
    )
