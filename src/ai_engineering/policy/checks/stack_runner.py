"""Stack-aware check execution and check registry."""

from __future__ import annotations

import shutil
import subprocess
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
            # CVE-2026-4539: ReDoS in pygments (CVSS 3.3, no patch). DEC-025.
            cmd=["pip-audit", "--ignore-vuln", "CVE-2026-4539"],
        ),
        CheckConfig(
            name="stack-tests",
            cmd=[
                "uv",
                "run",
                "pytest",
                "--tb=short",
                "-q",
                "-x",
                "--no-cov",
                "-n",
                "auto",
                "--dist",
                "worksteal",
                "-m",
                "unit",
            ],
            timeout=120,
        ),
        CheckConfig(
            name="duplication-check",
            cmd=[
                "uv",
                "run",
                "python",
                "-m",
                "ai_engineering.policy.duplication",
                "--path",
                "src/ai_engineering",
                "--threshold",
                "3",
            ],
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
        for check in registry.get(stack, []):
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
                        "Run 'ai-eng doctor --fix-tools' to install."
                    ),
                )
            )
        else:
            result.checks.append(
                GateCheckResult(
                    name=name,
                    passed=True,
                    output=f"{tool_name} not found — skipped (run 'ai-eng doctor --fix-tools')",
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
                f"{tool_name} not found — required. Run 'ai-eng doctor --fix-tools' to install."
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
