"""Doctor runtime check: branch-policy -- warns when on a protected branch.

A simple guard that alerts the developer if they are currently on ``main``
or ``master``. This is informational only (WARN, not FAIL) because some
workflows legitimately operate on protected branches.

spec-113 G-9 / D-113-12: a "first install grace period" suppresses the
WARN for the first 5 minutes after ``install_state.installed_at``. The
freshly-installed-repo case is the typical false-positive -- the
operator just ran ``ai-eng install`` on the existing main checkout and
HAS NOT had a chance to create a feature branch yet. The grace window
is intentionally short so subsequent doctor runs do warn as expected.

Robustness notes:
- Detects git presence via ``git rev-parse --is-inside-work-tree`` so that
  worktrees (``.git`` is a file, not a directory) and submodules are
  recognised correctly.
- Reads the current branch via ``git symbolic-ref --short HEAD`` which
  succeeds on a freshly-init'd repo with no commits (whereas
  ``git rev-parse --abbrev-ref HEAD`` exits non-zero on an unborn HEAD).
- Detached HEAD is reported as OK with a note rather than as a warning;
  it's a legitimate workflow state (e.g., during a rebase).
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext

_PROTECTED_BRANCHES = frozenset({"main", "master"})

# spec-113 D-113-12: grace window during which the protected-branch warning
# is suppressed. 5 minutes is short enough that the warning fires on
# subsequent doctor invocations without being noisy on the install run.
_FIRST_INSTALL_GRACE_PERIOD = timedelta(minutes=5)


def _run_git(args: list[str], cwd) -> subprocess.CompletedProcess[str] | None:
    """Run a git command, returning ``None`` if git itself is unavailable."""
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return None


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Check whether the working tree is on a protected branch."""
    inside = _run_git(["rev-parse", "--is-inside-work-tree"], ctx.target)
    if inside is None:
        return [
            CheckResult(
                name="branch-policy",
                status=CheckStatus.WARN,
                message="git binary not available",
            )
        ]
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return [
            CheckResult(
                name="branch-policy",
                status=CheckStatus.WARN,
                message="not a git repository",
            )
        ]

    # ``symbolic-ref`` succeeds on a freshly-init'd repo (unborn HEAD)
    # whereas ``rev-parse --abbrev-ref HEAD`` would fail with
    # "ambiguous argument 'HEAD': unknown revision".
    head = _run_git(["symbolic-ref", "--short", "HEAD"], ctx.target)
    if head is None or head.returncode != 0:
        # Detached HEAD (rebase, bisect, etc.) — legitimate workflow state.
        return [
            CheckResult(
                name="branch-policy",
                status=CheckStatus.OK,
                message="detached HEAD (rebase / bisect / tagged checkout)",
            )
        ]

    branch = head.stdout.strip()
    if branch in _PROTECTED_BRANCHES:
        if _within_first_install_grace_period(ctx):
            return [
                CheckResult(
                    name="branch-policy",
                    status=CheckStatus.OK,
                    message=(
                        f"on protected branch '{branch}' during first-install "
                        "grace period; create a feature branch before committing"
                    ),
                )
            ]
        return [
            CheckResult(
                name="branch-policy",
                status=CheckStatus.WARN,
                message=f"on protected branch '{branch}'; create a feature branch",
            )
        ]

    return [
        CheckResult(
            name="branch-policy",
            status=CheckStatus.OK,
            message=f"on branch '{branch}'",
        )
    ]


def _within_first_install_grace_period(ctx: DoctorContext) -> bool:
    """Return True when ``ctx.install_state.installed_at`` is within the grace window.

    spec-113 D-113-12: 5 minutes from install timestamp. Beyond that the
    pre-spec-113 warning is restored. When ``install_state`` is missing
    or ``installed_at`` is None, returns False -- no install state means
    no grace period (the fresh-install signal is required).
    """
    state = getattr(ctx, "install_state", None)
    if state is None:
        return False
    installed_at = getattr(state, "installed_at", None)
    if installed_at is None:
        return False
    if installed_at.tzinfo is None:
        installed_at = installed_at.replace(tzinfo=UTC)
    return datetime.now(tz=UTC) - installed_at <= _FIRST_INSTALL_GRACE_PERIOD
