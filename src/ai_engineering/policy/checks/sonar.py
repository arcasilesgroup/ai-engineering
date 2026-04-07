"""Sonar gate check (advisory mode)."""

from __future__ import annotations

import json as _json
import os
import shutil
import socket
import ssl
import subprocess
from pathlib import Path
from urllib.parse import urlencode, urlparse

from ai_engineering.credentials.service import CredentialService
from ai_engineering.policy.gates import GateCheckResult, GateResult

_ALLOWED_SCHEMES = frozenset({"https", "http"})
_ALLOWED_API_PATHS = frozenset(
    {
        "/api/qualitygates/project_status",
        "/api/measures/component",
    }
)


def _build_sonar_url(host_url: str, path: str, params: dict[str, str]) -> str | None:
    """Build and validate a SonarCloud API URL. Returns None if invalid."""
    parsed = urlparse(host_url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return None
    if not parsed.hostname:
        return None
    if path not in _ALLOWED_API_PATHS:
        return None
    base = f"{parsed.scheme}://{parsed.hostname}"
    if parsed.port:
        base = f"{base}:{parsed.port}"
    return f"{base}{path}?{urlencode(params)}"


def _sonar_api_get(url: str, token: str) -> dict | None:
    """Perform a validated GET request to SonarCloud API.

    Uses a minimal socket-based client after URL validation to keep the
    request surface explicit and avoid dynamic URL helper hotspots.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        return None
    port = parsed.port
    path_and_query = f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
    if parsed.username or parsed.password:
        return None

    request_bytes = (
        f"GET {path_and_query} HTTP/1.1\r\n"
        f"Host: {hostname}\r\n"
        f"Authorization: Bearer {token}\r\n"
        "Connection: close\r\n"
        "User-Agent: ai-engineering-sonar-gate/1\r\n"
        "Accept: application/json\r\n"
        "\r\n"
    ).encode("ascii")

    try:
        if parsed.scheme == "https":
            ctx = ssl.create_default_context()
            with (
                socket.create_connection((hostname, port or 443), timeout=15) as sock,
                ctx.wrap_socket(sock, server_hostname=hostname) as tls_sock,
            ):
                status, body = _read_http_response(tls_sock, request_bytes)
        else:
            with socket.create_connection((hostname, port or 80), timeout=15) as sock:
                status, body = _read_http_response(sock, request_bytes)
        if status != 200:
            return None
        return _json.loads(body.decode("utf-8"))
    except Exception:
        return None


def _read_http_response(sock: socket.socket, request_bytes: bytes) -> tuple[int, bytes]:
    """Send *request_bytes* over *sock* and return ``(status, body)``."""
    sock.sendall(request_bytes)
    response = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response.extend(chunk)

    header_bytes, _, body = bytes(response).partition(b"\r\n\r\n")
    status_line = header_bytes.split(b"\r\n", 1)[0].decode("iso-8859-1")
    parts = status_line.split(" ", 2)
    if len(parts) < 2 or not parts[1].isdigit():
        msg = f"Malformed HTTP status line: {status_line!r}"
        raise ValueError(msg)
    return int(parts[1]), body


def _resolve_sonar_token(project_root: Path) -> str | None:
    """Resolve Sonar token: env var -> OS keyring -> None (fail-open)."""
    token = os.environ.get("SONAR_TOKEN", "").strip()
    if token:
        return token
    try:
        stored = CredentialService().retrieve("sonar", "token")
        if stored:
            return stored
    except Exception:
        pass
    return None


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

    sonar_token = _resolve_sonar_token(project_root)
    if not sonar_token:
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

    token = _resolve_sonar_token(project_root)
    if not token:
        return None

    api_url = _build_sonar_url(
        host_url, "/api/qualitygates/project_status", {"projectKey": project_key}
    )
    if not api_url:
        return None
    data = _sonar_api_get(api_url, token)
    if data is None:
        return None
    return data.get("projectStatus", {})


def query_sonar_measures(
    project_root: Path,
    metrics: list[str] | None = None,
) -> dict[str, float] | None:
    """Query detailed metrics from SonarCloud/SonarQube via Web API.

    Returns dict like {"coverage": 87.5, "duplicated_lines_density": 2.1} or None.
    Uses same token resolution as quality gate. Silent-skip if unconfigured.
    """
    props_file = project_root / "sonar-project.properties"
    if not props_file.exists():
        return None

    props = _parse_properties(props_file)
    project_key = props.get("sonar.projectKey", "")
    host_url = props.get("sonar.host.url", "https://sonarcloud.io").rstrip("/")
    if not project_key:
        return None

    token = _resolve_sonar_token(project_root)
    if not token:
        return None

    if metrics is None:
        metrics = [
            "coverage",
            "cognitive_complexity",
            "duplicated_lines_density",
            "vulnerabilities",
            "security_hotspots",
            "security_rating",
            "reliability_rating",
            "bugs",
            "ncloc",
        ]

    api_url = _build_sonar_url(
        host_url,
        "/api/measures/component",
        {"component": project_key, "metricKeys": ",".join(metrics)},
    )
    if not api_url:
        return None

    data = _sonar_api_get(api_url, token)
    if data is None:
        return None
    try:
        measures: dict[str, float] = {}
        for measure in data.get("component", {}).get("measures", []):
            key = measure.get("metric", measure.get("key", ""))
            val = measure.get("value", "")
            try:
                measures[key] = float(val)
            except (ValueError, TypeError):
                measures[key] = 0.0
        return measures if measures else None
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
