"""Stack-aware check execution and check registry."""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.policy.gates import GateCheckResult, GateResult


@dataclass
class CheckConfig:
    """Configuration for a single gate check command."""

    name: str
    cmd: list[str]
    required: bool = True
    timeout: int = 300


def detect_python_source_root(project_root: Path) -> str:
    """Detect Python source root from pyproject.toml or filesystem probes.

    Resolution order:
    1. ``[tool.hatch.build.targets.wheel] packages`` (first entry)
    2. ``[tool.setuptools] packages`` (first entry)
    3. ``src/`` directory exists on disk
    4. Fallback ``"."``
    """
    pyproject = project_root / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

        # 1. Hatch build config
        hatch_pkgs = (
            data.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("packages", [])
        )
        if hatch_pkgs:
            return hatch_pkgs[0]

        # 2. Setuptools config
        setuptools_pkgs = data.get("tool", {}).get("setuptools", {}).get("packages", [])
        if setuptools_pkgs:
            return setuptools_pkgs[0]
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        pass

    # 3. Probe: src/ directory
    if (project_root / "src").is_dir():
        return "src"

    # 4. Fallback
    return "."


def detect_python_test_dir(project_root: Path) -> str | None:
    """Detect Python test directory from pyproject.toml or filesystem probes.

    For pre-push gates, fast feedback is critical.  When the resolved
    test directory contains a ``unit/`` subdirectory, return that
    narrower path so the gate runs only unit tests (CI handles the
    full suite).

    Resolution order:
    1. ``[tool.pytest.ini_options] testpaths`` (first entry)
    2. ``tests/`` directory exists on disk
    3. ``test/`` directory exists on disk
    4. ``None`` (no test directory found)

    After resolution, if ``<resolved>/unit/`` exists, return it instead.
    """
    pyproject = project_root / "pyproject.toml"
    resolved: str | None = None
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

        # 1. pytest testpaths config
        testpaths = (
            data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths", [])
        )
        if testpaths:
            resolved = testpaths[0]
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        pass

    if resolved is None:
        # 2. Probe: tests/ directory
        if (project_root / "tests").is_dir():
            resolved = "tests"
        # 3. Probe: test/ directory
        elif (project_root / "test").is_dir():
            resolved = "test"

    if resolved is None:
        return None

    # Prefer unit/ subdirectory for fast pre-push feedback
    unit_sub = project_root / resolved / "unit"
    if unit_sub.is_dir():
        return f"{resolved}/unit"

    return resolved


# Pre-commit checks per stack.
PRE_COMMIT_CHECKS: dict[str, list[CheckConfig]] = {
    "common": [
        CheckConfig(
            name="gitleaks",
            cmd=["gitleaks", "protect", "--staged", "--no-banner"],
        ),
    ],
    "python": [
        CheckConfig(name="ruff-format", cmd=["ruff", "format", "--check", "."]),
        CheckConfig(name="ruff-lint", cmd=["ruff", "check", "."]),
    ],
    "dotnet": [
        CheckConfig(name="dotnet-format", cmd=["dotnet", "format", "--verify-no-changes"]),
    ],
    "nextjs": [
        CheckConfig(name="prettier-check", cmd=["prettier", "--check", "."]),
        CheckConfig(name="eslint", cmd=["eslint", "."]),
    ],
}

# Pre-push checks per stack.
PRE_PUSH_CHECKS: dict[str, list[CheckConfig]] = {
    "common": [
        CheckConfig(
            name="semgrep",
            cmd=["semgrep", "--config", ".semgrep.yml", "--error", "."],
        ),
    ],
    "python": [
        CheckConfig(
            name="pip-audit",
            cmd=["pip-audit"],
        ),
        CheckConfig(
            name="stack-tests",
            cmd=[
                "uv",
                "run",
                "pytest",
                "tests/unit/",
                "--tb=short",
                "-q",
                "-x",
                "--no-cov",
                "-n",
                "auto",
                "--dist",
                "worksteal",
            ],
            timeout=120,
        ),
        CheckConfig(name="ty-check", cmd=["ty", "check", "src/ai_engineering"]),
    ],
    "dotnet": [
        CheckConfig(name="dotnet-build", cmd=["dotnet", "build", "--no-restore"]),
        CheckConfig(name="dotnet-test", cmd=["dotnet", "test", "--no-build"]),
        CheckConfig(name="dotnet-vuln", cmd=["dotnet", "list", "package", "--vulnerable"]),
    ],
    "nextjs": [
        CheckConfig(name="tsc-check", cmd=["tsc", "--noEmit"]),
        CheckConfig(name="vitest", cmd=["vitest", "run"]),
        CheckConfig(name="npm-audit", cmd=["npm", "audit"]),
    ],
}


def _resolve_python_checks(
    project_root: Path,
    checks: list[CheckConfig],
    result: GateResult,
) -> list[CheckConfig]:
    """Resolve dynamic paths in Python stack checks.

    Replaces hardcoded paths in ``stack-tests`` and ``ty-check`` with
    values detected from pyproject.toml or filesystem probes.  When no
    test directory is found, ``stack-tests`` is recorded as a skip and
    excluded from the returned list.
    """
    source_root = detect_python_source_root(project_root)
    test_dir = detect_python_test_dir(project_root)

    resolved: list[CheckConfig] = []
    for check in checks:
        if check.name == "stack-tests":
            if test_dir is None:
                result.checks.append(
                    GateCheckResult(
                        name="stack-tests",
                        passed=True,
                        output="No test directory found, skipping stack-tests",
                    )
                )
                continue
            resolved.append(
                CheckConfig(
                    name=check.name,
                    cmd=[
                        "uv",
                        "run",
                        "pytest",
                        test_dir,
                        "--tb=short",
                        "-q",
                        "-x",
                        "--no-cov",
                        "-n",
                        "auto",
                        "--dist",
                        "worksteal",
                    ],
                    required=check.required,
                    timeout=check.timeout,
                )
            )
        elif check.name == "ty-check":
            resolved.append(
                CheckConfig(
                    name=check.name,
                    cmd=["ty", "check", source_root],
                    required=check.required,
                    timeout=check.timeout,
                )
            )
        else:
            resolved.append(check)
    return resolved


def run_checks_for_stacks(
    project_root: Path,
    result: GateResult,
    registry: dict[str, list[CheckConfig]],
    stacks: list[str],
) -> None:
    """Execute checks from *registry* for common + each active stack."""
    # Always run common checks
    for check in registry.get("common", []):
        run_tool_check(
            result,
            name=check.name,
            cmd=check.cmd,
            cwd=project_root,
            required=check.required,
            timeout=check.timeout,
        )

    # Run per-stack checks
    for stack in stacks:
        checks = registry.get(stack, [])
        if stack == "python":
            checks = _resolve_python_checks(project_root, checks, result)
        for check in checks:
            run_tool_check(
                result,
                name=check.name,
                cmd=check.cmd,
                cwd=project_root,
                required=check.required,
                timeout=check.timeout,
            )


def run_tool_check(
    result: GateResult,
    *,
    name: str,
    cmd: list[str],
    cwd: Path,
    required: bool = True,
    timeout: int = 300,
) -> None:
    """Run a tool command and record the result."""
    tool_name = cmd[0]
    if not shutil.which(tool_name):
        if required:
            result.checks.append(
                GateCheckResult(
                    name=name,
                    passed=False,
                    output=(
                        f"{tool_name} not found — required. "
                        "Run 'ai-eng doctor --fix --phase tools' to install."
                    ),
                )
            )
        else:
            result.checks.append(
                GateCheckResult(
                    name=name,
                    passed=True,
                    output=(
                        f"{tool_name} not found — skipped (run 'ai-eng doctor --fix --phase tools')"
                    ),
                )
            )
        return

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        passed = proc.returncode == 0
        output = proc.stdout.strip() or proc.stderr.strip()
        if not output:
            output = f"{tool_name} exited with code {proc.returncode}"
        # Truncate long output
        if len(output) > 500:
            output = output[:500] + "\n... (truncated)"
    except subprocess.TimeoutExpired:
        passed = False
        output = f"{tool_name} timed out after {timeout}s"
    except FileNotFoundError:
        if required:
            passed = False
            output = (
                f"{tool_name} not found — required."
                " Run 'ai-eng doctor --fix --phase tools' to install."
            )
        else:
            passed = True
            output = f"{tool_name} not found — skipped"

    result.checks.append(
        GateCheckResult(
            name=name,
            passed=passed,
            output=output,
        )
    )
