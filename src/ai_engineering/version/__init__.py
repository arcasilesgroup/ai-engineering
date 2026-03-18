"""Version lifecycle management for ai-engineering.

Public API:
- VersionStatus, VersionEntry, VersionRegistry — data models.
- VersionCheckResult — check outcome.
- load_registry, check_version, find_latest_version — checker functions.
"""

from ai_engineering.version.checker import (
    VersionCheckResult,
    check_version,
    find_latest_version,
    find_version_entry,
    load_registry,
)
from ai_engineering.version.models import VersionEntry, VersionRegistry, VersionStatus

__all__ = [
    "VersionCheckResult",
    "VersionEntry",
    "VersionRegistry",
    "VersionStatus",
    "check_version",
    "find_latest_version",
    "find_version_entry",
    "load_registry",
]
