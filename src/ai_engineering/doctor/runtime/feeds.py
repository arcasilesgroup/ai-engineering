"""Doctor runtime check: feeds -- validates enterprise artifact feed config.

Inspects ``pyproject.toml`` for UV index entries and checks for common
supply-chain misconfigurations:

- Mixed private + PyPI sources (dependency confusion risk)
- PyPI references leaked into ``uv.lock`` when only private feeds configured
- Stale lock file compared to ``pyproject.toml``
- Missing keyring for credential-backed feeds (non-CI only)
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext


@dataclass(frozen=True)
class FeedValidationResult:
    """Outcome of feed preflight validation before install or repair work."""

    status: str
    feeds: list[str]
    message: str


@dataclass(frozen=True)
class FeedProbeResult:
    """Reachability/auth outcome for a configured feed probe."""

    reachable: bool
    auth_required: bool = False


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all feed-related checks."""
    pyproject_path = ctx.target / "pyproject.toml"
    if not pyproject_path.is_file():
        return []

    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return []

    indexes = _extract_uv_indexes(data)
    if not indexes:
        return []

    private_feeds = [idx for idx in indexes if not _is_pypi(idx.get("url", ""))]
    pypi_feeds = [idx for idx in indexes if _is_pypi(idx.get("url", ""))]

    if not private_feeds:
        return []

    results: list[CheckResult] = []

    # Check: mixed sources
    if pypi_feeds:
        results.append(
            CheckResult(
                name="feed-mixed-sources",
                status=CheckStatus.WARN,
                message="Both private and PyPI feeds configured; dependency confusion risk",
            )
        )
        return results

    # Check: lock file leaks (only when private-only)
    results.append(_check_lock_leak(ctx.target))

    # Check: lock freshness
    results.append(_check_lock_freshness(ctx.target))

    # Check: keyring availability (skip in CI)
    keyring_result = _check_keyring()
    if keyring_result is not None:
        results.append(keyring_result)

    return results


def validate_feeds_for_install(ctx: DoctorContext, mode: str) -> FeedValidationResult:
    """Validate private feeds before dependency resolution or repair begins."""
    pyproject_path = ctx.target / "pyproject.toml"
    configured_feeds: set[str] = set()

    if pyproject_path.is_file():
        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError):
            data = {}
        indexes = _extract_uv_indexes(data)
        configured_feeds.update(
            idx.get("url", "")
            for idx in indexes
            if idx.get("url") and not _is_pypi(idx.get("url", ""))
        )

    configured_feeds.update(detect_feeds_from_lockfile(ctx.target / "uv.lock"))
    feeds: list[str] = [feed for feed in sorted(configured_feeds) if feed]
    if not feeds:
        return FeedValidationResult(status="ok", feeds=[], message="No private feeds detected")

    unreachable: list[str] = []
    auth_required: list[str] = []
    for feed in feeds:
        probe = _probe_feed(feed)
        if probe.reachable:
            continue
        if probe.auth_required:
            auth_required.append(feed)
            continue
        unreachable.append(feed)

    if unreachable:
        return FeedValidationResult(
            status="blocked",
            feeds=unreachable,
            message=f"Blocked {mode}: private feed preflight failed before dependency resolution.",
        )

    if auth_required:
        return FeedValidationResult(
            status="ok",
            feeds=feeds,
            message=(
                f"Validated {len(feeds)} private feed(s) before {mode}; "
                f"{len(auth_required)} require package-manager credentials."
            ),
        )

    return FeedValidationResult(
        status="ok",
        feeds=feeds,
        message=f"Validated {len(feeds)} private feed(s) before {mode}.",
    )


def detect_feeds_from_lockfile(lock_path: Path) -> set[str]:
    """Extract private registry URLs referenced in ``uv.lock``."""
    if not lock_path.is_file():
        return set()

    try:
        content = lock_path.read_text(encoding="utf-8")
    except OSError:
        return set()

    matches = re.findall(r'registry\s*=\s*"([^"]+)"', content)
    return {match for match in matches if not _is_pypi(match)}


def _extract_uv_indexes(data: dict) -> list[dict]:
    """Extract ``tool.uv.index`` entries from parsed pyproject.toml."""
    tool = data.get("tool", {})
    uv = tool.get("uv", {})
    return list(uv.get("index", []))


def _is_pypi(url: str) -> bool:
    """Return True if the URL points to PyPI."""
    return "pypi.org" in url


def _check_lock_leak(target: Path) -> CheckResult:
    """FAIL if uv.lock contains PyPI references despite private-only config."""
    lock_path = target / "uv.lock"
    if not lock_path.is_file():
        return CheckResult(
            name="feed-lock-leak",
            status=CheckStatus.OK,
            message="No uv.lock to check",
        )
    try:
        content = lock_path.read_text(encoding="utf-8")
    except OSError:
        return CheckResult(
            name="feed-lock-leak",
            status=CheckStatus.OK,
            message="Could not read uv.lock",
        )
    if "pypi.org/simple" in content:
        return CheckResult(
            name="feed-lock-leak",
            status=CheckStatus.FAIL,
            message="uv.lock contains pypi.org/simple references despite private-only feed config",
        )
    return CheckResult(
        name="feed-lock-leak",
        status=CheckStatus.OK,
        message="No PyPI leak in uv.lock",
    )


def _check_lock_freshness(target: Path) -> CheckResult:
    """WARN if uv.lock is missing or older than pyproject.toml."""
    lock_path = target / "uv.lock"
    pyproject_path = target / "pyproject.toml"

    if not lock_path.is_file():
        return CheckResult(
            name="feed-lock-freshness",
            status=CheckStatus.WARN,
            message="uv.lock missing; run 'uv lock' to generate",
        )

    try:
        lock_mtime = lock_path.stat().st_mtime
        pyproject_mtime = pyproject_path.stat().st_mtime
    except OSError:
        return CheckResult(
            name="feed-lock-freshness",
            status=CheckStatus.WARN,
            message="Could not compare file timestamps",
        )

    if lock_mtime < pyproject_mtime:
        return CheckResult(
            name="feed-lock-freshness",
            status=CheckStatus.WARN,
            message="uv.lock is older than pyproject.toml; run 'uv lock' to refresh",
        )

    return CheckResult(
        name="feed-lock-freshness",
        status=CheckStatus.OK,
        message="uv.lock is up to date",
    )


def _check_keyring() -> CheckResult | None:
    """Check keyring availability for credential-backed feeds.

    Returns None when running in CI (check is irrelevant there).
    """
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return None

    if not shutil.which("keyring"):
        return CheckResult(
            name="feed-keyring",
            status=CheckStatus.WARN,
            message="keyring binary not found; install 'keyring' for credential-backed feeds",
        )

    try:
        result = subprocess.run(
            ["keyring", "--list-backends"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return CheckResult(
            name="feed-keyring",
            status=CheckStatus.FAIL,
            message="keyring binary found but failed to execute",
        )

    if result.returncode != 0:
        return CheckResult(
            name="feed-keyring",
            status=CheckStatus.FAIL,
            message="keyring returned an error; check keyring configuration",
        )

    return CheckResult(
        name="feed-keyring",
        status=CheckStatus.OK,
        message="keyring available and functional",
    )


def _probe_feed(feed_url: str) -> FeedProbeResult:
    """Best-effort reachability probe for a configured feed."""
    request = Request(feed_url, method="HEAD")
    try:
        with urlopen(request, timeout=5) as response:
            return FeedProbeResult(reachable=200 <= response.status < 400)
    except HTTPError as exc:
        if exc.code in (401, 403):
            return FeedProbeResult(reachable=False, auth_required=True)
        if exc.code == 405:
            try:
                with urlopen(Request(feed_url, method="GET"), timeout=5) as response:
                    return FeedProbeResult(reachable=200 <= response.status < 400)
            except (HTTPError, URLError, OSError):
                return FeedProbeResult(reachable=False)
        return FeedProbeResult(reachable=False)
    except (URLError, OSError):
        return FeedProbeResult(reachable=False)
