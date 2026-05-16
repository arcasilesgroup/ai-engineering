"""Commit message validation and gate trailer injection."""

from __future__ import annotations

import re
from pathlib import Path

_GATE_TRAILER = "Ai-Eng-Gate: passed"

# Spec-122 Phase C: ``commit_conventional.rego`` is the canonical
# definition; this regex is the Python fallback used when OPA is not
# available on the host. Keep the two patterns in sync.
_CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|perf|refactor|style|docs|test|build|ci|chore|revert)"
    r"(\([^)]+\))?!?:\s+.+"
)


def _format_error(first_line: str) -> str:
    """Build the canonical "invalid commit format" error message."""
    valid_types = "feat, fix, perf, refactor, style, docs, test, build, ci, chore, revert"
    return (
        f"Invalid commit format: '{first_line}'. "
        f"Expected: type(scope): description. "
        f"Valid types: {valid_types}. "
        f"Example: feat(auth): add login validation"
    )


def validate_commit_message(msg: str) -> list[str]:
    """Validate a commit message against conventional commit format.

    Pure-Python fallback used when OPA is not on PATH or when callers
    want a quick check without a subprocess (tests, REPL).

    Returns:
        List of validation errors (empty if valid).
    """
    errors: list[str] = []

    if not msg:
        errors.append("Commit message is empty")
        return errors

    first_line = msg.splitlines()[0].strip()

    if not first_line:
        errors.append("First line is empty")
        return errors

    if len(first_line) > 100:
        errors.append(f"First line exceeds 100 characters ({len(first_line)} chars)")

    if not _CONVENTIONAL_RE.match(first_line):
        errors.append(_format_error(first_line))

    return errors


def validate_commit_message_opa(
    msg: str,
    *,
    project_root: Path,
) -> list[str]:
    """Validate via OPA ``data.commit_conventional.deny`` with regex fallback.

    Spec-122 Phase C T-3.11: the format check delegates to the OPA
    policy when the binary is on PATH. When OPA is unavailable we fall
    back to the in-process regex so installs in progress don't lose
    the gate. The length-cap check stays Python-side because the OPA
    policy is intentionally narrow (subject pattern only).
    """
    errors: list[str] = []

    if not msg:
        errors.append("Commit message is empty")
        return errors

    first_line = msg.splitlines()[0].strip()
    if not first_line:
        errors.append("First line is empty")
        return errors

    if len(first_line) > 100:
        errors.append(f"First line exceeds 100 characters ({len(first_line)} chars)")

    # Defer the OPA import to call-time so the module stays light when
    # callers only need the pure-Python `validate_commit_message`.
    from ai_engineering.governance import opa_runner
    from ai_engineering.policy.checks.opa_gate import evaluate_deny

    bundle_dir = project_root / opa_runner.DEFAULT_BUNDLE_PATH
    if not opa_runner.available() or not bundle_dir.is_dir():
        # OPA binary missing OR the policy bundle is not present at the
        # caller's project root — fall back to the in-process regex so
        # tests / out-of-tree contexts still validate. Prevents a noisy
        # "bundle not found" OpaError from masquerading as a real deny.
        if not _CONVENTIONAL_RE.match(first_line):
            errors.append(_format_error(first_line))
        return errors

    decision = evaluate_deny(
        project_root=project_root,
        policy="commit_conventional",
        input_data={"subject": first_line},
        component="gate-engine",
        source="commit-msg",
    )
    if not decision.passed:
        # OPA fired a deny -- surface its message verbatim (it's the
        # canonical text "commit subject must follow conventional format")
        # but also include the non-compliant subject for the user.
        errors.append(_format_error(first_line))
    return errors


def inject_gate_trailer(commit_msg_file: Path) -> None:
    """Append gate verification trailer if not already present."""
    try:
        content = commit_msg_file.read_text(encoding="utf-8")
    except OSError:
        return

    if _GATE_TRAILER in content:
        return

    updated = content.rstrip() + f"\n\n{_GATE_TRAILER}\n"
    try:
        commit_msg_file.write_text(updated, encoding="utf-8")
    except OSError:
        return
