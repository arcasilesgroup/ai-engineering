"""Venv health diagnostic check."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport


def check_venv_health(target: Path, report: DoctorReport, *, fix: bool) -> None:
    """Check that the project venv exists and points to a valid Python path."""
    venv_dir = target / ".venv"
    cfg_path = venv_dir / "pyvenv.cfg"

    if not venv_dir.is_dir():
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="No .venv directory found",
            )
        )
        return

    if not cfg_path.is_file():
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="No .venv/pyvenv.cfg found",
            )
        )
        return

    home_path = parse_pyvenv_home(cfg_path)
    if home_path is None:
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.WARN,
                message="Could not parse home from pyvenv.cfg",
            )
        )
        return

    if Path(home_path).is_dir():
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.OK,
                message=f"Venv home valid: {home_path}",
            )
        )
        return

    if fix:
        success = recreate_venv(target)
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.FIXED if success else CheckStatus.FAIL,
                message="Venv recreated" if success else "Venv recreation failed",
            )
        )
    else:
        report.checks.append(
            CheckResult(
                name="venv-health",
                status=CheckStatus.FAIL,
                message=(
                    f"Stale venv — home path does not exist: {home_path}. "
                    "Run 'ai-eng doctor --fix-tools' to recreate."
                ),
            )
        )


def parse_pyvenv_home(cfg_path: Path) -> str | None:
    """Extract the ``home`` value from a pyvenv.cfg file."""
    try:
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("home"):
                _, _, value = line.partition("=")
                return value.strip()
    except OSError:
        pass
    return None


def recreate_venv(target: Path) -> bool:
    """Recreate the project venv using ``uv venv``."""
    cmd: list[str] = ["uv", "venv"]

    pin_file = target / ".python-version"
    if pin_file.is_file():
        version = pin_file.read_text(encoding="utf-8").strip()
        if version:
            cmd.extend(["--python", version])

    cmd.append(str(target / ".venv"))

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            timeout=60,
            cwd=target,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False
