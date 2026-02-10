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
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.models import CacheConfig, RemoteSource, SourcesLock


@dataclass
class SyncResult:
    """Summary of a skill sync operation."""

    fetched: list[str] = field(default_factory=list)
    cached: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    untrusted: list[str] = field(default_factory=list)


_CACHE_DIR_NAME: str = "skills-cache"


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
        source.cache.last_fetched_at = datetime.now(tz=timezone.utc)
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

    lock.sources.append(RemoteSource(
        url=url,
        trusted=trusted,
        cache=CacheConfig(),
    ))

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

    now = datetime.now(tz=timezone.utc)
    # Ensure last_fetched_at is timezone-aware
    last_fetched = source.cache.last_fetched_at
    if last_fetched.tzinfo is None:
        last_fetched = last_fetched.replace(tzinfo=timezone.utc)

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
        with urllib.request.urlopen(url, timeout=30) as response:  # noqa: S310
            return response.read()
    except Exception:  # noqa: BLE001
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
