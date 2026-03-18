"""Repository context extraction from git remote URL.

Parses the ``origin`` remote to determine the VCS provider,
organization, project, and repository name.

Supported formats:
- GitHub HTTPS / SSH
- Azure DevOps HTTPS (modern + legacy) / SSH
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ai_engineering.git.operations import run_git

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RepoContext:
    """Parsed repository coordinates."""

    provider: str
    organization: str
    project: str
    repository: str


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_cached_context: RepoContext | None = None
_cache_populated: bool = False

# ---------------------------------------------------------------------------
# URL patterns (compiled once)
# ---------------------------------------------------------------------------

# GitHub HTTPS: https://github.com/org/repo.git
_GITHUB_HTTPS = re.compile(
    r"^https?://github\.com/(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
)
# GitHub SSH: git@github.com:org/repo.git
_GITHUB_SSH = re.compile(
    r"^git@github\.com:(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
)
# ADO HTTPS modern: https://dev.azure.com/org/project/_git/repo
# Also handles user-prefix: https://user@dev.azure.com/org/project/_git/repo
_ADO_HTTPS = re.compile(
    r"^https?://(?:[^@]+@)?dev\.azure\.com/(?P<org>[^/]+)/(?P<project>[^/]+)/_git/(?P<repo>[^/]+?)(?:\.git)?$",
)
# ADO SSH: git@ssh.dev.azure.com:v3/org/project/repo
_ADO_SSH = re.compile(
    r"^git@ssh\.dev\.azure\.com:v3/(?P<org>[^/]+)/(?P<project>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
)
# ADO legacy: https://org.visualstudio.com/project/_git/repo
_ADO_LEGACY = re.compile(
    r"^https?://(?P<org>[^.]+)\.visualstudio\.com/(?P<project>[^/]+)/_git/(?P<repo>[^/]+?)(?:\.git)?$",
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_repo_context(project_root: Path) -> RepoContext | None:
    """Extract repository context from the git remote ``origin`` URL.

    Uses a module-level cache — the remote URL is read only once per
    process lifetime.

    Args:
        project_root: Root directory of the git repository.

    Returns:
        ``RepoContext`` with provider/org/project/repo, or ``None``
        if the URL cannot be parsed or git fails.
    """
    global _cached_context, _cache_populated

    if _cache_populated:
        return _cached_context

    try:
        ok, output = run_git(
            ["config", "--get", "remote.origin.url"],
            project_root,
        )
        if not ok or not output:
            _cache_populated = True
            return None

        url = output.splitlines()[0].strip()
        if not url:
            _cache_populated = True
            return None

        _cached_context = _parse_remote_url(url)
        _cache_populated = True
        return _cached_context
    except Exception:
        _cache_populated = True
        return None


def _reset_cache() -> None:
    """Reset the module-level cache (used by tests)."""
    global _cached_context, _cache_populated
    _cached_context = None
    _cache_populated = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_remote_url(url: str) -> RepoContext | None:
    """Match *url* against known VCS remote patterns."""
    # GitHub HTTPS
    m = _GITHUB_HTTPS.match(url)
    if m:
        org = m.group("org")
        repo = m.group("repo")
        return RepoContext(provider="github", organization=org, project=org, repository=repo)

    # GitHub SSH
    m = _GITHUB_SSH.match(url)
    if m:
        org = m.group("org")
        repo = m.group("repo")
        return RepoContext(provider="github", organization=org, project=org, repository=repo)

    # ADO HTTPS modern (includes user-prefix variant)
    m = _ADO_HTTPS.match(url)
    if m:
        return RepoContext(
            provider="azure-devops",
            organization=m.group("org"),
            project=m.group("project"),
            repository=m.group("repo"),
        )

    # ADO SSH
    m = _ADO_SSH.match(url)
    if m:
        return RepoContext(
            provider="azure-devops",
            organization=m.group("org"),
            project=m.group("project"),
            repository=m.group("repo"),
        )

    # ADO legacy (visualstudio.com)
    m = _ADO_LEGACY.match(url)
    if m:
        return RepoContext(
            provider="azure-devops",
            organization=m.group("org"),
            project=m.group("project"),
            repository=m.group("repo"),
        )

    return None
