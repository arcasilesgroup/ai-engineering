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
import shutil
import subprocess
import tomllib
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext


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
