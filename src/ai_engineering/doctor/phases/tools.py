"""Doctor phase: tool availability and venv health validation.

Checks:
- tools-required: ruff, ty, gitleaks, semgrep, pip-audit on PATH.
- tools-vcs: gh/az based on VCS provider in install state.
- venv-health: .venv/pyvenv.cfg exists and home path is valid.
- venv-python: Python version in venv matches .python-version.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ai_engineering.detector.readiness import is_tool_available
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.doctor.remediation import RemediationEngine, RemediationStatus
from ai_engineering.installer.tools import can_auto_install_tool, ensure_tool, manual_install_step

_REQUIRED_TOOLS: list[str] = ["ruff", "ty", "gitleaks", "semgrep", "pip-audit"]

_VCS_TOOL_MAP: dict[str, str] = {
    "github": "gh",
    "azure_devops": "az",
}


def _check_tools_required(ctx: DoctorContext) -> CheckResult:
    """Check that all required tools are available on PATH."""
    missing: list[str] = []
    for tool in _REQUIRED_TOOLS:
        if not is_tool_available(tool):
            missing.append(tool)

    if missing:
        return CheckResult(
            name="tools-required",
            status=CheckStatus.WARN,
            message=f"missing tools: {', '.join(missing)}",
            fixable=True,
        )

    return CheckResult(
        name="tools-required",
        status=CheckStatus.OK,
        message="all required tools available",
    )


def _check_tools_vcs(ctx: DoctorContext) -> CheckResult:
    """Check VCS-specific tool based on install state provider."""
    if ctx.install_state is None:
        return CheckResult(
            name="tools-vcs",
            status=CheckStatus.OK,
            message="no install state; skipping VCS tool check",
        )

    vcs_provider = ctx.install_state.vcs_provider
    if vcs_provider is None:
        return CheckResult(
            name="tools-vcs",
            status=CheckStatus.OK,
            message="no VCS provider configured; skipping",
        )

    tool = _VCS_TOOL_MAP.get(vcs_provider)
    if tool is None:
        return CheckResult(
            name="tools-vcs",
            status=CheckStatus.OK,
            message=f"unknown VCS provider '{vcs_provider}'; skipping",
        )

    if not is_tool_available(tool):
        return CheckResult(
            name="tools-vcs",
            status=CheckStatus.WARN,
            message=f"VCS tool '{tool}' not found (provider: {vcs_provider})",
        )

    return CheckResult(
        name="tools-vcs",
        status=CheckStatus.OK,
        message=f"VCS tool '{tool}' available",
    )


def _parse_pyvenv_cfg(cfg_path: Path) -> dict[str, str]:
    """Parse a pyvenv.cfg file into key-value pairs."""
    result: dict[str, str] = {}
    if not cfg_path.is_file():
        return result
    try:
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if "=" in line:
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
    except OSError:
        pass
    return result


def _check_venv_health(ctx: DoctorContext) -> CheckResult:
    """Check that .venv/pyvenv.cfg exists and home path is valid."""
    cfg_path = ctx.target / ".venv" / "pyvenv.cfg"
    if not cfg_path.is_file():
        return CheckResult(
            name="venv-health",
            status=CheckStatus.WARN,
            message="no .venv/pyvenv.cfg found; virtual environment may not exist",
            fixable=True,
        )

    cfg = _parse_pyvenv_cfg(cfg_path)
    home = cfg.get("home")
    if home is None:
        return CheckResult(
            name="venv-health",
            status=CheckStatus.FAIL,
            message="pyvenv.cfg missing 'home' key",
            fixable=True,
        )

    home_path = Path(home)
    if not home_path.is_dir():
        return CheckResult(
            name="venv-health",
            status=CheckStatus.FAIL,
            message=f"pyvenv.cfg home path does not exist: {home}",
            fixable=True,
        )

    return CheckResult(
        name="venv-health",
        status=CheckStatus.OK,
        message="virtual environment healthy",
    )


def _check_venv_python(ctx: DoctorContext) -> CheckResult:
    """Check that venv Python matches .python-version if present."""
    pyver_path = ctx.target / ".python-version"
    if not pyver_path.is_file():
        return CheckResult(
            name="venv-python",
            status=CheckStatus.OK,
            message="no .python-version file; skipping version check",
        )

    try:
        expected = pyver_path.read_text(encoding="utf-8").strip()
    except OSError:
        return CheckResult(
            name="venv-python",
            status=CheckStatus.WARN,
            message="could not read .python-version",
        )

    cfg_path = ctx.target / ".venv" / "pyvenv.cfg"
    cfg = _parse_pyvenv_cfg(cfg_path)
    version = cfg.get("version")

    if version is None:
        return CheckResult(
            name="venv-python",
            status=CheckStatus.WARN,
            message="pyvenv.cfg missing 'version' key; cannot verify Python version",
        )

    if not version.startswith(expected):
        return CheckResult(
            name="venv-python",
            status=CheckStatus.WARN,
            message=f"venv Python {version} does not match .python-version {expected}",
        )

    return CheckResult(
        name="venv-python",
        status=CheckStatus.OK,
        message=f"venv Python {version} matches .python-version",
    )


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all tools phase checks."""
    return [
        _check_tools_required(ctx),
        _check_tools_vcs(ctx),
        _check_venv_health(ctx),
        _check_venv_python(ctx),
    ]


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Attempt to fix failed tools checks.

    Fixable:
    - ``tools-required``: try_install() for each missing tool.
    - ``venv-health``: recreate venv via ``uv venv``.

    Not fixable: ``tools-vcs``, ``venv-python``.
    """
    results: list[CheckResult] = []

    for cr in failed:
        if cr.name == "tools-required":
            results.append(_fix_tools_required(ctx, cr, dry_run=dry_run))
        elif cr.name == "venv-health":
            results.append(_fix_venv_health(ctx, cr, dry_run=dry_run))
        else:
            results.append(cr)

    return results


def _fix_tools_required(
    ctx: DoctorContext,
    cr: CheckResult,
    *,
    dry_run: bool = False,
) -> CheckResult:
    """Try to install missing required tools through the shared remediation engine."""
    missing = [tool for tool in _REQUIRED_TOOLS if not is_tool_available(tool)]

    if dry_run:
        auto_installable = [tool for tool in missing if can_auto_install_tool(tool)]
        manual_only = [tool for tool in missing if tool not in auto_installable]
        if manual_only:
            message = "would attempt auto-install for: "
            message += ", ".join(auto_installable) if auto_installable else "none"
            message += f"; manual follow-up required: {', '.join(manual_only)}"
            return CheckResult(
                name=cr.name,
                status=CheckStatus.WARN,
                message=message,
                fixable=True,
            )
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FIXED,
            message=(
                f"would attempt to install missing tools: {', '.join(missing)}"
                if missing
                else "all tools now available"
            ),
        )

    engine = RemediationEngine(
        tool_capability=can_auto_install_tool,
        tool_installer=lambda tool: ensure_tool(tool, allow_install=True).available,
        tool_manual_step=manual_install_step,
    )
    remediation = engine.remediate_missing_tools(missing, source="doctor.tools-required")

    if remediation.status == RemediationStatus.REPAIRED:
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FIXED,
            message=(
                f"installed: {', '.join(remediation.repaired_items)}"
                if remediation.repaired_items
                else "all tools now available"
            ),
        )

    if remediation.status in (RemediationStatus.MANUAL, RemediationStatus.BLOCKED):
        parts: list[str] = []
        if remediation.repaired_items:
            parts.append(f"installed: {', '.join(remediation.repaired_items)}")
        if remediation.remaining_items:
            parts.append(f"manual follow-up required: {', '.join(remediation.remaining_items)}")
        if remediation.detail:
            parts.append(remediation.detail)
        return CheckResult(
            name=cr.name,
            status=CheckStatus.WARN,
            message="; ".join(parts) if parts else remediation.summary,
            fixable=True,
        )

    return CheckResult(
        name=cr.name,
        status=CheckStatus.WARN,
        message=remediation.summary,
        fixable=True,
    )


def _fix_venv_health(
    ctx: DoctorContext,
    cr: CheckResult,
    *,
    dry_run: bool = False,
) -> CheckResult:
    """Recreate the virtual environment using uv."""
    if dry_run:
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FIXED,
            message="would recreate .venv via uv venv",
        )

    # Build uv venv command
    cmd: list[str] = ["uv", "venv", ".venv"]
    pyver_path = ctx.target / ".python-version"
    if pyver_path.is_file():
        try:
            version = pyver_path.read_text(encoding="utf-8").strip()
            if version:
                cmd = ["uv", "venv", "--python", version, ".venv"]
        except OSError:
            pass

    try:
        subprocess.run(
            cmd,
            cwd=str(ctx.target),
            check=True,
            capture_output=True,
            timeout=120,
        )
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FIXED,
            message="recreated .venv via uv venv",
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            name=cr.name,
            status=CheckStatus.FAIL,
            message=f"failed to recreate .venv: {exc}",
            fixable=True,
        )
