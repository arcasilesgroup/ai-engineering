"""VCS provider factory — dispatch based on manifest configuration.

Reads ``manifest.yml`` for the VCS provider and ``install-state.json``
for the tooling mode, with fallback to remote URL detection and
ultimately to GitHub.

Functions:
    get_provider — resolve and return the appropriate VcsProvider.
"""

from __future__ import annotations

import logging
from pathlib import Path

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.git.operations import run_git
from ai_engineering.state.service import load_install_state
from ai_engineering.vcs.api_fallback import ApiFallbackProvider
from ai_engineering.vcs.azure_devops import AzureDevOpsProvider
from ai_engineering.vcs.github import GitHubProvider
from ai_engineering.vcs.protocol import VcsProvider

# Mapping from provider identifier → provider class constructor.
logger = logging.getLogger(__name__)

_PROVIDERS: dict[str, type[GitHubProvider] | type[AzureDevOpsProvider]] = {
    "github": GitHubProvider,
    "azure_devops": AzureDevOpsProvider,
    "azdo": AzureDevOpsProvider,
}


def get_provider(project_root: Path) -> VcsProvider:
    """Resolve the VCS provider from the project manifest.

    Resolution order:

    1. Read ``providers.vcs`` from ``manifest.yml`` (config) and
       tooling mode from ``install-state.json`` (state).
    2. If not set or unknown, detect from the ``origin`` remote URL.
    3. Default to ``GitHubProvider``.

    Args:
        project_root: Root directory of the project.

    Returns:
        An instance satisfying the VcsProvider protocol.
    """
    # 1. Try manifest config + install state
    try:
        config = load_manifest_config(project_root)
        primary = config.providers.vcs

        state_dir = project_root / ".ai-engineering" / "state"
        state = load_install_state(state_dir)

        mode = ""
        tool_key = "gh" if primary == "github" else "az"
        tool_entry = state.tooling.get(tool_key)
        if tool_entry is not None:
            mode = tool_entry.mode
        if mode == "api":
            return ApiFallbackProvider(primary)
        cls = _PROVIDERS.get(primary)
        if cls is not None:
            return cls()
    except Exception:  # fail-open: fall through to remote detection
        logger.debug("Config/state-based provider lookup failed", exc_info=True)

    # 2. Detect from remote URL
    provider_name = detect_from_remote(project_root)
    cls = _PROVIDERS.get(provider_name)
    if cls is not None:
        return cls()

    # 3. Default
    return GitHubProvider()


def detect_from_remote(project_root: Path) -> str:
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
