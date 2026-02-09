"""Remote skills lock and cache services."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from ai_engineering.paths import ai_engineering_root, repo_root, state_dir
from ai_engineering.state.io import load_model, write_json
from ai_engineering.state.models import SkillSource, SourcesLock


ALLOWED_SKILL_HOSTS = {"skills.sh", "www.aitmpl.com"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _cache_file_path(cache_dir: Path, url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return cache_dir / f"{digest}.skill"


def _fetch_url(url: str, timeout: int = 15) -> bytes:
    parsed = urlparse(url)
    host = parsed.hostname
    if parsed.scheme != "https" or host is None or host not in ALLOWED_SKILL_HOSTS:
        raise URLError("source url is not an allowlisted https host")
    request = Request(url, method="GET")
    with urlopen(request, timeout=timeout) as response:  # noqa: S310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        return response.read()


def _compute_checksum(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _is_allowlisted(url: str) -> bool:
    host = urlparse(url).hostname
    if host is None:
        return False
    return host in ALLOWED_SKILL_HOSTS


def _sync_single_source(
    source: SkillSource,
    cache_dir: Path,
    *,
    offline: bool,
    fetcher: Callable[[str], bytes],
) -> tuple[SkillSource, dict[str, Any]]:
    if not _is_allowlisted(source.url):
        return source, {
            "url": source.url,
            "status": "allowlist-rejected",
            "cached": False,
            "error": "source host is not allowlisted",
        }

    cache_file = _cache_file_path(cache_dir, source.url)
    if source.signatureMetadata is None:
        return source, {
            "url": source.url,
            "status": "signature-metadata-missing",
            "cached": False,
            "error": "signature metadata scaffold is required",
        }

    if offline:
        if cache_file.exists():
            source.cache.lastFetchedAt = source.cache.lastFetchedAt or _now_iso()
            return source, {"url": source.url, "status": "offline-cache", "cached": True}
        return source, {"url": source.url, "status": "offline-miss", "cached": False}

    try:
        payload = fetcher(source.url)
    except (URLError, TimeoutError, OSError) as exc:
        if cache_file.exists():
            source.cache.lastFetchedAt = source.cache.lastFetchedAt or _now_iso()
            return source, {
                "url": source.url,
                "status": "network-fallback-cache",
                "cached": True,
                "error": str(exc),
            }
        return source, {
            "url": source.url,
            "status": "network-failed",
            "cached": False,
            "error": str(exc),
        }

    cache_file.parent.mkdir(parents=True, exist_ok=True)
    computed_checksum = _compute_checksum(payload)
    if source.checksum is not None and source.checksum != computed_checksum:
        return source, {
            "url": source.url,
            "status": "checksum-mismatch",
            "cached": cache_file.exists(),
            "error": "pinned checksum does not match fetched content",
            "expected": source.checksum,
            "actual": computed_checksum,
        }

    cache_file.write_bytes(payload)
    source.checksum = computed_checksum
    source.cache.lastFetchedAt = _now_iso()
    return source, {
        "url": source.url,
        "status": "synced",
        "cached": True,
        "checksum": source.checksum,
    }


def list_sources() -> dict[str, Any]:
    """Return sources and cache metadata from sources lock."""
    root = repo_root()
    lock = load_model(state_dir(root) / "sources.lock.json", SourcesLock)
    return {
        "schemaVersion": lock.schemaVersion,
        "defaultRemoteEnabled": lock.defaultRemoteEnabled,
        "sources": [source.model_dump(mode="json") for source in lock.sources],
    }


def sync_sources(*, offline: bool = False) -> dict[str, Any]:
    """Sync remote sources and update lock file with cache metadata."""
    root = repo_root()
    lock_path = state_dir(root) / "sources.lock.json"
    lock = load_model(lock_path, SourcesLock)

    cache_dir = ai_engineering_root(root) / ".cache" / "skills"
    results: list[dict[str, Any]] = []
    updated_sources: list[SkillSource] = []
    for source in lock.sources:
        updated, result = _sync_single_source(
            source, cache_dir, offline=offline, fetcher=_fetch_url
        )
        updated_sources.append(updated)
        results.append(result)

    lock.sources = updated_sources
    lock.generatedAt = _now_iso()
    write_json(lock_path, lock.model_dump(mode="json"))

    summary = {
        "synced": len([item for item in results if item["status"] == "synced"]),
        "fallback": len([item for item in results if item["status"] == "network-fallback-cache"]),
        "offlineCache": len([item for item in results if item["status"] == "offline-cache"]),
        "failed": len(
            [
                item
                for item in results
                if item["status"]
                in {
                    "network-failed",
                    "offline-miss",
                    "allowlist-rejected",
                    "checksum-mismatch",
                    "signature-metadata-missing",
                }
            ]
        ),
    }
    return {"offline": offline, "summary": summary, "results": results}


def export_sync_report_json(path: Path, payload: dict[str, Any]) -> None:
    """Write sync report payload for troubleshooting and audit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
