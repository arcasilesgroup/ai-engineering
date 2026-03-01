"""Remote skills synchronisation service.

Manages the lifecycle of remote skill sources:
- Source discovery from ``sources.lock.json``.
- Checksum verification for integrity.
- Allowlist-only trust policy enforcement.
- Offline fallback using cached content.
- Sync operation to refresh remote skills.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import yaml

from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.models import CacheConfig, RemoteSource, SourcesLock

_logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Summary of a skill sync operation."""

    fetched: list[str] = field(default_factory=list)
    cached: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    untrusted: list[str] = field(default_factory=list)


@dataclass
class SkillStatus:
    """Eligibility status for a local governance skill."""

    name: str
    file_path: str
    eligible: bool
    missing_bins: list[str] = field(default_factory=list)
    missing_any_bins: list[str] = field(default_factory=list)
    missing_env: list[str] = field(default_factory=list)
    missing_config: list[str] = field(default_factory=list)
    missing_os: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def list_local_skill_status(target: Path) -> list[SkillStatus]:
    """Evaluate local `.ai-engineering/skills` requirement eligibility."""
    skills_root = target / ".ai-engineering" / "skills"
    if not skills_root.is_dir():
        return []

    manifest = _safe_yaml_load(target / ".ai-engineering" / "manifest.yml")
    install_manifest = _safe_json_load(
        target / ".ai-engineering" / "state" / "install-manifest.json"
    )
    config_roots = [manifest, install_manifest]

    # Only scan skill definition files:
    # - Directory-based: skills/<category>/<name>/SKILL.md
    # - File-based: skills/<category>/<name>.md (direct children of category dirs)
    skill_files: list[Path] = []
    skill_files.extend(sorted(skills_root.rglob("SKILL.md")))
    for category_dir in sorted(skills_root.iterdir()):
        if category_dir.is_dir():
            for md in sorted(category_dir.glob("*.md")):
                if md.is_file() and md.name != "SKILL.md":
                    skill_files.append(md)

    statuses: list[SkillStatus] = []
    for skill_file in skill_files:
        rel = skill_file.relative_to(target).as_posix()
        frontmatter, errors = _load_skill_frontmatter(skill_file)

        name = str(frontmatter.get("name") or skill_file.stem)
        requires_raw = frontmatter.get("requires") if isinstance(frontmatter, dict) else {}
        requires: dict[str, object] = (
            cast(dict[str, object], requires_raw) if isinstance(requires_raw, dict) else {}
        )

        bins = _ensure_str_list(requires.get("bins"))
        any_bins = _ensure_str_list(requires.get("anyBins"))
        env_vars = _ensure_str_list(requires.get("env"))
        config_paths = _ensure_str_list(requires.get("config"))
        os_required = _ensure_str_list(frontmatter.get("os"))

        missing_bins = [bin_name for bin_name in bins if not shutil.which(bin_name)]
        missing_any_bins = []
        if any_bins and not any(shutil.which(bin_name) for bin_name in any_bins):
            missing_any_bins = any_bins
        missing_env = [env_name for env_name in env_vars if not os.environ.get(env_name)]
        missing_config = [
            path
            for path in config_paths
            if not any(_config_path_truthy(root, path) for root in config_roots)
        ]
        missing_os = []
        if os_required and not _platform_matches(os_required):
            missing_os = os_required

        eligible = not (
            errors
            or missing_bins
            or missing_any_bins
            or missing_env
            or missing_config
            or missing_os
        )

        statuses.append(
            SkillStatus(
                name=name,
                file_path=rel,
                eligible=eligible,
                missing_bins=missing_bins,
                missing_any_bins=missing_any_bins,
                missing_env=missing_env,
                missing_config=missing_config,
                missing_os=missing_os,
                errors=errors,
            )
        )

    return statuses


_CACHE_DIR_NAME: str = "skills-cache"


def _safe_yaml_load(path: Path) -> dict[str, object]:
    """Read YAML file into dict; return empty dict on failure."""
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _safe_json_load(path: Path) -> dict[str, object]:
    """Read JSON file into dict; return empty dict on failure."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _ensure_str_list(value: object) -> list[str]:
    """Normalize potentially-invalid list values to list[str]."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _load_skill_frontmatter(path: Path) -> tuple[dict[str, object], list[str]]:
    """Parse SKILL markdown frontmatter and return errors if invalid."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, [f"read-failed: {exc}"]

    if not text.startswith("---\n"):
        return {}, ["missing-frontmatter"]

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, ["unterminated-frontmatter"]

    block = text[4:end]
    try:
        parsed = yaml.safe_load(block) or {}
    except yaml.YAMLError as exc:
        return {}, [f"invalid-frontmatter-yaml: {exc}"]

    if not isinstance(parsed, dict):
        return {}, ["frontmatter-not-mapping"]
    return parsed, []


def _config_path_truthy(root: dict[str, object], dotted_path: str) -> bool:
    """Evaluate dotted config path against mapping-like config data."""
    if not dotted_path:
        return False

    current: object = root
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return False
        current = current.get(part)
    return bool(current)


def _platform_matches(required: list[str]) -> bool:
    """Check if current platform identifier matches required list."""
    platform = sys.platform.lower()
    if platform.startswith("darwin"):
        platform = "darwin"
    elif platform.startswith("win"):
        platform = "win32"
    elif platform.startswith("linux"):
        platform = "linux"
    return platform in required


def load_sources_lock(target: Path) -> SourcesLock:
    """Load the sources lock file from the target project.

    Args:
        target: Root directory of the target project.

    Returns:
        Parsed SourcesLock model.

    Raises:
        FileNotFoundError: If the lock file does not exist.
    """
    lock_path = target / ".ai-engineering" / "state" / "sources.lock.json"
    return read_json_model(lock_path, SourcesLock)


def sync_sources(
    target: Path,
    *,
    offline: bool = False,
) -> SyncResult:
    """Synchronise remote skill sources.

    Fetches content from trusted sources, verifies checksums, and caches
    results locally.  In offline mode, only serves from cache.

    Args:
        target: Root directory of the target project.
        offline: If True, only use cached content.

    Returns:
        SyncResult with details of fetched, cached, and failed sources.
    """
    result = SyncResult()
    lock = load_sources_lock(target)

    if not lock.default_remote_enabled:
        return result

    cache_dir = target / ".ai-engineering" / _CACHE_DIR_NAME
    cache_dir.mkdir(parents=True, exist_ok=True)

    sources_changed = False

    for source in lock.sources:
        if not source.trusted:
            result.untrusted.append(source.url)
            continue

        cache_file = _cache_path(cache_dir, source.url)

        if offline:
            if cache_file.exists():
                result.cached.append(source.url)
            else:
                result.failed.append(source.url)
            continue

        # Check if cache is still fresh
        if _is_cache_fresh(source, cache_file):
            result.cached.append(source.url)
            continue

        # Fetch remote content
        content = _fetch_url(source.url)
        if content is None:
            # Fall back to cache
            if cache_file.exists():
                result.cached.append(source.url)
            else:
                result.failed.append(source.url)
            continue

        # Verify checksum if provided
        if source.checksum and not _verify_checksum(content, source.checksum):
            result.failed.append(source.url)
            continue

        # Write cache
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(content)

        # Update source metadata
        source.cache.last_fetched_at = datetime.now(tz=UTC)
        if not source.checksum:
            source.checksum = _compute_checksum(content)
        sources_changed = True

        result.fetched.append(source.url)

    # Persist updated lock file
    if sources_changed:
        lock_path = target / ".ai-engineering" / "state" / "sources.lock.json"
        write_json_model(lock_path, lock)

    return result


def add_source(
    target: Path,
    url: str,
    *,
    trusted: bool = True,
) -> SourcesLock:
    """Add a remote source to the sources lock file.

    Args:
        target: Root directory of the target project.
        url: URL of the remote source.
        trusted: Whether the source is trusted.

    Returns:
        Updated SourcesLock.

    Raises:
        ValueError: If the source URL already exists.
    """
    lock = load_sources_lock(target)

    if any(s.url == url for s in lock.sources):
        msg = f"Source already exists: {url}"
        raise ValueError(msg)

    lock.sources.append(
        RemoteSource(
            url=url,
            trusted=trusted,
            cache=CacheConfig(),
        )
    )

    lock_path = target / ".ai-engineering" / "state" / "sources.lock.json"
    write_json_model(lock_path, lock)
    return lock


def remove_source(target: Path, url: str) -> SourcesLock:
    """Remove a remote source from the sources lock file.

    Args:
        target: Root directory of the target project.
        url: URL of the remote source to remove.

    Returns:
        Updated SourcesLock.

    Raises:
        ValueError: If the source URL is not found.
    """
    lock = load_sources_lock(target)

    original_len = len(lock.sources)
    lock.sources = [s for s in lock.sources if s.url != url]

    if len(lock.sources) == original_len:
        msg = f"Source not found: {url}"
        raise ValueError(msg)

    lock_path = target / ".ai-engineering" / "state" / "sources.lock.json"
    write_json_model(lock_path, lock)
    return lock


def list_sources(target: Path) -> list[RemoteSource]:
    """List all configured remote sources.

    Args:
        target: Root directory of the target project.

    Returns:
        List of remote sources.
    """
    lock = load_sources_lock(target)
    return lock.sources


def _cache_path(cache_dir: Path, url: str) -> Path:
    """Compute a deterministic cache file path for a URL.

    Args:
        cache_dir: Root cache directory.
        url: Source URL.

    Returns:
        Path to the cached file.
    """
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    return cache_dir / f"{url_hash}.cache"


def _is_cache_fresh(source: RemoteSource, cache_file: Path) -> bool:
    """Check if cached content is still within TTL.

    Args:
        source: Remote source with cache configuration.
        cache_file: Path to the cached file.

    Returns:
        True if cache exists and is within TTL.
    """
    if not cache_file.exists():
        return False

    if source.cache.last_fetched_at is None:
        return False

    now = datetime.now(tz=UTC)
    # Ensure last_fetched_at is timezone-aware
    last_fetched = source.cache.last_fetched_at
    if last_fetched.tzinfo is None:
        last_fetched = last_fetched.replace(tzinfo=UTC)

    age_hours = (now - last_fetched).total_seconds() / 3600
    return age_hours < source.cache.ttl_hours


def _fetch_url(url: str) -> bytes | None:
    """Fetch content from a URL.

    Args:
        url: URL to fetch.

    Returns:
        Response content bytes, or None on failure.
    """
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read()
    except (urllib.error.URLError, OSError, ValueError) as exc:
        _logger.debug("Failed to fetch %s: %s", url, exc)
        return None


def _compute_checksum(content: bytes) -> str:
    """Compute SHA-256 checksum of content.

    Args:
        content: Raw content bytes.

    Returns:
        Hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(content).hexdigest()


def _verify_checksum(content: bytes, expected: str) -> bool:
    """Verify content against expected checksum.

    Args:
        content: Raw content bytes.
        expected: Expected SHA-256 hex digest.

    Returns:
        True if checksum matches.
    """
    return _compute_checksum(content) == expected
