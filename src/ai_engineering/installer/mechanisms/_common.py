"""Shared helpers for installer mechanism modules."""

from __future__ import annotations

from typing import Any

from ai_engineering.installer.results import InstallResult


def install_result_from_proc(
    proc: Any,
    *,
    mechanism: str,
) -> InstallResult:
    """Build an :class:`InstallResult` from a subprocess-shaped object."""
    returncode = getattr(proc, "returncode", 0) or 0
    stderr_raw = getattr(proc, "stderr", "") or ""
    stderr = stderr_raw if isinstance(stderr_raw, str) else stderr_raw.decode(errors="replace")
    return InstallResult(
        failed=returncode != 0,
        stderr=stderr,
        mechanism=mechanism,
    )


def run_install(argv: list[str], *, mechanism: str) -> InstallResult:
    """Run an installer argv via the package-level `_safe_run` hook.

    Tests patch `ai_engineering.installer.mechanisms._safe_run`; resolve the
    callable dynamically from the package root so split modules preserve that
    long-standing patch surface.
    """
    from ai_engineering.installer import mechanisms as mechanisms_module

    proc = mechanisms_module._safe_run(argv)
    return install_result_from_proc(proc, mechanism=mechanism)
