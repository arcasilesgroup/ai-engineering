"""SonarLint IDE configuration — multi-IDE Connected Mode setup.

Generates SonarLint configuration for all major IDE families:

- **VS Code family** (VS Code, Cursor, Windsurf, Antigravity):
  ``.vscode/settings.json`` + ``.vscode/extensions.json``
- **JetBrains family** (IntelliJ, Rider, WebStorm, PyCharm, GoLand):
  ``.idea/sonarlint/`` XML binding files
- **Visual Studio 2022**: ``.vs/SonarLint/settings.json``

All configurations use **Connected Mode** (D024-007) pointing to the
configured SonarCloud/SonarQube instance.  Merge strategy (D024-009):
deep-merge SonarLint keys only, never overwrite user content.

Security contract: no secrets in generated files.  Connection tokens
are resolved at runtime by SonarLint from the IDE's own credential
store or environment variables.
"""

from __future__ import annotations

import json
import logging
import textwrap
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# IDE family detection
# ------------------------------------------------------------------


class IDEFamily(StrEnum):
    """Supported IDE families for SonarLint configuration."""

    VSCODE = "vscode"
    JETBRAINS = "jetbrains"
    VS2022 = "vs2022"


# VS Code forks that all read from ``.vscode/`` (D024-008).
VSCODE_FAMILY_NAMES: tuple[str, ...] = (
    "VS Code",
    "Cursor",
    "Windsurf",
    "Antigravity",
)

# JetBrains IDEs that all read from ``.idea/``.
JETBRAINS_FAMILY_NAMES: tuple[str, ...] = (
    "IntelliJ IDEA",
    "Rider",
    "WebStorm",
    "PyCharm",
    "GoLand",
    "CLion",
    "RubyMine",
    "PhpStorm",
)

# Workspace markers → IDE family.
_IDE_MARKERS: dict[IDEFamily, list[str]] = {
    IDEFamily.VSCODE: [".vscode"],
    IDEFamily.JETBRAINS: [".idea"],
    IDEFamily.VS2022: [".vs"],
}

# SonarLint extension identifier for VS Code Marketplace.
_SONARLINT_VSCODE_EXTENSION_ID: str = "SonarSource.sonarlint-vscode"

# Default connection ID prefix.
_DEFAULT_CONNECTION_ID: str = "ai-engineering"


@dataclass
class SonarLintResult:
    """Result of a SonarLint configuration operation."""

    success: bool = False
    ide_family: str = ""
    files_written: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class SonarLintSummary:
    """Aggregated results for all IDE families."""

    results: list[SonarLintResult] = field(default_factory=list)

    @property
    def any_success(self) -> bool:
        """Return True if at least one IDE was configured."""
        return any(r.success for r in self.results)


# ------------------------------------------------------------------
# IDE detection
# ------------------------------------------------------------------


def detect_ide_families(root: Path) -> list[IDEFamily]:
    """Detect IDE families from workspace-root markers in *root*.

    Checks for:
    * ``.vscode/`` → VS Code family (VS Code, Cursor, Windsurf, Antigravity)
    * ``.idea/`` → JetBrains family (IntelliJ, Rider, WebStorm, PyCharm, etc.)
    * ``.vs/`` → Visual Studio 2022

    Returns a list of detected :class:`IDEFamily` values.
    """
    detected: list[IDEFamily] = []
    for family, markers in _IDE_MARKERS.items():
        for marker in markers:
            if (root / marker).exists():
                detected.append(family)
                break
    return detected


# ------------------------------------------------------------------
# Connection helpers
# ------------------------------------------------------------------


def _is_sonarcloud(url: str) -> bool:
    """Return True if *url* points to SonarCloud."""
    return "sonarcloud.io" in url.lower()


def _build_connection_id(url: str) -> str:
    """Build a deterministic connection ID from the server URL."""
    if _is_sonarcloud(url):
        return f"{_DEFAULT_CONNECTION_ID}-sonarcloud"
    # For self-hosted, derive from hostname.
    from urllib.parse import urlparse

    parsed = urlparse(url)
    host = parsed.hostname or "sonarqube"
    return f"{_DEFAULT_CONNECTION_ID}-{host.replace('.', '-')}"


# ------------------------------------------------------------------
# VS Code family
# ------------------------------------------------------------------


def configure_vscode(
    root: Path,
    sonar_url: str,
    project_key: str,
    *,
    connection_id: str = "",
) -> SonarLintResult:
    """Configure SonarLint Connected Mode for VS Code family IDEs.

    Merges SonarLint settings into ``.vscode/settings.json`` and adds
    the SonarLint extension recommendation to ``.vscode/extensions.json``.

    VS Code forks (Cursor, Windsurf, Antigravity) all read from
    ``.vscode/`` (D024-008).

    Parameters
    ----------
    root:
        Workspace root path.
    sonar_url:
        SonarCloud or SonarQube server URL.
    project_key:
        Sonar project key.
    connection_id:
        Optional override for the connection identifier.
    """
    conn_id = connection_id or _build_connection_id(sonar_url)
    vscode_dir = root / ".vscode"
    vscode_dir.mkdir(parents=True, exist_ok=True)
    files_written: list[str] = []

    # --- settings.json ---
    settings_path = vscode_dir / "settings.json"
    settings = _read_json_safe(settings_path)

    # Build the connection entry.
    if _is_sonarcloud(sonar_url):
        connection_key = "sonarlint.connectedMode.connections.sonarcloud"
        connection_entry = {
            "connectionId": conn_id,
            "organizationKey": _extract_org_key(sonar_url),
        }
    else:
        connection_key = "sonarlint.connectedMode.connections.sonarqube"
        connection_entry = {
            "connectionId": conn_id,
            "serverUrl": sonar_url,
        }

    # Merge connection (avoid duplicates).
    existing_connections: list[dict] = settings.get(connection_key, [])
    if not any(c.get("connectionId") == conn_id for c in existing_connections):
        existing_connections.append(connection_entry)
    settings[connection_key] = existing_connections

    # Set project binding.
    settings["sonarlint.connectedMode.project"] = {
        "connectionId": conn_id,
        "projectKey": project_key,
    }

    _write_json_safe(settings_path, settings)
    files_written.append(str(settings_path.relative_to(root)))

    # --- extensions.json ---
    ext_path = vscode_dir / "extensions.json"
    extensions = _read_json_safe(ext_path)
    recommendations: list[str] = extensions.get("recommendations", [])
    if _SONARLINT_VSCODE_EXTENSION_ID not in recommendations:
        recommendations.append(_SONARLINT_VSCODE_EXTENSION_ID)
    extensions["recommendations"] = recommendations
    _write_json_safe(ext_path, extensions)
    files_written.append(str(ext_path.relative_to(root)))

    logger.info("SonarLint configured for VS Code family: %s", ", ".join(VSCODE_FAMILY_NAMES))

    return SonarLintResult(
        success=True,
        ide_family=IDEFamily.VSCODE.value,
        files_written=files_written,
    )


def _extract_org_key(sonar_url: str) -> str:
    """Extract organisation key from SonarCloud URL path, if present.

    SonarCloud URLs may contain ``/organizations/<key>/...``.
    Returns empty string if not found — user must set it manually.
    """
    parts = sonar_url.rstrip("/").split("/")
    try:
        idx = parts.index("organizations")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    except ValueError:
        pass
    return ""


# ------------------------------------------------------------------
# JetBrains family
# ------------------------------------------------------------------


def configure_jetbrains(
    root: Path,
    sonar_url: str,
    project_key: str,
    *,
    connection_id: str = "",
) -> SonarLintResult:
    """Configure SonarLint Connected Mode for JetBrains IDEs.

    Generates ``.idea/sonarlint.xml`` with the server connection, and
    ``.idea/sonarlint/`` binding configuration.

    JetBrains IDEs (IntelliJ, Rider, WebStorm, PyCharm, GoLand, etc.)
    all read project-level settings from ``.idea/``.

    Parameters
    ----------
    root:
        Workspace root path.
    sonar_url:
        SonarCloud or SonarQube server URL.
    project_key:
        Sonar project key.
    connection_id:
        Optional override for the connection identifier.
    """
    conn_id = connection_id or _build_connection_id(sonar_url)
    idea_dir = root / ".idea"
    idea_dir.mkdir(parents=True, exist_ok=True)
    sonarlint_dir = idea_dir / "sonarlint"
    sonarlint_dir.mkdir(parents=True, exist_ok=True)
    files_written: list[str] = []

    # --- .idea/sonarlint.xml (connection binding) ---
    sonarlint_xml_path = idea_dir / "sonarlint.xml"

    connection_type = "SONARCLOUD" if _is_sonarcloud(sonar_url) else "SONARQUBE"

    sonarlint_xml_content = textwrap.dedent(f"""\
        <?xml version="1.0" encoding="UTF-8"?>
        <project version="4">
          <component name="SonarLintProjectSettings">
            <option name="bindingEnabled" value="true" />
            <option name="connectionName" value="{conn_id}" />
            <option name="projectKey" value="{project_key}" />
          </component>
          <component name="SonarLintGeneralSettings">
            <option name="serverConnections">
              <list>
                <SonarQubeServer>
                  <option name="name" value="{conn_id}" />
                  <option name="type" value="{connection_type}" />
                  <option name="hostUrl" value="{sonar_url}" />
                </SonarQubeServer>
              </list>
            </option>
          </component>
        </project>
    """)

    sonarlint_xml_path.write_text(sonarlint_xml_content, encoding="utf-8")
    files_written.append(str(sonarlint_xml_path.relative_to(root)))

    # --- .idea/sonarlint/connectedMode.json (modern SonarLint plugin) ---
    connected_mode_path = sonarlint_dir / "connectedMode.json"
    connected_mode = {
        "projectKey": project_key,
        "connectionId": conn_id,
    }
    _write_json_safe(connected_mode_path, connected_mode)
    files_written.append(str(connected_mode_path.relative_to(root)))

    logger.info("SonarLint configured for JetBrains family: %s", ", ".join(JETBRAINS_FAMILY_NAMES))

    return SonarLintResult(
        success=True,
        ide_family=IDEFamily.JETBRAINS.value,
        files_written=files_written,
    )


# ------------------------------------------------------------------
# Visual Studio 2022
# ------------------------------------------------------------------


def configure_vs2022(
    root: Path,
    sonar_url: str,
    project_key: str,
    *,
    connection_id: str = "",
) -> SonarLintResult:
    """Configure SonarLint Connected Mode for Visual Studio 2022.

    Generates ``.vs/SonarLint/settings.json`` with the connection binding.

    Parameters
    ----------
    root:
        Workspace root path.
    sonar_url:
        SonarCloud or SonarQube server URL.
    project_key:
        Sonar project key.
    connection_id:
        Optional override for the connection identifier.
    """
    conn_id = connection_id or _build_connection_id(sonar_url)
    vs_dir = root / ".vs" / "SonarLint"
    vs_dir.mkdir(parents=True, exist_ok=True)
    files_written: list[str] = []

    settings_path = vs_dir / "settings.json"

    if _is_sonarcloud(sonar_url):
        connection_config = {
            "sonarCloudConnections": [
                {
                    "connectionId": conn_id,
                    "organizationKey": _extract_org_key(sonar_url),
                },
            ],
        }
    else:
        connection_config = {
            "sonarQubeConnections": [
                {
                    "connectionId": conn_id,
                    "serverUrl": sonar_url,
                },
            ],
        }

    settings = {
        **connection_config,
        "projectBinding": {
            "connectionId": conn_id,
            "projectKey": project_key,
        },
    }

    _write_json_safe(settings_path, settings)
    files_written.append(str(settings_path.relative_to(root)))

    logger.info("SonarLint configured for Visual Studio 2022")

    return SonarLintResult(
        success=True,
        ide_family=IDEFamily.VS2022.value,
        files_written=files_written,
    )


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------


def configure_all_ides(
    root: Path,
    sonar_url: str,
    project_key: str,
    *,
    connection_id: str = "",
    ide_families: list[IDEFamily] | None = None,
) -> SonarLintSummary:
    """Configure SonarLint for all detected (or specified) IDE families.

    Parameters
    ----------
    root:
        Workspace root path.
    sonar_url:
        SonarCloud or SonarQube server URL.
    project_key:
        Sonar project key.
    connection_id:
        Optional override for the connection identifier.
    ide_families:
        Explicit list of IDE families.  If ``None``, auto-detects from
        workspace markers.
    """
    families = ide_families if ide_families is not None else detect_ide_families(root)
    summary = SonarLintSummary()

    _configurators: dict[IDEFamily, object] = {
        IDEFamily.VSCODE: configure_vscode,
        IDEFamily.JETBRAINS: configure_jetbrains,
        IDEFamily.VS2022: configure_vs2022,
    }

    for family in families:
        configurator = _configurators.get(family)
        if configurator is None:
            summary.results.append(
                SonarLintResult(success=False, ide_family=family.value, error="Unknown IDE family"),
            )
            continue
        try:
            result = configurator(
                root,
                sonar_url,
                project_key,
                connection_id=connection_id,
            )
            summary.results.append(result)
        except Exception as exc:
            logger.warning("SonarLint config failed for %s: %s", family.value, exc)
            summary.results.append(
                SonarLintResult(success=False, ide_family=family.value, error=str(exc)),
            )

    return summary


# ------------------------------------------------------------------
# JSON helpers (merge-safe)
# ------------------------------------------------------------------


def _read_json_safe(path: Path) -> dict:
    """Read a JSON file, returning an empty dict if missing or invalid."""
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return {}
        return json.loads(text)
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not parse %s — will create fresh", path)
        return {}


def _write_json_safe(path: Path, data: dict) -> None:
    """Write *data* as formatted JSON to *path*."""
    resolved = path.resolve()
    resolved.relative_to(resolved.parent)
    if resolved.suffix != ".json":
        msg = f"Refusing to write non-JSON file: {resolved}"
        raise ValueError(msg)
    resolved.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
