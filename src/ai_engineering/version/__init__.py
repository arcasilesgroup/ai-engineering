"""Version lifecycle management for ai-engineering.

Public API:
- VersionStatus, VersionEntry, VersionRegistry — data models.
- VersionCheckResult — check outcome.
- load_registry, check_version, find_latest_version — checker functions.
- resolve_latest_known — authoritative latest-version SSOT across signals.
"""

from ai_engineering.version import cache, install_method, pypi, refresh
from ai_engineering.version.checker import (
    VersionCheckResult,
    check_version,
    find_latest_version,
    find_version_entry,
    load_registry,
)
from ai_engineering.version.latest import resolve_latest_known
from ai_engineering.version.models import VersionEntry, VersionRegistry, VersionStatus

__all__ = [
    "VersionCheckResult",
    "VersionEntry",
    "VersionRegistry",
    "VersionStatus",
    "cache",
    "check_version",
    "find_latest_version",
    "find_version_entry",
    "install_method",
    "load_registry",
    "pypi",
    "refresh",
    "resolve_latest_known",
]
