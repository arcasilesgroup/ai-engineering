"""Convergence checks for the Ralph Loop (spec-120 R-2).

Stdlib-only — hooks must run before any ``pip install``. The Ralph Loop
in ``runtime-stop.py`` calls :func:`check_convergence` to decide whether
the working tree has reached a terminal state ("tests pass + lint
clean") or whether the model should be reinjected with another loop
iteration.

Design choices:

* **Fail-open on missing tools.** A repository without ``ruff`` is not
  failing convergence — there is simply nothing to check. Tools are
  probed via :func:`shutil.which`; missing tools are skipped silently.

* **Fail-open on subprocess errors.** ``FileNotFoundError`` (binary
  vanished between probe and call) and ``TimeoutExpired`` are recorded
  as failures so the loop sees them, but a Python interpreter that
  cannot launch *anything* (e.g. inside a stripped sandbox) returns an
  empty failure list — the caller in ``runtime-stop.py`` treats that as
  "converged" so we never trap the user in a fake-failure loop.

* **Fast vs full.** Pre-commit-style convergence (``fast=True``) caps
  the budget at ~5s by skipping the full pytest run and using
  ``--collect-only`` to verify the test suite is at least importable.
  ``fast=False`` runs ``pytest -x`` for genuine convergence at a ~60s
  budget; reserved for periodic full sweeps, not the Stop hot path.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# Per-tool subprocess timeouts (seconds). Generous enough for cold
# imports on a slow disk; small enough to keep ``fast=True`` under the
# documented ~5s budget even when both checks run.
_TIMEOUT_RUFF_S = 5
_TIMEOUT_PYTEST_COLLECT_S = 10
_TIMEOUT_PYTEST_RUN_S = 60
_TIMEOUT_GIT_DIFF_S = 3


@dataclass(frozen=True)
class ConvergenceResult:
    """Outcome of one convergence sweep.

    ``failures`` is a list of human-readable strings (e.g.
    ``"ruff check: 3 issues"`` or ``"pytest collect: import error"``).
    Empty list ⇔ ``converged is True``. ``duration_ms`` is the wall
    time spent inside :func:`check_convergence` so the caller can log
    over-budget sweeps.
    """

    converged: bool
    failures: list[str] = field(default_factory=list)
    duration_ms: int = 0


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: int,
) -> tuple[int | None, str, str]:
    """Run ``cmd`` and return ``(returncode, stdout, stderr)``.

    A returncode of ``None`` means the subprocess could not be launched
    or timed out — the caller decides whether that counts as a failure
    or a silent skip. ``stderr`` carries the diagnostic for
    ``TimeoutExpired`` so the loop can surface it.
    """
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return None, "", f"binary not found: {exc}"
    except subprocess.TimeoutExpired:
        return None, "", f"timeout after {timeout}s"
    except OSError as exc:
        return None, "", f"os error: {exc}"
    return proc.returncode, proc.stdout or "", proc.stderr or ""


def _short_reason(stderr: str, stdout: str, *, default: str) -> str:
    """First non-empty line of stderr (then stdout) for a failure summary."""
    for stream in (stderr, stdout):
        for line in stream.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped[:200]
    return default


# spec-158 D-158-11: Python packaging markers. Convergence is multi-stack;
# the Python lint+test tools run ONLY when the project IS a Python project.
# A TypeScript-only repo (no marker) must run no Python verifier — otherwise a
# missing test runner reports as a false convergence failure and blocks the
# Stop hook. Marker detection is stdlib-only to honour the package-free hook
# contract.
_PYTHON_PROJECT_MARKERS = ("pyproject.toml", "setup.py")


def _is_python_project(project_root: Path) -> bool:
    """True iff a Python packaging marker file exists at the project root."""
    return any((project_root / marker).is_file() for marker in _PYTHON_PROJECT_MARKERS)


def _runner_absent(text: str) -> bool:
    """True iff *text* shows the test runner module is not installed (fail-open)."""
    return "No module named pytest" in text or "No module named 'pytest'" in text


def _check_ruff(project_root: Path) -> str | None:
    """Run ``ruff check --quiet --no-fix``; return failure summary or None.

    Missing binary, or a non-Python project, is not a failure (returns None).
    """
    if not _is_python_project(project_root):
        return None
    if shutil.which("ruff") is None:
        return None
    rc, stdout, stderr = _run(
        ["ruff", "check", "--quiet", "--no-fix", "."],
        cwd=project_root,
        timeout=_TIMEOUT_RUFF_S,
    )
    if rc is None:
        # Probed via shutil.which then vanished, or hit the timeout.
        return f"ruff check: {stderr.strip() or 'failed to run'}"
    if rc == 0:
        return None
    summary = _short_reason(stderr, stdout, default=f"exit {rc}")
    return f"ruff check: {summary}"


def _check_pytest_collect(project_root: Path) -> str | None:
    """``pytest --collect-only`` to verify the suite imports.

    spec-158 D-158-10/11: runs ONLY in a Python project, under
    ``sys.executable`` (the resolved hook interpreter — NOT a bare PATH
    ``python3`` that may belong to another environment), and fails open
    when the test runner is not installed (a missing runner is "nothing
    to verify", not a convergence failure).
    """
    if not _is_python_project(project_root):
        return None
    rc, stdout, stderr = _run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=project_root,
        timeout=_TIMEOUT_PYTEST_COLLECT_S,
    )
    if rc is None:
        return f"pytest collect: {stderr.strip() or 'failed to run'}"
    # pytest exit codes: 0 = passed, 5 = no tests collected (treat as
    # "nothing to verify" — fail-open). A missing runner module is also
    # fail-open. Anything else means collection itself blew up.
    if rc in (0, 5) or _runner_absent(stderr) or _runner_absent(stdout):
        return None
    summary = _short_reason(stderr, stdout, default=f"exit {rc}")
    return f"pytest collect: {summary}"


def _check_pytest_run(project_root: Path) -> str | None:
    """``pytest -x --tb=no -q`` — full convergence (slow); Python projects only."""
    if not _is_python_project(project_root):
        return None
    rc, stdout, stderr = _run(
        [sys.executable, "-m", "pytest", "-x", "--tb=no", "-q"],
        cwd=project_root,
        timeout=_TIMEOUT_PYTEST_RUN_S,
    )
    if rc is None:
        return f"pytest run: {stderr.strip() or 'failed to run'}"
    if rc in (0, 5) or _runner_absent(stderr) or _runner_absent(stdout):
        return None
    summary = _short_reason(stderr, stdout, default=f"exit {rc}")
    return f"pytest run: {summary}"


def _check_ruff_format(project_root: Path) -> str | None:
    """``ruff format --check`` — full mode only, Python projects only, optional."""
    if not _is_python_project(project_root):
        return None
    if shutil.which("ruff") is None:
        return None
    rc, stdout, stderr = _run(
        ["ruff", "format", "--check", "."],
        cwd=project_root,
        timeout=_TIMEOUT_RUFF_S,
    )
    if rc is None:
        return f"ruff format: {stderr.strip() or 'failed to run'}"
    if rc == 0:
        return None
    summary = _short_reason(stderr, stdout, default=f"exit {rc}")
    return f"ruff format: {summary}"


def _git_diff_quiet(project_root: Path) -> None:
    """Informational ``git diff --quiet HEAD --``.

    Documented in the spec but **not** treated as a failure — a dirty
    working tree is the *expected* state during Ralph Loop iteration.
    Kept for parity with the public contract (``fast=True`` does run
    it) but no return value is consumed by the caller.
    """
    if shutil.which("git") is None:
        return
    _run(
        ["git", "diff", "--quiet", "HEAD", "--"],
        cwd=project_root,
        timeout=_TIMEOUT_GIT_DIFF_S,
    )


def check_convergence(project_root: Path, *, fast: bool = True) -> ConvergenceResult:
    """Run a convergence sweep over ``project_root``.

    ``fast=True`` (default) — pre-commit-style sweep, ~5s budget:
        * ``git diff --quiet HEAD --`` (informational)
        * ``ruff check --quiet --no-fix`` (if installed)
        * ``python -m pytest --collect-only -q``

    ``fast=False`` — full sweep, ~60s budget:
        Everything in ``fast=True`` plus:
        * ``python -m pytest -x --tb=no -q``
        * ``ruff format --check`` (if installed)

    Tools that cannot be located via :func:`shutil.which` are skipped
    silently and never appear in ``failures``. A tool that is present
    but blows up (timeout, OSError, non-zero exit) appears as one
    string in ``failures`` summarising the problem.
    """
    start = time.perf_counter()
    failures: list[str] = []

    # git diff is informational — never appended to failures.
    _git_diff_quiet(project_root)

    if (msg := _check_ruff(project_root)) is not None:
        failures.append(msg)

    if (msg := _check_pytest_collect(project_root)) is not None:
        failures.append(msg)

    if not fast:
        if (msg := _check_pytest_run(project_root)) is not None:
            failures.append(msg)
        if (msg := _check_ruff_format(project_root)) is not None:
            failures.append(msg)

    duration_ms = max(0, round((time.perf_counter() - start) * 1000))
    return ConvergenceResult(
        converged=not failures,
        failures=failures,
        duration_ms=duration_ms,
    )
