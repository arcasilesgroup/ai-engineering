"""Auto-detect platforms from repository markers.

Scans for well-known directory/file patterns to determine which
platform integrations are available in the target repository.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.credentials.models import PlatformKind

# Mapping of platform markers to their platform kind.
_MARKERS: dict[PlatformKind, list[str]] = {
    PlatformKind.GITHUB: [".github"],
    PlatformKind.AZURE_DEVOPS: ["azure-pipelines.yml", ".azuredevops"],
    PlatformKind.SONAR: ["sonar-project.properties"],
}


def detect_platforms(root: Path) -> list[PlatformKind]:
    """Detect platforms from repo-root markers in *root*.

    Checks for well-known directories and files:

    * ``.github/`` → GitHub
    * ``azure-pipelines.yml`` or ``.azuredevops/`` → Azure DevOps
    * ``sonar-project.properties`` → SonarCloud / SonarQube

    Returns a list of detected :class:`PlatformKind` values,
    ordered by detection priority. The list may be empty.
    """
    detected: list[PlatformKind] = []

    for platform, markers in _MARKERS.items():
        for marker in markers:
            candidate = root / marker
            if candidate.exists():
                detected.append(platform)
                break  # one match is enough per platform

    return detected
