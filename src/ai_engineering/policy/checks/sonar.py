"""Sonar gate check (advisory mode)."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

from ai_engineering.credentials.service import CredentialService
from ai_engineering.policy.gates import GateCheckResult, GateResult


def check_sonar_gate(project_root: Path, result: GateResult) -> None:
    """Run local Sonar scanner in advisory mode for pre-push.

    This check never blocks push; all outcomes append passed=True.
    """
    if not shutil.which("sonar-scanner"):
        # Try API-only quality gate check when scanner not installed
        _check_sonar_api_gate(project_root, result)
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


def _check_sonar_api_gate(project_root: Path, result: GateResult) -> None:
    """Check SonarCloud Quality Gate status via Web API (advisory, D038-005)."""
    qg = query_sonar_quality_gate(project_root)
    if qg is None:
        result.checks.append(
            GateCheckResult(
                name="sonar-gate",
                passed=True,
                output="sonar-scanner not found and API unavailable — skipped",
            )
        )
        return

    status = qg.get("status", "UNKNOWN")
    output = f"SonarCloud Quality Gate: {status}"
    result.checks.append(
        GateCheckResult(
            name="sonar-gate",
            passed=True,
            output=output,
        )
    )


def query_sonar_quality_gate(project_root: Path) -> dict | None:
    """Query SonarCloud/SonarQube Quality Gate status via Web API.

    Returns dict with 'status' key ('OK', 'ERROR', etc.) or None if unavailable.
    Silent-skip if unconfigured — never raises.
    """
    props_file = project_root / "sonar-project.properties"
    if not props_file.exists():
        return None

    props = _parse_properties(props_file)
    project_key = props.get("sonar.projectKey", "")
    host_url = props.get("sonar.host.url", "https://sonarcloud.io").rstrip("/")
    if not project_key:
        return None

    token = os.environ.get("SONAR_TOKEN", "").strip()
    if not token:
        try:
            tools = CredentialService.load_tools_state(project_root / ".ai-engineering" / "state")
            if not tools.sonar.configured:
                return None
        except Exception:
            return None

    api_url = f"{host_url}/api/qualitygates/project_status?projectKey={project_key}"
    try:
        req = Request(api_url, headers={"Authorization": f"Bearer {token}"})
        with urlopen(req, timeout=15) as resp:
            import json

            data = json.loads(resp.read().decode("utf-8"))
            return data.get("projectStatus", {})
    except Exception:
        return None


def _parse_properties(path: Path) -> dict[str, str]:
    """Parse a Java .properties file into a dict."""
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            result[key.strip()] = value.strip()
    return result
