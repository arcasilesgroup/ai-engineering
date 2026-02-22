"""VCS provider factory — dispatch based on manifest configuration.

Reads ``install-manifest.json`` to determine which VCS provider to use,
with fallback to remote URL detection and ultimately to GitHub.

Functions:
    get_provider — resolve and return the appropriate VcsProvider.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.git.operations import run_git
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import InstallManifest
from ai_engineering.vcs.azure_devops import AzureDevOpsProvider
from ai_engineering.vcs.github import GitHubProvider
from ai_engineering.vcs.protocol import VcsProvider

# Mapping from provider identifier → provider class constructor.
_PROVIDERS: dict[str, type[GitHubProvider] | type[AzureDevOpsProvider]] = {
    "github": GitHubProvider,
    "azure_devops": AzureDevOpsProvider,
}


def get_provider(project_root: Path) -> VcsProvider:
    """Resolve the VCS provider from the project manifest.

    Resolution order:

    1. Read ``providers.primary`` from ``install-manifest.json``.
    2. If not set or unknown, detect from the ``origin`` remote URL.
    3. Default to ``GitHubProvider``.

    Args:
        project_root: Root directory of the project.

    Returns:
        An instance satisfying the VcsProvider protocol.
    """
    # 1. Try manifest
    manifest_path = project_root / ".ai-engineering" / "state" / "install-manifest.json"
    if manifest_path.exists():
        try:
            manifest = read_json_model(manifest_path, InstallManifest)
            primary = manifest.providers.primary
            cls = _PROVIDERS.get(primary)
            if cls is not None:
                return cls()
        except Exception:
            pass  # Fall through to remote detection

    # 2. Detect from remote URL
    provider_name = _detect_from_remote(project_root)
    cls = _PROVIDERS.get(provider_name)
    if cls is not None:
        return cls()

    # 3. Default
    return GitHubProvider()


def _detect_from_remote(project_root: Path) -> str:
    """Detect the VCS provider from the git remote origin URL.

    Args:
        project_root: Root directory of the project.

    Returns:
        Provider identifier string (``"github"`` or ``"azure_devops"``).
        Defaults to ``"github"`` if detection fails.
    """
    ok, output = run_git(["remote", "get-url", "origin"], project_root)
    if not ok:
        return "github"

    url = output.strip().lower()
    if "dev.azure.com" in url or "visualstudio.com" in url:
        return "azure_devops"
    return "github"
