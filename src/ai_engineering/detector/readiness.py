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
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.installer.tools import provider_required_tools
from ai_engineering.state.service import load_install_state


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

# Per-stack required tools (excluding common security tools).
_STACK_TOOLS: dict[str, list[str]] = {
    "python": ["uv", "ruff", "ty", "pip-audit"],
    "dotnet": ["dotnet"],
    "nextjs": ["node", "npm", "eslint", "prettier"],
}

# Common tools required regardless of stack.
_COMMON_TOOLS: list[str] = ["gitleaks", "semgrep"]

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
    "dotnet": ["dotnet", "--version"],
    "node": ["node", "--version"],
    "npm": ["npm", "--version"],
    "eslint": ["eslint", "--version"],
    "prettier": ["prettier", "--version"],
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


def check_tools_for_stacks(
    stacks: list[str],
    *,
    vcs_provider: str | None = None,
) -> ReadinessReport:
    """Check readiness of tools required by the given stacks.

    Always checks common security tools. Optionally checks VCS CLI tools:
    when ``vcs_provider`` is provided, only that provider's CLI is checked;
    when omitted, both GitHub and Azure DevOps CLIs are included for
    backward compatibility.

    Additionally checks stack-specific tools for each active stack.

    Args:
        stacks: List of active stack names (e.g., ["python"], ["python", "dotnet"]).
        vcs_provider: Optional active VCS provider used to scope VCS tooling.

    Returns:
        ReadinessReport with status of each relevant tool.
    """
    report = ReadinessReport()
    seen: set[str] = set()

    # Common tools always checked
    for name in _COMMON_TOOLS:
        if name not in seen:
            report.tools.append(check_tool(name))
            seen.add(name)

    # VCS tools (optional)
    if vcs_provider is None:
        vcs_tools = ("gh", "az")
    else:
        vcs_tools = tuple(provider_required_tools(vcs_provider))

    for name in vcs_tools:
        if name not in seen:
            report.tools.append(check_tool(name))
            seen.add(name)

    # Stack-specific tools
    for stack in stacks:
        for name in _STACK_TOOLS.get(stack, []):
            if name not in seen:
                report.tools.append(check_tool(name))
                seen.add(name)

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


def is_tool_available(name: str) -> bool:
    """Check if a tool is available on PATH.

    Public convenience wrapper around :func:`check_tool` for callers that only
    need a boolean answer.

    Args:
        name: Tool name to look up (e.g. ``"ruff"``).

    Returns:
        ``True`` if the tool is found on PATH.
    """
    return shutil.which(name) is not None


def try_install(package: str) -> bool:
    """Attempt to install a Python package via *uv* or *pip*.

    Tries ``uv pip install <package>`` first; falls back to
    ``pip install <package>``.

    Args:
        package: Package name to install.

    Returns:
        ``True`` if installation succeeded.
    """
    return _try_install(package)


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


def check_operational_readiness(project_root: Path) -> ReadinessReport:
    """Check auth/pipeline/policy readiness from config and install state."""
    report = ReadinessReport()
    state_dir = project_root / ".ai-engineering" / "state"
    state_path = state_dir / "install-state.json"
    if not state_path.exists():
        return report

    try:
        config = load_manifest_config(project_root)
        state = load_install_state(state_dir)
    except Exception:
        report.tools.append(
            ToolInfo(name="state", available=False, version=None, path=str(state_path))
        )
        return report

    provider = config.providers.vcs
    tool_key = "gh" if provider == "github" else "az"
    tool_entry = state.tooling.get(tool_key)
    authenticated = tool_entry.authenticated if tool_entry else False
    report.tools.append(ToolInfo(name=f"auth:{provider}", available=authenticated))
    report.tools.append(
        ToolInfo(name="branch-policy:applied", available=state.branch_policy.applied)
    )
    return report
