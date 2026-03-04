"""Sonar gate check (advisory mode)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ai_engineering.credentials.service import CredentialService
from ai_engineering.policy.gates import GateCheckResult, GateResult


def check_sonar_gate(project_root: Path, result: GateResult) -> None:
    """Run local Sonar scanner in advisory mode for pre-push.

    This check never blocks push; all outcomes append passed=True.
    """
    if not shutil.which("sonar-scanner"):
        result.checks.append(
            GateCheckResult(
                name="sonar-gate",
                passed=True,
                output="sonar-scanner not found — skipped",
            )
        )
        return

    props_file = project_root / "sonar-project.properties"
    if not props_file.exists():
        result.checks.append(
            GateCheckResult(
                name="sonar-gate",
                passed=True,
                output="sonar-project.properties not found — skipped",
            )
        )
        return

    sonar_token = os.environ.get("SONAR_TOKEN", "").strip()
    if not sonar_token:
        tools = CredentialService.load_tools_state(project_root / ".ai-engineering" / "state")
        if not tools.sonar.configured:
            result.checks.append(
                GateCheckResult(
                    name="sonar-gate",
                    passed=True,
                    output="SONAR_TOKEN not set and Sonar not configured — skipped",
                )
            )
            return

    try:
        proc = subprocess.run(
            ["sonar-scanner"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        result.checks.append(
            GateCheckResult(
                name="sonar-gate",
                passed=True,
                output="sonar-scanner execution unavailable — skipped",
            )
        )
        return

    if proc.returncode == 0:
        output = proc.stdout.strip() or "Sonar gate passed"
        result.checks.append(
            GateCheckResult(
                name="sonar-gate",
                passed=True,
                output=output,
            )
        )
        return

    failure_output = proc.stderr.strip() or proc.stdout.strip() or "unknown scanner error"
    result.checks.append(
        GateCheckResult(
            name="sonar-gate",
            passed=True,
            output=f"Sonar gate FAILED (advisory): {failure_output}",
        )
    )
