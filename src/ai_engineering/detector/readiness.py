"""Tool readiness detection and auto-remediation.

Detects availability of:
- Python tools: ruff, ty, gitleaks, semgrep, pip-audit.
- VCS providers: gh (GitHub CLI), az (Azure CLI).
- Package managers: uv, pip.

Provides auto-remediation for missing Python tools via ``uv pip install``
or ``pip install`` fallback.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass
class ToolInfo:
    """Information about a single tool's readiness."""

    name: str
    available: bool
    version: str | None = None
    path: str | None = None


@dataclass
class ReadinessReport:
    """Aggregated report of all tool readiness checks."""

    tools: list[ToolInfo] = field(default_factory=list)

    @property
    def all_ready(self) -> bool:
        """True if all required tools are available."""
        return all(t.available for t in self.tools if t.name not in _OPTIONAL_TOOLS)

    @property
    def missing(self) -> list[str]:
        """Names of required tools that are not available."""
        return [t.name for t in self.tools if not t.available and t.name not in _OPTIONAL_TOOLS]


# Tools that are checked but not strictly required.
_OPTIONAL_TOOLS: frozenset[str] = frozenset({"gh", "az"})

# Python tools that can be installed via pip/uv.
_INSTALLABLE_TOOLS: dict[str, str] = {
    "ruff": "ruff",
    "ty": "ty",
    "pip-audit": "pip-audit",
}

# Tools that require OS-level installation.
_SYSTEM_TOOLS: list[str] = ["gitleaks", "semgrep"]

# Version flag per tool (some use --version, others version).
_VERSION_FLAGS: dict[str, list[str]] = {
    "ruff": ["ruff", "--version"],
    "ty": ["ty", "--version"],
    "gitleaks": ["gitleaks", "version"],
    "semgrep": ["semgrep", "--version"],
    "pip-audit": ["pip-audit", "--version"],
    "gh": ["gh", "--version"],
    "az": ["az", "--version"],
    "uv": ["uv", "--version"],
    "pip": ["pip", "--version"],
}


def check_tool(name: str) -> ToolInfo:
    """Check if a single tool is available and get its version.

    Args:
        name: Tool name to check.

    Returns:
        ToolInfo with availability and optional version string.
    """
    path = shutil.which(name)
    if path is None:
        return ToolInfo(name=name, available=False)

    version = _get_version(name)
    return ToolInfo(name=name, available=True, version=version, path=path)


def check_all_tools() -> ReadinessReport:
    """Check readiness of all required and optional tools.

    Returns:
        ReadinessReport with status of each tool.
    """
    report = ReadinessReport()
    tool_names = [
        "uv",
        "ruff",
        "ty",
        "gitleaks",
        "semgrep",
        "pip-audit",
        "gh",
        "az",
    ]
    for name in tool_names:
        report.tools.append(check_tool(name))
    return report


def remediate_missing_tools(
    report: ReadinessReport,
) -> list[str]:
    """Attempt to install missing Python tools.

    Only attempts installation for tools in ``_INSTALLABLE_TOOLS``.
    Uses ``uv pip install`` if uv is available, otherwise ``pip install``.

    Args:
        report: Readiness report with current tool status.

    Returns:
        List of tool names that were successfully installed.
    """
    missing = [t.name for t in report.tools if not t.available and t.name in _INSTALLABLE_TOOLS]

    if not missing:
        return []

    installed: list[str] = []
    for tool_name in missing:
        package_name = _INSTALLABLE_TOOLS[tool_name]
        if _try_install(package_name):
            installed.append(tool_name)

    return installed


def _get_version(name: str) -> str | None:
    """Get the version string for a tool.

    Args:
        name: Tool name.

    Returns:
        Version string or None if unavailable.
    """
    cmd = _VERSION_FLAGS.get(name)
    if cmd is None:
        return None

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip() or result.stderr.strip()
        # Return first non-empty line
        for line in output.splitlines():
            line = line.strip()
            if line:
                return line
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _try_install(package: str) -> bool:
    """Attempt to install a Python package via uv or pip.

    Args:
        package: Package name to install.

    Returns:
        True if installation succeeded.
    """
    # Try uv first
    if shutil.which("uv"):
        try:
            subprocess.run(
                ["uv", "pip", "install", package],
                check=True,
                capture_output=True,
                timeout=120,
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # Fall back to pip
    try:
        subprocess.run(
            ["pip", "install", package],
            check=True,
            capture_output=True,
            timeout=120,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return False
