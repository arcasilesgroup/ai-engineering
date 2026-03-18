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


def detect_platforms(root: Path, *, vcs_provider: str | None = None) -> list[PlatformKind]:
    """Detect platforms from repo-root markers in *root*.

    Checks for well-known directories and files:

    * ``.github/`` → GitHub
    * ``azure-pipelines.yml`` or ``.azuredevops/`` → Azure DevOps
    * ``sonar-project.properties`` → SonarCloud / SonarQube

    When *vcs_provider* is given, the corresponding platform is always
    included and conflicting VCS platforms are excluded (e.g. selecting
    ``azure_devops`` suppresses a false-positive ``.github/`` detection).

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

    # Reconcile with explicit VCS provider selection
    if vcs_provider == "azure_devops":
        if PlatformKind.GITHUB in detected:
            detected.remove(PlatformKind.GITHUB)
        if PlatformKind.AZURE_DEVOPS not in detected:
            detected.insert(0, PlatformKind.AZURE_DEVOPS)
    elif vcs_provider == "github":
        if PlatformKind.AZURE_DEVOPS in detected:
            detected.remove(PlatformKind.AZURE_DEVOPS)
        if PlatformKind.GITHUB not in detected:
            detected.insert(0, PlatformKind.GITHUB)

    return detected
