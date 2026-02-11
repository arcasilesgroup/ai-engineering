"""Version lifecycle checker — pure functions for version status evaluation.

Provides:
- load_registry: load the embedded registry.json from package data.
- check_version: compare installed version against registry, return typed result.
- find_latest_version: find the highest version in the registry.
- find_version_entry: look up a specific version entry.

All functions are pure (no side effects) and fail-open (D-010-3):
corrupted or missing registry returns graceful defaults, never blocks.
"""

from __future__ import annotations

import contextlib
import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from ai_engineering.version.models import VersionEntry, VersionRegistry, VersionStatus


@dataclass(frozen=True)
class VersionCheckResult:
    """Outcome of a version lifecycle check.

    Attributes:
        installed: The version string that was checked.
        status: Lifecycle status from the registry, or None if unknown.
        is_current: True if installed version is the current release.
        is_outdated: True if a newer version exists (but installed is still supported).
        is_deprecated: True if installed version is deprecated (security risk).
        is_eol: True if installed version has reached end-of-life.
        latest: The latest available version string, or None.
        message: Human-readable status message.
    """

    installed: str
    status: VersionStatus | None
    is_current: bool
    is_outdated: bool
    is_deprecated: bool
    is_eol: bool
    latest: str | None
    message: str


def _parse_semver(version: str) -> tuple[int, ...]:
    """Parse a strict X.Y.Z version string into a comparable tuple.

    Args:
        version: Version string in X.Y.Z format.

    Returns:
        Tuple of integers for comparison.

    Raises:
        ValueError: If the version string is not valid.
    """
    return tuple(int(x) for x in version.split("."))


def load_registry(registry_path: Path | None = None) -> VersionRegistry | None:
    """Load the version registry from embedded package data or a custom path.

    Fail-open (D-010-3): returns None on any error rather than raising.

    Args:
        registry_path: Optional path override for testing. If None,
            loads from the bundled ``version/registry.json``.

    Returns:
        Parsed VersionRegistry, or None if loading fails.
    """
    try:
        if registry_path is not None:
            raw = registry_path.read_text(encoding="utf-8")
        else:
            ref = resources.files("ai_engineering.version").joinpath("registry.json")
            raw = ref.read_text(encoding="utf-8")
        data = json.loads(raw)
        return VersionRegistry.model_validate(data)
    except Exception:
        return None


def find_version_entry(registry: VersionRegistry, version: str) -> VersionEntry | None:
    """Find a version entry in the registry by version string.

    Args:
        registry: The loaded version registry.
        version: Version string to look up.

    Returns:
        VersionEntry if found, else None.
    """
    for entry in registry.versions:
        if entry.version == version:
            return entry
    return None


def find_latest_version(registry: VersionRegistry) -> str | None:
    """Find the highest version in the registry by semver comparison.

    Args:
        registry: The loaded version registry.

    Returns:
        The highest version string, or None if registry has no versions.
    """
    if not registry.versions:
        return None

    best: VersionEntry | None = None
    for entry in registry.versions:
        if best is None:
            best = entry
        else:
            try:
                if _parse_semver(entry.version) > _parse_semver(best.version):
                    best = entry
            except ValueError:
                continue
    return best.version if best else None


def check_version(
    installed: str,
    registry: VersionRegistry | None = None,
    *,
    registry_path: Path | None = None,
) -> VersionCheckResult:
    """Check the lifecycle status of an installed version.

    Pure function: loads registry if not provided, compares versions,
    and returns a typed result. Fail-open on errors.

    Args:
        installed: The installed version string (e.g., "0.1.0").
        registry: Pre-loaded registry. If None, loads from package data.
        registry_path: Optional path override for registry loading.

    Returns:
        VersionCheckResult describing the lifecycle status.
    """
    if registry is None:
        registry = load_registry(registry_path)

    if registry is None:
        return VersionCheckResult(
            installed=installed,
            status=None,
            is_current=False,
            is_outdated=False,
            is_deprecated=False,
            is_eol=False,
            latest=None,
            message="Version registry unavailable — skipping lifecycle check",
        )

    entry = find_version_entry(registry, installed)
    latest = find_latest_version(registry)

    if entry is None:
        return VersionCheckResult(
            installed=installed,
            status=None,
            is_current=False,
            is_outdated=False,
            is_deprecated=False,
            is_eol=False,
            latest=latest,
            message=f"Version {installed} not found in registry",
        )

    is_current = entry.status == VersionStatus.CURRENT
    is_deprecated = entry.status == VersionStatus.DEPRECATED
    is_eol = entry.status == VersionStatus.EOL

    # Outdated: supported but not current, AND a newer version exists
    is_outdated = False
    if entry.status == VersionStatus.SUPPORTED and latest:
        with contextlib.suppress(ValueError):
            is_outdated = _parse_semver(installed) < _parse_semver(latest)

    if is_current:
        message = f"{installed} (current)"
    elif is_outdated:
        message = f"{installed} (outdated — latest is {latest})"
    elif is_deprecated:
        reason = entry.deprecated_reason or "security vulnerability"
        message = f"{installed} (deprecated — {reason})"
    elif is_eol:
        message = f"{installed} (end-of-life — no longer supported)"
    else:
        message = f"{installed} ({entry.status.value})"

    return VersionCheckResult(
        installed=installed,
        status=entry.status,
        is_current=is_current,
        is_outdated=is_outdated,
        is_deprecated=is_deprecated,
        is_eol=is_eol,
        latest=latest,
        message=message,
    )
