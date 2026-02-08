"""Tooling readiness detectors used by `ai doctor`."""

from __future__ import annotations

import shutil
import subprocess


def _has_command(command: str) -> bool:
    return shutil.which(command) is not None


def _command_ok(args: list[str]) -> bool:
    try:
        proc = subprocess.run(args, check=False, capture_output=True, text=True)
    except OSError:
        return False
    return proc.returncode == 0


def detect_gh() -> dict[str, bool]:
    """Detect gh install/config/auth status."""
    installed = _has_command("gh")
    if not installed:
        return {"installed": False, "configured": False, "authenticated": False}
    configured = _command_ok(["gh", "--version"])
    authenticated = _command_ok(["gh", "auth", "status"])
    return {"installed": installed, "configured": configured, "authenticated": authenticated}


def detect_az() -> dict[str, bool]:
    """Detect az install/config/auth status."""
    installed = _has_command("az")
    if not installed:
        return {
            "installed": False,
            "configured": False,
            "authenticated": False,
            "requiredNow": False,
        }
    configured = _command_ok(["az", "version"])
    authenticated = _command_ok(["az", "account", "show"])
    return {
        "installed": installed,
        "configured": configured,
        "authenticated": authenticated,
        "requiredNow": False,
    }


def detect_python_tools() -> dict[str, dict[str, bool]]:
    """Detect Python tooling baseline readiness."""
    return {
        "uv": {"ready": _has_command("uv")},
        "ruff": {"ready": _has_command("ruff")},
        "ty": {"ready": _has_command("ty")},
        "pipAudit": {"ready": _has_command("pip-audit")},
    }
